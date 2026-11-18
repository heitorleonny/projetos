"""Métricas personalizadas: expressão segura, cálculo, papéis na API e texto livre.

Determinístico: nenhum teste chama modelo pago. O texto livre usa um intérprete
falso que devolve os planos que um modelo bem-comportado (ou hostil) devolveria.
A RLS da tabela é testada no Postgres em tests/test_rls_metricas.py.
"""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import settings
from app.dependencies import get_supabase
from app.ia.metricas_interprete import InterpretacaoMetrica, instrucoes, propor
from app.main import criar_app
from app.metricas.catalogo import VARIAVEIS
from app.metricas.expressao import ErroExpressao, analisar, avaliar, formatar, unidade_inferida
from app.models.metricas import DefinicaoMetrica, MetricaEntrada, PlanoMetrica
from app.routers.metricas import get_interprete
from app.services import metricas_service

ANO = settings.ANO_DEFAULT
PE, MG = 12, 7


# ══════════════════════════════════════════════════════════════
# Expressão
# ══════════════════════════════════════════════════════════════


class TestExpressao:
    @pytest.mark.parametrize("texto, esperado", [
        ("faturamento * csat * projetos_vendidos", 13500.0),
        ("faturamento × csat ÷ 2", 2250.0),
        ("(faturamento - meta_faturamento) / meta_faturamento * 100", 25.0),
        ("faturamento - csat - 0,5", 995.0),
        ("-faturamento + 1000", 0.0),
        ("FATURAMENTO * 2", 2000.0),
    ])
    def test_avalia_com_precedencia(self, texto, esperado):
        valores = {"faturamento": 1000, "csat": 4.5, "projetos_vendidos": 3, "meta_faturamento": 800}
        assert avaliar(analisar(texto), valores) == pytest.approx(esperado)

    @pytest.mark.parametrize("texto", [
        "", "   ", "faturamento *", "(faturamento", "faturamento)", "cidade * 2", "2 * 3",
        "__import__('os').system('ls')", "faturamento; DROP TABLE metas", "faturamento ** 2",
        "faturamento if csat else 0", "max(faturamento, csat)", "faturamento.real", "faturamento[0]",
        "x" * 301, "(" * 13 + "csat" + ")" * 13, " + ".join(["csat"] * 40), "faturamento * 1e99",
    ])
    def test_recusa_fora_da_gramatica(self, texto):
        with pytest.raises(ErroExpressao):
            analisar(texto)

    def test_divisao_por_zero_e_ausencia_viram_sem_valor(self):
        assert avaliar(analisar("faturamento / (csat - csat)"), {"faturamento": 10, "csat": 4}) is None
        assert avaliar(analisar("faturamento * csat"), {"faturamento": 10, "csat": None}) is None

    def test_formato_canonico_e_legivel(self):
        no = analisar("faturamento-(csat-membros)")
        assert formatar(no) == "faturamento - (csat - membros)"
        assert formatar(no, legivel=True) == "Faturamento no período − (CSAT − Membros)"
        assert formatar(analisar(formatar(no))) == formatar(no)

    @pytest.mark.parametrize("texto, unidade", [
        ("faturamento", "moeda"), ("faturamento + faturamento_colab", "moeda"), ("faturamento * 2", "moeda"),
        ("faturamento / 12", "moeda"), ("faturamento * csat", "numero"), ("csat", "numero"),
        ("faturamento / meta_faturamento * 100", "numero"),
    ])
    def test_unidade_inferida(self, texto, unidade):
        assert unidade_inferida(analisar(texto)) == unidade

    def test_definicao_normaliza_e_valida_janela(self):
        d = DefinicaoMetrica(expressao="faturamento*csat", ano=ANO, mes_inicio=10, mes_fim=11)
        assert d.expressao == "faturamento * csat"
        with pytest.raises(ValidationError):
            DefinicaoMetrica(expressao="faturamento", ano=ANO, mes_inicio=11, mes_fim=10)
        with pytest.raises(ValidationError):
            DefinicaoMetrica(expressao="sql", ano=ANO)
        with pytest.raises(ValidationError):
            DefinicaoMetrica(expressao="faturamento", ano=ANO, federacao_id=7)

    def test_nome_sem_marcacao(self):
        with pytest.raises(ValidationError):
            MetricaEntrada(nome="<script>x</script>", definicao={"expressao": "csat", "ano": ANO})

    def test_prompt_cita_todo_o_catalogo(self):
        texto = instrucoes(ANO)
        for nome in VARIAVEIS:
            assert nome in texto
        for valor in ("pronto", "esclarecer", "recusar", "metrica", "periodo", "escopo", "ranking", "valor", "serie"):
            assert valor in texto


