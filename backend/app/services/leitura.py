"""
Leitura completa de uma consulta ao PostgREST, página por página.

POR QUE ISTO EXISTE

O PostgREST devolve no máximo `max_rows` linhas por requisição (1000 no
`supabase/config.toml` da demo e no padrão do Supabase). Passado esse teto,
ele NÃO dá erro: corta a resposta e segue. `.limit(10000)` do lado do cliente
não adianta, porque o teto é do servidor.

Enquanto o portal servia só a FEJEPE (43 EJs × 12 meses = 516 linhas de
monitoramento por ano), ninguém encostou nisso. A FEJEMG tem 291 EJs, e 2.619
linhas em 2026: chegavam 1000, e 139 EJs apareciam com faturamento R$ 0 em
todas as telas. Medido em 29/09/2026 — ver
docs/achado-9.17-limites-com-segundo-tenant.md.

A REGRA

Toda consulta de VÁRIAS EJs (a federação inteira, uma página de resultado)
passa por `ler_todas`. Consulta de UMA EJ (no máximo 12 meses) não precisa.

Uma consulta nova é montada por página porque o query builder do
`postgrest-py` é mutável: chamar `.range()` duas vezes no mesmo objeto
ACUMULA `offset`/`limit` na URL em vez de substituir.
"""

from collections.abc import Callable, Sequence
from typing import Any

from app.database import Client

# Igual ao `max_rows` do servidor. Se o servidor tiver um teto MENOR, a leitura
# continua correta: o avanço é pelo tamanho do lote recebido, não por este valor.
TAMANHO_PAGINA = 1000


class LeituraIncompleta(RuntimeError):
    """O banco disse que havia N linhas e a paginação trouxe menos."""


def ler_todas(
    sb: Client,
    tabela: str,
    colunas: str = "*",
    filtros: Callable[[Any], Any] = lambda consulta: consulta,
    *,
    ordem: Sequence[str] = ("id",),
) -> list[dict]:
    """
    Todas as linhas de `tabela` que casam com `filtros`, sem o corte do servidor.

    Args:
        sb: Cliente Supabase da requisição (com o token do usuário — a RLS vale).
        tabela: Nome da tabela.
        colunas: Colunas do `select`.
        filtros: Função que recebe a consulta e devolve a consulta filtrada.
            É chamada uma vez por página.
        ordem: Colunas que identificam a linha de forma única. Sem ordem
            estável, o PostgREST pode repetir ou pular linhas entre páginas.

    Raises:
        LeituraIncompleta: quando o total informado pelo banco (`count`) não
            fecha com o que foi lido. Número errado em silêncio é justamente o
            defeito que esta função existe para impedir.
    """
    linhas: list[dict] = []
    total: int | None = None

    while True:
        consulta = filtros(sb.table(tabela).select(colunas, count="exact"))
        for coluna in ordem:
            consulta = consulta.order(coluna)
        inicio = len(linhas)
        resposta = consulta.range(inicio, inicio + TAMANHO_PAGINA - 1).execute()

        lote = resposta.data or []
        if total is None:
            contagem = getattr(resposta, "count", None)
            # Só um inteiro conta como total: o PostgREST devolve `None` quando
            # não foi pedido `count`, e isso não pode virar "zero linhas".
            total = contagem if isinstance(contagem, int) else None
        linhas.extend(lote)

        if not lote:
            break
        if total is not None:
            if len(linhas) >= total:
                break
        elif len(lote) < TAMANHO_PAGINA:
            break

    if total is not None and len(linhas) < total:
        raise LeituraIncompleta(
            f"{tabela}: o banco informou {total} linhas e a leitura trouxe {len(linhas)}."
        )
    return linhas
