"""
Serviço de indicadores da rede FEJEPE.

Calcula KPIs consolidados: faturamento total, SDE, distribuição
por cluster, crescimento e ritmo mensal.
"""

from app.database import Client

from app.models.empresa import EmpresaComIndicadores, Ritmo
from app.models.indicadores import EjMovimento, IndicadoresRede, RankingItem, RitmoMensalResponse, RitmoMesItem, SdeCenario, SdeResponse
from app.services.cluster_service import buscar_historico_do_ano, buscar_ids_por_cluster
from app.services.leitura import ler_todas
from app.services.tenant import filtrar_por_tenant
from app.services.calculo_service import (
    aplicar_regra_projeto_impacto,
    calcular_projetos_impacto,
    tem_projeto_impacto,
    calcular_crescimento,
    calcular_media_csat,
    calcular_pontos_cluster,
    calcular_sde,
    calcular_taxa_colaboracao,
    classificar_cluster,
    classificar_ritmo,
    calcular_percentual_meta,
)
from app.utils.cluster import get_cluster_value_for_year
from app.utils.constants import MESES_ANO


def calcular_indicadores_rede(
    sb: Client,
    *,
    ano: int,
    mes: int | None = None,
    cluster: int | None = None,
    federacao_id: int | None = None,
) -> IndicadoresRede:
    """
    Calcula os KPIs consolidados da rede FEJEPE.

    Referência: estrutura.md → 1️⃣ Dashboard Geral da Rede

    Args:
        sb: Cliente Supabase.
        ano: Ano de referência.
        mes: Mês de referência (None = todos os meses disponíveis).
        cluster: Filtrar apenas EJs de um cluster.

    Returns:
        IndicadoresRede com todos os KPIs calculados.
    """
    # 1. Buscar todas as EJs (com filtros)
    ids_no_cluster: list[int] | None = None
    if cluster is not None:
        # O cluster do ano vive em `cluster_historico`: busca os id_ej primeiro
        # e filtra com `.in_`, mesmo idioma de metas/monitoramento.
        ids_no_cluster = buscar_ids_por_cluster(sb, ano=ano, cluster=cluster)
        if not ids_no_cluster:
            # Nenhuma EJ nesse cluster neste ano.
            return IndicadoresRede(ano=ano, mes=mes)
    empresas = _ler_ejs(sb, federacao_id, ids_no_cluster)
    if not empresas:
        return IndicadoresRede(ano=ano, mes=mes)

    empresa_ids = [e["id_ej"] for e in empresas]

    historico_cluster = buscar_historico_do_ano(sb, ano=ano, ids_ej=empresa_ids)

    # 2. Monitoramento do ano
    monitoramentos = _ler_monitoramento(sb, ano=ano, mes=mes, ids_ej=empresa_ids)

    # 3. Metas do ano
    metas = ler_todas(sb, "metas", "*", lambda q: q.eq("ano", ano).in_("id_ej", empresa_ids))

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

    for ej in empresas:
        mons = mon_por_empresa.get(ej["id_ej"], [])
        if not mons:
            # EJ sem dados no período
            cl = get_cluster_value_for_year(historico_cluster, ej["id_ej"]) or 1
            distribuicao_clusters[cl] = distribuicao_clusters.get(cl, 0) + 1
            continue

        # Último mês registrado
        mons_sorted = sorted(mons, key=lambda m: m["mes"])
        ultimo = mons_sorted[-1]

        fat_acum = float(ultimo.get("faturamento_acumulado", 0) or 0)
        fat_colab_acum = float(ultimo.get("faturamento_colab_acumulado", 0) or 0)
        # A exportação acumulada fornece CONTRATOS por mês. A coluna legada
        # projetos_totais não é alimentada pela ingestão; somar os meses evita
        # que o indicador da rede fique sempre zerado.
        proj_totais = sum(int(m.get("projetos_vendidos_mes") or 0) for m in mons_sorted)
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
        cl = get_cluster_value_for_year(historico_cluster, ej["id_ej"]) or 1
        distribuicao_clusters[cl] = distribuicao_clusters.get(cl, 0) + 1


    # Média CSAT da rede
    media_csat = calcular_media_csat(valores_csat)

    # Crescimento vs ano anterior
    mes_referencia = max((m["mes"] for m in monitoramentos), default=None)
    crescimento = _calcular_crescimento_rede(
        sb, empresa_ids, ano, faturamento_total, mes_referencia=mes_referencia
    )

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
    )