# ══════════════════════════════════════════════════════════════
# Banco falso: respeita filtros do código (a RLS é testada no Postgres)
# ══════════════════════════════════════════════════════════════


class Consulta:
    def __init__(self, sb, tabela):
        self.sb, self.tabela = sb, tabela
        self.filtros, self.inicio, self.fim, self.unica = [], 0, 10**6, False
        self.operacao, self.dados, self.colunas = "select", None, "*"

    def select(self, colunas="*", count=None):
        self.colunas = colunas
        return self

    def _f(self, campo, op, valor):
        self.filtros.append((campo, op, valor))
        return self

    def eq(self, c, v): return self._f(c, "eq", v)
    def in_(self, c, v): return self._f(c, "in", list(v))
    def gte(self, c, v): return self._f(c, "gte", v)
    def lte(self, c, v): return self._f(c, "lte", v)
    def order(self, *_a, **_k): return self
    def maybe_single(self): self.unica = True; return self
    def limit(self, n): self.fim = n - 1; return self
    def insert(self, dados): self.operacao, self.dados = "insert", dados; return self
    def update(self, dados): self.operacao, self.dados = "update", dados; return self
    def delete(self): self.operacao = "delete"; return self

    def range(self, inicio, fim):
        self.inicio, self.fim = inicio, fim
        return self

    def _casa(self, linha):
        for campo, op, valor in self.filtros:
            atual = linha.get(campo)
            if op == "eq" and atual != valor: return False
            if op == "in" and atual not in valor: return False
            if op == "gte" and not atual >= valor: return False
            if op == "lte" and not atual <= valor: return False
        return True

    def execute(self):
        tabela = self.sb.tabelas.setdefault(self.tabela, [])
        self.sb.lidas.append((self.tabela, tuple(self.filtros)))
        if self.operacao == "insert":
            self.sb.proximo_id += 1
            linha = {"id": self.sb.proximo_id, "versao": 1, "criado_em": "2026-11-12T00:00:00+00:00",
                     "atualizado_em": "2026-11-12T00:00:00+00:00", "arquivada_em": None, "descricao": None,
                     **deepcopy(self.dados)}
            tabela.append(linha)
            return SimpleNamespace(data=[deepcopy(linha)], count=None)
        alvo = [linha for linha in tabela if self._casa(linha)]
        if self.operacao == "update":
            for linha in alvo:
                if "definicao" in self.dados and self.dados["definicao"] != linha.get("definicao"):
                    linha["versao"] += 1
                linha.update(deepcopy(self.dados))
            return SimpleNamespace(data=deepcopy(alvo), count=None)
        if self.operacao == "delete":
            for linha in alvo:
                tabela.remove(linha)
            return SimpleNamespace(data=deepcopy(alvo), count=None)
        if self.unica:
            return SimpleNamespace(data=deepcopy(alvo[0]) if alvo else None, count=None)
        lote = alvo[self.inicio:self.fim + 1]
        if self.colunas != "*":
            colunas = [c.strip() for c in self.colunas.split(",")]
            lote = [{c: linha.get(c) for c in colunas} for linha in lote]
        return SimpleNamespace(data=deepcopy(lote), count=len(alvo))


def _mon(id_ej, mes, fat=None, csat=None, proj=None, **extra):
    return {"id": id_ej * 100 + mes, "id_ej": id_ej, "ano": ANO, "mes": mes, "faturamento_mes": fat,
            "csat": csat, "projetos_vendidos_mes": proj, **extra}


