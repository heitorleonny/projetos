"""
Testes de segurança do Portal FEJEPE — autenticação JWT e CORS restrito.

Cobre os dois bugs descritos em `.kiro/specs/auth-cors-seguranca/bugfix.md`:

    Bug 1 — JWT não validado: endpoints `/api/v1` respondem sem exigir token.
    Bug 2 — CORS aberto: `CORSMiddleware` usa `allow_origins=["*"]`.

Organização (metodologia de bugfix exploratório):

    TestBugConditionJWT / TestBugConditionCORS
        Testes de EXPLORAÇÃO — codificam o comportamento esperado (Properties 1 e 2).
        FALHAM no código não corrigido; passam depois do fix.

    TestPreservacaoJWT / TestPreservacaoCORS
        Testes de PRESERVAÇÃO — codificam o baseline observado (Properties 3 e 4).
        PASSAM no código não corrigido e devem continuar passando depois do fix.

O Supabase Auth é mockado via `app.dependency_overrides[get_supabase]`, substituindo
`sb.auth.get_user` — nenhum teste depende de rede real.
"""

import os

# Garantir variáveis de ambiente antes de importar a app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

import random
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import get_supabase
from app.main import app

# ── Tokens usados nos testes ─────────────────────────────────

TOKEN_VALIDO = "token.valido.supabase"

# Tokens que o Supabase Auth rejeitaria (inválidos, malformados ou expirados)
TOKENS_INVALIDOS = [
    "abc.invalido.xyz",
    "",
    "   ",
    "nao-e-um-jwt",
    "a.b",
    "eyJhbGciOiJIUzI1NiJ9.payload-corrompido",
    "Bearer",
    "null",
]


# ── Mocks do Supabase (dados + auth) ─────────────────────────


class MockSupabaseResponse:
    """Mock simplificado de resposta do Supabase."""

    def __init__(self, data: list[dict] | None = None):
        self.data = data or []


class MockSupabaseQuery:
    """Mock do query builder do Supabase com encadeamento."""

    def __init__(self, data: list[dict] | None = None):
        self._data = data or []

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return MockSupabaseResponse(self._data)


class UsuarioFake:
    """Usuário autenticado devolvido pelo Supabase Auth mockado."""

    def __init__(self, id_usuario: str = "usuario-de-teste"):
        self.id = id_usuario
        self.email = "teste@fejepe.org.br"


class RespostaAuthFake:
    """Resposta de `sb.auth.get_user(token)` mockada."""

    def __init__(self, user):
        self.user = user


def _make_mock_supabase(empresas=None, monitoramentos=None, metas=None):
    """
    Cria mock do cliente Supabase com dados configuráveis e Auth mockado.

    O `auth.get_user(token)` devolve um usuário apenas para `TOKEN_VALIDO`;
    para qualquer outro token levanta exceção, como o SDK real faz para
    tokens inválidos, expirados ou malformados.
    """
    mock_sb = MagicMock()

    table_data = {
        "empresa_junior": empresas or [],
        "monitoramento": monitoramentos or [],
        "metas": metas or [],
    }

    def table(name):
        return MockSupabaseQuery(table_data.get(name, []))

    def get_user(token: str | None = None):
        if token != TOKEN_VALIDO:
            raise Exception("Invalid JWT")
        return RespostaAuthFake(UsuarioFake())

    mock_sb.table = table
    mock_sb.auth.get_user = get_user
    return mock_sb


@pytest.fixture
def client():
    """TestClient com Supabase (dados + auth) mockado."""
    mock_sb = _make_mock_supabase(EMPRESAS, MONITORAMENTOS, METAS)
    app.dependency_overrides[get_supabase] = lambda: mock_sb
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth() -> dict[str, str]:
    """Header `Authorization` com um JWT válido (mockado)."""
    return {"Authorization": f"Bearer {TOKEN_VALIDO}"}


# ── Dados de teste ───────────────────────────────────────────

