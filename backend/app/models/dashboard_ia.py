"""Contratos fechados para dashboards de evento montados por IA."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MetricaDashboard = Literal["faturamento_mes", "projetos_vendidos_mes", "csat"]
AgregacaoDashboard = Literal["soma", "media"]
DimensaoDashboard = Literal["ej", "mes"]
VisualDashboard = Literal["ranking", "barras", "linha", "cartao"]


class PlanoDashboard(BaseModel):
    """Parâmetros que o modelo pode selecionar; nenhuma expressão livre é aceita."""

    model_config = ConfigDict(extra="forbid", strict=True)

    titulo: str = Field(min_length=3, max_length=100)
    metrica: MetricaDashboard
    agregacao: AgregacaoDashboard
    dimensao: DimensaoDashboard
    visualizacao: VisualDashboard
    ano: int = Field(ge=2000, le=2100)
    mes_inicio: int = Field(ge=1, le=12)
    mes_fim: int = Field(ge=1, le=12)
    limite: int = Field(default=10, ge=1, le=50)

    @field_validator("titulo")
    @classmethod
    def titulo_sem_controle(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3 or any(ord(c) < 32 for c in value):
            raise ValueError("Título inválido.")
        return value

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.mes_fim < self.mes_inicio:
            raise ValueError("O mês final deve ser igual ou posterior ao mês inicial.")
        return self


class InterpretacaoDashboard(BaseModel):
    """Modelo pode pedir esclarecimento ou recusar fora do catálogo."""

    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["pronto", "esclarecer", "fora_do_catalogo"]
    plano: PlanoDashboard | None
    mensagem: str | None = Field(default=None, max_length=240)


class PedidoDashboard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pedido: str = Field(min_length=5, max_length=1000)
    evento_id: str = Field(min_length=1, max_length=80)

    @field_validator("pedido")
    @classmethod
    def normalizar_pedido(cls, value: str) -> str:
        return value.strip()


class CriarDashboard(PedidoDashboard):
    publico: bool = False


class AtualizarDashboard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    publico: bool


class PontoDashboard(BaseModel):
    rotulo: str
    valor: float | None


class DashboardResponse(BaseModel):
    id: UUID
    evento_id: str
    titulo: str
    metrica: MetricaDashboard
    unidade: Literal["BRL", "numero", "nota"]
    agregacao: AgregacaoDashboard
    dimensao: DimensaoDashboard
    visualizacao: VisualDashboard
    ano: int
    mes_inicio: int
    mes_fim: int
    publico: bool
    criado_por: UUID
    pontos: list[PontoDashboard] = Field(default_factory=list)


class DashboardPublicoResponse(BaseModel):
    titulo: str
    evento_id: str
    unidade: Literal["BRL", "numero", "nota"]
    visualizacao: VisualDashboard
    periodo: str
    pontos: list[PontoDashboard] = Field(default_factory=list)


class CotaDashboardResponse(BaseModel):
    mes: str
    consumidos: int
    reservados: int
    limite: int
    disponiveis: int