class Banco:
    def __init__(self, papel="admin", federacao=PE):
        self.papel, self.federacao = papel, federacao
        self.lidas, self.proximo_id, self.reservas = [], 0, 0
        self.reserva = True
        self.tabelas = {
            "empresa_junior": [
                {"id": 1, "id_ej": 101, "nome": "EJ Alfa", "federacao_id": PE},
                {"id": 2, "id_ej": 102, "nome": "EJ Beta", "federacao_id": PE},
                {"id": 3, "id_ej": 103, "nome": "EJ Gama", "federacao_id": PE},
                {"id": 4, "id_ej": 201, "nome": "EJ de Minas", "federacao_id": MG},
            ],
            "monitoramento": [
                _mon(101, 9, 100), _mon(101, 10, 1000, 4.0, 1), _mon(101, 11, 2000, None, 2),
                _mon(102, 9, 0), _mon(102, 10, 5000, None, 0), _mon(102, 11, 0, 4.8, 1),
                _mon(103, 10, 700, 5.0, 1),  # sem novembro: fica fora de out–nov
                _mon(201, 10, 99999, 5.0, 9), _mon(201, 11, 99999, 5.0, 9),
            ],
            "metas": [
                {"id": 1, "id_ej": 101, "ano": ANO, "meta_faturamento": 6000},
                {"id": 2, "id_ej": 102, "ano": ANO, "meta_faturamento": 0},
            ],
            "cluster_historico": [{"id": 1, "id_ej": 101, "ano": ANO, "cluster": 3},
                                  {"id": 2, "id_ej": 102, "ano": ANO, "cluster": 2}],
            "federacao": [{"id": PE, "nome": "FEJEPE", "slug": "fejepe"}],
            "metrica_personalizada": [],
        }

    def table(self, nome):
        return Consulta(self, nome)

    def rpc(self, nome, params=None):
        if nome == "usuario_atual":
            linha = {"id": 1, "federacao_id": self.federacao, "papel": self.papel, "nome": "Teste", "email": "t@x.invalid"}
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=[linha] if self.papel else []))
        assert nome == "reservar_consulta_ia"
        self.reservas += 1
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=self.reserva))


def definicao(**alt):
    return DefinicaoMetrica(**({"expressao": "faturamento", "ano": ANO, "mes_inicio": 10, "mes_fim": 11} | alt))


# ══════════════════════════════════════════════════════════════
# Cálculo
# ══════════════════════════════════════════════════════════════


class TestCalculo:
    def test_top_faturamento_outubro_novembro(self):
        r = metricas_service.calcular(Banco(), PE, definicao(unidade="moeda"))
        assert r.status == "ok"
        assert [(l.nome, l.valor) for l in r.linhas] == [("EJ Beta", 5000), ("EJ Alfa", 3000)]
        assert r.linhas[0].cluster == 2 and r.linhas[1].posicao == 2
        assert (r.total_ejs, r.avaliadas, r.sem_cobertura, r.sem_valor) == (3, 2, 1, 0)
        assert r.valor_rede == 8000
        assert "EJ de Minas" not in {l.nome for l in r.linhas}

    def test_formula_composta_usa_csat_como_valor_unico(self):
        # Alfa: CSAT registrado só em outubro (4.0) vale para o período; Beta só em novembro (4.8).
        r = metricas_service.calcular(Banco(), PE, definicao(expressao="faturamento * csat * projetos_vendidos"))
        assert {l.nome: l.valor for l in r.linhas} == {"EJ Alfa": 36000, "EJ Beta": 24000}

    def test_ordem_crescente_e_limite(self):
        r = metricas_service.calcular(Banco(), PE, definicao(ordem="asc", limite=1))
        assert [l.nome for l in r.linhas] == ["EJ Alfa"]

    def test_divisao_por_zero_conta_como_sem_valor(self):
        r = metricas_service.calcular(Banco(), PE, definicao(expressao="faturamento / meta_faturamento * 100"))
        assert [(l.nome, l.valor) for l in r.linhas] == [("EJ Alfa", 50)]
        assert r.sem_valor == 1 and r.sem_cobertura == 1

    def test_mes_sem_dados_nao_e_substituido(self):
        r = metricas_service.calcular(Banco(), PE, definicao(mes_fim=12))
        assert r.status == "sem_dados" and "12/2026" in r.mensagem and "Não troquei" in r.mensagem
        assert r.linhas == []

    def test_sem_mes_final_vai_ate_o_ultimo_mes_com_dados(self):
        r = metricas_service.calcular(Banco(), PE, definicao(mes_inicio=10, mes_fim=None))
        assert r.mes_fim == 11 and r.status == "ok"

    def test_serie_mensal_e_media(self):
        r = metricas_service.calcular(Banco(), PE, definicao(agregacao_rede="media"))
        assert [(p.mes, p.valor, p.ejs) for p in r.serie] == [(10, pytest.approx(6700 / 3), 3), (11, 1000, 2)]
        assert r.valor_rede == 4000

    def test_tenant_entra_na_leitura_de_ejs(self):
        sb = Banco()
        metricas_service.calcular(sb, PE, definicao())
        filtros = [f for tabela, f in sb.lidas if tabela == "empresa_junior"]
        assert filtros and all(("federacao_id", "eq", PE) in f for f in filtros)

    def test_filtro_de_cluster(self, monkeypatch):
        monkeypatch.setattr("app.services.metricas_service.buscar_ids_por_cluster", lambda *_a, **_k: [101])
        r = metricas_service.calcular(Banco(), PE, definicao(cluster=3))
        assert [l.nome for l in r.linhas] == ["EJ Alfa"] and r.total_ejs == 1

    def test_explicacao_em_linguagem_de_gestor(self):
        r = metricas_service.calcular(Banco(), PE, definicao(expressao="faturamento * csat"))
        texto = " ".join(r.explicacao)
        assert "de outubro a novembro de 2026" in texto and "último CSAT registrado" in texto
        assert "não é indicador oficial" in texto


