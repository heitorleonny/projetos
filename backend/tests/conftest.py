"""
Fixtures compartilhadas para os testes do Portal FEJEPE.
"""

import os

# Garantir variáveis de ambiente para testes (antes de qualquer import da app)
#
# São duas chaves desde a separação anon/service: a anônima é a do caminho de
# request (respeita RLS) e é a única que os testes precisam. Nenhum valor aqui
# é real — nada nesta suíte fala com o Supabase de verdade.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--require-lab", action="store_true", default=False,
        help="Falha se houver teste pulado; usado na verificação completa com Postgres.",
    )


def pytest_sessionfinish(session, exitstatus):
    # Uma verificação completa não pode parecer bem-sucedida com a RLS pulada.
    if session.config.getoption("--require-lab"):
        terminal = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminal and terminal.stats.get("skipped"):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


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
