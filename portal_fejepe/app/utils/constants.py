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