# ══════════════════════════════════════════════════════════════
# API: todos leem, só admin do banco escreve
# ══════════════════════════════════════════════════════════════


def _cliente(papel_token="admin", papel_banco="admin", federacao=PE, interprete=None):
    app = criar_app()
    sb = Banco(papel=papel_banco, federacao=federacao)
    usuario = SimpleNamespace(id="00000000-0000-0000-0000-000000000001",
                              app_metadata={"federacao_id": federacao, "papel": papel_token})
    sb.auth = SimpleNamespace(get_user=lambda token: SimpleNamespace(user=usuario))
    app.dependency_overrides[get_supabase] = lambda: sb
    if interprete is not None:
        app.dependency_overrides[get_interprete] = lambda: interprete
    return TestClient(app), sb


H = {"Authorization": "Bearer fake"}
NOVA = {"nome": "Impacto comercial", "visual": "ranking",
        "definicao": {"expressao": "faturamento * csat * projetos_vendidos", "ano": ANO, "mes_inicio": 10, "mes_fim": 11}}


class TestApi:
    def test_exige_login(self):
        client, _ = _cliente()
        assert client.get("/api/v1/metricas").status_code == 401

    def test_ciclo_completo_do_admin(self):
        client, sb = _cliente()
        criada = client.post("/api/v1/metricas", headers=H, json=NOVA)
        assert criada.status_code == 201, criada.text
        corpo = criada.json()
        assert corpo["formula_legivel"] == "Faturamento no período × CSAT × Projetos vendidos no período"
        assert sb.tabelas["metrica_personalizada"][0]["federacao_id"] == PE
        mid = corpo["id"]

        resultado = client.get(f"/api/v1/metricas/{mid}/resultado", headers=H).json()
        assert [l["nome"] for l in resultado["linhas"]] == ["EJ Alfa", "EJ Beta"]

        assert client.post(f"/api/v1/metricas/{mid}/painel", headers=H, json={"no_painel": False}).json()["no_painel"] is False
        editada = client.put(f"/api/v1/metricas/{mid}", headers=H, json=NOVA | {"definicao": NOVA["definicao"] | {"expressao": "faturamento"}})
        assert editada.json()["versao"] == 2
        assert client.delete(f"/api/v1/metricas/{mid}", headers=H).status_code == 422  # ainda ativa
        arquivada = client.post(f"/api/v1/metricas/{mid}/arquivar", headers=H).json()
        assert arquivada["arquivada"] is True and arquivada["no_painel"] is False
        assert client.get("/api/v1/metricas", headers=H).json() == []
        assert len(client.get("/api/v1/metricas?arquivadas=true", headers=H).json()) == 1
        assert client.post(f"/api/v1/metricas/{mid}/restaurar", headers=H).json()["arquivada"] is False
        client.post(f"/api/v1/metricas/{mid}/arquivar", headers=H)
        assert client.delete(f"/api/v1/metricas/{mid}", headers=H).status_code == 204
        assert sb.tabelas["metrica_personalizada"] == []

    def test_membro_le_mas_nao_escreve(self):
        client, sb = _cliente(papel_token="membro", papel_banco="membro")
        sb.tabelas["metrica_personalizada"].append({
            "id": 9, "federacao_id": PE, "nome": "Já criada", "descricao": None, "visual": "valor",
            "definicao": NOVA["definicao"], "no_painel": True, "ordem": 0, "versao": 1,
            "criado_em": "2026-11-12", "atualizado_em": "2026-11-12", "arquivada_em": None})
        assert client.get("/api/v1/metricas/catalogo", headers=H).json()["pode_editar"] is False
        assert [m["nome"] for m in client.get("/api/v1/metricas", headers=H).json()] == ["Já criada"]
        assert client.get("/api/v1/metricas/9/resultado", headers=H).status_code == 200
        for metodo, rota, corpo in [("post", "/api/v1/metricas", NOVA), ("put", "/api/v1/metricas/9", NOVA),
                                    ("post", "/api/v1/metricas/9/arquivar", None),
                                    ("post", "/api/v1/metricas/9/painel", {"no_painel": False}),
                                    ("delete", "/api/v1/metricas/9", None),
                                    ("post", "/api/v1/metricas/previa", {"definicao": NOVA["definicao"]}),
                                    ("post", "/api/v1/metricas/interpretar", {"texto": "top 10 faturamento"})]:
            resposta = getattr(client, metodo)(rota, headers=H, **({"json": corpo} if corpo else {}))
            assert resposta.status_code == 403, (rota, resposta.text)
        assert sb.tabelas["metrica_personalizada"][0]["nome"] == "Já criada"

    def test_admin_master_cria_na_propria_federacao(self):
        client, sb = _cliente(papel_token="plataforma", papel_banco="plataforma")
        assert client.get("/api/v1/metricas/catalogo", headers=H).json()["pode_editar"] is True
        assert client.post("/api/v1/metricas", headers=H, json=NOVA).status_code == 201
        assert sb.tabelas["metrica_personalizada"][0]["federacao_id"] == PE

    def test_admin_master_de_outra_federacao_nao_escreve(self):
        # Token aponta para PE, mas o vínculo no banco é com MG.
        client, sb = _cliente(papel_token="plataforma", papel_banco="plataforma")
        sb.federacao = MG
        assert client.post("/api/v1/metricas", headers=H, json=NOVA).status_code == 403

    def test_papel_vem_do_banco_nao_do_token(self):
        # Token diz admin, banco diz membro (rebaixado depois do login): não escreve.
        client, _ = _cliente(papel_token="admin", papel_banco="membro")
        assert client.post("/api/v1/metricas", headers=H, json=NOVA).status_code == 403

    def test_admin_de_outra_federacao_nao_alcanca(self):
        client, sb = _cliente()
        sb.tabelas["metrica_personalizada"].append({
            "id": 50, "federacao_id": MG, "nome": "De Minas", "descricao": None, "visual": "valor",
            "definicao": NOVA["definicao"], "no_painel": True, "ordem": 0, "versao": 1,
            "criado_em": "2026-11-12", "atualizado_em": "2026-11-12", "arquivada_em": "2026-11-12"})
        assert client.get("/api/v1/metricas?arquivadas=true", headers=H).json() == []
        assert client.get("/api/v1/metricas/50/resultado", headers=H).status_code == 404
        assert client.delete("/api/v1/metricas/50", headers=H).status_code == 404
        assert client.put("/api/v1/metricas/50", headers=H, json=NOVA).status_code == 404
        assert len(sb.tabelas["metrica_personalizada"]) == 1

    def test_corpo_nao_escolhe_tenant_nem_autoria(self):
        client, _ = _cliente()
        for extra in ({"federacao_id": MG}, {"criado_por": "outro"}):
            assert client.post("/api/v1/metricas", headers=H, json=NOVA | extra).status_code == 422

    def test_so_ano_padrao(self):
        client, _ = _cliente()
        outra = NOVA | {"definicao": NOVA["definicao"] | {"ano": ANO - 1}}
        assert client.post("/api/v1/metricas", headers=H, json=outra).status_code == 422
        assert client.post("/api/v1/metricas/previa", headers=H, json={"definicao": outra["definicao"]}).status_code == 422

    def test_nome_repetido_e_formula_invalida(self):
        client, _ = _cliente()
        assert client.post("/api/v1/metricas", headers=H, json=NOVA).status_code == 201
        assert client.post("/api/v1/metricas", headers=H, json=NOVA | {"nome": " impacto COMERCIAL "}).status_code == 422
        ruim = NOVA | {"nome": "Outra", "definicao": NOVA["definicao"] | {"expressao": "faturamento; DROP"}}
        assert client.post("/api/v1/metricas", headers=H, json=ruim).status_code == 422

    def test_reordenar(self):
        client, _ = _cliente()
        a = client.post("/api/v1/metricas", headers=H, json=NOVA).json()["id"]
        b = client.post("/api/v1/metricas", headers=H, json=NOVA | {"nome": "Segunda"}).json()["id"]
        assert [m["id"] for m in client.put("/api/v1/metricas/ordem", headers=H, json={"ids": [b, a]}).json()] == [b, a]
        assert client.put("/api/v1/metricas/ordem", headers=H, json={"ids": [a, a]}).status_code == 422

    def test_limite_de_ativas(self, monkeypatch):
        monkeypatch.setattr(metricas_service, "LIMITE_ATIVAS", 1)
        client, _ = _cliente()
        assert client.post("/api/v1/metricas", headers=H, json=NOVA).status_code == 201
        assert client.post("/api/v1/metricas", headers=H, json=NOVA | {"nome": "Outra"}).status_code == 422


