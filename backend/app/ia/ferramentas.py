"""Catálogo somente leitura, executado com o cliente autenticado da requisição."""

from app.models.ia import LinhaResposta, PlanoConsulta, RespostaRede
from app.services.empresa_service import listar_empresas
from app.services.leitura import ler_todas
from app.services.rede_service import (calcular_indicadores_rede, gerar_ranking_com_exclusoes,
                                       calcular_sde_cenarios, calcular_ritmo_mensal)
from app.services.cluster_service import buscar_ids_por_cluster
from app.services.tenant import filtrar_por_tenant
from app.ia.conversa import esclarecer
from app.ia.glossario import explicar, recusar_conceito


def executar_consulta(sb, plano: PlanoConsulta, *, federacao_id: int, ano_padrao: int) -> RespostaRede:
    if federacao_id is None:
        raise ValueError("Consulta exige federação autenticada.")
    if plano.ferramenta == "esclarecer":
        return esclarecer(plano.esclarecimento, plano)
    if plano.ferramenta == "explicar":
        # Glossário curado e nacional: nenhuma leitura do banco. Filtros de dado
        # num pedido de definição seriam descartados em silêncio; por isso recusa.
        if plano.conceito is None or any(getattr(plano, campo) is not None
                                         for campo in ("busca", "cluster", "criterio", "limite")):
            return recusar_conceito()
        return explicar(plano.conceito)
    if plano.conceito is not None:
        return recusar_conceito()
    if plano.ordem == "asc" and plano.ferramenta != "ranking":
        # Menores valores fora do ranking seriam ignorados em silêncio.
        return RespostaRede(status="fora_do_catalogo", resposta=(
            "Ordenar pelos menores valores está disponível só no ranking por faturamento, CSAT, "
            "projetos ou faturamento colaborativo."
        ))
    if plano.ferramenta == "recusar" or (plano.busca and plano.ferramenta != "fora_do_zero"):
        return RespostaRede(status="fora_do_catalogo", resposta=(
            "Posso consultar EJs fora do zero, indicadores, rankings, ritmo mensal e SDE da sua federação, "
            "com filtro de cluster, e explicar os indicadores. Busca por nome está disponível nas EJs fora do zero. "
            "Para rankings, indique faturamento, CSAT, projetos ou faturamento colaborativo."
        ))
    ano = plano.ano if plano.ano is not None else ano_padrao
    empresas = ler_todas(sb, "empresa_junior", "id_ej,nome", lambda q: filtrar_por_tenant(q, federacao_id))
    if plano.cluster is not None:
        ids_cluster = set(buscar_ids_por_cluster(sb, ano=ano, cluster=plano.cluster))
        empresas = [e for e in empresas if e["id_ej"] in ids_cluster]
    if plano.busca:
        empresas = [e for e in empresas if plano.busca.casefold() in e.get("nome", "").casefold()]
    ids = [e["id_ej"] for e in empresas]
    meses = ler_todas(
        sb, "monitoramento", "id_ej,mes",
        lambda q: q.in_("id_ej", ids).eq("ano", ano),
    ) if ids else []
    mes = plano.mes if plano.mes is not None else max((m["mes"] for m in meses), default=None)
    cobertos = {m["id_ej"] for m in meses if m["mes"] == mes}
    if not cobertos or cobertos != set(ids):
        periodo = f"{mes:02d}/{ano}" if mes is not None else str(ano)
        completos = [m for m in range(1, 13) if ids and
                     {r["id_ej"] for r in meses if r["mes"] == m} == set(ids)]
        sugestoes = [f"E em {m:02d}/{ano}" + (f" no cluster {plano.cluster}" if plano.cluster else "") + "?" for m in completos[-3:]]
        return RespostaRede(status="sem_dados", ano=ano, mes=mes, sugestoes=sugestoes, resposta=(
            f"Não há dados completos para {periodo} na sua federação "
            f"({len(cobertos)} de {len(ids)} EJs com monitoramento). "
            "Não substituí o período solicitado por outro mês."
            + (" Meses com dados completos: " + ", ".join(f"{m:02d}/{ano}" for m in completos) + "." if completos else "")
        ))
    periodo = f"{mes:02d}/{ano}"
    recorte = f" do cluster {plano.cluster}" if plano.cluster is not None else ""
    if plano.busca:
        recorte += f" com nome contendo {plano.busca!r}"
    if plano.ferramenta == "fora_do_zero":
        # A classificação usa o acumulado já calculado pelo service; todas as
        # páginas entram antes do filtro, inclusive nas federações maiores.
        ejs = []
        pagina = 1
        while True:
            lote = listar_empresas(sb, ano=ano, mes=mes, federacao_id=federacao_id, page=pagina, page_size=100,
                                   cluster=plano.cluster)
            ejs.extend(lote.data)
            if pagina >= lote.meta.total_pages:
                break
            pagina += 1
        linhas = [LinhaResposta(id_ej=e.id_ej, nome=e.nome, valor=e.faturamento_acumulado)
                  for e in ejs if e.faturamento_acumulado > 0
                  and (not plano.busca or plano.busca.casefold() in e.nome.casefold())]
        return RespostaRede(status="respondida", resposta=(
            f"{len(linhas)} EJs{recorte} estão fora do zero em {periodo}: faturamento acumulado no ano maior que zero."
        ), fonte="empresa_service.listar_empresas", ano=ano, mes=mes, total=len(linhas), linhas=linhas, unidade="moeda")
    if plano.ferramenta == "ranking":
        criterio = plano.criterio or "faturamento"
        ordem = plano.ordem or "desc"
        ranking, sem_coleta = gerar_ranking_com_exclusoes(
            sb, ano=ano, mes=mes, federacao_id=federacao_id, criterio=criterio, limit=plano.limite or 10,
            cluster=plano.cluster, ordem=ordem)
        linhas = [LinhaResposta(id_ej=e.id_ej, nome=e.nome, valor=e.valor) for e in ranking]
        if ordem == "asc":
            texto = f"Menores valores de {criterio}{recorte} em {periodo}."
            if sem_coleta:
                texto += (f" {sem_coleta} EJ{'s' if sem_coleta > 1 else ''} sem coleta de {criterio} no período "
                          f"ficou{'aram' if sem_coleta > 1 else ''} fora do ranking.")
        else:
            texto = f"Ranking por {criterio}{recorte} em {periodo}."
        return RespostaRede(status="respondida", resposta=texto,
                            fonte="rede_service.gerar_ranking", ano=ano, mes=mes, linhas=linhas, total=len(linhas),
                            unidade="moeda" if criterio in ("faturamento", "colab") else "numero")
    if plano.ferramenta == "sde":
        sde = calcular_sde_cenarios(sb, ano=ano, mes=mes, federacao_id=federacao_id, cluster=plano.cluster)
        return RespostaRede(status="respondida", resposta=f"Cenários de SDE{recorte} em {periodo}.",
                            fonte="rede_service.calcular_sde_cenarios", ano=ano, mes=mes,
                            total=len(sde.cenarios), linhas=[LinhaResposta(nome=c.nome, valor=c.sde, unidade="numero")
                                                            for c in sde.cenarios])
    if plano.ferramenta == "ritmo_mensal":
        ritmo = calcular_ritmo_mensal(sb, ano=ano, federacao_id=federacao_id, cluster=plano.cluster)
        item = next(r for r in ritmo.meses if r.mes == mes)
        return RespostaRede(status="respondida", resposta=(
            f"Ritmo mensal{recorte} em {periodo}, calculado sobre as vendas do mês. "
            "Fora do zero usa o acumulado anual; são medidas diferentes."
        ), fonte="rede_service.calcular_ritmo_mensal", ano=ano, mes=mes, total=3, linhas=[
            LinhaResposta(nome="Sem vendas", valor=item.total_ejs - item.ejs_ritmo_minimo - item.ejs_ritmo_significativo),
            LinhaResposta(nome="Ritmo mínimo", valor=item.ejs_ritmo_minimo),
            LinhaResposta(nome="Ritmo significativo", valor=item.ejs_ritmo_significativo)])
    indicadores = calcular_indicadores_rede(sb, ano=ano, mes=mes, federacao_id=federacao_id, cluster=plano.cluster)
    # Projeção explícita: nada de CNPJ, contatos ou dados brutos na resposta.
    return RespostaRede(status="respondida", resposta=(
        f"Indicadores da rede{recorte} em {periodo}: {indicadores.total_ejs} EJs, "
        f"{indicadores.ejs_fora_do_zero} fora do zero e {indicadores.total_projetos} projetos."
    ), fonte="rede_service.calcular_indicadores_rede", ano=ano, mes=mes, total=6, unidade="numero",
        linhas=[LinhaResposta(nome="Faturamento acumulado", valor=indicadores.faturamento_total, unidade="moeda"),
                LinhaResposta(nome="Faturamento colaborativo acumulado", valor=indicadores.faturamento_colab_total, unidade="moeda"),
                LinhaResposta(nome="Total de EJs", valor=indicadores.total_ejs),
                LinhaResposta(nome="EJs fora do zero", valor=indicadores.ejs_fora_do_zero),
                LinhaResposta(nome="Projetos", valor=indicadores.total_projetos),
                LinhaResposta(nome="CSAT médio", valor=indicadores.media_csat)])
