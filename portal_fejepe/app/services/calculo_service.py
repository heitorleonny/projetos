"""
Serviço de cálculos estratégicos do Portal FEJEPE.

Centraliza TODA a lógica de cálculos conforme documentado em calculos.md.
Nenhum cálculo estratégico deve ser feito no frontend.

Referência principal: calculos.md
"""

from app.models.empresa import Ritmo, TendenciaCluster
from app.utils.constants import (
    CLUSTER_RANGES,
    FATOR_ESCALA_PONTOS,
    MESES_ANO,
    SDE_WEIGHTS,
)


# ── 1. Percentual de Meta Atingida ───────────────────────────


def calcular_percentual_meta(
    faturamento_acumulado: float,
    meta_faturamento: float | None,
) -> float | None:
    """
    Calcula o percentual da meta de faturamento atingido.

    Fórmula:
        % meta = (faturamento_acumulado / meta_faturamento) * 100

    Args:
        faturamento_acumulado: Faturamento acumulado no ano.
        meta_faturamento: Meta anual de faturamento.

    Returns:
        Percentual atingido (ex: 75.5 para 75,5%), ou None se meta não definida.
    """
    if not meta_faturamento or meta_faturamento <= 0:
        return None
    return round((faturamento_acumulado / meta_faturamento) * 100, 2)


# ── 2. Classificação de Ritmo ────────────────────────────────


def classificar_ritmo(
    faturamento_mes: float,
    meta_anual: float | None,
) -> Ritmo:
    """
    Classifica o ritmo de uma EJ no mês.

    Referência: calculos.md → 2️⃣ Classificação de Ritmo

    Regras:
        - sem_vendas: faturamento_mes == 0
        - minimo: faturamento_mes > 0
        - significativo: faturamento_mes >= meta_anual / 12

    Args:
        faturamento_mes: Faturamento do mês atual.
        meta_anual: Meta anual de faturamento.

    Returns:
        Ritmo enum (sem_vendas, minimo ou significativo).
    """
    if faturamento_mes <= 0:
        return Ritmo.sem_vendas

    if meta_anual and meta_anual > 0:
        meta_mensal = meta_anual / MESES_ANO
        if faturamento_mes >= meta_mensal:
            return Ritmo.significativo

    return Ritmo.minimo


# ── 3. Taxa de Colaboração ───────────────────────────────────


def calcular_taxa_colaboracao(
    faturamento_colab_acumulado: float,
    faturamento_acumulado: float,
) -> float | None:
    """
    Calcula a taxa de faturamento colaborativo.

    Fórmula:
        taxa = faturamento_colab_acumulado / faturamento_acumulado

    Args:
        faturamento_colab_acumulado: Faturamento colaborativo acumulado.
        faturamento_acumulado: Faturamento total acumulado.

    Returns:
        Taxa como decimal (ex: 0.25 para 25%), ou None se sem faturamento.
    """
    if faturamento_acumulado <= 0:
        return None
    return round(faturamento_colab_acumulado / faturamento_acumulado, 4)


# ── 4. Pontuação de Cluster ──────────────────────────────────


def calcular_pontos_cluster(
    faturamento: float,
    csat: float,
    engajamento_mej: float,
    faturamento_colab_pct: float,
) -> float:
    """
    Calcula a pontuação de cluster de uma EJ.

    Referência: calculos.md → 5️⃣ Fórmula Oficial de Pontos de Cluster

    Fórmula:
        Pontos = Faturamento * CSAT * (1 + %Engajamento_MEJ) * (1 + %Fat_Colab) * 100

    Args:
        faturamento: Faturamento (anualizado ou real).
        csat: CSAT (meta ou real).
        engajamento_mej: Percentual de engajamento com o MEJ (decimal, ex: 0.25).
        faturamento_colab_pct: Percentual de faturamento colaborativo (decimal).

    Returns:
        Pontuação de cluster (float).
    """
    return (
        faturamento
        * csat
        * (1 + engajamento_mej)
        * (1 + faturamento_colab_pct)
        * FATOR_ESCALA_PONTOS
    )


