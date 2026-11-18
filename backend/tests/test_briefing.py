"""
Briefing do mês por IA: fatos, guardas, cache, falha fechada e rotas.

Nenhum teste chama modelo real: o redator é sempre falso.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, get_supabase
from app.ia import briefing as mod
from app.ia.briefing import Redacao, gerar_briefing, montar_fatos, validar_redacao
from app.ia.provedor import ProvedorIndisponivel
from app.main import app
from app.models.analise import AnaliseMes, Briefing, Comparativo, EjDestaque, MotivoDestaque, ResumoAnalise
from app.routers.analise import get_redator


def _analise() -> AnaliseMes:
    alerta = EjDestaque(id_ej=1, nome="Alfa Consultoria", gravidade="alta",
                        motivos=[MotivoDestaque(codigo="sem_vendas_seguidas", descricao="Sem vendas há 3 meses seguidos")])
    ascensao = EjDestaque(id_ej=2, nome="Beta Jr",
                          motivos=[MotivoDestaque(codigo="subiu_cluster", descricao="Subiu do cluster 2 para o 3")])
    return AnaliseMes(
        ano=2026, mes=10, mes_anterior=9,
        resumo=ResumoAnalise(
            total_ejs=22,
            fora_do_zero=Comparativo(atual=14, anterior=12),
            no_verde=Comparativo(atual=8, anterior=8),
            ritmo_significativo=Comparativo(atual=7, anterior=5),
            faturamento_acumulado=Comparativo(atual=812000.0, anterior=700000.0),
            meta_faturamento_total=1140000.0, percentual_meta_rede=71.2,
        ),
        alertas=[alerta], ascensao=[ascensao],
        briefing=Briefing(frases=["Resumo fixo."], gerado_por_ia=False),
    )


NOMES = ["Alfa Consultoria", "Beta Jr"]
BOAS = [
    "Em outubro de 2026, 14 das 22 EJs estão fora do zero, variação de +2 em relação a setembro.",
    "O faturamento acumulado da federação é R$ 812.000,00, 71,2% da soma das metas anuais, abaixo dos 83% esperados.",
    "1 EJ está em alerta, sem vendas há 3 meses ou mais, e 1 está em ascensão.",
]


class RedatorFalso:
    def __init__(self, frases=None, erro=None, configurado=True):
        self.frases, self.erro, self._configurado, self.chamadas = frases or BOAS, erro, configurado, 0

    @property
    def configurado(self):
        return self._configurado

    def redigir(self, fatos):
        self.chamadas += 1
        if self.erro:
            raise self.erro
        return Redacao(list(self.frases), "modelo-falso", 100, 50)


class SbFalso:
    """Só o RPC da reserva; as leituras da análise não passam por aqui nestes testes."""

    def __init__(self, permitido=True):
        self.permitido, self.reservas = permitido, 0

    def rpc(self, nome):
        assert nome == "reservar_consulta_ia"
        self.reservas += 1
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=self.permitido))


@pytest.fixture(autouse=True)
def _cache_limpo():
    mod.cache.limpar()
    yield
    mod.cache.limpar()


def _gerar(redator, sb=None, analise=None, forcar=False):
    return gerar_briefing(sb or SbFalso(), redator, analise or _analise(), federacao_id=12,
                          federacao_nome="FEJEPE", nomes_ejs=NOMES, forcar=forcar)


# ── Fatos ────────────────────────────────────────────────────


def test_fatos_formatados_e_sem_nome_de_ej():
    fatos = montar_fatos(_analise(), "FEJEPE")
    assert fatos["faturamento_acumulado_da_federacao"] == "R$ 812.000,00"
    assert fatos["percentual_da_soma_das_metas_anuais"] == "71,2%"
    assert fatos["ejs_fora_do_zero"] == {"atual": "14", "em setembro": "12", "variacao": "+2"}
    assert fatos["percentual_esperado_ate_o_mes_para_estar_no_verde"] == "83%"
    texto = str(fatos)
    assert "Alfa" not in texto and "Beta" not in texto and "id_ej" not in texto


# ── Guardas ──────────────────────────────────────────────────


def test_texto_fiel_aos_fatos_e_aceito():
    assert validar_redacao(BOAS, montar_fatos(_analise(), "FEJEPE"), NOMES) is None


@pytest.mark.parametrize("frase, motivo", [
    ("O faturamento chegou a R$ 812 mil no ano.", "numero_fora_dos_fatos"),
    ("O faturamento cresceu 16% em relação a setembro.", "numero_fora_dos_fatos"),
    ("Há risco de 3 EJs ficarem sem vendas.", "vocabulario_proibido"),
    ("A federação vai bater a meta em dezembro.", "vocabulario_proibido"),
    ("A tendência é de alta para 14 EJs.", "vocabulario_proibido"),
    ("A Alfa Consultoria está sem vendas há 3 meses.", "nome_de_ej"),
    ("1 EJ está em alerta, a maioria sem vendas há 3 meses ou mais.", "vocabulario_proibido"),
    ("Veja **14 EJs** fora do zero.", "marcacao"),
    ("Mais detalhes em https://exemplo.com.", "marcacao"),
])
def test_guardas_recusam(frase, motivo):
    assert validar_redacao([BOAS[0], frase], montar_fatos(_analise(), "FEJEPE"), NOMES) == motivo


def test_guarda_quantidade_de_frases():
    fatos = montar_fatos(_analise(), "FEJEPE")
    assert validar_redacao([BOAS[0]], fatos, NOMES) == "quantidade_de_frases"
    assert validar_redacao(BOAS * 3, fatos, NOMES) == "quantidade_de_frases"


# ── Orquestração ─────────────────────────────────────────────


def test_texto_aceito_vira_briefing_por_ia_e_fica_em_cache():
    redator, sb = RedatorFalso(), SbFalso()
    b1 = _gerar(redator, sb)
    b2 = _gerar(redator, sb)
    assert b1.gerado_por_ia and b1.frases == BOAS and b1.modelo == "modelo-falso"
    assert b2 == b1
    assert redator.chamadas == 1 and sb.reservas == 1


def test_texto_recusado_cai_no_resumo_fixo_e_nao_insiste():
    redator = RedatorFalso(frases=[BOAS[0], "Há risco de queda em novembro."])
    assert _gerar(redator).frases == ["Resumo fixo."]
    _gerar(redator)
    assert redator.chamadas == 1  # recusa guardada por TTL_RECUSA_SEGUNDOS


def test_provedor_indisponivel_cai_no_resumo_fixo():
    b = _gerar(RedatorFalso(erro=ProvedorIndisponivel("fora")))
    assert not b.gerado_por_ia and b.frases == ["Resumo fixo."]


def test_sem_configuracao_nao_reserva_nem_chama():
    redator, sb = RedatorFalso(configurado=False), SbFalso()
    assert not _gerar(redator, sb).gerado_por_ia
    assert redator.chamadas == 0 and sb.reservas == 0


def test_limite_por_minuto_nao_chama_modelo_nem_guarda_recusa():
    redator = RedatorFalso()
    assert not _gerar(redator, SbFalso(permitido=False)).gerado_por_ia
    assert redator.chamadas == 0
    assert _gerar(redator, SbFalso(permitido=True)).gerado_por_ia  # tenta de novo no acesso seguinte


def test_fatos_novos_geram_texto_novo():
    redator = RedatorFalso()
    _gerar(redator)
    outra = _analise()
    outra.resumo.fora_do_zero = Comparativo(atual=15, anterior=12)
    _gerar(redator, analise=outra)
    assert redator.chamadas == 2


def test_forcar_regenera():
    redator = RedatorFalso()
    _gerar(redator)
    _gerar(redator, forcar=True)
    assert redator.chamadas == 2


def test_sem_mes_devolve_fixo_sem_chamar():
    redator = RedatorFalso()
    b = _gerar(redator, analise=AnaliseMes(ano=2026))
    assert not b.gerado_por_ia and redator.chamadas == 0


# ── Rotas ────────────────────────────────────────────────────


class _Resp:
    def __init__(self, data):
        self.data, self.count = data, len(data)


class _Consulta:
    def __init__(self, dados):
        self.dados = dados

    def __getattr__(self, nome):
        return lambda *a, **k: self

    def execute(self):
        return _Resp(self.dados)


class _SbRota(SbFalso):
    TABELAS = {
        "empresa_junior": [{"id": 1, "id_ej": 1, "nome": "Alfa Consultoria", "status": "ativa"}],
        # Vendeu em julho e parou: entra no A1 (sem vendas há 3 meses) em outubro.
        "monitoramento": [{"id_ej": 1, "ano": 2026, "mes": m, "faturamento_mes": 500 if m == 7 else 0,
                           "faturamento_acumulado": 500} for m in (7, 8, 9, 10)],
        "federacao": [{"nome": "FEJEPE"}],
    }

    def table(self, nome):
        return _Consulta(self.TABELAS.get(nome, []))


def _usuario(papel="membro"):
    return SimpleNamespace(id="u", app_metadata={"papel": papel, "federacao_id": 12})


@pytest.fixture
def cliente():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_rota_briefing_devolve_texto_aceito(cliente):
    frases = ["Em outubro de 2026, 1 das 1 EJs estão fora do zero.",
              "1 EJ está em alerta, sem vendas há 3 meses ou mais."]
    app.dependency_overrides[get_current_user] = lambda: _usuario()
    app.dependency_overrides[get_supabase] = lambda: _SbRota()
    app.dependency_overrides[get_redator] = lambda: RedatorFalso(frases=frases)
    r = cliente.get("/api/v1/analise/briefing?ano=2026&mes=10")
    assert r.status_code == 200, r.text
    assert r.json()["gerado_por_ia"] is True and r.json()["frases"] == frases


def test_rota_briefing_recusa_nome_de_ej_da_federacao(cliente):
    app.dependency_overrides[get_current_user] = lambda: _usuario()
    app.dependency_overrides[get_supabase] = lambda: _SbRota()
    app.dependency_overrides[get_redator] = lambda: RedatorFalso(
        frases=["A Alfa Consultoria está sem vendas.", "1 EJ está em alerta."])
    corpo = cliente.get("/api/v1/analise/briefing?ano=2026&mes=10").json()
    assert corpo["gerado_por_ia"] is False


def test_regenerar_exige_admin(cliente):
    app.dependency_overrides[get_current_user] = lambda: _usuario("membro")
    app.dependency_overrides[get_supabase] = lambda: _SbRota()
    app.dependency_overrides[get_redator] = lambda: RedatorFalso()
    assert cliente.post("/api/v1/analise/briefing/regenerar?ano=2026").status_code == 403


# ── Calibração de 17/11: direção da comparação e empate ─────


def test_fatos_trazem_direcao_e_motivo_mais_comum():
    fatos = montar_fatos(_analise(), "FEJEPE")
    assert fatos["faturamento_frente_ao_esperado"] == "abaixo do esperado"  # 71,2% vs 83%
    assert fatos["motivo_mais_comum_de_alerta"] == "sem vendas há 3 meses ou mais (1)"


def test_empate_no_motivo_mais_comum_vem_escrito():
    a = _analise()
    a.alertas.append(EjDestaque(id_ej=3, nome="Gama", gravidade="alta",
                                motivos=[MotivoDestaque(codigo="caiu_cluster", descricao="x")]))
    assert montar_fatos(a, None)["motivo_mais_comum_de_alerta"].startswith("empate entre ")


def test_guarda_recusa_comparacao_invertida():
    fatos = montar_fatos(_analise(), "FEJEPE")
    invertida = "O faturamento chegou a 71,2% da soma das metas anuais, acima dos 83% esperados."
    correta = "O faturamento chegou a 71,2% da soma das metas anuais, abaixo dos 83% esperados."
    assert validar_redacao([BOAS[0], invertida], fatos, NOMES) == "comparacao_invertida"
    assert validar_redacao([BOAS[0], correta], fatos, NOMES) is None
