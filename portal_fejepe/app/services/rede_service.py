"""
Serviço de indicadores da rede FEJEPE.

Calcula KPIs consolidados: faturamento total, SDE, distribuição
por cluster, participação por comunidade, etc.
"""

from supabase import Client

from app.models.empresa import EmpresaComIndicadores, Ritmo
from app.models.indicadores import EjMovimento, IndicadoresRede, RankingItem, RitmoMensalResponse, RitmoMesItem, SdeCenario, SdeResponse
from app.services.calculo_service import (
    calcular_crescimento,
    calcular_media_csat,
    calcular_pontos_cluster,
    calcular_sde,
    calcular_taxa_colaboracao,
    classificar_cluster,
    classificar_ritmo,
    calcular_percentual_meta,
)
from app.utils.cluster import get_cluster_column_name, get_cluster_value_for_year
from app.utils.constants import MESES_ANO


def calcular_indicadores_rede(
    sb: Client,
    *,
    ano: int,
    mes: int | None = None,
    cluster: int | None = None,
    comunidade: str | None = None,
) -> IndicadoresRede:
    """
    Calcula os KPIs consolidados da rede FEJEPE.

    Referência: estrutura.md → 1️⃣ Dashboard Geral da Rede

    Args:
        sb: Cliente Supabase.
        ano: Ano de referência.
        mes: Mês de referência (None = todos os meses disponíveis).
        cluster: Filtrar apenas EJs de um cluster.
        comunidade: Filtrar apenas EJs de uma comunidade.

    Returns:
        IndicadoresRede com todos os KPIs calculados.
    """
    # 1. Buscar todas as EJs (com filtros)
    ej_query = sb.table("empresa_junior").select("*")
    if cluster is not None:
        ej_query = ej_query.eq(get_cluster_column_name(ano), cluster)
    if comunidade:
        ej_query = ej_query.eq("comunidade", comunidade)

    empresas = (ej_query.execute()).data or []
    if not empresas:
        return IndicadoresRede(ano=ano, mes=mes)

    empresa_ids = [e["id_ej"] for e in empresas]

    # 2. Monitoramento do ano
    mon_query = sb.table("monitoramento").select("*").eq("ano", ano).in_("id_ej", empresa_ids)
    if mes is not None:
        mon_query = mon_query.lte("mes", mes)
    monitoramentos = (mon_query.execute()).data or []

    # 3. Metas do ano
    metas = (
        sb.table("metas").select("*").eq("ano", ano).in_("id_ej", empresa_ids).execute()
    ).data or []

    # Indexar
    mon_por_empresa: dict[int, list[dict]] = {}
    for m in monitoramentos:
        mon_por_empresa.setdefault(m["id_ej"], []).append(m)

    metas_por_empresa: dict[int, dict] = {}
    for mt in metas:
        metas_por_empresa[mt["id_ej"]] = mt

    # 4. Calcular indicadores por EJ e agregar
    faturamento_total = 0.0
    faturamento_colab_total = 0.0
    total_projetos = 0
    valores_csat: list[float | None] = []
    ejs_fora_do_zero = 0
    ejs_ritmo_minimo = 0
    ejs_ritmo_significativo = 0
    distribuicao_clusters: dict[int, int] = {}
    faturamento_por_comunidade: dict[str, float] = {}

    for ej in empresas:
        mons = mon_por_empresa.get(ej["id_ej"], [])
        if not mons:
            # EJ sem dados no período
            cl = get_cluster_value_for_year(ej, ano) or 1
            distribuicao_clusters[cl] = distribuicao_clusters.get(cl, 0) + 1
            continue

        # Último mês registrado
        mons_sorted = sorted(mons, key=lambda m: m["mes"])
        ultimo = mons_sorted[-1]

        fat_acum = float(ultimo.get("faturamento_acumulado", 0) or 0)
        fat_colab_acum = float(ultimo.get("faturamento_colab_acumulado", 0) or 0)
        proj_totais = int(ultimo.get("projetos_totais", 0) or 0)
        fat_mes = float(ultimo.get("faturamento_mes", 0) or 0)

        faturamento_total += fat_acum
        faturamento_colab_total += fat_colab_acum
        total_projetos += proj_totais

        # CSAT
        csats_ej = [m.get("csat") for m in mons_sorted]
        csat_medio = calcular_media_csat(csats_ej)
        if csat_medio is not None:
            valores_csat.append(csat_medio)

        # Ritmo
        meta_raw = metas_por_empresa.get(ej["id_ej"])
        meta_fat = meta_raw.get("meta_faturamento") if meta_raw else None
        ritmo = classificar_ritmo(fat_mes, meta_fat)

        if fat_acum > 0:
            ejs_fora_do_zero += 1
        if ritmo == Ritmo.minimo:
            ejs_ritmo_minimo += 1
        elif ritmo == Ritmo.significativo:
            ejs_ritmo_significativo += 1

        # Cluster
        cl = get_cluster_value_for_year(ej, ano) or 1
        distribuicao_clusters[cl] = distribuicao_clusters.get(cl, 0) + 1

        # Comunidade
        com = ej.get("comunidade")
        if com:
            faturamento_por_comunidade[com] = faturamento_por_comunidade.get(com, 0) + fat_acum

    # Média CSAT da rede
    media_csat = calcular_media_csat(valores_csat)

    # Participação por comunidade (percentual)
    participacao_comunidades: dict[str, float] = {}
    if faturamento_total > 0:
        for com, fat in faturamento_por_comunidade.items():
            participacao_comunidades[com] = round((fat / faturamento_total) * 100, 2)

    # Crescimento vs ano anterior
    crescimento = _calcular_crescimento_rede(sb, empresa_ids, ano, faturamento_total)

    return IndicadoresRede(
        ano=ano,
        mes=mes,
        faturamento_total=round(faturamento_total, 2),
        faturamento_colab_total=round(faturamento_colab_total, 2),
        total_projetos=total_projetos,
        media_csat=media_csat,
        total_ejs=len(empresas),
        ejs_fora_do_zero=ejs_fora_do_zero,
        ejs_ritmo_minimo=ejs_ritmo_minimo,
        ejs_ritmo_significativo=ejs_ritmo_significativo,
        sde=None,  # SDE requer comparação de clusters ano atual vs anterior — calculado separado
        crescimento_vs_ano_anterior=crescimento,
        distribuicao_clusters=distribuicao_clusters,
        participacao_comunidades=participacao_comunidades,
    )


