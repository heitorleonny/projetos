"""
Router de endpoints para Empresas Juniores.

Endpoints:
    GET /api/v1/empresas          — Listar EJs com filtros, ordenação e paginação
    GET /api/v1/empresas/comparar — Comparar múltiplas EJs lado a lado
    GET /api/v1/empresas/{id_ej}  — Perfil completo de uma EJ
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from supabase import Client

from app.config import settings
from app.dependencies import get_supabase
from app.models.empresa import (
    Direcao,
    EmpresaComIndicadores,
    EmpresaListaResponse,
    EmpresaPerfilCompleto,
    OrdemEmpresa,
)
from app.services.empresa_service import (
    buscar_empresa,
    comparar_empresas,
    listar_empresas,
)

router = APIRouter(prefix="/api/v1/empresas", tags=["Empresas"])


@router.get(
    "",
    response_model=EmpresaListaResponse,
    summary="Listar EJs",
    description=(
        "Retorna a lista de Empresas Juniores da rede FEJEPE com indicadores "
        "calculados, suportando filtros por ano, mês, cluster, comunidade, "
        "status e busca por nome. Inclui paginação e ordenação."
    ),
)
def list_empresas(
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência (1-12). Omita para usar acumulado até o último mês disponível."),
    fora_do_zero_colab: bool = Query(default=False, description="Filtrar apenas EJs com faturamento colaborativo acumulado maior que zero"),
    cluster: int | None = Query(default=None, ge=1, le=5, description="Filtrar por cluster (1-5)"),
    comunidade: str | None = Query(default=None, description="Filtrar por comunidade"),
    status: str | None = Query(default=None, description="Filtrar por status da EJ"),
    search: str | None = Query(default=None, min_length=1, max_length=100, description="Busca por nome da EJ"),
    cidade: str | None = Query(default=None, min_length=1, max_length=100, description="Filtrar por cidade"),
    universidade: str | None = Query(default=None, min_length=1, max_length=200, description="Filtrar por universidade"),
    ordem_por: OrdemEmpresa = Query(default=OrdemEmpresa.nome, description="Campo de ordenação"),
    direcao: Direcao = Query(default=Direcao.asc, description="Direção da ordenação"),
    page: int = Query(default=1, ge=1, description="Página atual"),
    page_size: int = Query(default=20, ge=1, le=100, description="Itens por página"),
    sb: Client = Depends(get_supabase),
) -> EmpresaListaResponse:
    """Lista EJs com filtros, indicadores calculados, ordenação e paginação."""
    return listar_empresas(
        sb,
        ano=ano,
        mes=mes,
        fora_do_zero_colab=fora_do_zero_colab,
        cluster=cluster,
        comunidade=comunidade,
        status=status,
        search=search,
        cidade=cidade,
        universidade=universidade,
        ordem_por=ordem_por,
        direcao=direcao,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/comparar",
    response_model=list[EmpresaComIndicadores],
    summary="Comparar EJs",
    description=(
        "Compara múltiplas EJs lado a lado. Retorna indicadores calculados "
        "para cada EJ selecionada, ordenados por faturamento."
    ),
)
def compare_empresas(
    ids: list[int] = Query(..., min_length=2, max_length=10, description="IDs das EJs a comparar (id_ej). Min 2, max 10."),
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    sb: Client = Depends(get_supabase),
) -> list[EmpresaComIndicadores]:
    """Compara EJs lado a lado com indicadores calculados."""
    return comparar_empresas(sb, ids, ano=ano, mes=mes)


@router.get(
    "/{id_ej}",
    response_model=EmpresaPerfilCompleto,
    summary="Perfil da EJ",
    description=(
        "Retorna o perfil estratégico completo de uma EJ, incluindo "
        "série temporal de faturamento, metas vs realizado, projeção "
        "anual, ritmo necessário e crescimento."
    ),
)
def get_empresa(
    id_ej: int,
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    sb: Client = Depends(get_supabase),
) -> EmpresaPerfilCompleto:
    """Retorna perfil completo de uma EJ individual."""
    result = buscar_empresa(sb, id_ej, ano=ano, mes=mes)
    if result is None:
        raise HTTPException(status_code=404, detail=f"EJ com id_ej={id_ej} não encontrada.")
    return result