def calcular_pontos_cluster_adaptativo(
    faturamento_acumulado: float,
    mes_atual: int,
    meta_csat: float | None,
    csat_real: float | None,
    meta_engajamento_mej: float | None,
    engajamento_real: float | None,
    taxa_colaboracao: float | None,
) -> float | None:
    """
    Calcula a pontuação de cluster adaptativa por fase do ano.

    Referência: calculos.md → 6️⃣ Fórmula Adaptativa de Cluster

    A fórmula varia conforme o trimestre para usar dados mais confiáveis
    à medida que o ano avança:

    Fase 1 (mês 1-3):
        (fat/mês)*12 * (1 + meta_engaj) * (1 + taxa_colab) * meta_csat * 100

    Fase 2 (mês 4-6):
        (fat/mês)*12 * (1 + engaj_ajustado) * (1 + taxa_colab) * meta_csat * 100
        Onde engaj_ajustado = meta_engaj se engaj_real >= 25% da meta,
                              senão engaj_real / 0.25 (penalização)

    Fase 3 (mês 7-12):
        (fat/mês)*12 * (1 + engaj_real) * (1 + taxa_colab) * csat_real * 100

    Args:
        faturamento_acumulado: Faturamento acumulado até o mês atual.
        mes_atual: Número do mês mais recente com dados (1-12).
        meta_csat: Meta de CSAT da EJ.
        csat_real: CSAT real medido (média dos meses).
        meta_engajamento_mej: Meta de engajamento MEJ (decimal).
        engajamento_real: Engajamento real medido (decimal).
        taxa_colaboracao: Taxa real de faturamento colaborativo (decimal).

    Returns:
        Pontuação de cluster adaptativa, ou None se dados insuficientes.
    """
    if mes_atual <= 0 or faturamento_acumulado <= 0:
        return None

    # Anualizar faturamento: média mensal * 12
    faturamento_anualizado = (faturamento_acumulado / mes_atual) * MESES_ANO

    colab = taxa_colaboracao if taxa_colaboracao is not None else 0.0

    if mes_atual <= 3:
        # Fase 1 (Q1): usa meta_csat e meta_engajamento
        csat = meta_csat
        if csat is None or csat <= 0:
            return None
        engajamento = meta_engajamento_mej if meta_engajamento_mej is not None else 0.0

    elif mes_atual <= 6:
        # Fase 2 (Q2): usa meta_csat; engajamento condicional
        csat = meta_csat
        if csat is None or csat <= 0:
            return None
        engajamento = _calcular_engajamento_fase2(
            meta_engajamento_mej, engajamento_real
        )

    else:
        # Fase 3 (Q3/Q4, mês 7-12): usa valores reais
        csat = csat_real
        if csat is None or csat <= 0:
            return None
        engajamento = engajamento_real if engajamento_real is not None else 0.0

    return calcular_pontos_cluster(
        faturamento_anualizado,
        csat,
        engajamento,
        colab,
    )


def _calcular_engajamento_fase2(
    meta_engajamento: float | None,
    engajamento_real: float | None,
) -> float:
    """
    Calcula o engajamento ajustado para a Fase 2 (mês 4-6).

    Regra:
        Se engajamento_real >= 25% da meta → usa meta (beneficia)
        Senão → usa engajamento_real / 0.25 (penaliza)

    Args:
        meta_engajamento: Meta de engajamento (decimal).
        engajamento_real: Engajamento real medido (decimal).

    Returns:
        Valor de engajamento a ser usado no cálculo.
    """
    meta = meta_engajamento if meta_engajamento is not None else 0.0
    real = engajamento_real if engajamento_real is not None else 0.0

    limite = meta * 0.25
    if real >= limite:
        return meta
    else:
        return real / 0.25 if real > 0 else 0.0


# ── 5. Classificação de Cluster por Pontuação ────────────────


def classificar_cluster(pontos: float) -> int:
    """
    Determina o cluster de uma EJ com base na pontuação.

    Referência: calculos.md → 4️⃣ Tabela de Classificação de Cluster

    Faixas:
        Cluster 1: 0 a 12.000.000
        Cluster 2: 12.000.000,01 a 24.000.000
        Cluster 3: 24.000.000,01 a 61.000.000
        Cluster 4: 61.000.000,01 a 130.000.000
        Cluster 5: 130.000.000,01+

    Args:
        pontos: Pontuação calculada pela fórmula de cluster.

    Returns:
        Número do cluster (1 a 5).
    """
    for min_val, max_val, cluster in CLUSTER_RANGES:
        if min_val <= pontos <= max_val:
            return cluster
    return 1  # fallback


# ── 6. Tendência de Cluster ──────────────────────────────────


def calcular_tendencia_cluster(
    cluster_atual: int | None,
    cluster_anterior: int | None,
) -> TendenciaCluster | None:
    """
    Determina a tendência do cluster (sobe, mantém, desce).

    Args:
        cluster_atual: Cluster calculado no período atual.
        cluster_anterior: Cluster do período anterior.

    Returns:
        TendenciaCluster ou None se dados insuficientes.
    """
    if cluster_atual is None or cluster_anterior is None:
        return None
    if cluster_atual > cluster_anterior:
        return TendenciaCluster.sobe
    if cluster_atual < cluster_anterior:
        return TendenciaCluster.desce
    return TendenciaCluster.mantem