def gerar_ranking(
    sb: Client,
    *,
    ano: int,
    mes: int | None = None,
    criterio: str = "faturamento",
    cluster: int | None = None,
    comunidade: str | None = None,
    limit: int = 20,
) -> list[RankingItem]:
    """
    Gera ranking dinâmico de EJs por critério.

    Referência: estrutura.md → 3️⃣ Aba de Comparação (rankings)

    Args:
        sb: Cliente Supabase.
        ano: Ano de referência.
        mes: Mês de referência.
        criterio: Campo de ranking (faturamento, csat, projetos, colab).
        cluster: Filtro por cluster.
        comunidade: Filtro por comunidade.
        limit: Máximo de itens no ranking.

    Returns:
        Lista de RankingItem ordenada por valor decrescente.
    """
    # Buscar EJs
    ej_query = sb.table("empresa_junior").select("*")
    if cluster is not None:
        ej_query = ej_query.eq(get_cluster_column_name(ano), cluster)
    if comunidade:
        ej_query = ej_query.eq("comunidade", comunidade)
    empresas = (ej_query.execute()).data or []

    if not empresas:
        return []

    empresa_ids = [e["id_ej"] for e in empresas]

    # Monitoramento
    mon_query = sb.table("monitoramento").select("*").eq("ano", ano).in_("id_ej", empresa_ids)
    if mes is not None:
        mon_query = mon_query.lte("mes", mes)
    monitoramentos = (mon_query.execute()).data or []

    mon_por_empresa: dict[int, list[dict]] = {}
    for m in monitoramentos:
        mon_por_empresa.setdefault(m["id_ej"], []).append(m)

    # Calcular valor por EJ
    itens: list[dict] = []
    for ej in empresas:
        mons = mon_por_empresa.get(ej["id_ej"], [])
        if not mons:
            continue

        mons_sorted = sorted(mons, key=lambda m: m["mes"])
        ultimo = mons_sorted[-1]

        valor = 0.0
        if criterio == "faturamento":
            valor = float(ultimo.get("faturamento_acumulado", 0) or 0)
        elif criterio == "colab":
            valor = float(ultimo.get("faturamento_colab_acumulado", 0) or 0)
        elif criterio == "projetos":
            valor = float(ultimo.get("projetos_totais", 0) or 0)
        elif criterio == "csat":
            csats = [m.get("csat") for m in mons_sorted]
            csat_m = calcular_media_csat(csats)
            valor = csat_m if csat_m is not None else 0.0

        itens.append({
            "id_ej": ej["id_ej"],
            "nome": ej["nome"],
            "cluster": get_cluster_value_for_year(ej, ano),
            "comunidade": ej.get("comunidade"),
            "valor": valor,
            "foto_url": ej.get("foto_url"),
        })

    # Ordenar e atribuir posição
    itens.sort(key=lambda x: x["valor"], reverse=True)
    ranking: list[RankingItem] = []
    for i, item in enumerate(itens[:limit]):
        ranking.append(
            RankingItem(
                posicao=i + 1,
                id_ej=item["id_ej"],
                nome=item["nome"],
                cluster=item["cluster"],
                comunidade=item["comunidade"],
                valor=round(item["valor"], 2),
                foto_url=item["foto_url"],
            )
        )
    return ranking


