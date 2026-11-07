"""Contrato fechado de interpretação: nenhum parâmetro escolhe tenant ou SQL."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Conceito = Literal["fora_do_zero", "ritmo", "cluster", "sde", "taxa_colaboracao", "faturamento_colaborativo",
                   "csat", "engajamento", "tracking_cluster", "projecao_anual", "ritmo_necessario", "meta_atingida"]


class PlanoConsulta(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    ferramenta: Literal["fora_do_zero", "indicadores_rede", "ranking", "sde", "ritmo_mensal", "explicar",
                        "esclarecer", "recusar"]
    ano: int | None = Field(ge=2000, le=2100)
    mes: int | None = Field(ge=1, le=12)
    criterio: Literal["faturamento", "csat", "projetos", "colab"] | None
    limite: int | None = Field(ge=1, le=100)
    cluster: int | None = Field(default=None, ge=1, le=5)
    busca: str | None = Field(default=None, min_length=2, max_length=80)
    esclarecimento: Literal["metrica_ranking", "periodo", "escopo"] | None = None
    federacao_mencionada: str | None = Field(default=None, min_length=2, max_length=200)
    # Só com `explicar`: o texto vem do glossário curado, nunca do modelo.
    conceito: Conceito | None = None

    @field_validator("busca")
    @classmethod
    def validar_busca(cls, valor):
        if valor is not None and (not valor.strip() or any(c in valor for c in "%_\n\r")):
            raise ValueError("Use um trecho literal do nome, sem curingas.")
        return valor.strip() if valor is not None else None


class PerguntaRede(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pergunta: str = Field(min_length=3, max_length=1000)
    contexto: PlanoConsulta | None = None

    @field_validator("pergunta")
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 3:
            raise ValueError("Escreva uma pergunta com pelo menos três caracteres.")
        return valor


class LinhaResposta(BaseModel):
    id_ej: int | None = None
    nome: str
    valor: float | None = None
    unidade: Literal["moeda", "numero"] | None = None


class OpcaoEsclarecimento(BaseModel):
    rotulo: str
    pergunta: str


class Esclarecimento(BaseModel):
    pergunta: str
    opcoes: list[OpcaoEsclarecimento]


class PontoSerie(BaseModel):
    """Um mês da série exibida na visualização da consulta; preenchido só pelo backend."""
    mes: int = Field(ge=1, le=12)
    valor: float


class RespostaRede(BaseModel):
    status: Literal["respondida", "fora_do_catalogo", "sem_dados", "esclarecimento"]
    resposta: str
    fonte: str | None = None
    ano: int | None = None
    mes: int | None = None
    total: int = 0
    linhas: list[LinhaResposta] = Field(default_factory=list)
    unidade: Literal["moeda", "numero"] = "numero"
    modelo: str | None = None

    contexto: PlanoConsulta | None = None
    sugestoes: list[str] = Field(default_factory=list)
    esclarecimento: Esclarecimento | None = None
    serie: list[PontoSerie] | None = None
