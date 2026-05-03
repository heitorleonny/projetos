"""
Serviço de empresas juniores.

Responsável por consultar EJs no Supabase e enriquecer
os dados com cálculos estratégicos.
"""

from supabase import Client

from app.models.empresa import (
    Direcao,
    EmpresaComIndicadores,
    EmpresaJunior,
    EmpresaListaResponse,
    EmpresaPerfilCompleto,
    FaturamentoMensal,
    MetaVsRealizado,
    OrdemEmpresa,
    PaginacaoMeta,
)
from app.services.calculo_service import (
    calcular_crescimento,
    calcular_media_csat,
    calcular_percentual_meta,
    calcular_pontos_cluster,
    calcular_pontos_cluster_adaptativo,
    calcular_ritmo_necessario,
    calcular_taxa_colaboracao,
    calcular_tendencia_cluster,
    classificar_cluster,
    classificar_ritmo,
    projetar_faturamento_anual,
)
from app.utils.cluster import get_cluster_column_name, get_cluster_value_for_year
from app.utils.constants import MESES_ANO


# ── Consulta de EJs ──────────────────────────────────────────


def listar_empresas(
    sb: Client,
    *,
    ano: int,
    mes: int | None = None,
    fora_do_zero_colab: bool = False,
    cluster: int | None = None,
    comunidade: str | None = None,
    status: str | None = None,
    search: str | None = None,
    cidade: str | None = None,
    universidade: str | None = None,
    ordem_por: OrdemEmpresa = OrdemEmpresa.nome,
    direcao: Direcao = Direcao.asc,
    page: int = 1,
    page_size: int = 20,
) -> EmpresaListaResponse:
    """
    Lista EJs com filtros, ordenação e paginação.

    Fluxo:
        1. Consulta tabela empresa_junior com filtros
        2. Para cada EJ, busca monitoramento e metas do ano
        3. Calcula indicadores derivados
        4. Ordena e pagina

    Args:
        sb: Cliente Supabase.
        ano: Ano de referência.
        mes: Mês de referência (None = último mês disponível).
        cluster: Filtro por cluster.
        comunidade: Filtro por comunidade.
        status: Filtro por status.
        search: Busca por nome.
        ordem_por: Campo de ordenação.
        direcao: Direção da ordenação (asc/desc).
        page: Página atual.
        page_size: Itens por página.

    Returns:
        EmpresaListaResponse com dados paginados e indicadores.
    """
    # 1. Buscar EJs com filtros
    query = sb.table("empresa_junior").select("*")

    if cluster is not None:
        query = query.eq(get_cluster_column_name(ano), cluster)
    if comunidade:
        query = query.eq("comunidade", comunidade)
    if status:
        query = query.eq("status", status)
    if search:
        query = query.ilike("nome", f"%{search}%")
    if cidade:
        query = query.ilike("cidade", f"%{cidade}%")
    if universidade:
        query = query.ilike("universidade", f"%{universidade}%")

    result = query.execute()
    empresas_raw = result.data or []

    if not empresas_raw:
        return EmpresaListaResponse(
            data=[],
            meta=PaginacaoMeta(page=page, page_size=page_size, total=0, total_pages=0),
        )

    # 2. IDs das EJs encontradas (id_ej é a FK em monitoramento e metas)
    empresa_ids = [e["id_ej"] for e in empresas_raw]

    # 3. Buscar monitoramento do ano
    mon_query = sb.table("monitoramento").select("*").eq("ano", ano).in_("id_ej", empresa_ids)
    if mes is not None:
        mon_query = mon_query.lte("mes", mes)
    monitoramentos = (mon_query.execute()).data or []

    # 4. Buscar metas do ano
    metas = (
        sb.table("metas").select("*").eq("ano", ano).in_("id_ej", empresa_ids).execute()
    ).data or []

    # Indexar por id_ej
    mon_por_empresa: dict[int, list[dict]] = {}
    for m in monitoramentos:
        mon_por_empresa.setdefault(m["id_ej"], []).append(m)

    metas_por_empresa: dict[int, dict] = {}
    for mt in metas:
        metas_por_empresa[mt["id_ej"]] = mt

    # 5. Calcular indicadores
    empresas_com_indicadores: list[EmpresaComIndicadores] = []
    for ej in empresas_raw:
        ind = _calcular_indicadores_ej(
            ej,
            mon_por_empresa.get(ej["id_ej"], []),
            metas_por_empresa.get(ej["id_ej"]),
            ano,
            mes,
        )
        empresas_com_indicadores.append(ind)

    # 5b. Calcular tendência de cluster (requer dados do ano anterior)
    _preencher_tendencia_cluster(sb, empresas_com_indicadores, ano)

    # 5c. Filtro opcional: apenas EJs com ao menos 1 projeto colaborativo vendido
    if fora_do_zero_colab:
        empresas_com_indicadores = [
            ej for ej in empresas_com_indicadores if ej.projetos_colab_totais > 0
        ]

    # 6. Ordenar
    empresas_com_indicadores = _ordenar_empresas(empresas_com_indicadores, ordem_por, direcao)

    # 7. Paginar
    total = len(empresas_com_indicadores)
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    pagina = empresas_com_indicadores[offset : offset + page_size]

    return EmpresaListaResponse(
        data=pagina,
        meta=PaginacaoMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


def buscar_empresa(
    sb: Client,
    id_ej: int,
    *,
    ano: int,
    mes: int | None = None,
) -> EmpresaPerfilCompleto | None:
    """
    Busca o perfil completo de uma EJ individual.

    Inclui série temporal, metas vs realizado, projeção e crescimento.

    Args:
        sb: Cliente Supabase.
        id_ej: Identificador da EJ (campo id_ej).
        ano: Ano de referência.
        mes: Mês de referência (None = último disponível).

    Returns:
        EmpresaPerfilCompleto ou None se EJ não encontrada.
    """
    # Buscar EJ
    result = sb.table("empresa_junior").select("*").eq("id_ej", id_ej).execute()
    if not result.data:
        return None
    ej_raw = result.data[0]
    empresa = EmpresaJunior(**{**ej_raw, "cluster": get_cluster_value_for_year(ej_raw, ano)})

    # Monitoramento do ano (todos os meses)
    mon_ano = (
        sb.table("monitoramento")
        .select("*")
        .eq("id_ej", ej_raw["id_ej"])
        .eq("ano", ano)
        .order("mes")
        .execute()
    ).data or []

    # Metas do ano
    metas_result = (
        sb.table("metas")
        .select("*")
        .eq("id_ej", ej_raw["id_ej"])
        .eq("ano", ano)
        .execute()
    ).data or []
    meta_raw = metas_result[0] if metas_result else None

    # Filtrar meses até o mês de referência
    if mes is not None:
        mon_filtrado = [m for m in mon_ano if m["mes"] <= mes]
    else:
        mon_filtrado = mon_ano

    # Indicadores
    indicadores = _calcular_indicadores_ej(ej_raw, mon_filtrado, meta_raw, ano, mes)

    # Tendência de cluster
    _preencher_tendencia_cluster(sb, [indicadores], ano)

    # Série mensal (todos os meses disponíveis até o filtro)
    colab_acumulado = 0.0
    serie_mensal = []
    for m in mon_filtrado:
        colab_acumulado += float(m.get("faturamento_colab_mes", 0) or 0)
        fat_acum_mes = float(m.get("faturamento_acumulado", 0) or 0)
        taxa_colab_mes = (
            round(colab_acumulado / fat_acum_mes, 4) if fat_acum_mes > 0 else None
        )
        serie_mensal.append(FaturamentoMensal(
            mes=m["mes"],
            faturamento=float(m.get("faturamento_mes", 0) or 0),
            faturamento_colab=float(m.get("faturamento_colab_mes", 0) or 0),
            faturamento_colab_acumulado=colab_acumulado,
            taxa_colaboracao=taxa_colab_mes,
            projetos_vendidos=int(m.get("projetos_vendidos_mes", 0) or 0),
            projetos_colab_vendidos=int(m.get("projetos_colab_mes", 0) or 0),
            csat=m.get("csat"),
        ))

    # Metas vs realizado
    metas_vs = None
    if meta_raw:
        fat_acum = indicadores.faturamento_acumulado
        metas_vs = MetaVsRealizado(
            meta_faturamento=meta_raw.get("meta_faturamento"),
            faturamento_acumulado=fat_acum,
            percentual_meta=indicadores.percentual_meta or 0,
            meta_csat=meta_raw.get("meta_csat"),
            csat_medio=indicadores.csat_medio,
            meta_taxa_colaboracao=meta_raw.get("meta_taxa_colaboracao"),
            taxa_colaboracao=indicadores.taxa_colaboracao,
            meta_projetos_impacto=meta_raw.get("meta_projetos_impacto"),
            meta_engajamento_mej=meta_raw.get("meta_engajamento_mej"),
            engajamento_mej=indicadores.engajamento_mej,
        )

    # Projeção anual
    faturamentos_mensais = [m.faturamento for m in serie_mensal]
    projecao = projetar_faturamento_anual(faturamentos_mensais)

    # Ritmo necessário
    meses_restantes = MESES_ANO - len(serie_mensal)
    meta_fat = meta_raw.get("meta_faturamento") if meta_raw else None
    ritmo_necessario = calcular_ritmo_necessario(
        meta_fat, indicadores.faturamento_acumulado, meses_restantes
    )

    # Crescimento mensal (último mês vs penúltimo)
    crescimento_mensal = None
    if len(faturamentos_mensais) >= 2:
        crescimento_mensal = calcular_crescimento(
            faturamentos_mensais[-1], faturamentos_mensais[-2]
        )

    # Crescimento anual (buscar ano anterior)
    crescimento_anual = _calcular_crescimento_anual(
        sb, ej_raw["id_ej"], ano, indicadores.faturamento_acumulado
    )

    # Índice de Cluster (snapshot com valores reais acumulados)
    indice_cluster = None
    indice_cluster_calc = None
    if (
        indicadores.csat_medio is not None
        and indicadores.engajamento_mej is not None
        and indicadores.faturamento_acumulado > 0
    ):
        indice = calcular_pontos_cluster(
            indicadores.faturamento_acumulado,
            indicadores.csat_medio,
            indicadores.engajamento_mej,
            indicadores.taxa_colaboracao or 0.0,
        )
        indice_cluster = round(indice, 2)
        indice_cluster_calc = classificar_cluster(indice)

    # Índice real com meta de CSAT (fat real × meta_csat × engajamento real × colab real)
    indice_meta_csat = None
    indice_meta_csat_calc = None
    if meta_raw and indicadores.engajamento_mej is not None and indicadores.faturamento_acumulado > 0:
        meta_csat_para_indice = meta_raw.get("meta_csat")
        if meta_csat_para_indice:
            indice_mc = calcular_pontos_cluster(
                indicadores.faturamento_acumulado,
                meta_csat_para_indice,
                indicadores.engajamento_mej,
                indicadores.taxa_colaboracao or 0.0,
            )
            indice_meta_csat = round(indice_mc, 2)
            indice_meta_csat_calc = classificar_cluster(indice_mc)

    # Tracking de Cluster (anualização simples × metas de qualidade)
    tracking_cluster = None
    tracking_cluster_calc = None
    if meta_raw and serie_mensal and indicadores.faturamento_acumulado > 0:
        meta_csat_val = meta_raw.get("meta_csat")
        meta_eng_val = float(meta_raw.get("meta_engajamento_mej") or 0) / 100
        mes_atual_num = serie_mensal[-1].mes
        if meta_csat_val and mes_atual_num > 0:
            fat_anualizado = (indicadores.faturamento_acumulado / mes_atual_num) * MESES_ANO
            tracking = calcular_pontos_cluster(
                fat_anualizado,
                meta_csat_val,
                meta_eng_val,
                indicadores.taxa_colaboracao or 0.0,
            )
            tracking_cluster = round(tracking, 2)
            tracking_cluster_calc = classificar_cluster(tracking)

    return EmpresaPerfilCompleto(
        empresa=empresa,
        indicadores=indicadores,
        serie_mensal=serie_mensal,
        metas=metas_vs,
        projecao_anual=projecao,
        ritmo_necessario=ritmo_necessario,
        crescimento_mensal=crescimento_mensal,
        crescimento_anual=crescimento_anual,
        indice_cluster=indice_cluster,
        indice_cluster_calculado=indice_cluster_calc,
        indice_meta_csat=indice_meta_csat,
        indice_meta_csat_calculado=indice_meta_csat_calc,
        tracking_cluster=tracking_cluster,
        tracking_cluster_calculado=tracking_cluster_calc,
    )


def comparar_empresas(
    sb: Client,
    ids_ej: list[int],
    *,
    ano: int,
    mes: int | None = None,
) -> list[EmpresaComIndicadores]:
    """
    Compara múltiplas EJs lado a lado.

    Args:
        sb: Cliente Supabase.
        ids_ej: Lista de id_ej para comparar (max 10).
        ano: Ano de referência.
        mes: Mês de referência.

    Returns:
        Lista de EmpresaComIndicadores ordenada por faturamento desc.
    """
    # Buscar EJs
    result = sb.table("empresa_junior").select("*").in_("id_ej", ids_ej).execute()
    empresas_raw = result.data or []

    if not empresas_raw:
        return []

    empresa_ids = [e["id_ej"] for e in empresas_raw]

    # Monitoramento
    mon_query = sb.table("monitoramento").select("*").eq("ano", ano).in_("id_ej", empresa_ids)
    if mes is not None:
        mon_query = mon_query.lte("mes", mes)
    monitoramentos = (mon_query.execute()).data or []

    # Metas
    metas = (
        sb.table("metas").select("*").eq("ano", ano).in_("id_ej", empresa_ids).execute()
    ).data or []

    mon_por_empresa: dict[int, list[dict]] = {}
    for m in monitoramentos:
        mon_por_empresa.setdefault(m["id_ej"], []).append(m)

    metas_por_empresa: dict[int, dict] = {}
    for mt in metas:
        metas_por_empresa[mt["id_ej"]] = mt

    resultado: list[EmpresaComIndicadores] = []
    for ej in empresas_raw:
        ind = _calcular_indicadores_ej(
            ej,
            mon_por_empresa.get(ej["id_ej"], []),
            metas_por_empresa.get(ej["id_ej"]),
            ano,
            mes,
        )
        resultado.append(ind)

    # Calcular tendência de cluster
    _preencher_tendencia_cluster(sb, resultado, ano)

    # Ordenar por faturamento decrescente
    resultado.sort(key=lambda x: x.faturamento_acumulado, reverse=True)
    return resultado


# ── Helpers privados ─────────────────────────────────────────


def _calcular_indicadores_ej(
    ej_raw: dict,
    monitoramentos: list[dict],
    meta_raw: dict | None,
    ano: int,
    mes: int | None,
) -> EmpresaComIndicadores:
    """
    Calcula todos os indicadores derivados de uma EJ.

    Args:
        ej_raw: Dados brutos da EJ (dict do Supabase).
        monitoramentos: Lista de registros de monitoramento.
        meta_raw: Dados brutos da meta (dict do Supabase).
        mes: Mês de referência.
    """
    # Acumulados — pegar o registro do último mês disponível
    monitoramentos_sorted = sorted(monitoramentos, key=lambda m: m["mes"])

    faturamento_acum = 0.0
    faturamento_colab_acum = 0.0
    projetos_totais = 0
    projetos_colab_totais = 0
    faturamento_mes_atual = 0.0

    if monitoramentos_sorted:
        ultimo = monitoramentos_sorted[-1]
        faturamento_acum = float(ultimo.get("faturamento_acumulado", 0) or 0)
        faturamento_colab_acum = sum(
            float(m.get("faturamento_colab_mes", 0) or 0) for m in monitoramentos_sorted
        )
        projetos_totais = int(ultimo.get("projetos_totais", 0) or 0)
        if not projetos_totais:
            projetos_totais = sum(int(m.get("projetos_vendidos_mes", 0) or 0) for m in monitoramentos_sorted)
        projetos_colab_totais = sum(
            int(m.get("projetos_colab_mes", 0) or 0) for m in monitoramentos_sorted
        )
        faturamento_mes_atual = float(ultimo.get("faturamento_mes", 0) or 0)

    # CSAT médio
    valores_csat = [m.get("csat") for m in monitoramentos_sorted]
    csat_medio = calcular_media_csat(valores_csat)

    # Engajamento MEJ real: max(membros_engajados_mes) / numero_membros
    # membros_engajados_mes é 0 nos meses sem evento MEJ, então o máximo
    # representa o melhor mês e reflete o alcance real do engajamento.
    engajamento_real = None
    if monitoramentos_sorted:
        numero_membros = int(monitoramentos_sorted[-1].get("numero_membros") or 0)
        max_engajados = max(
            int(m.get("membros_engajados_mes") or 0) for m in monitoramentos_sorted
        )
        if numero_membros > 0:
            engajamento_real = round(max_engajados / numero_membros, 4)

    # Meta
    meta_fat = meta_raw.get("meta_faturamento") if meta_raw else None

    # Percentual meta
    percentual_meta = calcular_percentual_meta(faturamento_acum, meta_fat)

    # Ritmo
    ritmo = classificar_ritmo(faturamento_mes_atual, meta_fat)

    # Taxa de colaboração
    taxa_colab = calcular_taxa_colaboracao(faturamento_colab_acum, faturamento_acum)

    # Pontuação de cluster adaptativa (varia por fase do ano)
    # Fase 1 (Q1): meta_csat + meta_engajamento
    # Fase 2 (Q2): meta_csat + engajamento condicional
    # Fase 3 (Q3/Q4): csat_real + engajamento_real
    meta_csat = meta_raw.get("meta_csat") if meta_raw else None
    meta_engajamento = meta_raw.get("meta_engajamento_mej") if meta_raw else None
    mes_atual = monitoramentos_sorted[-1]["mes"] if monitoramentos_sorted else 0

    pontos = calcular_pontos_cluster_adaptativo(
        faturamento_acumulado=faturamento_acum,
        mes_atual=mes_atual,
        meta_csat=meta_csat,
        csat_real=csat_medio,
        meta_engajamento_mej=meta_engajamento,
        engajamento_real=engajamento_real,
        taxa_colaboracao=taxa_colab,
    )
    cluster_calc = classificar_cluster(pontos) if pontos is not None else None

    # Tracking de Cluster — replica exatamente o cenário 3 da rede_service:
    # sem mons → mantendo; fat=0 → cluster 1; sem meta_csat → mantendo; com tudo → fórmula
    cluster_atual_val = get_cluster_value_for_year(ej_raw, ano) or 1
    tracking_cluster_val = None
    tracking_cluster_calc: int
    if not monitoramentos_sorted:
        tracking_cluster_calc = cluster_atual_val
    elif faturamento_acum <= 0:
        tracking_cluster_calc = 1
    else:
        meta_csat_val = meta_raw.get("meta_csat") if meta_raw else None
        if meta_csat_val and mes_atual > 0:
            meta_eng_val = float(meta_raw.get("meta_engajamento_mej") or 0) / 100
            fat_anualizado = (faturamento_acum / mes_atual) * MESES_ANO
            tracking = calcular_pontos_cluster(
                fat_anualizado,
                meta_csat_val,
                meta_eng_val,
                taxa_colab or 0.0,
            )
            tracking_cluster_val = round(tracking, 2)
            tracking_cluster_calc = classificar_cluster(tracking)
        else:
            tracking_cluster_calc = cluster_atual_val

    return EmpresaComIndicadores(
        id=ej_raw["id"],
        id_ej=ej_raw["id_ej"],
        nome=ej_raw["nome"],
        cluster=get_cluster_value_for_year(ej_raw, ano),
        comunidade=ej_raw.get("comunidade"),
        status=ej_raw.get("status"),
        foto_url=ej_raw.get("foto_url"),
        cidade=ej_raw.get("cidade"),
        universidade=ej_raw.get("universidade"),
        faturamento_acumulado=faturamento_acum,
        faturamento_colab_acumulado=faturamento_colab_acum,
        faturamento_mes=faturamento_mes_atual,
        projetos_totais=projetos_totais,
        projetos_colab_totais=projetos_colab_totais,
        csat_medio=csat_medio,
        percentual_meta=percentual_meta,
        ritmo=ritmo,
        taxa_colaboracao=taxa_colab,
        engajamento_mej=engajamento_real,
        pontos_cluster=round(pontos, 2) if pontos is not None else None,
        cluster_calculado=cluster_calc,
        tendencia_cluster=None,
        tracking_cluster=tracking_cluster_val,
        tracking_cluster_calculado=tracking_cluster_calc,
    )


def _ordenar_empresas(
    empresas: list[EmpresaComIndicadores],
    ordem_por: OrdemEmpresa,
    direcao: Direcao,
) -> list[EmpresaComIndicadores]:
    """Ordena a lista de empresas pelo campo e direção informados."""
    reverse = direcao == Direcao.desc

    key_map = {
        OrdemEmpresa.nome: lambda e: (e.nome or "").lower(),
        OrdemEmpresa.faturamento: lambda e: e.faturamento_acumulado,
        OrdemEmpresa.faturamento_colab: lambda e: e.faturamento_colab_acumulado,
        OrdemEmpresa.cluster: lambda e: e.cluster or 0,
        OrdemEmpresa.comunidade: lambda e: (e.comunidade or "").lower(),
        OrdemEmpresa.csat: lambda e: e.csat_medio or 0,
        OrdemEmpresa.percentual_meta: lambda e: e.percentual_meta or 0,
        OrdemEmpresa.projetos: lambda e: e.projetos_totais,
    }

    key_fn = key_map.get(ordem_por, key_map[OrdemEmpresa.nome])
    return sorted(empresas, key=key_fn, reverse=reverse)


def _calcular_crescimento_anual(
    sb: Client,
    id_ej: int,
    ano: int,
    faturamento_atual: float,
) -> float | None:
    """Busca o faturamento do ano anterior e calcula o crescimento percentual."""
    ano_anterior = ano - 1
    result = (
        sb.table("monitoramento")
        .select("faturamento_acumulado")
        .eq("id_ej", id_ej)
        .eq("ano", ano_anterior)
        .order("mes", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    fat_anterior = float(result.data[0].get("faturamento_acumulado", 0) or 0)
    return calcular_crescimento(faturamento_atual, fat_anterior)


def _preencher_tendencia_cluster(
    sb: Client,
    empresas: list[EmpresaComIndicadores],
    ano: int,
) -> None:
    """
    Preenche a tendência de cluster para uma lista de EJs,
    comparando o cluster_calculado (projeção dinâmica) com o
    cluster oficial atribuído à EJ.

    Resultado: sobe / mantém / desce.
    """
    for emp in empresas:
        emp.tendencia_cluster = calcular_tendencia_cluster(
            emp.cluster_calculado, emp.cluster
        )
