"""
Router de endpoints para a aba de Eventos.

Papel mínimo por endpoint (decisão registrada aqui porque o código sozinho não
a explica): LEITURA exige `membro`; ESCRITA, quando existir, exige `admin`.
Hoje o router é só de leitura, então na prática nada muda — mas quem adicionar
o primeiro POST/PUT/DELETE precisa saber a regra antes de escrever a rota.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import Client

from app.config import settings
from app.dependencies import get_current_user, get_federacao_id, get_supabase, require_papel
from app.models.evento import EventoDetalheResponse, EventoResumo
from app.services.evento_service import calcular_evento, listar_eventos, obter_evento
from app.services.federacao_service import buscar_federacao_do_usuario

router = APIRouter(
    prefix="/api/v1/eventos",
    tags=["Eventos"],
    dependencies=[Depends(get_current_user), Depends(require_papel("membro"))],
)


@router.get(
    "",
    response_model=list[EventoResumo],
    summary="Listar eventos",
    description="Retorna os eventos disponíveis para monitoramento na aba de Eventos.",
)
def get_eventos(
    sb: Client = Depends(get_supabase),
    federacao_id: int | None = Depends(get_federacao_id),
) -> list[EventoResumo]:
    return listar_eventos(_slug_do_usuario(sb, federacao_id))


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
    federacao_id: int | None = Depends(get_federacao_id),
) -> EventoDetalheResponse:
    evento = obter_evento(evento_id, _slug_do_usuario(sb, federacao_id))
    if evento is None:
        raise HTTPException(status_code=404, detail=f'Evento "{evento_id}" não encontrado.')

    try:
        resultado = calcular_evento(sb, evento_id, ano=ano, mes=mes, federacao_id=federacao_id)
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao Supabase no momento. Tente novamente em instantes.",
        ) from exc

    if resultado is None:
        raise HTTPException(status_code=404, detail=f'Evento "{evento_id}" não encontrado.')
    return resultado


def _slug_do_usuario(sb: Client, federacao_id: int | None) -> str | None:
    """Slug da federação de quem chamou — é por ele que o evento tem dono."""
    try:
        federacao = buscar_federacao_do_usuario(sb, federacao_id)
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao Supabase no momento. Tente novamente em instantes.",
        ) from exc
    return federacao["slug"] if federacao else None
