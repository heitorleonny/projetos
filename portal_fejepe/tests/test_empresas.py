"""
Testes para os endpoints de empresas.

Usa TestClient do FastAPI com mock do Supabase
para testar os endpoints sem depender do banco real.
"""

import os

# Garantir variáveis de ambiente antes de importar a app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_supabase


@pytest.fixture
def client():
    """TestClient do FastAPI."""
    return TestClient(app)


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


def _make_mock_supabase(empresas=None, monitoramentos=None, metas=None):
    """Cria mock do cliente Supabase com dados configuráveis."""
    mock_sb = MagicMock()

    table_data = {
        "empresa_junior": empresas or [],
        "monitoramento": monitoramentos or [],
        "metas": metas or [],
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


class TestCompararEmpresas:
    def test_comparar_exige_ids(self):
        """ids é obrigatório."""
        mock_sb = _make_mock_supabase()
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        client = TestClient(app)
        response = client.get("/api/v1/empresas/comparar")
        app.dependency_overrides.clear()
        assert response.status_code == 422  # Validation error
