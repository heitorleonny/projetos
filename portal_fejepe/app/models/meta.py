"""
Schemas Pydantic para a tabela `metas`.

Referência: banco.md → Tabela metas
"""

from datetime import datetime

from pydantic import BaseModel


class Meta(BaseModel):
    """Representação completa de uma meta anual (espelho da tabela `metas`)."""

    id: int
    id_ej: int
    ano: int
    meta_faturamento: float | None = None
    meta_taxa_colaboracao: float | None = None
    meta_csat: float | None = None
    meta_projetos_impacto: int | None = None
    meta_pdi: bool | None = None
    meta_engajamento_mej: float | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
