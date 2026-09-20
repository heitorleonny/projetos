"""
Acesso a `cluster_historico` — o cluster de cada EJ por ano.

Até a migração 08 o cluster era uma coluna por ano em `empresa_junior`
(`cluster_2023`…`cluster_2026`), então ler ou filtrar por cluster não custava
consulta nenhuma: vinha junto no `select("*")`. Agora é uma tabela, e o custo
existe — por isso as duas funções daqui são EM LOTE, nunca por EJ.

A regra, e ela não é estilística: **uma consulta por página de resultado, nunca
uma por EJ**. Uma listagem de 20 EJs que chamasse o banco uma vez por linha faria
21 idas ao PostgREST; com 1.484 EJs federadas no país, o mesmo padrão numa tela
de rede inteira derruba o tempo de resposta. Se um refactor futuro fizer estas
funções serem chamadas dentro de um laço, o refactor está errado.

O idioma é o mesmo que `metas` e `monitoramento` já usam neste código para se
relacionar com `empresa_junior`: buscar os `id_ej` primeiro, depois `.in_`.
Nada de join embutido do PostgREST (`select("*, cluster_historico(...)")`) —
um segundo idioma para a mesma coisa custaria mais do que a economia de linhas.
"""

from supabase import Client


def buscar_ids_por_cluster(sb: Client, *, ano: int, cluster: int) -> list[int]:
    """
    `id_ej` de todas as EJs que estavam no cluster informado, naquele ano.

    Devolve lista vazia quando nenhuma EJ está nesse cluster — e nesse caso
    quem chama não precisa nem rodar a consulta principal.
    """
    resposta = (
        sb.table("cluster_historico")
        .select("id_ej")
        .eq("ano", ano)
        .eq("cluster", cluster)
        .execute()
    )
    return [linha["id_ej"] for linha in (resposta.data or [])]


def buscar_historico_do_ano(sb: Client, *, ano: int, ids_ej: list[int]) -> dict[int, int]:
    """
    Mapa `{id_ej: cluster}` do ano, para as EJs informadas.

    É o formato que `get_cluster_value_for_year` espera. Uma chamada resolve a
    página inteira.
    """
    if not ids_ej:
        return {}

    resposta = (
        sb.table("cluster_historico")
        .select("id_ej,cluster")
        .eq("ano", ano)
        .in_("id_ej", list(ids_ej))
        .execute()
    )
    return {linha["id_ej"]: linha["cluster"] for linha in (resposta.data or [])}
