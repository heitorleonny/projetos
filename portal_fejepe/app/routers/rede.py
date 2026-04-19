"""
Router de endpoints para indicadores da rede FEJEPE.

Endpoints:
    GET /api/v1/rede/indicadores — KPIs consolidados da rede
    GET /api/v1/rede/ranking     — Ranking dinâmico de EJs
"""

from fastapi import APIRouter, Depends, Query

from supabase import Client

from app.config import settings
from app.dependencies import get_supabase
from app.models.indicadores import IndicadoresRede, RankingItem, RitmoMensalResponse, SdeResponse
from app.services.rede_service import calcular_indicadores_rede, calcular_ritmo_mensal, calcular_sde_cenarios, gerar_ranking

router = APIRouter(prefix="/api/v1/rede", tags=["Rede"])


@router.get(
    "/indicadores",
    response_model=IndicadoresRede,
    summary="Indicadores da rede",
    description=(
        "Retorna os KPIs consolidados da rede FEJEPE: faturamento total, "
        "faturamento colaborativo, média de CSAT, número de EJs fora do zero, "
        "distribuição por cluster, participação por comunidade e crescimento."
    ),
)
def get_indicadores_rede(
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    cluster: int | None = Query(default=None, ge=1, le=5, description="Filtrar por cluster"),
    comunidade: str | None = Query(default=None, description="Filtrar por comunidade"),
    sb: Client = Depends(get_supabase),
) -> IndicadoresRede:
    """Calcula e retorna indicadores consolidados da rede."""
    return calcular_indicadores_rede(
        sb,
        ano=ano,
        mes=mes,
        cluster=cluster,
        comunidade=comunidade,
    )


@router.get(
    "/ritmo-mensal",
    response_model=RitmoMensalResponse,
    summary="Ritmo mensal da rede",
    description=(
        "Retorna a contagem de EJs em ritmo mínimo e significativo "
        "para cada mês do ano."
    ),
)
def get_ritmo_mensal(
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    cluster: int | None = Query(default=None, ge=1, le=5, description="Filtrar por cluster"),
    comunidade: str | None = Query(default=None, description="Filtrar por comunidade"),
    sb: Client = Depends(get_supabase),
) -> RitmoMensalResponse:
    """Calcula ritmo mínimo e significativo para cada mês do ano."""
    return calcular_ritmo_mensal(
        sb,
        ano=ano,
        cluster=cluster,
        comunidade=comunidade,
    )


@router.get(
    "/sde",
    response_model=SdeResponse,
    summary="SDE da rede (3 cenários)",
    description=(
        "Calcula o Saldo de Desenvolvimento Estratégico em três cenários: "
        "Índice de Cluster, Índice c/ Meta CSAT e Tracking de Cluster."
    ),
)
def get_sde(
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    cluster: int | None = Query(default=None, ge=1, le=5, description="Filtrar por cluster"),
    comunidade: str | None = Query(default=None, description="Filtrar por comunidade"),
    sb: Client = Depends(get_supabase),
) -> SdeResponse:
    """Calcula SDE da rede em três cenários de índice de cluster."""
    return calcular_sde_cenarios(sb, ano=ano, mes=mes, cluster=cluster, comunidade=comunidade)


@router.get(
    "/ranking",
    response_model=list[RankingItem],
    summary="Ranking de EJs",
    description=(
        "Gera ranking dinâmico de EJs por critério: faturamento, CSAT, "
        "projetos ou faturamento colaborativo. Pode ser filtrado por "
        "cluster e comunidade."
    ),
)
def get_ranking(
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    criterio: str = Query(
        default="faturamento",
        description="Critério de ranking: faturamento, csat, projetos, colab",
        pattern="^(faturamento|csat|projetos|colab)$",
    ),
    cluster: int | None = Query(default=None, ge=1, le=5, description="Filtrar por cluster"),
    comunidade: str | None = Query(default=None, description="Filtrar por comunidade"),
    limit: int = Query(default=20, ge=1, le=100, description="Máximo de itens no ranking"),
    sb: Client = Depends(get_supabase),
) -> list[RankingItem]:
    """Gera ranking dinâmico de EJs."""
    return gerar_ranking(
        sb,
        ano=ano,
        mes=mes,
        criterio=criterio,
        cluster=cluster,
        comunidade=comunidade,
        limit=limit,
    )