def calcular_sde_cenarios(
    sb: Client,
    *,
    ano: int,
    mes: int | None = None,
    cluster: int | None = None,
    comunidade: str | None = None,
) -> SdeResponse:
    """
    Calcula o SDE da rede em três cenários, comparando o cluster calculado
    de cada EJ com seu cluster oficial atual.

    Cenários:
        1. Índice de Cluster (fat real × CSAT real × engaj real × colab real)
        2. Índice c/ Meta CSAT (fat real × meta CSAT × engaj real × colab real)
        3. Tracking de Cluster (fat anualizado × meta CSAT × meta engaj × colab real)
    """
    # 1. Buscar EJs
    ej_query = sb.table("empresa_junior").select("*")
    if cluster is not None:
        ej_query = ej_query.eq(get_cluster_column_name(ano), cluster)
    if comunidade:
        ej_query = ej_query.eq("comunidade", comunidade)
    empresas = (ej_query.execute()).data or []

    if not empresas:
        return SdeResponse(ano=ano, mes=mes)

    empresa_ids = [e["id_ej"] for e in empresas]

    # 2. Monitoramento
    mon_query = sb.table("monitoramento").select("*").eq("ano", ano).in_("id_ej", empresa_ids)
    if mes is not None:
        mon_query = mon_query.lte("mes", mes)
    monitoramentos = (mon_query.execute()).data or []

    # 3. Metas
    metas_data = (
        sb.table("metas").select("*").eq("ano", ano).in_("id_ej", empresa_ids).execute()
    ).data or []

    mon_por_empresa: dict[int, list[dict]] = {}
    for m in monitoramentos:
        mon_por_empresa.setdefault(m["id_ej"], []).append(m)

    metas_por_empresa: dict[int, dict] = {}
    for mt in metas_data:
        metas_por_empresa[mt["id_ej"]] = mt

    # 4. Calcular índices por EJ e determinar movimento
    subidas: list[list[int]] = [[0] * 5, [0] * 5, [0] * 5]
    descidas: list[list[int]] = [[0] * 5, [0] * 5, [0] * 5]

    movimentos: list[list[EjMovimento]] = [[], [], []]
    NOMES_CENARIOS = [
        ("Índice de Cluster", "Faturamento real × CSAT real × Engajamento real"),
        ("Índice c/ Meta CSAT", "Faturamento real × Meta CSAT × Engajamento real"),
        ("Tracking de Cluster", "Faturamento anualizado × Meta CSAT × Meta Engajamento"),
    ]

    for ej in empresas:
        eid = ej["id_ej"]
        cluster_atual = get_cluster_value_for_year(ej, ano) or 1
        mons = sorted(mon_por_empresa.get(eid, []), key=lambda m: m["mes"])
        meta_raw = metas_por_empresa.get(eid)

        if not mons:
            # Sem dados de monitoramento: mantém cluster atual em todos os cenários
            for i in range(3):
                movimentos[i].append(EjMovimento(
                    id_ej=eid,
                    nome=ej["nome"],
                    cluster_atual=cluster_atual,
                    cluster_calculado=cluster_atual,
                    foto_url=ej.get("foto_url"),
                ))
            continue

        ultimo = mons[-1]
        fat_acum = float(ultimo.get("faturamento_acumulado", 0) or 0)

        # EJs sem faturamento têm índice 0 → cluster 1 calculado
        if fat_acum <= 0:
            idx_cluster = cluster_atual - 1
            for i in range(3):
                ej_mov = EjMovimento(
                    id_ej=eid,
                    nome=ej["nome"],
                    cluster_atual=cluster_atual,
                    cluster_calculado=1,
                    foto_url=ej.get("foto_url"),
                )
                if 1 > cluster_atual:
                    subidas[i][idx_cluster] += 1
                elif 1 < cluster_atual:
                    descidas[i][idx_cluster] += 1
                movimentos[i].append(ej_mov)
            continue

        # CSAT médio real
        csat_real = calcular_media_csat([m.get("csat") for m in mons])

        # Engajamento real (decimal)
        numero_membros = int(ultimo.get("numero_membros") or 0)
        max_engajados = max(int(m.get("membros_engajados_mes") or 0) for m in mons)
        engaj_real = round(max_engajados / numero_membros, 4) if numero_membros > 0 else None

        # Taxa colaboração (decimal)
        fat_colab_acum = sum(float(m.get("faturamento_colab_mes", 0) or 0) for m in mons)
        taxa_colab = calcular_taxa_colaboracao(fat_colab_acum, fat_acum) or 0.0

        # Metas
        meta_csat = meta_raw.get("meta_csat") if meta_raw else None
        meta_engaj = float(meta_raw.get("meta_engajamento_mej") or 0) / 100 if meta_raw else 0.0

        # Faturamento anualizado (cenário 3)
        mes_atual_num = mons[-1]["mes"]
        fat_anualizado = (fat_acum / mes_atual_num) * MESES_ANO if mes_atual_num > 0 else 0.0

        # Calcular os três índices
        indices: list[float | None] = [None, None, None]

        if csat_real is not None and engaj_real is not None:
            indices[0] = calcular_pontos_cluster(fat_acum, csat_real, engaj_real, taxa_colab)
            indices[1] = calcular_pontos_cluster(fat_acum, meta_csat, engaj_real, taxa_colab) if meta_csat else None

        if meta_csat and fat_anualizado > 0:
            indices[2] = calcular_pontos_cluster(fat_anualizado, meta_csat, meta_engaj, taxa_colab)

        # Determinar movimento em cada cenário
        idx_cluster = cluster_atual - 1  # 0-based
        for i, indice in enumerate(indices):
            if indice is None:
                # Dados insuficientes para o cenário: mantém cluster atual
                movimentos[i].append(EjMovimento(
                    id_ej=eid,
                    nome=ej["nome"],
                    cluster_atual=cluster_atual,
                    cluster_calculado=cluster_atual,
                    foto_url=ej.get("foto_url"),
                ))
                continue
            cluster_calc = classificar_cluster(indice)

            # Regra temporária: EJs em Cluster 4 sempre descendo no Índice de Cluster
            # pois dependem de um indicador ainda não implementado.
            if i == 0 and cluster_atual == 4:
                cluster_calc = min(cluster_calc, 3)

            ej_mov = EjMovimento(
                id_ej=eid,
                nome=ej["nome"],
                cluster_atual=cluster_atual,
                cluster_calculado=cluster_calc,
                foto_url=ej.get("foto_url"),
            )
            if cluster_calc > cluster_atual:
                subidas[i][idx_cluster] += 1
                movimentos[i].append(ej_mov)
            elif cluster_calc < cluster_atual:
                descidas[i][idx_cluster] += 1
                movimentos[i].append(ej_mov)
            else:
                movimentos[i].append(ej_mov)

    # 5. Montar cenários
    cenarios: list[SdeCenario] = []
    for i in range(3):
        nome, descricao = NOMES_CENARIOS[i]
        sde_val = calcular_sde(subidas[i], descidas[i])
        subindo = [m for m in movimentos[i] if m.cluster_calculado is not None and m.cluster_atual is not None and m.cluster_calculado > m.cluster_atual]
        descendo = [m for m in movimentos[i] if m.cluster_calculado is not None and m.cluster_atual is not None and m.cluster_calculado < m.cluster_atual]
        mantendo = [m for m in movimentos[i] if m.cluster_calculado is not None and m.cluster_atual is not None and m.cluster_calculado == m.cluster_atual]
        cenarios.append(SdeCenario(
            nome=nome,
            descricao=descricao,
            sde=round(sde_val, 4),
            subindo=sorted(subindo, key=lambda e: e.nome),
            mantendo=sorted(mantendo, key=lambda e: e.nome),
            descendo=sorted(descendo, key=lambda e: e.nome),
        ))

    return SdeResponse(ano=ano, mes=mes, cenarios=cenarios)


