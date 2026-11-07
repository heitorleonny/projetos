"""
Testes para os endpoints de empresas.

Usa TestClient do FastAPI com mock do Supabase
para testar os endpoints sem depender do banco real.
"""

import os
from types import SimpleNamespace

# Garantir variáveis de ambiente antes de importar a app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user, get_supabase
from app.services.empresa_service import _calcular_indicadores_ej
from app.services.rede_service import calcular_sde_cenarios, gerar_ranking


@pytest.fixture
def client():
    """TestClient do FastAPI."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def _autenticado():
    """
    Autentica todos os testes deste módulo.

    Os endpoints `/api/v1` exigem JWT válido do Supabase; aqui o foco é a
    lógica de negócio, então a dependency de autenticação é mockada.
    A cobertura do gate de autenticação em si fica em `test_seguranca.py`.
    """
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="usuario-de-teste",app_metadata={"federacao_id":12,"papel":"membro"})
    yield
    app.dependency_overrides.clear()


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

    def range(self, *args, **kwargs):
        return self

    def execute(self):
        return MockSupabaseResponse(self._data)


def _make_mock_supabase(empresas=None, monitoramentos=None, metas=None, clusters=None, federacoes=None):
    """Cria mock do cliente Supabase com dados configuráveis."""
    mock_sb = MagicMock()

    table_data = {
        "federacao": federacoes or [],
        "empresa_junior": empresas or [],
        "monitoramento": monitoramentos or [],
        "metas": metas or [],
        "cluster_historico": CLUSTER_HISTORICO if clusters is None else clusters,
    }

    def table(name):
        return MockSupabaseQuery(table_data.get(name, []))

    mock_sb.table = table
    return mock_sb


# ── Dados de teste ───────────────────────────────────────────

EMPRESAS = [
    {
        "id": 1,
        "id_ej": 101,
        "nome": "EJ Alpha",
        "cnpj": "00.000.000/0001-01",
        "ano_federacao": 2020,
        "federacao": "FEJEPE",
        "cluster_legado": 1,
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
        "cluster_legado": 3,
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

# Cluster por EJ por ano, como vive em `cluster_historico` desde a migração 08.
# Antes era a coluna `cluster_20XX` na própria linha da EJ — os valores são os
# mesmos, o lugar é outro. A coluna antiga sobrevive como `cluster_legado` nos
# fixtures acima, que espelham a linha crua da tabela, mas nenhum service a lê.
CLUSTER_HISTORICO = [
    {"id_ej": 101, "ano": 2026, "cluster": 1},
    {"id_ej": 102, "ano": 2026, "cluster": 3},
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


# ── Testes ───────────────────────────────────────────────────


def _client_with_mock(empresas=None, monitoramentos=None, metas=None):
    """Cria TestClient com Supabase mockado via dependency override."""
    mock_sb = _make_mock_supabase(empresas, monitoramentos, metas)
    app.dependency_overrides[get_supabase] = lambda: mock_sb
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestHealthCheck:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestListarEmpresas:
    def test_lista_vazia(self):
        mock_sb = _make_mock_supabase()
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        client = TestClient(app)
        response = client.get("/api/v1/empresas")
        app.dependency_overrides.clear()
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    def test_lista_com_dados(self):
        mock_sb = _make_mock_supabase(EMPRESAS, MONITORAMENTOS, METAS)
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        client = TestClient(app)
        response = client.get("/api/v1/empresas")
        app.dependency_overrides.clear()
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == 2

    def test_empresa_tem_indicadores(self):
        mock_sb = _make_mock_supabase(EMPRESAS, MONITORAMENTOS, METAS)
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        client = TestClient(app)
        response = client.get("/api/v1/empresas")
        app.dependency_overrides.clear()
        data = response.json()
        ej = data["data"][0]  # Sorted by nome asc → Alpha first
        # Verifica que indicadores foram calculados
        assert "faturamento_acumulado" in ej
        assert "ritmo" in ej
        assert "percentual_meta" in ej


class TestPerfilEmpresa:
    def test_empresa_nao_encontrada(self):
        mock_sb = _make_mock_supabase()
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        client = TestClient(app)
        response = client.get("/api/v1/empresas/999")
        app.dependency_overrides.clear()
        assert response.status_code == 404

    def test_federacao_vem_da_fk_e_nao_da_coluna_legada(self):
        """
        A coluna texto `federacao` virou `federacao_legado` na migração 04, e o
        perfil passou a mostrar "Federação: —" para todo mundo (29/09/2026).
        O nome agora vem de `federacao`, pela FK `federacao_id`.
        """
        ej = {k: v for k, v in EMPRESAS[0].items() if k != "federacao"}
        ej["federacao_id"] = 12
        mock_sb = _make_mock_supabase([ej], MONITORAMENTOS, METAS, federacoes=[{"nome": "FEJEPE"}])
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        client = TestClient(app)
        response = client.get("/api/v1/empresas/101")
        app.dependency_overrides.clear()
        assert response.status_code == 200
        assert response.json()["empresa"]["federacao"] == "FEJEPE"

    def test_colaborativo_acumulado_usa_coluna_oficial_nao_soma_mensal(self):
        monitoramentos = [
            {"id": 1, "id_ej": 101, "ano": 2026, "mes": 1,
             "faturamento_mes": 100, "faturamento_acumulado": 100,
             "faturamento_colab_mes": 20, "faturamento_colab_acumulado": 20},
            {"id": 2, "id_ej": 101, "ano": 2026, "mes": 2,
             "faturamento_mes": 100, "faturamento_acumulado": 200,
             "faturamento_colab_mes": 20, "faturamento_colab_acumulado": 80},
        ]
        mock_sb = _make_mock_supabase([EMPRESAS[0]], monitoramentos)
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        response = TestClient(app).get("/api/v1/empresas/101")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        perfil = response.json()
        assert perfil["indicadores"]["faturamento_colab_acumulado"] == 80
        assert perfil["indicadores"]["taxa_colaboracao"] == 0.4
        assert [m["faturamento_colab"] for m in perfil["serie_mensal"]] == [20, 20]
        assert [m["faturamento_colab_acumulado"] for m in perfil["serie_mensal"]] == [20, 80]
        assert perfil["serie_mensal"][1]["taxa_colaboracao"] == 0.4


def test_sde_usa_colaborativo_acumulado_oficial():
    monitoramentos = [{
        "id": 1, "id_ej": 101, "ano": 2026, "mes": 12,
        "faturamento_mes": 100_000, "faturamento_acumulado": 100_000,
        "faturamento_colab_mes": 0, "faturamento_colab_acumulado": 100_000,
        "csat": 4.0, "numero_membros": 1, "membros_engajados_mes": 0,
    }]
    sb = _make_mock_supabase(
        [EMPRESAS[0]], monitoramentos,
        clusters=[{"id_ej": 101, "ano": 2026, "cluster": 3}],
    )

    resposta = calcular_sde_cenarios(sb, ano=2026)

    assert resposta.cenarios[0].subindo[0].cluster_calculado == 4
    assert resposta.cenarios[0].sde == 0.15


def test_ranking_projetos_soma_contratos_mensais_sem_coluna_legada():
    monitoramentos = [{**m, "projetos_totais": None} for m in MONITORAMENTOS]
    sb = _make_mock_supabase(EMPRESAS, monitoramentos)

    ranking = gerar_ranking(sb, ano=2026, criterio="projetos")

    assert {item.id_ej: item.valor for item in ranking} == {101: 5.0, 102: 5.0}


class TestCompararEmpresas:
    def test_comparar_exige_ids(self):
        """ids é obrigatório."""
        mock_sb = _make_mock_supabase()
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        client = TestClient(app)
        response = client.get("/api/v1/empresas/comparar")
        app.dependency_overrides.clear()
        assert response.status_code == 422  # Validation error


def test_ano_sem_monitoramento_e_diferente_de_ano_com_zero():
    """Comparação anual não deve apresentar ausência de série como resultado zero."""
    ej = {"id": 1, "id_ej": 900001, "nome": "EJ Sintética"}
    sem_serie = _calcular_indicadores_ej(ej, [], None, 2025, None)
    com_zero = _calcular_indicadores_ej(
        ej, [{"id_ej": 900001, "mes": 1, "faturamento_mes": 0, "faturamento_acumulado": 0}],
        None, 2026, None,
    )
    assert sem_serie.tem_dados_no_ano is False
    assert com_zero.tem_dados_no_ano is True
