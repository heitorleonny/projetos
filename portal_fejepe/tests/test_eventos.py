"""
Testes para os endpoints de Eventos.
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user, get_supabase


@pytest.fixture(autouse=True)
def _autenticado():
    """
    Autentica todos os testes deste módulo.

    Os endpoints `/api/v1` exigem JWT válido do Supabase; aqui o foco é a
    lógica de negócio, então a dependency de autenticação é mockada.
    A cobertura do gate de autenticação em si fica em `test_seguranca.py`.
    """
    app.dependency_overrides[get_current_user] = lambda: {"id": "usuario-de-teste"}
    yield
    app.dependency_overrides.clear()



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
    assert any(evento["id_evento"] == "ciranda-mej-26" for evento in data)


def test_evento_calcula_metas_e_gaps():
    """
    Metas do CirandaMEJ'26 sobre os mocks deste módulo (3 EJs ativas).

    Os valores esperados são derivados à mão a partir de `METAS_EVENTO`
    (`evento_service.py`) e dos dados fixos acima, não copiados da saída:

        meta_contagem = ceil(meta_percentual / 100 * total_ejs), total_ejs = 3

        faturamento_zero (72%)  meta=ceil(2,16)=3; acumulado > 0 nas 3 → 3
        colab_zero       (34%)  meta=ceil(1,02)=2; colab > 0 nas 3      → 3
        verde_mes        (30%)  meta=ceil(0,90)=1; limiar = 5/12 = 41,67%
                                da meta anual — 101: 40,0%, 102: 41,67%,
                                103: 8,0% → só a 102 alcança            → 1
        cluster_tracking (67%)  meta=ceil(2,01)=3; tracking >= cluster —
                                101: 3>=1, 102: 4>=3, 103: 1>=2 falha   → 2

    O gap é `max(meta_contagem - resultado_contagem, 0)`, logo só
    `cluster_tracking` fica com gap (3 - 2 = 1).
    """
    client = _client_with_mock(EMPRESAS, MONITORAMENTOS, METAS)
    response = client.get("/api/v1/eventos/ciranda-mej-26")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()

    assert data["total_ejs"] == 3

    metas = {meta["tipo"]: meta for meta in data["metas"]}
    assert set(metas) == {
        "faturamento_zero",
        "colab_zero",
        "verde_mes",
        "cluster_tracking",
    }

    faturamento_zero = metas["faturamento_zero"]
    assert faturamento_zero["meta_contagem"] == 3
    assert faturamento_zero["resultado_contagem"] == 3
    assert faturamento_zero["gap_contagem"] == 0

    colab_zero = metas["colab_zero"]
    assert colab_zero["meta_contagem"] == 2
    assert colab_zero["resultado_contagem"] == 3
    assert colab_zero["gap_contagem"] == 0

    verde_mes = metas["verde_mes"]
    assert verde_mes["meta_contagem"] == 1
    assert verde_mes["resultado_contagem"] == 1
    assert [ej["id_ej"] for ej in verde_mes["participantes"]] == [102]
    assert verde_mes["gap_contagem"] == 0

    cluster_tracking = metas["cluster_tracking"]
    assert cluster_tracking["meta_contagem"] == 3
    assert cluster_tracking["resultado_contagem"] == 2
    assert [ej["id_ej"] for ej in cluster_tracking["participantes"]] == [101, 102]
    assert cluster_tracking["gap_contagem"] == 1


def test_evento_nao_encontrado():
    client = TestClient(app)
    response = client.get("/api/v1/eventos/inexistente")
    assert response.status_code == 404