def gerar_ranking(
    sb: Client,
    *,
    ano: int,
    mes: int | None = None,
    criterio: str = "faturamento",
    cluster: int | None = None,
    limit: int = 20,
    federacao_id: int | None = None,
    ordem: str = "desc",
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
        limit: Máximo de itens no ranking.
        ordem: "desc" (padrão, maiores valores) ou "asc" (menores valores; ver
            `gerar_ranking_com_exclusoes`).

    Returns:
        Lista de RankingItem ordenada pelo valor na ordem pedida.
    """
    itens, _sem_coleta = gerar_ranking_com_exclusoes(
        sb, ano=ano, mes=mes, criterio=criterio, cluster=cluster, limit=limit,
        federacao_id=federacao_id, ordem=ordem,
    )
    return itens


def _valor_do_criterio(criterio: str, mons_sorted: list[dict]) -> float | None:
    """Valor da EJ no critério; None quando a métrica não foi coletada."""
    ultimo = mons_sorted[-1]
    if criterio == "faturamento":
        bruto = ultimo.get("faturamento_acumulado")
        return None if bruto is None else float(bruto)
    if criterio == "colab":
        bruto = ultimo.get("faturamento_colab_acumulado")
        return None if bruto is None else float(bruto)
    if criterio == "projetos":
        vendidos = [m.get("projetos_vendidos_mes") for m in mons_sorted]
        if all(v is None for v in vendidos):
            return None
        return float(sum(int(v or 0) for v in vendidos))
    if criterio == "csat":
        return calcular_media_csat([m.get("csat") for m in mons_sorted])
    return 0.0


def gerar_ranking_com_exclusoes(
    sb: Client,
    *,
    ano: int,
    mes: int | None = None,
    criterio: str = "faturamento",
    cluster: int | None = None,
    limit: int = 20,
    federacao_id: int | None = None,
    ordem: str = "desc",
) -> tuple[list[RankingItem], int]:
    """
    Ranking e quantidade de EJs deixadas de fora por falta de coleta.

    Em "desc" o comportamento é o histórico do portal: métrica ausente conta
    como zero e só a EJ sem nenhum monitoramento fica de fora (sem contar).
    Em "asc" a ausência não pode virar "menor valor": EJ sem monitoramento ou
    sem coleta da métrica fica fora e é contada. Faturamento zero informado
    entra normalmente.
    """
    if ordem not in ("desc", "asc"):
        raise ValueError("ordem deve ser 'desc' ou 'asc'.")
    # Buscar EJs
    ids_no_cluster: list[int] | None = None
    if cluster is not None:
        # O cluster do ano vive em `cluster_historico`: busca os id_ej primeiro
        # e filtra com `.in_`, mesmo idioma de metas/monitoramento.
        ids_no_cluster = buscar_ids_por_cluster(sb, ano=ano, cluster=cluster)
        if not ids_no_cluster:
            # Nenhuma EJ nesse cluster neste ano.
            return [], 0
    empresas = _ler_ejs(sb, federacao_id, ids_no_cluster)

    if not empresas:
        return [], 0

    empresa_ids = [e["id_ej"] for e in empresas]

    historico_cluster = buscar_historico_do_ano(sb, ano=ano, ids_ej=empresa_ids)

    # Monitoramento
    monitoramentos = _ler_monitoramento(sb, ano=ano, mes=mes, ids_ej=empresa_ids)

    mon_por_empresa: dict[int, list[dict]] = {}
    for m in monitoramentos:
        mon_por_empresa.setdefault(m["id_ej"], []).append(m)

    # Calcular valor por EJ
    itens: list[dict] = []
    sem_coleta = 0
    for ej in empresas:
        mons = mon_por_empresa.get(ej["id_ej"], [])
        if not mons:
            sem_coleta += ordem == "asc"
            continue

        valor = _valor_do_criterio(criterio, sorted(mons, key=lambda m: m["mes"]))
        if valor is None:
            if ordem == "asc":
                sem_coleta += 1
                continue
            valor = 0.0

        itens.append({
            "id_ej": ej["id_ej"],
            "nome": ej["nome"],
            "cluster": get_cluster_value_for_year(historico_cluster, ej["id_ej"]),
            "valor": valor,
            "foto_url": ej.get("foto_url"),
        })

    # Ordenar e atribuir posição
    itens.sort(key=lambda x: x["valor"], reverse=ordem == "desc")
    ranking: list[RankingItem] = []
    for i, item in enumerate(itens[:limit]):
        ranking.append(
            RankingItem(
                posicao=i + 1,
                id_ej=item["id_ej"],
                nome=item["nome"],
                cluster=item["cluster"],
                valor=round(item["valor"], 2),
                foto_url=item["foto_url"],
            )
        )
    return ranking, sem_coleta


def calcular_sde_cenarios(
    sb: Client,
    *,
    ano: int,
    mes: int | None = None,
    cluster: int | None = None,
    federacao_id: int | None = None,
) -> SdeResponse:
    """
    Calcula o SDE da rede em três cenários, comparando o cluster calculado
    de cada EJ com seu cluster oficial atual.

    Cenários:
        1. Índice de Cluster (fat real × CSAT real × engaj real × colab real)
        2. Índice c/ Meta CSAT (fat real × meta CSAT × engaj real × colab real)
        3. Tracking de Cluster (fat anualizado × meta CSAT × meta engaj × colab real)

    Em todos os cenários o cluster comparado com o oficial é o cluster REAL:
    o que o índice aponta, limitado pela regra do projeto de impacto (obrigatório
    no C4 e no C5). Sem projeto de impacto o cluster real é no máximo C3 — a EJ
    do C3 não sobe para o C4 ou C5 e as do C4 e C5 descem para o C3. Isso substitui
    a antiga regra temporária que fazia todo C4 descer no cenário 1.
    """
    # 1. Buscar EJs
    ids_no_cluster: list[int] | None = None
    if cluster is not None:
        # O cluster do ano vive em `cluster_historico`: busca os id_ej primeiro
        # e filtra com `.in_`, mesmo idioma de metas/monitoramento.
        ids_no_cluster = buscar_ids_por_cluster(sb, ano=ano, cluster=cluster)
        if not ids_no_cluster:
            # Nenhuma EJ nesse cluster neste ano.
            return SdeResponse(ano=ano, mes=mes)
    empresas = _ler_ejs(sb, federacao_id, ids_no_cluster)

    if not empresas:
        return SdeResponse(ano=ano, mes=mes)

    empresa_ids = [e["id_ej"] for e in empresas]

    historico_cluster = buscar_historico_do_ano(sb, ano=ano, ids_ej=empresa_ids)

    # 2. Monitoramento
    monitoramentos = _ler_monitoramento(sb, ano=ano, mes=mes, ids_ej=empresa_ids)

    # 3. Metas
    metas_data = ler_todas(sb, "metas", "*", lambda q: q.eq("ano", ano).in_("id_ej", empresa_ids))

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
        cluster_atual = get_cluster_value_for_year(historico_cluster, ej["id_ej"]) or 1
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
                    cluster_apontado=cluster_atual,
                    foto_url=ej.get("foto_url"),
                ))
            continue

        ultimo = mons[-1]
        fat_acum = float(ultimo.get("faturamento_acumulado", 0) or 0)
        # Projeto de impacto: vazio = nenhum. Só vale como "sem projeto" porque
        # há linha de monitoramento (sem linha o ramo acima mantém o cluster).
        possui_projeto = tem_projeto_impacto(calcular_projetos_impacto(mons))

        # EJs sem faturamento têm índice 0 → cluster 1 calculado
        if fat_acum <= 0:
            idx_cluster = cluster_atual - 1
            for i in range(3):
                ej_mov = EjMovimento(
                    id_ej=eid,
                    nome=ej["nome"],
                    cluster_atual=cluster_atual,
                    cluster_calculado=1,
                    cluster_apontado=1,
                    tem_projeto_impacto=possui_projeto,
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
        fat_colab_acum = float(ultimo.get("faturamento_colab_acumulado", 0) or 0)
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
            # Sem insumo para o cenário o índice não aponta cluster e a EJ parte
            # do atual (mantém) — mas a regra do projeto de impacto continua
            # valendo: C5 sem projeto não permanece no C5.
            cluster_apontado = cluster_atual if indice is None else classificar_cluster(indice)
            cluster_calc = aplicar_regra_projeto_impacto(cluster_apontado, possui_projeto)

            ej_mov = EjMovimento(
                id_ej=eid,
                nome=ej["nome"],
                cluster_atual=cluster_atual,
                cluster_calculado=cluster_calc,
                cluster_apontado=cluster_apontado,
                tem_projeto_impacto=possui_projeto,
                limitado_por_projeto_impacto=cluster_calc != cluster_apontado,
                foto_url=ej.get("foto_url"),
            )
            if cluster_calc > cluster_atual:
                subidas[i][idx_cluster] += 1
            elif cluster_calc < cluster_atual:
                descidas[i][idx_cluster] += 1
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

    return SdeResponse(ano=ano, mes=mes, total_ejs=len(empresas), cenarios=cenarios)


def calcular_ritmo_mensal(
    sb: Client,
    *,
    ano: int,
    cluster: int | None = None,
    federacao_id: int | None = None,
) -> RitmoMensalResponse:
    """
    Calcula ritmo mínimo e significativo para cada mês do ano.

    Para cada mês, o ritmo é avaliado com base no faturamento_mes
    daquele mês específico (não acumulado).

    Args:
        sb: Cliente Supabase.
        ano: Ano de referência.
        cluster: Filtrar por cluster.

    Returns:
        RitmoMensalResponse com 12 itens (jan–dez).
    """
    # 1. Buscar EJs
    ids_no_cluster: list[int] | None = None
    if cluster is not None:
        # O cluster do ano vive em `cluster_historico`: busca os id_ej primeiro
        # e filtra com `.in_`, mesmo idioma de metas/monitoramento.
        ids_no_cluster = buscar_ids_por_cluster(sb, ano=ano, cluster=cluster)
        if not ids_no_cluster:
            # Nenhuma EJ nesse cluster neste ano.
            return RitmoMensalResponse(ano=ano)
    empresas = _ler_ejs(sb, federacao_id, ids_no_cluster)

    if not empresas:
        return RitmoMensalResponse(ano=ano)

    total_ejs = len(empresas)
    empresa_ids = [e["id_ej"] for e in empresas]

    # 2. Buscar todos os monitoramentos do ano (sem filtro de mês)
    monitoramentos = _ler_monitoramento(
        sb, ano=ano, mes=None, ids_ej=empresa_ids, colunas="id, id_ej, mes, faturamento_mes"
    )

    # 3. Buscar metas
    metas = ler_todas(
        sb, "metas", "id, id_ej, meta_faturamento", lambda q: q.eq("ano", ano).in_("id_ej", empresa_ids)
    )

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
    *,
    mes_referencia: int | None,
) -> float | None:
    """Calcula crescimento da rede em relação ao mesmo período do ano anterior."""
    if mes_referencia is None:
        return None
    ano_anterior = ano - 1
    linhas = _ler_monitoramento(
        sb, ano=ano_anterior, mes=mes_referencia, ids_ej=empresa_ids,
        colunas="id, mes, faturamento_acumulado, id_ej"
    )
    if not linhas:
        return None

    # O último mês do período pode ter ajuste negativo. Maior faturamento
    # histórico não é necessariamente o acumulado mais recente.
    por_empresa: dict[int, tuple[int, float]] = {}
    for m in linhas:
        eid = m["id_ej"]
        fat = float(m.get("faturamento_acumulado", 0) or 0)
        if eid not in por_empresa or m["mes"] > por_empresa[eid][0]:
            por_empresa[eid] = (m["mes"], fat)

    fat_anterior = sum(fat for _, fat in por_empresa.values())
    return calcular_crescimento(faturamento_atual, fat_anterior)


def _ler_ejs(
    sb: Client,
    federacao_id: int | None,
    ids_no_cluster: list[int] | None,
) -> list[dict]:
    """EJs do tenant, com filtro de cluster, sem o corte de 1000 linhas."""

    def _filtros(q):
        # O tenant entra primeiro, antes de qualquer filtro de usuário —
        # ver app/services/tenant.py.
        q = filtrar_por_tenant(q, federacao_id)
        if ids_no_cluster is not None:
            q = q.in_("id_ej", ids_no_cluster)
        return q

    return ler_todas(sb, "empresa_junior", "*", _filtros)


def _ler_monitoramento(
    sb: Client, *, ano: int, mes: int | None, ids_ej: list[int], colunas: str = "*"
) -> list[dict]:
    """Monitoramento do ano (até `mes`, se informado) das EJs, sem o corte de 1000 linhas."""

    def _filtros(q):
        q = q.eq("ano", ano).in_("id_ej", ids_ej)
        return q.lte("mes", mes) if mes is not None else q

    return ler_todas(sb, "monitoramento", colunas, _filtros)