# ── 7. SDE da Rede ───────────────────────────────────────────


def calcular_sde(
    subidas_por_cluster: list[int],
    descidas_por_cluster: list[int],
) -> float:
    """
    Calcula o SDE (Saldo de Desenvolvimento Estratégico) da rede.

    Referência: calculos.md → 1️⃣ Cálculo do SDE

    Fórmula:
        SDE = Σ (peso_i * (subidas_i - descidas_i))  para i = 1..5

    Pesos:
        Cluster 1: 0,30
        Cluster 2: 0,25
        Cluster 3: 0,15
        Cluster 4: 0,15
        Cluster 5: 0,15

    Args:
        subidas_por_cluster: Lista com qtd de EJs subindo em cada cluster [S1, S2, S3, S4, S5].
        descidas_por_cluster: Lista com qtd de EJs descendo em cada cluster [D1, D2, D3, D4, D5].

    Returns:
        Valor do SDE (float).

    Raises:
        ValueError: Se as listas não tiverem exatamente 5 elementos.
    """
    if len(subidas_por_cluster) != 5 or len(descidas_por_cluster) != 5:
        raise ValueError("Subidas e descidas devem ter exatamente 5 elementos (clusters 1-5).")

    sde = 0.0
    for i in range(5):
        sde += SDE_WEIGHTS[i] * (subidas_por_cluster[i] - descidas_por_cluster[i])
    return round(sde, 4)


# ── 8. Crescimento Percentual ────────────────────────────────


def calcular_crescimento(
    valor_atual: float,
    valor_anterior: float,
) -> float | None:
    """
    Calcula a variação percentual entre dois valores.

    Fórmula:
        crescimento = ((valor_atual - valor_anterior) / valor_anterior) * 100

    Args:
        valor_atual: Valor do período atual.
        valor_anterior: Valor do período anterior.

    Returns:
        Variação percentual (ex: 15.0 para +15%), ou None se anterior for zero.
    """
    if valor_anterior <= 0:
        return None
    return round(((valor_atual - valor_anterior) / valor_anterior) * 100, 2)


# ── 9. Projeção Anual ────────────────────────────────────────


def projetar_faturamento_anual(serie_mensal: list[float]) -> float | None:
    """
    Projeta o faturamento anual com base na série mensal usando regressão linear simples.

    Utiliza os meses já registrados para estimar o faturamento dos meses restantes.
    A projeção = acumulado até agora + soma das previsões para os meses futuros.

    Args:
        serie_mensal: Lista de faturamentos mensais (índice 0 = janeiro, etc.).
                      Deve ter pelo menos 2 meses para projetar.

    Returns:
        Faturamento anual projetado, ou None se dados insuficientes.
    """
    n = len(serie_mensal)
    if n < 2:
        return None

    # Regressão linear simples: y = a + b*x
    # x = número do mês (1, 2, 3, ..., n)
    sum_x = sum(range(1, n + 1))
    sum_y = sum(serie_mensal)
    sum_xy = sum((i + 1) * serie_mensal[i] for i in range(n))
    sum_x2 = sum(i * i for i in range(1, n + 1))

    # Coeficientes
    denominador = n * sum_x2 - sum_x * sum_x
    if denominador == 0:
        return None

    b = (n * sum_xy - sum_x * sum_y) / denominador
    a = (sum_y - b * sum_x) / n

    # Projetar faturamento total para 12 meses
    projecao = sum(a + b * mes for mes in range(1, MESES_ANO + 1))
    return round(max(projecao, 0), 2)


# ── 10. Ritmo Necessário para Bater Meta ─────────────────────


def calcular_ritmo_necessario(
    meta_anual: float | None,
    faturamento_acumulado: float,
    meses_restantes: int,
) -> float | None:
    """
    Calcula o faturamento mensal necessário nos meses restantes para atingir a meta.

    Fórmula:
        ritmo = (meta_anual - faturamento_acumulado) / meses_restantes

    Args:
        meta_anual: Meta anual de faturamento.
        faturamento_acumulado: Faturamento acumulado até o momento.
        meses_restantes: Quantidade de meses restantes no ano.

    Returns:
        Valor mensal necessário, ou None se meta não definida ou sem meses restantes.
    """
    if not meta_anual or meta_anual <= 0 or meses_restantes <= 0:
        return None

    restante = meta_anual - faturamento_acumulado
    if restante <= 0:
        return 0.0  # Meta já atingida

    return round(restante / meses_restantes, 2)


