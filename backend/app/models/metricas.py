"""Contratos das métricas personalizadas: definição validada, resultado e proposta da IA."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.metricas.expressao import ErroExpressao, analisar, formatar

Unidade = Literal["moeda", "numero"]
Visual = Literal["ranking", "valor", "serie"]


class DefinicaoMetrica(BaseModel):
    """O que a métrica calcula. É dado, não código: a expressão é revalidada sempre."""
    model_config = ConfigDict(extra="forbid")

    expressao: str = Field(min_length=1, max_length=300)
    unidade: Unidade = "numero"
    ano: int = Field(ge=2000, le=2100)
    mes_inicio: int = Field(default=1, ge=1, le=12)
    # None = até o último mês com dados da federação (resolvido na hora e mostrado na tela).
    mes_fim: int | None = Field(default=None, ge=1, le=12)
    cluster: int | None = Field(default=None, ge=1, le=5)
    ordem: Literal["desc", "asc"] = "desc"
    limite: int = Field(default=10, ge=1, le=50)
    agregacao_rede: Literal["soma", "media"] = "soma"

    @field_validator("expressao")
    @classmethod
    def validar_expressao(cls, valor: str) -> str:
        try:
            return formatar(analisar(valor))
        except ErroExpressao as exc:
            raise ValueError(str(exc)) from None

    @model_validator(mode="after")
    def validar_janela(self):
        if self.mes_fim is not None and self.mes_fim < self.mes_inicio:
            raise ValueError("O mês final do período não pode vir antes do mês inicial.")
        return self


def _texto_limpo(valor: str | None, campo: str) -> str | None:
    if valor is None:
        return None
    valor = " ".join(valor.split())
    if any(c in valor for c in "<>"):
        raise ValueError(f"{campo} não pode conter < ou >.")
    return valor


class MetricaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=3, max_length=80)
    descricao: str | None = Field(default=None, max_length=300)
    visual: Visual = "ranking"
    no_painel: bool = True
    definicao: DefinicaoMetrica

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        valor = _texto_limpo(valor, "O nome")
        if len(valor) < 3:
            raise ValueError("O nome precisa de pelo menos três caracteres.")
        return valor

    @field_validator("descricao")
    @classmethod
    def validar_descricao(cls, valor: str | None) -> str | None:
        valor = _texto_limpo(valor, "A descrição")
        return valor or None


class PainelEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    no_painel: bool


class OrdemEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[int] = Field(min_length=1, max_length=100)


class PreviaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definicao: DefinicaoMetrica


class Metrica(BaseModel):
    id: int
    nome: str
    descricao: str | None
    visual: Visual
    no_painel: bool
    ordem: int
    versao: int
    arquivada: bool
    definicao: DefinicaoMetrica
    formula_legivel: str
    criado_em: datetime | str
    atualizado_em: datetime | str


class VariavelCatalogo(BaseModel):
    nome: str
    rotulo: str
    descricao: str
    unidade: Unidade


class Catalogo(BaseModel):
    pode_editar: bool
    ano: int
    variaveis: list[VariavelCatalogo]
    texto_livre_disponivel: bool


class LinhaMetrica(BaseModel):
    posicao: int
    id_ej: int
    nome: str
    cluster: int | None = None
    valor: float


class PontoMetrica(BaseModel):
    mes: int = Field(ge=1, le=12)
    valor: float | None
    ejs: int


class ResultadoMetrica(BaseModel):
    status: Literal["ok", "sem_dados"]
    mensagem: str
    ano: int
    mes_inicio: int
    mes_fim: int | None
    unidade: Unidade
    formula: str
    formula_legivel: str
    explicacao: list[str]
    agregacao_rede: Literal["soma", "media"]
    ordem: Literal["desc", "asc"]
    linhas: list[LinhaMetrica] = []
    total_ejs: int = 0
    avaliadas: int = 0
    sem_cobertura: int = 0
    sem_valor: int = 0
    valor_rede: float | None = None
    serie: list[PontoMetrica] = []


# ── Texto livre ──────────────────────────────────────────────


class PlanoMetrica(BaseModel):
    """Saída do modelo. Fechada: nenhum campo escolhe tenant, ano livre, SQL ou texto exibido."""
    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["pronto", "esclarecer", "recusar"]
    esclarecimento: Literal["periodo", "metrica", "escopo"] | None
    nome: str | None = Field(min_length=3, max_length=80)
    expressao: str | None = Field(max_length=300)
    visual: Visual | None
    mes_inicio: int | None = Field(ge=1, le=12)
    mes_fim: int | None = Field(ge=1, le=12)
    cluster: int | None = Field(ge=1, le=5)
    ordem: Literal["desc", "asc"] | None
    limite: int | None = Field(ge=1, le=50)
    agregacao_rede: Literal["soma", "media"] | None
    ano_mencionado: int | None = Field(ge=1900, le=2200)
    federacao_mencionada: str | None = Field(max_length=200)


class TextoLivreEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texto: str = Field(min_length=3, max_length=500)

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 3:
            raise ValueError("Escreva um pedido com pelo menos três caracteres.")
        return valor


class OpcaoProposta(BaseModel):
    rotulo: str
    texto: str


class PropostaMetrica(BaseModel):
    status: Literal["pronta", "esclarecimento", "fora_do_catalogo"]
    mensagem: str
    opcoes: list[OpcaoProposta] = []
    metrica: MetricaEntrada | None = None
    formula_legivel: str | None = None
    resultado: ResultadoMetrica | None = None
    modelo: str | None = None