def calcular_ritmo_mensal(
    sb: Client,
    *,
    ano: int,
    cluster: int | None = None,
    comunidade: str | None = None,
) -> RitmoMensalResponse:
    """
    Calcula ritmo mínimo e significativo para cada mês do ano.

    Para cada mês, o ritmo é avaliado com base no faturamento_mes
    daquele mês específico (não acumulado).

    Args:
        sb: Cliente Supabase.
        ano: Ano de referência.
        cluster: Filtrar por cluster.
        comunidade: Filtrar por comunidade.

    Returns:
        RitmoMensalResponse com 12 itens (jan–dez).
    """
    # 1. Buscar EJs
    ej_query = sb.table("empresa_junior").select("*")
    if cluster is not None:
        ej_query = ej_query.eq(get_cluster_column_name(ano), cluster)
    if comunidade:
        ej_query = ej_query.eq("comunidade", comunidade)
    empresas = (ej_query.execute()).data or []

    if not empresas:
        return RitmoMensalResponse(ano=ano)

    total_ejs = len(empresas)
    empresa_ids = [e["id_ej"] for e in empresas]

    # 2. Buscar todos os monitoramentos do ano (sem filtro de mês)
    monitoramentos = (
        sb.table("monitoramento")
        .select("id_ej, mes, faturamento_mes")
        .eq("ano", ano)
        .in_("id_ej", empresa_ids)
        .execute()
    ).data or []

    # 3. Buscar metas
    metas = (
        sb.table("metas").select("id_ej, meta_faturamento")
        .eq("ano", ano)
        .in_("id_ej", empresa_ids)
        .execute()
    ).data or []

    metas_por_empresa: dict[int, float | None] = {}
    for mt in metas:
        metas_por_empresa[mt["id_ej"]] = mt.get("meta_faturamento")

    # Indexar monitoramentos por (id_ej, mes)
    mon_por_ej_mes: dict[tuple[int, int], dict] = {}
    for m in monitoramentos:
        mon_por_ej_mes[(m["id_ej"], m["mes"])] = m

    # 4. Para cada mês, classificar cada EJ
    meses: list[RitmoMesItem] = []
    for mes in range(1, 13):
        rm = 0
        rs = 0
        for ej in empresas:
            eid = ej["id_ej"]
            mon = mon_por_ej_mes.get((eid, mes))
            fat_mes = float(mon.get("faturamento_mes", 0) or 0) if mon else 0.0
            meta_fat = metas_por_empresa.get(eid)
            ritmo = classificar_ritmo(fat_mes, meta_fat)
            if ritmo == Ritmo.minimo:
                rm += 1
            elif ritmo == Ritmo.significativo:
                rs += 1
        meses.append(RitmoMesItem(mes=mes, ejs_ritmo_minimo=rm, ejs_ritmo_significativo=rs, total_ejs=total_ejs))

    return RitmoMensalResponse(ano=ano, meses=meses)


# ── Helpers privados ─────────────────────────────────────────


def _calcular_crescimento_rede(
    sb: Client,
    empresa_ids: list[int],
    ano: int,
    faturamento_atual: float,
) -> float | None:
    """Calcula crescimento da rede em relação ao mesmo período do ano anterior."""
    ano_anterior = ano - 1
    result = (
        sb.table("monitoramento")
        .select("faturamento_acumulado, id_ej")
        .eq("ano", ano_anterior)
        .in_("id_ej", empresa_ids)
        .execute()
    )
    if not result.data:
        return None

    # Pegar último registro por empresa
    por_empresa: dict[int, float] = {}
    for m in result.data:
        eid = m["id_ej"]
        fat = float(m.get("faturamento_acumulado", 0) or 0)
        if eid not in por_empresa or fat > por_empresa[eid]:
            por_empresa[eid] = fat

    fat_anterior = sum(por_empresa.values())
    return calcular_crescimento(faturamento_atual, fat_anterior)
