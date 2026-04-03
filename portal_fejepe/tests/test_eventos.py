"""
Testes para os endpoints de Eventos.
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_supabase


class MockSupabaseResponse:
    def __init__(self, data: list[dict] | None = None):
        self.data = data or []


class MockSupabaseQuery:
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


EMPRESAS = [
    {
        "id": 1,
        "id_ej": 101,
        "nome": "EJ Alpha",
        "cluster": 1,
        "comunidade": "Comunidade A",
        "status": "ativa",
        "foto_url": None,
    },
    {
        "id": 2,
        "id_ej": 102,
        "nome": "EJ Beta",
        "cluster": 3,
        "comunidade": "Comunidade B",
        "status": "ativa",
        "foto_url": None,
    },
    {
        "id": 3,
        "id_ej": 103,
        "nome": "EJ Gamma",
        "cluster": 2,
        "comunidade": "Comunidade C",
        "status": "ativa",
        "foto_url": None,
    },
]

MONITORAMENTOS = [
    {
        "id": 1,
        "id_ej": 101,
        "ano": 2026,
        "mes": 4,
        "faturamento_mes": 15_000,
        "faturamento_acumulado": 40_000,
        "faturamento_colab_mes": 3_000,
        "faturamento_colab_acumulado": 5_000,
        "projetos_vendidos_mes": 4,
        "projetos_totais": 10,
        "projetos_colab_mes": 1,
        "csat": 4.5,
    },
    {
        "id": 2,
        "id_ej": 102,
        "ano": 2026,
        "mes": 4,
        "faturamento_mes": 20_000,
        "faturamento_acumulado": 50_000,
        "faturamento_colab_mes": 2_000,
        "faturamento_colab_acumulado": 3_000,
        "projetos_vendidos_mes": 5,
        "projetos_totais": 12,
        "projetos_colab_mes": 1,
        "csat": 4.7,
    },
    {
        "id": 3,
        "id_ej": 103,
        "ano": 2026,
        "mes": 4,
        "faturamento_mes": 2_000,
        "faturamento_acumulado": 8_000,
        "faturamento_colab_mes": 1_000,
        "faturamento_colab_acumulado": 1_000,
        "projetos_vendidos_mes": 1,
        "projetos_totais": 3,
        "projetos_colab_mes": 0,
        "csat": 4.2,
    },
]

METAS = [
    {
        "id": 1,
        "id_ej": 101,
        "ano": 2026,
        "meta_faturamento": 100_000,
        "meta_taxa_colaboracao": 0.15,
        "meta_csat": 4.5,
        "meta_projetos_impacto": 2,
        "meta_pdi": True,
        "meta_engajamento_mej": 0.25,
    },
    {
        "id": 2,
        "id_ej": 102,
        "ano": 2026,
        "meta_faturamento": 120_000,
        "meta_taxa_colaboracao": 0.20,
        "meta_csat": 4.8,
        "meta_projetos_impacto": 3,
        "meta_pdi": True,
        "meta_engajamento_mej": 0.30,
    },
    {
        "id": 3,
        "id_ej": 103,
        "ano": 2026,
        "meta_faturamento": 100_000,
        "meta_taxa_colaboracao": 0.12,
        "meta_csat": 4.4,
        "meta_projetos_impacto": 1,
        "meta_pdi": True,
        "meta_engajamento_mej": 0.20,
    },
]


def _client_with_mock(empresas=None, monitoramentos=None, metas=None):
    mock_sb = _make_mock_supabase(empresas, monitoramentos, metas)
    app.dependency_overrides[get_supabase] = lambda: mock_sb
    client = TestClient(app)
    return client


def test_lista_eventos_disponiveis():
    client = TestClient(app)
    response = client.get("/api/v1/eventos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(evento["id_evento"] == "encontro-das-instancias" for evento in data)


def test_evento_calcula_metas_e_gaps():
    client = _client_with_mock(EMPRESAS, MONITORAMENTOS, METAS)
    response = client.get("/api/v1/eventos/encontro-das-instancias")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()

    assert data["total_ejs"] == 3

    fora_do_zero = next(meta for meta in data["metas"] if meta["tipo"] == "fora_do_zero")
    verde_abril = next(meta for meta in data["metas"] if meta["tipo"] == "verde_abril")
    colab_tracking = next(meta for meta in data["metas"] if meta["tipo"] == "colab_tracking")

    assert fora_do_zero["meta_contagem"] == 3
    assert fora_do_zero["resultado_contagem"] == 3
    assert fora_do_zero["gap_contagem"] == 0

    assert verde_abril["meta_contagem"] == 2
    assert verde_abril["resultado_contagem"] == 2
    assert verde_abril["submeta_contagem"] == 1
    assert verde_abril["subresultado_contagem"] == 1
    assert verde_abril["gap_contagem"] == 0

    assert colab_tracking["meta_contagem"] == 1
    assert colab_tracking["resultado_contagem"] == 2
    assert colab_tracking["gap_contagem"] == 0


def test_evento_nao_encontrado():
    client = TestClient(app)
    response = client.get("/api/v1/eventos/inexistente")
    assert response.status_code == 404