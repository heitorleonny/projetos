"""Utilitários para resolver o campo de cluster por ano."""

from __future__ import annotations


_CLUSTER_COLUMN_BY_YEAR: dict[int, str] = {
    2023: "cluster_2023",
    2024: "cluster_2024",
    2025: "cluster_2025",
    2026: "cluster_2026",
}


def get_cluster_column_name(ano: int) -> str:
    """Retorna o nome da coluna de cluster para o ano informado."""
    return _CLUSTER_COLUMN_BY_YEAR.get(ano, "cluster")


def get_cluster_value_for_year(ej_raw: dict, ano: int) -> int | None:
    """Lê o cluster anual da EJ com fallback para a coluna legada."""
    value = ej_raw.get(get_cluster_column_name(ano))
    if value is None:
        value = ej_raw.get("cluster")
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None
