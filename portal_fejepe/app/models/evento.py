"""
Schemas Pydantic para a aba de Eventos.

Os eventos são calculados a partir dos indicadores já consolidados
das EJs, sem precisar de uma tabela dedicada nesta primeira versão.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EventoMetaTipo(str, Enum):
    """Tipos de meta monitorados no evento."""

    fora_do_zero = "fora_do_zero"
    verde_abril = "verde_abril"
    colab_tracking = "colab_tracking"


class EventoResumo(BaseModel):
    """Resumo de um evento disponível na aba de Eventos."""

    id_evento: str
    nome: str
    descricao: str | None = None
    ativo: bool = True
    ano: int
    mes_referencia: int = Field(..., ge=1, le=12)


class EventoMetaParticipante(BaseModel):
    """EJ contabilizada em uma meta do evento."""

    id_ej: int
    nome: str
    comunidade: str | None = None
    cluster: int | None = None
    status: str | None = None
    faturamento_acumulado: float = 0
    percentual_meta: float | None = None
    projetos_colab_totais: int = 0
    atende_cluster_1_2: bool = False


class EventoMetaResultado(BaseModel):
    """Resultado calculado para uma meta do evento."""

    tipo: EventoMetaTipo
    titulo: str
    descricao: str
    meta_percentual: float
    meta_contagem: int
    resultado_percentual: float
    resultado_contagem: int
    gap_percentual: float
    gap_contagem: int
    submeta_titulo: str | None = None
    submeta_percentual: float | None = None
    submeta_contagem: int | None = None
    subresultado_contagem: int | None = None
    subgap_contagem: int | None = None
    participantes: list[EventoMetaParticipante] = Field(default_factory=list)


class EventoDetalheResponse(BaseModel):
    """Resposta principal da aba de Eventos."""

    evento: EventoResumo
    total_ejs: int
    metas: list[EventoMetaResultado]