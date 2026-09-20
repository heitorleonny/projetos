"""Utilitário para ler o cluster de uma EJ num ano."""

from __future__ import annotations


def get_cluster_value_for_year(historico: dict[int, int], id_ej: int) -> int | None:
    """
    Lê o cluster de uma EJ a partir do histórico já carregado.

    `historico` é um mapa `{id_ej: cluster}` DE UM ANO SÓ, montado por quem
    chama com uma consulta em lote a `cluster_historico`
    (`app/services/cluster_service.py`). O ano não é parâmetro aqui de
    propósito: se fosse, esta função precisaria do ano E do mapa, e a tentação
    seria consultar o banco por EJ — que é o N+1 que o desenho evita.

    Antes da migração 08 esta função lia `ej_raw["cluster_2026"]` com fallback
    para `ej_raw["cluster"]`. As colunas viraram `cluster_historico`
    (uma linha por EJ por ano); a regra de fallback foi aplicada uma vez, no
    backfill, e não se repete em tempo de leitura.

    Devolve `None` quando a EJ não tem cluster registrado naquele ano — o que
    passou a ser distinguível de "cluster de outro ano", e é informação.
    """
    valor = historico.get(id_ej)
    if valor is None:
        return None

    try:
        return int(valor)
    except (TypeError, ValueError):
        return None