EMPRESAS = [
    {
        "id": 1,
        "id_ej": 101,
        "nome": "EJ Alpha",
        "cnpj": "00.000.000/0001-01",
        "ano_federacao": 2020,
        "federacao": "FEJEPE",
        "cluster": 1,
        "comunidade": "Comunidade A",
        "estado": "PE",
        "cidade": "Recife",
        "universidade": "UFPE",
        "curso": "Engenharia",
        "status": "ativa",
        "created_at": "2020-01-01T00:00:00",
        "updated_at": "2025-12-01T00:00:00",
        "foto_url": None,
    },
    {
        "id": 2,
        "id_ej": 102,
        "nome": "EJ Beta",
        "cnpj": "00.000.000/0001-02",
        "ano_federacao": 2019,
        "federacao": "FEJEPE",
        "cluster": 3,
        "comunidade": "Comunidade B",
        "estado": "PE",
        "cidade": "Caruaru",
        "universidade": "UFPE-CAA",
        "curso": "Administração",
        "status": "ativa",
        "created_at": "2019-01-01T00:00:00",
        "updated_at": "2025-12-01T00:00:00",
        "foto_url": None,
    },
]

MONITORAMENTOS = [
    {
        "id": 1,
        "id_ej": 101,
        "ano": 2026,
        "mes": 1,
        "faturamento_mes": 8_000,
        "faturamento_acumulado": 8_000,
        "faturamento_colab_mes": 2_000,
        "faturamento_colab_acumulado": 2_000,
        "projetos_vendidos_mes": 2,
        "projetos_totais": 2,
        "csat": 4.5,
        "created_at": "2026-02-01T00:00:00",
    },
    {
        "id": 2,
        "id_ej": 101,
        "ano": 2026,
        "mes": 2,
        "faturamento_mes": 12_000,
        "faturamento_acumulado": 20_000,
        "faturamento_colab_mes": 3_000,
        "faturamento_colab_acumulado": 5_000,
        "projetos_vendidos_mes": 3,
        "projetos_totais": 5,
        "csat": 4.8,
        "created_at": "2026-03-01T00:00:00",
    },
    {
        "id": 3,
        "id_ej": 102,
        "ano": 2026,
        "mes": 1,
        "faturamento_mes": 50_000,
        "faturamento_acumulado": 50_000,
        "faturamento_colab_mes": 10_000,
        "faturamento_colab_acumulado": 10_000,
        "projetos_vendidos_mes": 5,
        "projetos_totais": 5,
        "csat": 4.9,
        "created_at": "2026-02-01T00:00:00",
    },
]

METAS = [
    {
        "id": 1,
        "id_ej": 101,
        "ano": 2026,
        "meta_faturamento": 120_000,
        "meta_taxa_colaboracao": 0.15,
        "meta_csat": 4.5,
        "meta_projetos_impacto": 2,
        "meta_pdi": True,
        "meta_engajamento_mej": 0.25,
        "created_at": "2026-01-01T00:00:00",
    },
    {
        "id": 2,
        "id_ej": 102,
        "ano": 2026,
        "meta_faturamento": 600_000,
        "meta_taxa_colaboracao": 0.20,
        "meta_csat": 4.8,
        "meta_projetos_impacto": 5,
        "meta_pdi": True,
        "meta_engajamento_mej": 0.30,
        "created_at": "2026-01-01T00:00:00",
    },
]

# Endpoints protegidos de `/api/v1` (todos devem exigir JWT válido)
ENDPOINTS_PROTEGIDOS = [
    "/api/v1/empresas",
    "/api/v1/empresas/101",
    "/api/v1/empresas/comparar?ids=101&ids=102",
    "/api/v1/rede/indicadores",
    "/api/v1/rede/ritmo-mensal",
    "/api/v1/rede/sde",
    "/api/v1/rede/ranking",
    "/api/v1/eventos",
]

# Origem arbitrária, garantidamente fora de `settings.cors_origin_list`
ORIGEM_NAO_PERMITIDA = "https://atacante.example"


def _origens_fora_da_allowlist(quantidade: int = 25) -> list[str]:
    """
    Gera origens pseudo-aleatórias garantidamente fora da allowlist.

    Semente fixa para que a suíte seja determinística (PBT com escopo).
    """
    rng = random.Random(20260909)
    esquemas = ["http", "https"]
    tlds = ["example", "test", "invalid", "attacker.example"]
    permitidas = set(settings.cors_origin_list)
    origens: list[str] = []
    while len(origens) < quantidade:
        host = "".join(rng.choices("abcdefghijklmnopqrstuvwxyz", k=rng.randint(4, 12)))
        origem = f"{rng.choice(esquemas)}://{host}.{rng.choice(tlds)}"
        if origem not in permitidas and origem not in origens:
            origens.append(origem)
    return origens


