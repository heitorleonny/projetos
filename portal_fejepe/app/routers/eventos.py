"""
Router de endpoints para a aba de Eventos.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from supabase import Client

from app.config import settings
from app.dependencies import get_supabase
from app.models.evento import EventoDetalheResponse, EventoResumo
from app.services.evento_service import calcular_evento, listar_eventos, obter_evento

router = APIRouter(prefix="/api/v1/eventos", tags=["Eventos"])


@router.get(
    "",
    response_model=list[EventoResumo],
    summary="Listar eventos",
    description="Retorna os eventos disponíveis para monitoramento na aba de Eventos.",
)
def get_eventos() -> list[EventoResumo]:
    return listar_eventos()


@router.get(
    "/{evento_id}",
    response_model=EventoDetalheResponse,
    summary="Detalhe do evento",
    description="Retorna as metas calculadas do evento selecionado.",
)
def get_evento(
    evento_id: str,
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    sb: Client = Depends(get_supabase),
) -> EventoDetalheResponse:
    evento = obter_evento(evento_id)
    if evento is None:
        raise HTTPException(status_code=404, detail=f'Evento "{evento_id}" não encontrado.')

    try:
        resultado = calcular_evento(sb, evento_id, ano=ano, mes=mes)
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao Supabase no momento. Tente novamente em instantes.",
        ) from exc

    if resultado is None:
        raise HTTPException(status_code=404, detail=f'Evento "{evento_id}" não encontrado.')
    return resultado