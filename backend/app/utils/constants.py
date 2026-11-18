"""
Constantes estratégicas do Portal FEJEPE.

Referência: calculos.md
Todas as faixas de cluster e pesos de SDE são definidos aqui
para manter uma única fonte de verdade.
"""

# ── Faixas de Classificação de Cluster ────────────────────────
# Cada tupla: (pontuação_mínima, pontuação_máxima, cluster)
# Referência: calculos.md → 4️⃣ Tabela de Classificação de Cluster
CLUSTER_RANGES: list[tuple[float, float, int]] = [
    (0.00, 12_000_000.00, 1),
    (12_000_000.01, 24_000_000.00, 2),
    (24_000_000.01, 61_000_000.00, 3),
    (61_000_000.01, 130_000_000.00, 4),
    (130_000_000.01, float("inf"), 5),
]

# ── Pesos do SDE por cluster ─────────────────────────────────
# Referência: calculos.md → 1️⃣ Cálculo do SDE
# Índice 0 = Cluster 1, ..., Índice 4 = Cluster 5
SDE_WEIGHTS: list[float] = [0.30, 0.25, 0.15, 0.15, 0.15]

# ── Ano padrão da plataforma ─────────────────────────────────
ANO_DEFAULT: int = 2026

# ── Meses do ano ─────────────────────────────────────────────
MESES_ANO: int = 12

# ── Fator de escala da pontuação de cluster ───────────────────
# Referência: calculos.md → 5️⃣ Fórmula Oficial de Pontos de Cluster
FATOR_ESCALA_PONTOS: int = 100

# ── Faixas de atingimento da meta anual de faturamento ───────
# Agrupamento usado pelo Lamps (consulta `metas` e glossário), definido por
# Heitor em 07/11/2026. O % da meta continua vindo de
# calculo_service.calcular_percentual_meta (regras-de-negocio.md §4.3).
# Faixas: ≥ LIMIAR_META_ATINGIDA; [LIMIAR_META_PARCIAL, LIMIAR_META_ATINGIDA); < LIMIAR_META_PARCIAL.
LIMIAR_META_ATINGIDA: float = 100.0
LIMIAR_META_PARCIAL: float = 50.0

# ── Projeto de impacto e o cluster real ───────────────────────
# Regra de negócio (Heitor, 09/11/2026): projeto de impacto é obrigatório nos
# clusters 4 e 5. O tracking e os índices apontam o cluster, mas o cluster REAL
# só chega ao C4, e só permanece no C4 ou no C5, se a EJ tiver ao menos um projeto
# de impacto. Sem projeto, o cluster real fica limitado ao C3.
CLUSTER_EXIGE_PROJETO_IMPACTO: int = 4
CLUSTER_MAXIMO_SEM_PROJETO_IMPACTO: int = 3
