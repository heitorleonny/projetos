"""
Schemas Pydantic para indicadores consolidados da rede.

Referência: calculos.md, estrutura.md → Dashboard Geral da Rede
"""

from pydantic import BaseModel


class IndicadoresRede(BaseModel):
    """KPIs consolidados de toda a rede FEJEPE."""

    ano: int
    mes: int | None = None

    # Totais
    faturamento_total: float = 0
    faturamento_colab_total: float = 0
    total_projetos: int = 0

    # Médias
    media_csat: float | None = None

    # Contagens
    total_ejs: int = 0
    ejs_fora_do_zero: int = 0
    ejs_ritmo_minimo: int = 0
    ejs_ritmo_significativo: int = 0

    # SDE
    sde: float | None = None

    # Crescimento
    crescimento_vs_ano_anterior: float | None = None

    # Distribuições
    distribuicao_clusters: dict[int, int] = {}
    participacao_comunidades: dict[str, float] = {}


class RitmoMesItem(BaseModel):
    """Contagem de ritmo de um mês específico."""

    mes: int
    ejs_ritmo_minimo: int = 0
    ejs_ritmo_significativo: int = 0
    total_ejs: int = 0


class RitmoMensalResponse(BaseModel):
    """Ritmo mínimo e significativo de todos os meses do ano."""

    ano: int
    meses: list[RitmoMesItem] = []


class RankingItem(BaseModel):
    """Item de um ranking de EJs."""

    posicao: int
    id_ej: int
    nome: str
    cluster: int | None = None
    comunidade: str | None = None
    valor: float
    foto_url: str | None = None
