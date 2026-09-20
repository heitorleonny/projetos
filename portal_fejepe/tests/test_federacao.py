"""
Testes do endpoint público de branding.

O que está sob teste não é o conteúdo do branding (isso é dado, e muda por
federação), e sim três propriedades do endpoint:

    1. ele responde SEM Authorization — é a razão de existir;
    2. ele devolve só o que a API prometeu devolver;
    3. abrir este endpoint não abriu nenhum outro.

A leitura do banco é mockada: o que `anon` consegue ou não consegue ler de
fato é comportamento do Postgres, e está em tests/test_rls_branding.py, contra
o laboratório de verdade.

Organização no mesmo padrão de tests/test_seguranca.py:

    TestBugCondition*   comportamento novo que precisa passar a funcionar.
    TestPreservacao*    comportamento antigo que não pode quebrar.
"""

import os

# Garantir variáveis de ambiente antes de importar a app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import get_supabase
from app.main import app

ROTA = "/api/v1/federacao/branding"

BRANDING_FEJEPE = {
    "slug": "fejepe",
    "nome": "FEJEPE",
    "logo_url": "/logo_fejepe.svg",
    "cor_primaria": "#0D6EFD",
}


def _supabase_com(linhas: list[dict], registro: list | None = None):
    """
    Mock do cliente Supabase que devolve `linhas` em qualquer consulta.

    Quando `registro` é passado, guarda os argumentos de `.select()` e `.eq()`
    — é assim que os testes conferem QUAIS colunas a API pede, sem depender de
    ler o código-fonte.
    """
    query = MagicMock()

    def select(*args, **kwargs):
        if registro is not None:
            registro.append(("select", args))
        return query

    def eq(*args, **kwargs):
        if registro is not None:
            registro.append(("eq", args))
        return query

    query.select.side_effect = select
    query.eq.side_effect = eq
    query.limit.return_value = query
    query.execute.return_value = MagicMock(data=linhas)

    cliente = MagicMock()
    cliente.table.return_value = query
    return cliente


@pytest.fixture
def client_com():
    """Devolve uma fábrica de TestClient com o Supabase mockado."""
    criados = []

    def fabricar(linhas: list[dict], registro: list | None = None):
        app.dependency_overrides[get_supabase] = lambda: _supabase_com(linhas, registro)
        cliente = TestClient(app)
        criados.append(cliente)
        return cliente

    yield fabricar
    app.dependency_overrides.clear()


# ══════════════════════════════════════════════════════════════
# O branding precisa existir antes do login
# ══════════════════════════════════════════════════════════════


class TestBugConditionBrandingSemToken:
    """Property — a primeira tela do portal consegue se apresentar."""

    def test_responde_sem_header_de_autorizacao(self, client_com):
        """
        Este é O teste deste arquivo.

        Todo o resto da API responde 401 sem token (tests/test_seguranca.py).
        Aqui, 401 seria o bug: a tela de login nunca teria como mostrar o nome
        e o logo da federação.
        """
        client = client_com([BRANDING_FEJEPE])
        resposta = client.get(ROTA, params={"slug": "fejepe"})
        assert resposta.status_code == 200, "branding sem token precisa responder"

    def test_devolve_nome_logo_e_cor(self, client_com):
        client = client_com([BRANDING_FEJEPE])
        corpo = client.get(ROTA, params={"slug": "fejepe"}).json()

        assert corpo["slug"] == "fejepe"
        assert corpo["nome"] == "FEJEPE"
        assert corpo["logo_url"] == "/logo_fejepe.svg"
        assert corpo["cor_primaria"] == "#0D6EFD"

    def test_devolve_o_ano_default_da_plataforma(self, client_com):
        """
        O frontend mantinha a própria cópia do ano em ~13 lugares. A fonte
        única é `settings.ANO_DEFAULT`, e ela chega por aqui.
        """
        client = client_com([BRANDING_FEJEPE])
        corpo = client.get(ROTA, params={"slug": "fejepe"}).json()
        assert corpo["ano_default"] == settings.ANO_DEFAULT

    def test_ano_default_acompanha_a_configuracao(self, client_com, monkeypatch):
        """Trocar a configuração troca a resposta — sem rebuild do frontend."""
        monkeypatch.setattr(settings, "ANO_DEFAULT", 2031)
        client = client_com([BRANDING_FEJEPE])
        assert client.get(ROTA, params={"slug": "fejepe"}).json()["ano_default"] == 2031

    def test_federacao_sem_branding_cadastrado_responde_com_nulos(self, client_com):
        """
        Uma federação recém-criada não tem logo nem cor — e isso não é erro.
        O frontend cai na paleta compilada e nas iniciais do nome.
        """
        client = client_com([{"slug": "fejece", "nome": "FEJECE", "logo_url": None, "cor_primaria": None}])
        corpo = client.get(ROTA, params={"slug": "fejece"}).json()

        assert corpo["nome"] == "FEJECE"
        assert corpo["logo_url"] is None
        assert corpo["cor_primaria"] is None


