"""
Schemas da Análise do mês: resumo, EJs em alerta e EJs em ascensão.

Referência: docs/plano-analise-do-mes-2026-11-17.md
"""

from enum import Enum

from pydantic import BaseModel, Field


class Gravidade(str, Enum):
    alta = "alta"
    media = "media"
    baixa = "baixa"


class MotivoAlerta(str, Enum):
    sem_vendas_seguidas = "sem_vendas_seguidas"   # A1
    caiu_cluster = "caiu_cluster"                 # A2
    saiu_do_verde = "saiu_do_verde"               # A3
    queda_faturamento = "queda_faturamento"       # A4
    sem_reporte = "sem_reporte"                   # A6


class MotivoAscensao(str, Enum):
    subiu_cluster = "subiu_cluster"               # S1
    entrou_no_verde = "entrou_no_verde"           # S2
    ritmo_significativo = "ritmo_significativo"   # S3
    bateu_meta = "bateu_meta"                     # S4
    maior_crescimento = "maior_crescimento"       # S5
    primeira_venda = "primeira_venda"             # S6


class MotivoDestaque(BaseModel):
    codigo: str
    descricao: str = Field(description="Motivo em linguagem de gestor.")


class EjDestaque(BaseModel):
    id_ej: int
    nome: str
    foto_url: str | None = None
    gravidade: Gravidade | None = Field(default=None, description="Só em alertas.")
    motivos: list[MotivoDestaque]
    faturamento_mes: float = 0
    percentual_meta: float | None = None


class Comparativo(BaseModel):
    atual: float = 0
    anterior: float | None = None


class ResumoAnalise(BaseModel):
    total_ejs: int = 0
    fora_do_zero: Comparativo = Comparativo()
    no_verde: Comparativo = Comparativo()
    ritmo_significativo: Comparativo = Comparativo()
    faturamento_acumulado: Comparativo = Comparativo()
    meta_faturamento_total: float | None = None
    percentual_meta_rede: float | None = None


class Briefing(BaseModel):
    frases: list[str] = []
    gerado_por_ia: bool = False
    modelo: str | None = None


class RedacaoModelo(BaseModel):
    """Saída estruturada do redator do briefing (JSON Schema estrito)."""

    model_config = {"extra": "forbid"}

    frases: list[str]


class AnaliseMes(BaseModel):
    ano: int
    mes: int | None = Field(default=None, description="Mês de referência; None quando não há dados no ano.")
    mes_anterior: int | None = None
    mes_parcial: bool = Field(default=False, description="O mês de referência ainda está em andamento.")
    resumo: ResumoAnalise = ResumoAnalise()
    alertas: list[EjDestaque] = []
    ascensao: list[EjDestaque] = []
    briefing: Briefing = Briefing()
