"""
Filtro de tenant aplicado no código, ao lado da Row Level Security.

POR QUE FILTRAR DE NOVO, SE A RLS JÁ FILTRA

Não é redundância por descuido: são duas camadas independentes, e cada uma
cobre a falha da outra.

    * Se a política de RLS estiver errada (ou desligada numa tabela nova, ou
      não aplicada ainda num ambiente), o `.eq("federacao_id", ...)` daqui
      segura.
    * Se alguém apagar este filtro num refactor — e isso acontece, porque ele
      parece redundante justamente quando está funcionando —, a política
      segura.

As duas juntas erram só quando as duas falham ao mesmo tempo, por motivos
diferentes, no mesmo dia. Separadas, qualquer uma sozinha basta.

Ver infra/db/init/07-rls-policies.sql e docs/adr-002-rls-local-sem-stack-completa.md.
"""


def filtrar_por_tenant(query, federacao_id: int | None):
    """
    Adiciona `federacao_id = <tenant>` à consulta, quando há tenant conhecido.

    `federacao_id=None` significa token sem o claim — situação de todos os
    tokens enquanto o Custom Access Token Hook não for ativado no Supabase.
    Nesse caso a consulta sai sem o filtro e o isolamento fica por conta da
    RLS; `settings.TENANT_CLAIM_OBRIGATORIO` existe para transformar essa
    situação em 403 assim que o hook entrar no ar.

    Só se aplica a `empresa_junior`: é a tabela que tem a coluna. `metas` e
    `monitoramento` são consultadas por `in_("id_ej", ...)` a partir das EJs já
    filtradas, então herdam o recorte — além de terem política própria no banco.
    """
    if federacao_id is None:
        return query
    return query.eq("federacao_id", federacao_id)
