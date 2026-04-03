"""
Schemas Pydantic para a tabela `empresa_junior`.

Referência: banco.md → Tabela empresa_junior
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Enums de ordenação / filtro ──────────────────────────────


class OrdemEmpresa(str, Enum):
    """Campos disponíveis para ordenação de EJs."""

    nome = "nome"
    faturamento = "faturamento"
    faturamento_colab = "faturamento_colab"
    cluster = "cluster"
    comunidade = "comunidade"
    csat = "csat"
    percentual_meta = "percentual_meta"
    projetos = "projetos"


class Direcao(str, Enum):
    """Direção da ordenação."""

    asc = "asc"
    desc = "desc"


class Ritmo(str, Enum):
    """
    Classificação de ritmo de uma EJ no mês.

    - sem_vendas: faturamento_mes == 0
    - minimo: faturamento_mes > 0 (já vendeu)
    - significativo: faturamento_mes >= meta_mensal
    """

    sem_vendas = "sem_vendas"
    minimo = "minimo"
    significativo = "significativo"


class TendenciaCluster(str, Enum):
    """Tendência do cluster em relação ao período anterior."""

    sobe = "sobe"
    mantem = "mantem"
    desce = "desce"


# ── Schemas ──────────────────────────────────────────────────


class EmpresaJunior(BaseModel):
    """Representação completa de uma EJ (espelho da tabela `empresa_junior`)."""

    id: int
    id_ej: int
    nome: str
    cnpj: str | None = None
    ano_federacao: int | None = None
    federacao: str | None = None
    cluster: int | None = None
    comunidade: str | None = None
    estado: str | None = None
    cidade: str | None = None
    universidade: str | None = None
    curso: str | None = None
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    foto_url: str | None = None

    model_config = {"from_attributes": True}


class EmpresaResumo(BaseModel):
    """Versão compacta de uma EJ para listagens rápidas."""

    id: int
    id_ej: int
    nome: str
    cluster: int | None = None
    comunidade: str | None = None
    status: str | None = None
    foto_url: str | None = None


class FaturamentoMensal(BaseModel):
    """Ponto de faturamento mensal (usado em gráficos de série temporal)."""

    mes: int = Field(..., ge=1, le=12)
    faturamento: float
    faturamento_colab: float
    projetos_vendidos: int
    projetos_colab_vendidos: int = 0
    csat: float | None = None


class MetaVsRealizado(BaseModel):
    """Comparação entre meta e valor realizado."""

    meta_faturamento: float | None = None
    faturamento_acumulado: float = 0
    percentual_meta: float = 0

    meta_csat: float | None = None
    csat_medio: float | None = None

    meta_taxa_colaboracao: float | None = None
    taxa_colaboracao: float | None = None

    meta_projetos_impacto: int | None = None

    meta_engajamento_mej: float | None = None


class EmpresaComIndicadores(BaseModel):
    """
    EJ enriquecida com indicadores calculados pelo backend.

    Usada na listagem principal e comparações.
    """

    # Dados cadastrais
    id: int
    id_ej: int
    nome: str
    cluster: int | None = None
    comunidade: str | None = None
    status: str | None = None
    foto_url: str | None = None
    cidade: str | None = None
    universidade: str | None = None

    # Indicadores calculados
    faturamento_acumulado: float = 0
    faturamento_colab_acumulado: float = 0
    faturamento_mes: float = 0
    projetos_totais: int = 0
    projetos_colab_totais: int = 0
    csat_medio: float | None = None
    percentual_meta: float | None = None
    ritmo: Ritmo = Ritmo.sem_vendas
    taxa_colaboracao: float | None = None

    # Tracking de cluster
    pontos_cluster: float | None = None
    cluster_calculado: int | None = None
    tendencia_cluster: TendenciaCluster | None = None


class EmpresaPerfilCompleto(BaseModel):
    """
    Perfil completo de uma EJ individual.

    Inclui série temporal, metas vs realizado, projeção e crescimento.
    """

    # Dados cadastrais
    empresa: EmpresaJunior

    # Indicadores do período
    indicadores: EmpresaComIndicadores

    # Série mensal (para gráficos)
    serie_mensal: list[FaturamentoMensal] = []

    # Metas vs realizado
    metas: MetaVsRealizado | None = None

    # Projeção e crescimento
    projecao_anual: float | None = None
    ritmo_necessario: float | None = None
    crescimento_mensal: float | None = None
    crescimento_anual: float | None = None


class PaginacaoMeta(BaseModel):
    """Metadados de paginação."""

    page: int
    page_size: int
    total: int
    total_pages: int


class EmpresaListaResponse(BaseModel):
    """Resposta paginada para listagem de EJs."""

    data: list[EmpresaComIndicadores]
    meta: PaginacaoMeta
