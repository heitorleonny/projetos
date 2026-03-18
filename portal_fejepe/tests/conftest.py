"""
Fixtures compartilhadas para os testes do Portal FEJEPE.
"""

import os

# Garantir variáveis de ambiente para testes (antes de qualquer import da app)
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

import pytest


# ── Dados fake de EJs ────────────────────────────────────────


@pytest.fixture
def ej_cluster1() -> dict:
    """EJ de cluster 1 — baixo desempenho, sem vendas no mês."""
    return {
        "id": 1,
        "id_ej": 101,
        "nome": "EJ Alpha",
        "cnpj": "00.000.000/0001-01",
        "cluster": 1,
        "comunidade": "Comunidade A",
        "status": "ativa",
        "foto_url": None,
    }


@pytest.fixture
def ej_cluster3() -> dict:
    """EJ de cluster 3 — desempenho médio."""
    return {
        "id": 2,
        "id_ej": 102,
        "nome": "EJ Beta",
        "cnpj": "00.000.000/0001-02",
        "cluster": 3,
        "comunidade": "Comunidade B",
        "status": "ativa",
        "foto_url": None,
    }


@pytest.fixture
def ej_cluster5() -> dict:
    """EJ de cluster 5 — alto desempenho."""
    return {
        "id": 3,
        "id_ej": 103,
        "nome": "EJ Gamma",
        "cnpj": "00.000.000/0001-03",
        "cluster": 5,
        "comunidade": "Comunidade A",
        "status": "ativa",
        "foto_url": None,
    }


# ── Dados fake de metas ─────────────────────────────────────


@pytest.fixture
def meta_ej_alpha() -> dict:
    """Meta anual da EJ Alpha (cluster 1)."""
    return {
        "id": 1,
        "id_ej": 101,
        "ano": 2026,
        "meta_faturamento": 120_000,
        "meta_taxa_colaboracao": 0.15,
        "meta_csat": 4.5,
        "meta_projetos_impacto": 2,
        "meta_pdi": True,
        "meta_engajamento_mej": 0.25,
    }


@pytest.fixture
def meta_ej_beta() -> dict:
    """Meta anual da EJ Beta (cluster 3)."""
    return {
        "id": 2,
        "id_ej": 102,
        "ano": 2026,
        "meta_faturamento": 600_000,
        "meta_taxa_colaboracao": 0.20,
        "meta_csat": 4.8,
        "meta_projetos_impacto": 5,
        "meta_pdi": True,
        "meta_engajamento_mej": 0.30,
    }