class TestBugConditionContratoDoEndpoint:
    """O que entra, o que sai, e o que acontece quando não dá certo."""

    def test_slug_e_obrigatorio(self, client_com):
        """Sem slug não há default silencioso — nenhuma federação é a padrão."""
        client = client_com([BRANDING_FEJEPE])
        assert client.get(ROTA).status_code == 422

    def test_slug_desconhecido_responde_404(self, client_com):
        client = client_com([])
        assert client.get(ROTA, params={"slug": "inexistente"}).status_code == 404

    def test_slug_e_normalizado(self, client_com):
        """`FEJEPE `, com maiúsculas e espaço, consulta o mesmo slug."""
        registro: list = []
        client = client_com([BRANDING_FEJEPE], registro)
        client.get(ROTA, params={"slug": "  FEJEPE  "})

        eqs = [args for nome, args in registro if nome == "eq"]
        assert ("slug", "fejepe") in eqs

    def test_pede_ao_banco_apenas_as_colunas_de_branding(self, client_com):
        """
        A consulta não pode pedir `*`: `anon` tem GRANT por coluna, e `SELECT *`
        seria recusado pelo Postgres em produção — com o mock, passaria batido.
        """
        registro: list = []
        client = client_com([BRANDING_FEJEPE], registro)
        client.get(ROTA, params={"slug": "fejepe"})

        colunas = [args[0] for nome, args in registro if nome == "select"]
        assert colunas, "a consulta precisa declarar colunas"
        for pedido in colunas:
            assert "*" not in pedido
            assert set(pedido.replace(" ", "").split(",")) <= {
                "slug",
                "nome",
                "logo_url",
                "cor_primaria",
            }

    def test_nao_devolve_colunas_alem_do_contrato(self, client_com):
        """
        Se um dia a consulta trouxer coluna a mais, o response_model corta.
        Vale como rede: o endpoint é público.
        """
        linha = {**BRANDING_FEJEPE, "id": 12, "uf": "PE", "status": "ativa"}
        client = client_com([linha])
        corpo = client.get(ROTA, params={"slug": "fejepe"}).json()

        assert set(corpo) == {"slug", "nome", "logo_url", "cor_primaria", "ano_default"}

    def test_supabase_fora_do_ar_responde_503(self):
        """Mesma tradução de erro dos outros routers — 503, não 500."""

        def _explodir():
            cliente = MagicMock()
            cliente.table.side_effect = httpx.ConnectError("sem rede")
            return cliente

        app.dependency_overrides[get_supabase] = _explodir
        try:
            resposta = TestClient(app).get(ROTA, params={"slug": "fejepe"})
        finally:
            app.dependency_overrides.clear()

        assert resposta.status_code == 503


# ══════════════════════════════════════════════════════════════
# PRESERVAÇÃO — o que não pode ter quebrado
# ══════════════════════════════════════════════════════════════


class TestPreservacaoOsOutrosEndpointsSeguemFechados:
    """Abrir um endpoint não abre os vizinhos."""

    @pytest.mark.parametrize(
        "rota",
        [
            "/api/v1/empresas",
            "/api/v1/rede/indicadores",
            "/api/v1/eventos",
        ],
    )
    def test_rota_autenticada_continua_recusando_sem_token(self, rota):
        assert TestClient(app).get(rota).status_code == 401

    def test_nenhum_outro_endpoint_publico_apareceu(self):
        """
        Inventário: `/api/v1/federacao/branding` é o único caminho de `/api/v1`
        sem dependência de autenticação. Se este teste quebrar, alguém abriu
        mais uma porta — e precisa dizer por quê aqui.
        """
        from app.dependencies import get_current_user

        publicas = []
        for rota in app.routes:
            caminho = getattr(rota, "path", "")
            if not caminho.startswith("/api/v1"):
                continue
            dependencias = getattr(getattr(rota, "dependant", None), "dependencies", [])
            chamaveis = {dep.call for dep in dependencias}
            if get_current_user not in chamaveis:
                publicas.append(caminho)

        assert publicas == [ROTA], f"endpoints públicos inesperados: {publicas}"
