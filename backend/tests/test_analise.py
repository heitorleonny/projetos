"""
Análise do mês: regras A1–A6 (alerta), S1–S6 (ascensão), resumo e rota.

As regras são testadas na função pura `classificar_ejs`, com EJs sintéticas.
A rota é testada com um Supabase falso, só para conferir contrato e tenant.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, get_supabase
from app.main import app
from app.models.empresa import EmpresaComIndicadores, Ritmo
from app.services.analise_service import (
    EntradaEj,
    briefing_fixo,
    classificar_ejs,
    limiar_verde,
    montar_resumo,
    no_verde,
)

# ── Fábrica de EJs sintéticas ────────────────────────────────


def _ej(id_ej=1, nome="EJ Teste", **kw) -> EmpresaComIndicadores:
    base = dict(id=id_ej, id_ej=id_ej, nome=nome, tem_dados_no_ano=True)
    base.update(kw)
    return EmpresaComIndicadores(**base)


def _entrada(fat: dict[int, float], *, atual=None, anterior=None, csat=None, id_ej=1, nome="EJ Teste"):
    return EntradaEj(
        atual=atual or _ej(id_ej, nome),
        anterior=anterior,
        faturamento_por_mes=fat,
        csat_por_mes=csat or {},
    )


def _codigos(destaques, id_ej=1) -> set[str]:
    for d in destaques:
        if d.id_ej == id_ej:
            return {m.codigo for m in d.motivos}
    return set()


# ── Verde ────────────────────────────────────────────────────


def test_limiar_verde_segue_regra_mes_sobre_12():
    assert limiar_verde(9) == pytest.approx(75.0)
    assert no_verde(75.0, 9) and not no_verde(74.99, 9)
    assert not no_verde(None, 9)


# ── A1: sem vendas seguidas ─────────────────────────────────


def test_a1_tres_meses_sem_venda_dispara():
    alertas, _ = classificar_ejs([_entrada({7: 100, 8: 0, 9: 0, 10: 0})], 10)
    assert "sem_vendas_seguidas" in _codigos(alertas)
    assert alertas[0].gravidade.value == "alta"
    assert "3 meses" in alertas[0].motivos[0].descricao


def test_a1_dois_meses_nao_dispara():
    alertas, _ = classificar_ejs([_entrada({8: 100, 9: 0, 10: 0})], 10)
    assert "sem_vendas_seguidas" not in _codigos(alertas)


def test_a1_nao_marca_quem_nunca_vendeu_no_ano():
    # Fica no número "fora do zero" do resumo, não no alerta.
    alertas, _ = classificar_ejs([_entrada({8: 0, 9: 0, 10: 0})], 10)
    assert "sem_vendas_seguidas" not in _codigos(alertas)


def test_a1_mes_sem_linha_conta_como_sem_venda():
    # Linha em outubro com zero; agosto e setembro sem linha nenhuma.
    alertas, _ = classificar_ejs([_entrada({7: 50, 10: 0})], 10)
    assert "sem_vendas_seguidas" in _codigos(alertas)


# ── A2 / S1: cluster no Cluster Track ───────────────────────


def test_a2_caiu_de_cluster_no_tracking():
    e = _entrada({9: 10, 10: 10}, atual=_ej(tracking_cluster_efetivo=2),
                 anterior=_ej(tracking_cluster_efetivo=3))
    alertas, ascensao = classificar_ejs([e], 10)
    assert "caiu_cluster" in _codigos(alertas)
    assert "subiu_cluster" not in _codigos(ascensao)


def test_s1_subiu_de_cluster_no_tracking():
    e = _entrada({9: 10, 10: 10}, atual=_ej(tracking_cluster_efetivo=3),
                 anterior=_ej(tracking_cluster_efetivo=2))
    _, ascensao = classificar_ejs([e], 10)
    assert "subiu_cluster" in _codigos(ascensao)
    assert "do cluster 2 para o 3" in ascensao[0].motivos[0].descricao


def test_cluster_sem_dados_no_mes_anterior_nao_compara():
    e = _entrada({10: 10}, atual=_ej(tracking_cluster_efetivo=3),
                 anterior=_ej(tracking_cluster_efetivo=1, tem_dados_no_ano=False))
    alertas, ascensao = classificar_ejs([e], 10)
    assert "subiu_cluster" not in _codigos(ascensao)
    assert "caiu_cluster" not in _codigos(alertas)


# ── A3 / S2: verde ──────────────────────────────────────────


def test_a3_saiu_do_verde():
    # Setembro: 75% esperado, tinha 76%. Outubro: 83,3% esperado, tem 80%.
    e = _entrada({9: 10, 10: 10}, atual=_ej(percentual_meta=80.0), anterior=_ej(percentual_meta=76.0))
    alertas, _ = classificar_ejs([e], 10)
    assert "saiu_do_verde" in _codigos(alertas)


def test_s2_entrou_no_verde():
    e = _entrada({9: 10, 10: 10}, atual=_ej(percentual_meta=90.0), anterior=_ej(percentual_meta=70.0))
    _, ascensao = classificar_ejs([e], 10)
    assert "entrou_no_verde" in _codigos(ascensao)


def test_janeiro_nao_compara_verde():
    e = _entrada({1: 10}, atual=_ej(percentual_meta=1.0), anterior=None)
    alertas, ascensao = classificar_ejs([e], 1)
    assert "saiu_do_verde" not in _codigos(alertas)
    assert "entrou_no_verde" not in _codigos(ascensao)


# ── A4: queda de faturamento por trimestre móvel ────────────


def test_a4_trimestre_com_queda_de_exatamente_50_por_cento_dispara():
    # Últimos 3 (ago–out) = 150; 3 anteriores (mai–jul) = 300.
    fat = {5: 100, 6: 100, 7: 100, 8: 50, 9: 50, 10: 50}
    alertas, _ = classificar_ejs([_entrada(fat)], 10)
    assert "queda_faturamento" in _codigos(alertas)
    assert "últimos 3 meses 50%" in alertas[0].motivos[0].descricao


def test_a4_queda_menor_nao_dispara():
    fat = {5: 100, 6: 100, 7: 100, 8: 51, 9: 50, 10: 50}
    alertas, _ = classificar_ejs([_entrada(fat)], 10)
    assert "queda_faturamento" not in _codigos(alertas)


def test_a4_mes_isolado_sem_venda_nao_dispara():
    # Vendas em pulsos: um mês zerado depois de uma boa venda não é queda do trimestre.
    fat = {5: 0, 6: 300, 7: 0, 8: 0, 9: 300, 10: 0}
    alertas, _ = classificar_ejs([_entrada(fat)], 10)
    assert "queda_faturamento" not in _codigos(alertas)


def test_a4_sem_seis_meses_nao_dispara():
    alertas, _ = classificar_ejs([_entrada({1: 100, 2: 100, 3: 100, 4: 0, 5: 0})], 5)
    assert "queda_faturamento" not in _codigos(alertas)


# ── A5 retirada ─────────────────────────────────────────────


def test_csat_abaixo_da_meta_nao_gera_alerta():
    e = _entrada({10: 10}, atual=_ej(meta_csat=4.5), csat={10: 4.0})
    alertas, _ = classificar_ejs([e], 10)
    assert alertas == []


# ── A6: sem reporte ─────────────────────────────────────────


def test_a6_ej_ativa_sem_linha_no_mes_so_recebe_sem_reporte():
    # Mesmo com dados ruins de meses passados, sem linha no mês só cabe A6.
    e = _entrada({6: 0, 7: 0, 8: 0, 9: 0}, atual=_ej(status="ativa", tracking_cluster_efetivo=1),
                 anterior=_ej(tracking_cluster_efetivo=3))
    alertas, ascensao = classificar_ejs([e], 10)
    assert _codigos(alertas) == {"sem_reporte"}
    assert ascensao == []


def test_a6_ej_inativa_nao_entra():
    alertas, _ = classificar_ejs([_entrada({}, atual=_ej(status="Inativa"))], 10)
    assert alertas == []


# ── S3, S4, S6 ──────────────────────────────────────────────


def test_s3_ritmo_significativo():
    _, ascensao = classificar_ejs([_entrada({10: 10}, atual=_ej(ritmo=Ritmo.significativo))], 10)
    assert "ritmo_significativo" in _codigos(ascensao)


def test_s4_bateu_meta_so_no_mes_em_que_passou():
    passou = _entrada({10: 10}, atual=_ej(percentual_meta=101.0), anterior=_ej(percentual_meta=95.0))
    ja_tinha = _entrada({10: 10}, id_ej=2, atual=_ej(2, percentual_meta=120.0),
                        anterior=_ej(2, percentual_meta=110.0))
    _, ascensao = classificar_ejs([passou, ja_tinha], 10)
    assert "bateu_meta" in _codigos(ascensao, 1)
    assert "bateu_meta" not in _codigos(ascensao, 2)


def test_s6_primeira_venda_do_ano():
    e = _entrada({9: 0, 10: 500}, atual=_ej(faturamento_acumulado=500.0),
                 anterior=_ej(faturamento_acumulado=0.0))
    _, ascensao = classificar_ejs([e], 10)
    assert "primeira_venda" in _codigos(ascensao)


# ── S5: maiores altas ───────────────────────────────────────


def test_s5_top_5_maiores_altas_com_mes_anterior_positivo():
    entradas = [_entrada({9: 100, 10: 100 + 10 * i}, id_ej=i, atual=_ej(i, f"EJ {i}")) for i in range(1, 8)]
    # Mês anterior zerado não entra (crescimento indefinido).
    entradas.append(_entrada({9: 0, 10: 9999}, id_ej=99, atual=_ej(99, "EJ Zero")))
    _, ascensao = classificar_ejs(entradas, 10)
    com_s5 = {d.id_ej for d in ascensao if any(m.codigo == "maior_crescimento" for m in d.motivos)}
    assert com_s5 == {3, 4, 5, 6, 7}


# ── Ordenação e EJ nas duas listas ──────────────────────────


def test_ej_pode_estar_nas_duas_listas():
    # Saiu do verde (alerta) e subiu no Cluster Track (ascensão) no mesmo mês.
    e = _entrada({9: 10, 10: 10}, atual=_ej(tracking_cluster_efetivo=3, percentual_meta=80.0),
                 anterior=_ej(tracking_cluster_efetivo=2, percentual_meta=76.0))
    alertas, ascensao = classificar_ejs([e], 10)
    assert _codigos(alertas) == {"saiu_do_verde"}
    assert "subiu_cluster" in _codigos(ascensao)


def test_alertas_ordenados_por_gravidade():
    media = _entrada({9: 10, 10: 10}, id_ej=1, nome="A", atual=_ej(1, "A", percentual_meta=80.0),
                     anterior=_ej(1, "A", percentual_meta=76.0))
    alta = _entrada({7: 50, 8: 0, 9: 0, 10: 0}, id_ej=2, nome="B", atual=_ej(2, "B"))
    alertas, _ = classificar_ejs([media, alta], 10)
    assert [d.id_ej for d in alertas] == [2, 1]


# ── Resumo e briefing fixo ──────────────────────────────────


def test_resumo_compara_com_mes_anterior():
    entradas = [
        _entrada({10: 10}, id_ej=1, atual=_ej(1, faturamento_acumulado=100.0, meta_faturamento=100.0, percentual_meta=100.0),
                 anterior=_ej(1, faturamento_acumulado=90.0, percentual_meta=90.0)),
        _entrada({10: 0}, id_ej=2, atual=_ej(2, faturamento_acumulado=0.0, meta_faturamento=100.0),
                 anterior=_ej(2, faturamento_acumulado=0.0)),
    ]
    r = montar_resumo(entradas, 10)
    assert r.total_ejs == 2
    assert (r.fora_do_zero.atual, r.fora_do_zero.anterior) == (1, 1)
    assert r.faturamento_acumulado.anterior == 90.0
    assert r.percentual_meta_rede == 50.0
    assert r.no_verde.atual == 1

    b = briefing_fixo(r, 10, n_alertas=1, n_ascensao=0)
    assert not b.gerado_por_ia
    assert b.frases[0].startswith("Em outubro, 1 das 2 EJs estão fora do zero")
    assert "R$ 100,00" in b.frases[1]


# ── Mês padrão: último mês fechado ─────────────────────────


@pytest.fixture
def hoje_17_nov(monkeypatch):
    from datetime import date
    from app.services import analise_service
    monkeypatch.setattr(analise_service, "_hoje", lambda: date(2026, 11, 17))


def test_mes_padrao_pula_o_mes_em_andamento(hoje_17_nov):
    from app.services.analise_service import escolher_mes
    assert escolher_mes(list(range(1, 12)), 2026, None) == (10, False)


def test_mes_corrente_pedido_vem_marcado_parcial(hoje_17_nov):
    from app.services.analise_service import escolher_mes
    assert escolher_mes(list(range(1, 12)), 2026, 11) == (11, True)
    assert escolher_mes(list(range(1, 12)), 2026, 9) == (9, False)


def test_ano_passado_usa_o_ultimo_mes_com_dados(hoje_17_nov):
    from app.services.analise_service import escolher_mes
    assert escolher_mes(list(range(1, 13)), 2025, None) == (12, False)


def test_so_mes_corrente_com_dados_mostra_parcial(hoje_17_nov):
    from app.services.analise_service import escolher_mes
    assert escolher_mes([11], 2026, None) == (11, True)
    assert escolher_mes([], 2026, None) == (None, False)


def test_briefing_fixo_avisa_mes_parcial():
    from app.models.analise import ResumoAnalise
    b = briefing_fixo(ResumoAnalise(total_ejs=1), 11, 0, 0, parcial=True)
    assert b.frases[0] == "Novembro ainda está em andamento: os dados são parciais."


# ── Rota ────────────────────────────────────────────────────


class _Resposta:
    def __init__(self, data):
        self.data, self.count = data, len(data)


class _Consulta:
    def __init__(self, tabela, dados, registro):
        self.tabela, self.dados, self.registro = tabela, dados, registro

    def select(self, *a, **k):
        return self

    def eq(self, coluna, valor):
        self.registro.append((self.tabela, coluna, valor))
        return self

    def in_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def range(self, *a, **k):
        return self

    def execute(self):
        return _Resposta(self.dados)


class _Supabase:
    def __init__(self, tabelas):
        self.tabelas, self.registro = tabelas, []

    def table(self, nome):
        return _Consulta(nome, self.tabelas.get(nome, []), self.registro)


def _usuario(federacao_id):
    meta = {"papel": "membro"}
    if federacao_id is not None:
        meta["federacao_id"] = federacao_id
    return SimpleNamespace(id="u", app_metadata=meta)


@pytest.fixture
def cliente():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_rota_devolve_analise_e_filtra_tenant(cliente, hoje_17_nov):
    sb = _Supabase({
        "empresa_junior": [{"id": 1, "id_ej": 1, "nome": "EJ Um", "status": "ativa"}],
        "monitoramento": [
            {"id_ej": 1, "ano": 2026, "mes": 7, "faturamento_mes": 500, "faturamento_acumulado": 500},
            {"id_ej": 1, "ano": 2026, "mes": 8, "faturamento_mes": 0, "faturamento_acumulado": 500},
            {"id_ej": 1, "ano": 2026, "mes": 9, "faturamento_mes": 0, "faturamento_acumulado": 500},
            {"id_ej": 1, "ano": 2026, "mes": 10, "faturamento_mes": 0, "faturamento_acumulado": 500},
            {"id_ej": 1, "ano": 2026, "mes": 11, "faturamento_mes": 0, "faturamento_acumulado": 500},
        ],
    })
    app.dependency_overrides[get_current_user] = lambda: _usuario(12)
    app.dependency_overrides[get_supabase] = lambda: sb
    r = cliente.get("/api/v1/analise?ano=2026")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["mes"] == 10 and corpo["mes_anterior"] == 9 and corpo["mes_parcial"] is False
    assert corpo["alertas"][0]["motivos"][0]["codigo"] == "sem_vendas_seguidas"
    assert ("empresa_junior", "federacao_id", 12) in sb.registro


def test_rota_exige_tenant(cliente):
    app.dependency_overrides[get_current_user] = lambda: _usuario(None)
    app.dependency_overrides[get_supabase] = lambda: _Supabase({})
    assert cliente.get("/api/v1/analise").status_code == 403


def test_rota_sem_dados_no_ano(cliente):
    app.dependency_overrides[get_current_user] = lambda: _usuario(12)
    app.dependency_overrides[get_supabase] = lambda: _Supabase(
        {"empresa_junior": [{"id": 1, "id_ej": 1, "nome": "EJ Um"}]})
    corpo = cliente.get("/api/v1/analise").json()
    assert corpo["mes"] is None and corpo["alertas"] == []


def test_a4_nao_repete_o_a1():
    # Vendeu bem de mai a jul e zerou de ago a out: um motivo só, "sem vendas".
    fat = {5: 100, 6: 100, 7: 100, 8: 0, 9: 0, 10: 0}
    alertas, _ = classificar_ejs([_entrada(fat)], 10)
    assert _codigos(alertas) == {"sem_vendas_seguidas"}