def _tokens_malformados(quantidade: int = 25) -> list[str]:
    """Gera tokens malformados pseudo-aleatórios (nunca iguais ao TOKEN_VALIDO)."""
    rng = random.Random(1234)
    alfabeto = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
    tokens: list[str] = []
    while len(tokens) < quantidade:
        token = "".join(rng.choices(alfabeto, k=rng.randint(1, 60)))
        if token != TOKEN_VALIDO:
            tokens.append(token)
    return tokens


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 1: Bug Condition (JWT)
# Estes testes FALHAM no código não corrigido (retornam 200 em vez de 401).
# ══════════════════════════════════════════════════════════════


class TestBugConditionJWT:
    """Property 1 — requisições sem JWT válido devem ser rejeitadas com 401."""

    def test_empresas_sem_header_authorization(self, client):
        """isBugCondition: header ausente → esperado 401 (hoje: 200 com todas as EJs)."""
        response = client.get("/api/v1/empresas")
        assert response.status_code == 401
        assert "data" not in response.json()

    def test_rede_indicadores_com_token_invalido(self, client):
        """isBugCondition: token inválido → esperado 401 (hoje: 200 com os KPIs)."""
        response = client.get(
            "/api/v1/rede/indicadores",
            headers={"Authorization": "Bearer abc.invalido.xyz"},
        )
        assert response.status_code == 401

    def test_eventos_sem_header_authorization(self, client):
        """Cobre o endpoint que não usa `get_supabase` — o gate é em nível de router."""
        response = client.get("/api/v1/eventos")
        assert response.status_code == 401

    @pytest.mark.parametrize("endpoint", ENDPOINTS_PROTEGIDOS)
    def test_todos_endpoints_protegidos_sem_token(self, client, endpoint):
        """Nenhum endpoint `/api/v1` responde sem autenticação."""
        response = client.get(endpoint)
        assert response.status_code == 401, f"{endpoint} não exigiu autenticação"

    @pytest.mark.parametrize("token", TOKENS_INVALIDOS)
    def test_tokens_invalidos_conhecidos(self, client, token):
        """Casos concretos de token inválido/malformado → 401."""
        response = client.get(
            "/api/v1/empresas", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    def test_esquema_nao_bearer(self, client):
        """Esquema diferente de Bearer (ex.: Basic) → 401."""
        response = client.get(
            "/api/v1/empresas", headers={"Authorization": f"Basic {TOKEN_VALIDO}"}
        )
        assert response.status_code == 401

    def test_propriedade_tokens_malformados_sempre_401(self, client):
        """
        Propriedade escopada: para toda amostra de token malformado,
        a resposta é 401 e nenhum dado da rede é exposto.
        """
        for token in _tokens_malformados():
            response = client.get(
                "/api/v1/empresas", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401, f"token {token!r} não foi rejeitado"
            assert "data" not in response.json()

    def test_resposta_401_inclui_www_authenticate(self, client):
        """A resposta 401 deve indicar o esquema esperado."""
        response = client.get("/api/v1/empresas")
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 2: Bug Condition (CORS)
# Estes testes FALHAM no código não corrigido (ecoam `*`).
# ══════════════════════════════════════════════════════════════


class TestBugConditionCORS:
    """Property 2 — origens fora da allowlist não devem ser autorizadas."""

    def test_origem_nao_permitida_nao_e_autorizada(self, client):
        """Requisição simples de origem arbitrária não recebe `Access-Control-Allow-Origin`."""
        response = client.get("/health", headers={"Origin": ORIGEM_NAO_PERMITIDA})
        acao = response.headers.get("access-control-allow-origin")
        assert acao not in (ORIGEM_NAO_PERMITIDA, "*"), (
            f"origem não permitida foi autorizada com {acao!r}"
        )

    def test_preflight_de_origem_nao_permitida(self, client):
        """Preflight de origem fora da allowlist não é autorizado."""
        response = client.options(
            "/api/v1/empresas",
            headers={
                "Origin": ORIGEM_NAO_PERMITIDA,
                "Access-Control-Request-Method": "GET",
            },
        )
        acao = response.headers.get("access-control-allow-origin")
        assert acao not in (ORIGEM_NAO_PERMITIDA, "*")

    def test_propriedade_origens_fora_da_allowlist_nunca_autorizadas(self, client):
        """
        Propriedade: para toda origem gerada fora de `settings.cors_origin_list`,
        a resposta nunca ecoa a origem nem `*`.
        """
        for origem in _origens_fora_da_allowlist():
            response = client.get("/health", headers={"Origin": origem})
            acao = response.headers.get("access-control-allow-origin")
            assert acao not in (origem, "*"), f"origem {origem!r} autorizada com {acao!r}"

    def test_origem_permitida_recebe_a_propria_origem(self, client):
        """
        Pós-fix (Property 4): com allowlist explícita, a origem permitida é
        ecoada literalmente — e não como `*`, que hoje é o valor retornado.
        """
        origem = settings.cors_origin_list[0]
        response = client.get("/health", headers={"Origin": origem})
        assert response.headers.get("access-control-allow-origin") == origem

    def test_cors_usa_a_allowlist_configurada(self):
        """Requirement 2.4 — o middleware deve usar `settings.cors_origin_list`."""
        origens_do_middleware = [
            m.kwargs.get("allow_origins")
            for m in app.user_middleware
            if getattr(m, "kwargs", None) and "allow_origins" in m.kwargs
        ]
        assert origens_do_middleware, "CORSMiddleware não encontrado"
        assert origens_do_middleware[0] == settings.cors_origin_list


# ══════════════════════════════════════════════════════════════
# PRESERVAÇÃO — Property 3: JWT válido e `/health` inalterados
# Estes testes PASSAM no código não corrigido (baseline observado).
# ══════════════════════════════════════════════════════════════


class TestPreservacaoJWT:
    """Property 3 — requisições legítimas continuam produzindo os mesmos resultados."""

    def test_health_permanece_publico(self, client):
        """`/health` continua 200 sem token."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "0.1.0"}

    def test_empresas_com_token_valido(self, client, auth):
        """
        Baseline observado: lista de EJs com os indicadores calculados.

        Os valores são fixados exatamente para detectar qualquer alteração
        acidental nos services (Requirement 3.4).
        """
        response = client.get("/api/v1/empresas", headers=auth)
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 2
        assert [ej["nome"] for ej in data["data"]] == ["EJ Alpha", "EJ Beta"]
        alpha = data["data"][0]
        assert alpha["faturamento_acumulado"] == 20_000.0
        assert alpha["faturamento_colab_acumulado"] == 5_000.0
        assert alpha["faturamento_mes"] == 12_000.0
        assert alpha["projetos_totais"] == 5
        assert alpha["csat_medio"] == 4.65
        assert alpha["percentual_meta"] == 16.67
        assert alpha["ritmo"] == "significativo"
        assert alpha["cluster_calculado"] == 4
        assert alpha["tracking_cluster_calculado"] == 4

    def test_perfil_ej_com_token_valido(self, client, auth):
        """Baseline observado: perfil completo de uma EJ (services intocados)."""
        response = client.get("/api/v1/empresas/101", headers=auth)
        assert response.status_code == 200
        perfil = response.json()
        assert perfil["empresa"]["nome"] == "EJ Alpha"
        assert perfil["empresa"]["cnpj"] == "00.000.000/0001-01"
        assert perfil["indicadores"]["faturamento_acumulado"] == 20_000.0
        assert perfil["indicadores"]["csat_medio"] == 4.73
        assert perfil["metas"]["meta_faturamento"] == 120_000.0
        assert perfil["metas"]["percentual_meta"] == 16.67
        assert perfil["projecao_anual"] == 1_414_000.0
        assert perfil["ritmo_necessario"] == 11_111.11
        assert perfil["crescimento_mensal"] == 316.67
        assert perfil["crescimento_anual"] == 150.0
        assert perfil["tracking_cluster"] == 189_472_500.0

    def test_ej_inexistente_continua_404(self, auth):
        """Baseline: 404 de negócio preservado para requisição autenticada."""
        app.dependency_overrides[get_supabase] = lambda: _make_mock_supabase()
        with TestClient(app) as client:
            response = client.get("/api/v1/empresas/999", headers=auth)
        app.dependency_overrides.clear()
        assert response.status_code == 404

    def test_comparar_sem_ids_continua_422(self, client, auth):
        """Baseline: validação de query preservada para requisição autenticada."""
        response = client.get("/api/v1/empresas/comparar", headers=auth)
        assert response.status_code == 422

    def test_rede_indicadores_com_token_valido(self, client, auth):
        """Baseline: KPIs consolidados da rede."""
        response = client.get("/api/v1/rede/indicadores", headers=auth)
        assert response.status_code == 200
        kpis = response.json()
        assert kpis["total_ejs"] == 2
        assert kpis["faturamento_total"] == 70_000.0
        assert kpis["faturamento_colab_total"] == 15_000.0
        assert kpis["total_projetos"] == 10
        assert kpis["media_csat"] == 4.78
        assert kpis["ejs_fora_do_zero"] == 2
        assert kpis["ejs_ritmo_significativo"] == 2
        assert kpis["distribuicao_clusters"] == {"1": 1, "3": 1}
        assert kpis["participacao_comunidades"] == {
            "Comunidade A": 28.57,
            "Comunidade B": 71.43,
        }

    def test_rede_sde_com_token_valido(self, client, auth):
        """Baseline observado: SDE nos três cenários de índice de cluster."""
        response = client.get("/api/v1/rede/sde", headers=auth)
        assert response.status_code == 200
        sde = response.json()
        assert sde["total_ejs"] == 2
        assert [(c["nome"], c["sde"]) for c in sde["cenarios"]] == [
            ("Índice de Cluster", 0.0),
            ("Índice c/ Meta CSAT", 0.0),
            ("Tracking de Cluster", 0.45),
        ]

    def test_eventos_com_token_valido(self, client, auth):
        """Baseline: listagem de eventos (endpoint sem `get_supabase`)."""
        response = client.get("/api/v1/eventos", headers=auth)
        assert response.status_code == 200
        eventos = response.json()
        assert [e["id_evento"] for e in eventos] == ["ciranda-mej-26"]

    @pytest.mark.parametrize("endpoint", ENDPOINTS_PROTEGIDOS)
    def test_endpoints_protegidos_respondem_com_token_valido(self, client, auth, endpoint):
        """
        Propriedade de preservação: com JWT válido, nenhum endpoint protegido
        responde 401 — o gate de auth não altera o resultado legítimo.
        """
        response = client.get(endpoint, headers=auth)
        assert response.status_code != 401, f"{endpoint} rejeitou um JWT válido"

    def test_variacoes_de_parametros_preservadas(self, client, auth):
        """
        Propriedade de preservação: variações de parâmetros em endpoints protegidos
        com JWT válido continuam produzindo o mesmo resultado do baseline.
        """
        for ano in (2025, 2026):
            for mes in (None, 1, 2, 12):
                params = {"ano": ano}
                if mes is not None:
                    params["mes"] = mes
                response = client.get("/api/v1/empresas", headers=auth, params=params)
                assert response.status_code == 200
                assert response.json()["meta"]["total"] == 2


# ══════════════════════════════════════════════════════════════
# PRESERVAÇÃO — Property 4: origens permitidas continuam autorizadas
# Estes testes PASSAM no código não corrigido (baseline observado).
# ══════════════════════════════════════════════════════════════


class TestPreservacaoCORS:
    """Property 4 — origens em `CORS_ORIGINS` continuam autorizadas."""

    def test_allowlist_configurada_nao_esta_vazia(self):
        """Pré-condição dos testes de CORS: a allowlist tem origens."""
        assert settings.cors_origin_list

    def test_propriedade_origens_permitidas_sao_ecoadas(self, client):
        """
        Propriedade: para toda origem em `settings.cors_origin_list`,
        a resposta ecoa `Access-Control-Allow-Origin` igual à origem.
        """
        for origem in settings.cors_origin_list:
            response = client.get("/health", headers={"Origin": origem})
            acao = response.headers.get("access-control-allow-origin")
            assert acao in (origem, "*"), f"origem permitida {origem!r} recebeu {acao!r}"

    def test_preflight_de_origem_permitida(self, client):
        """Preflight de origem permitida continua autorizado."""
        origem = settings.cors_origin_list[0]
        response = client.options(
            "/api/v1/empresas",
            headers={
                "Origin": origem,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        acao = response.headers.get("access-control-allow-origin")
        assert acao in (origem, "*")