# ── 11. Faturamento para Próximo Cluster ─────────────────────


def calcular_faturamento_para_proximo_cluster(
    fat_acumulado: float,
    mes_atual: int,
    meta_csat: float | None,
    meta_engajamento: float,
    taxa_colaboracao: float,
    tracking_cluster_atual: int,
) -> float | None:
    """
    Calcula quanto de faturamento acumulado adicional é necessário para
    o Tracking de Cluster passar para o próximo cluster.

    Isola fat_acum da fórmula de tracking:
        tracking = (fat_acum / mes_atual * 12) * qualidade * 100
        fat_acum_necessario = limiar_proximo / (12 / mes_atual * qualidade * 100)

    Args:
        fat_acumulado: Faturamento acumulado atual.
        mes_atual: Mês atual (1–12).
        meta_csat: Meta de CSAT da EJ.
        meta_engajamento: Meta de engajamento MEJ em decimal (0–1).
        taxa_colaboracao: Taxa de faturamento colaborativo em decimal.
        tracking_cluster_atual: Cluster de tracking calculado atualmente (1–5).

    Returns:
        Valor adicional de faturamento acumulado necessário (R$), ou None se já
        estiver no cluster máximo ou dados insuficientes para o cálculo.
    """
    if tracking_cluster_atual >= 5:
        return None
    if mes_atual <= 0 or fat_acumulado < 0:
        return None
    if not meta_csat or meta_csat <= 0:
        return None

    quality = (
        meta_csat
        * (1 + meta_engajamento)
        * (1 + taxa_colaboracao)
        * FATOR_ESCALA_PONTOS
    )
    if quality <= 0:
        return None

    # Limiar mínimo do próximo cluster
    proximo_cluster = tracking_cluster_atual + 1
    limiar: float | None = None
    for min_val, _, c in CLUSTER_RANGES:
        if c == proximo_cluster:
            limiar = min_val
            break

    if limiar is None:
        return None

    fat_necessario = limiar * mes_atual / (MESES_ANO * quality)
    falta = fat_necessario - fat_acumulado
    return round(max(0.0, falta), 2)


# ── 12. Faturamento Colab para Próximo Cluster ───────────────


def calcular_faturamento_colab_para_proximo_cluster(
    fat_acumulado: float,
    fat_colab_acumulado: float,
    meta_csat: float | None,
    engajamento_real: float,
    indice_cluster_atual: int,
) -> float | None:
    """
    Calcula quanto de faturamento COLABORATIVO adicional é necessário para
    subir de cluster no índice c/ meta CSAT.

    Cada real de faturamento colab conta duplo na fórmula:
        pontos = fat_acum × (1 + taxa_colab) × quality
               = (fat_acum + fat_colab) × quality

    Adicionando X de faturamento colab (fat_acum e fat_colab crescem em X):
        (fat_acum + fat_colab + 2X) × quality = limiar
        X = (limiar / quality − fat_acum − fat_colab) / 2

    Args:
        fat_acumulado: Faturamento total acumulado atual.
        fat_colab_acumulado: Faturamento colaborativo acumulado atual.
        meta_csat: Meta de CSAT da EJ.
        engajamento_real: Engajamento real medido (decimal 0–1).
        indice_cluster_atual: Cluster resultante do índice real atual.

    Returns:
        Valor adicional de faturamento colaborativo necessário (R$), ou None se
        já no cluster máximo ou dados insuficientes.
    """
    if indice_cluster_atual >= 5:
        return None
    if fat_acumulado <= 0:
        return None
    if not meta_csat or meta_csat <= 0:
        return None

    # quality sem (1 + taxa_colab) — já expandido na derivação acima
    quality = meta_csat * (1 + engajamento_real) * FATOR_ESCALA_PONTOS
    if quality <= 0:
        return None

    proximo_cluster = indice_cluster_atual + 1
    limiar: float | None = None
    for min_val, _, c in CLUSTER_RANGES:
        if c == proximo_cluster:
            limiar = min_val
            break

    if limiar is None:
        return None

    falta = (limiar / quality - fat_acumulado - fat_colab_acumulado) / 2
    return round(max(0.0, falta), 2)


# ── 13. Média de CSAT ────────────────────────────────────────


def calcular_media_csat(valores_csat: list[float | None]) -> float | None:
    """
    Calcula a média de CSAT ignorando valores None.

    Args:
        valores_csat: Lista de valores de CSAT por mês.

    Returns:
        Média de CSAT ou None se não houver valores válidos.
    """
    validos = [v for v in valores_csat if v is not None]
    if not validos:
        return None
    return round(sum(validos) / len(validos), 2)