# ══════════════════════════════════════════════════════════════
# Texto livre: o "modelo" aqui sou eu escrevendo os planos à mão
# ══════════════════════════════════════════════════════════════


def plano(**alt) -> PlanoMetrica:
    base = dict(status="pronto", esclarecimento=None, nome=None, expressao=None, visual=None, mes_inicio=None,
                mes_fim=None, cluster=None, ordem=None, limite=None, agregacao_rede=None, ano_mencionado=None,
                federacao_mencionada=None)
    return PlanoMetrica(**(base | alt))


class InterpreteFalso:
    def __init__(self, p):
        self.p, self.chamadas = p, 0

    def interpretar(self, texto, ano):
        self.chamadas += 1
        return InterpretacaoMetrica(self.p, "modelo-falso")


def _propor(texto, p, sb=None):
    sb = sb or Banco()
    interprete = InterpreteFalso(p)
    proposta = propor(sb, interprete, texto, federacao_id=PE, ano=ANO, federacao={"nome": "FEJEPE", "slug": "fejepe"},
                      calcular=lambda d: metricas_service.calcular(sb, PE, d))
    return proposta, interprete, sb


class TestTextoLivre:
    def test_pedido_do_exemplo_top_10_outubro_novembro(self):
        proposta, _, sb = _propor("Top 10 EJs que mais faturaram em outubro e novembro", plano(
            nome="Top faturamento out–nov", expressao="faturamento", visual="ranking", mes_inicio=10, mes_fim=11,
            ordem="desc", limite=10, agregacao_rede="soma"))
        assert proposta.status == "pronta" and sb.reservas == 1
        assert proposta.metrica.definicao.unidade == "moeda" and proposta.metrica.definicao.ano == ANO
        assert [l.nome for l in proposta.resultado.linhas] == ["EJ Beta", "EJ Alfa"]
        assert sb.tabelas["metrica_personalizada"] == []  # proposta não salva nada

    def test_metrica_composta_com_nome(self):
        proposta, _, _ = _propor("Crie a métrica Impacto: faturamento vezes CSAT vezes projetos", plano(
            nome="Impacto", expressao="faturamento*csat*projetos_vendidos", visual="ranking", mes_inicio=1))
        assert proposta.metrica.nome == "Impacto"
        assert proposta.metrica.definicao.expressao == "faturamento * csat * projetos_vendidos"
        assert proposta.formula_legivel == "Faturamento no período × CSAT × Projetos vendidos no período"

    def test_esclarecimentos_tem_texto_fixo(self):
        proposta, _, _ = _propor("Quais as melhores EJs?", plano(status="esclarecer", esclarecimento="metrica"))
        assert proposta.status == "esclarecimento" and len(proposta.opcoes) == 3
        assert proposta.opcoes[0].texto == "Quais as melhores EJs por faturamento"
        proposta, _, _ = _propor("Faturamento em janeiro e março", plano(status="esclarecer", esclarecimento="periodo"))
        assert proposta.status == "esclarecimento" and "meses seguidos" in proposta.mensagem

    def test_recusa_usa_texto_do_portal(self):
        proposta, _, _ = _propor("Ranking das EJs de Recife", plano(status="recusar"))
        assert proposta.status == "fora_do_catalogo" and "Posso montar" in proposta.mensagem

    def test_outra_federacao_recusa_antes_do_modelo(self):
        proposta, interprete, sb = _propor("faturamento das EJs da FEJEMG", plano(expressao="faturamento"))
        assert proposta.status == "fora_do_catalogo" and interprete.chamadas == 0 and sb.reservas == 0

    def test_federacao_citada_pelo_modelo_e_conferida(self):
        proposta, _, _ = _propor("faturamento da federação Minas", plano(expressao="faturamento",
                                                                          federacao_mencionada="Minas Júnior"))
        assert proposta.status == "fora_do_catalogo"
        proposta, _, _ = _propor("faturamento da FEJEPE", plano(expressao="faturamento", federacao_mencionada="FEJEPE",
                                                                mes_inicio=10, mes_fim=11))
        assert proposta.status == "pronta"

    def test_outro_ano_recusado(self):
        proposta, _, _ = _propor("faturamento em 2025", plano(expressao="faturamento", ano_mencionado=2025))
        assert proposta.status == "fora_do_catalogo" and str(ANO) in proposta.mensagem

    @pytest.mark.parametrize("expressao", ["__import__('os')", "faturamento; DELETE FROM metas", "cidade",
                                           "SELECT * FROM empresa_junior", "faturamento ** 2"])
    def test_expressao_hostil_do_modelo_nao_executa(self, expressao):
        proposta, _, sb = _propor("algo", plano(expressao=expressao, mes_inicio=10, mes_fim=11))
        assert proposta.status == "fora_do_catalogo" and proposta.resultado is None
        assert not any(t == "monitoramento" for t, _ in sb.lidas)

    def test_janela_invertida_vira_esclarecimento(self):
        proposta, _, _ = _propor("de novembro a outubro", plano(expressao="faturamento", mes_inicio=11, mes_fim=10))
        assert proposta.status == "esclarecimento"

    def test_limite_por_minuto(self):
        sb = Banco()
        sb.reserva = False
        with pytest.raises(Exception, match="Limite"):
            _propor("faturamento", plano(expressao="faturamento"), sb=sb)

    def test_rota_sem_provedor_configurado(self, monkeypatch):
        monkeypatch.setattr(settings, "IA_MODELO", "")
        client, _ = _cliente()
        resposta = client.post("/api/v1/metricas/interpretar", headers=H, json={"texto": "top 10 faturamento"})
        assert resposta.status_code == 503 and "construtor" in resposta.json()["detail"]
        assert client.get("/api/v1/metricas/catalogo", headers=H).json()["texto_livre_disponivel"] is False

    def test_rota_com_interprete(self):
        client, _ = _cliente(interprete=InterpreteFalso(plano(expressao="faturamento", visual="valor",
                                                              mes_inicio=10, mes_fim=11)))
        corpo = client.post("/api/v1/metricas/interpretar", headers=H, json={"texto": "faturamento total"}).json()
        assert corpo["status"] == "pronta" and corpo["resultado"]["valor_rede"] == 8000
