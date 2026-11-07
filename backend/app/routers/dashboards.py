"""Autoria de dashboards de evento com interpretação IA e leitura sob RLS."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from app.database import Client

from app.config import settings
from app.dependencies import get_current_user, get_federacao_id, get_supabase, get_supabase_anon, require_papel
from app.ia.creditos import (
    IdentidadeCreditosIAInvalida,
    LimiteCreditosIA,
    consultar_creditos_ia,
)
from app.ia.dashboard_interpretador import PedidoDashboardNaoSuportado
from app.ia.provedor import ProvedorIndisponivel
from app.models.dashboard_ia import (
    AtualizarDashboard,
    CotaDashboardResponse,
    CriarDashboard,
    DashboardPublicoResponse,
    DashboardResponse,
)
from app.services.dashboard_ia_service import (
    atualizar_publicacao,
    listar_dashboards,
    obter_dashboard_publico,
    salvar_dashboard,
)

router = APIRouter(prefix="/api/v1/ia/dashboards", tags=["Dashboards de evento por IA"])


def _tenant(federacao_id: int | None) -> int:
    if federacao_id is None:
        raise HTTPException(403, "Associe seu usuário a uma federação para usar dashboards.")
    return federacao_id


@router.get("/publicos/{chave}", response_model=DashboardPublicoResponse)
def get_dashboard_publico(chave: UUID, sb: Client = Depends(get_supabase_anon)):
    """Entrega somente o snapshot que o gestor publicou, sem acessar fatos."""
    try:
        resultado = obter_dashboard_publico(sb, chave)
    except Exception:
        raise HTTPException(503, "Não foi possível carregar este dashboard público.") from None
    if resultado is None:
        raise HTTPException(404, "Dashboard público não encontrado.")
    return resultado


@router.get("", response_model=list[DashboardResponse], dependencies=[Depends(require_papel("membro"))])
def get_dashboards(
    sb: Client = Depends(get_supabase),
    federacao_id: int | None = Depends(get_federacao_id),
    user=Depends(get_current_user),
):
    try:
        return listar_dashboards(sb, _tenant(federacao_id), str(user.id))
    except Exception:
        raise HTTPException(503, "Não foi possível carregar os dashboards da federação.") from None


@router.get("/creditos", response_model=CotaDashboardResponse,
            dependencies=[Depends(require_papel("membro"))])
def get_creditos_dashboard(
    sb: Client = Depends(get_supabase),
    _user=Depends(get_current_user),
):
    try:
        return CotaDashboardResponse(**consultar_creditos_ia(sb))
    except Exception:
        raise HTTPException(503, "Não foi possível consultar a cota de dashboards.") from None


@router.post("", response_model=DashboardResponse, status_code=201,
             dependencies=[Depends(require_papel("admin"))])
def post_dashboard(
    entrada: CriarDashboard,
    sb: Client = Depends(get_supabase),
    federacao_id: int | None = Depends(get_federacao_id),
    user=Depends(get_current_user),
):
    tenant = _tenant(federacao_id)
    try:
        cota = consultar_creditos_ia(sb)
        if cota["disponiveis"] <= 0:
            raise LimiteCreditosIA("A federação esgotou os créditos mensais para criar dashboards.")
        return salvar_dashboard(
            sb,
            pedido=entrada.pedido,
            evento_id=entrada.evento_id,
            publico=entrada.publico,
            federacao_id=tenant,
            usuario_id=str(user.id),
            ano_padrao=settings.ANO_DEFAULT,
        )
    except LimiteCreditosIA as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "86400"}) from None
    except IdentidadeCreditosIAInvalida as exc:
        raise HTTPException(403, str(exc)) from None
    except ProvedorIndisponivel as exc:
        raise HTTPException(503, str(exc)) from None
    except PedidoDashboardNaoSuportado as exc:
        raise HTTPException(422, str(exc)) from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Não foi possível montar o dashboard. Nenhuma métrica foi alterada.") from None


@router.patch("/{dashboard_id}", response_model=DashboardResponse,
              dependencies=[Depends(require_papel("admin"))])
def patch_dashboard(
    dashboard_id: UUID,
    entrada: AtualizarDashboard,
    sb: Client = Depends(get_supabase),
    federacao_id: int | None = Depends(get_federacao_id),
    user=Depends(get_current_user),
):
    try:
        return atualizar_publicacao(
            sb, dashboard_id, publico=entrada.publico,
            federacao_id=_tenant(federacao_id), usuario_id=str(user.id),
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Não foi possível atualizar a publicação do dashboard.") from None
