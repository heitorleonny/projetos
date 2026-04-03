"""
Schemas Pydantic para a tabela `monitoramento`.

Referência: banco.md → Tabela monitoramento
"""

from datetime import datetime

from pydantic import BaseModel


class Monitoramento(BaseModel):
    """Representação completa de um registro mensal de monitoramento."""

    id: int
    id_ej: int
    ano: int
    mes: int
    faturamento_mes: float = 0
    faturamento_acumulado: float = 0
    faturamento_colab_mes: float = 0
    faturamento_colab_acumulado: float = 0
    projetos_vendidos_mes: int = 0
    projetos_colab_mes: int = 0
    projetos_totais: int = 0
    csat: float | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
