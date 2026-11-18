"""
Router da Análise do mês.

Endpoints:
    GET  /api/v1/analise                      — resumo, alertas, ascensão e resumo fixo
    GET  /api/v1/analise/briefing             — resumo redigido por IA (ou o fixo)
    POST /api/v1/analise/briefing/regenerar   — admin: descarta o cache e redige de novo

O briefing fica numa rota separada para a tela abrir na hora com o resumo fixo:
a chamada ao modelo pode levar alguns segundos na primeira vez do mês.

Leitura exige `membro`, como o restante dos painéis. O tenant é obrigatório
(sem compatibilidade sem claim, igual ao Nexo): a lista de alertas cita EJs pelo
nome e não pode ser montada sem uma federação definida.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.database import Client
from app.dependencies import get_current_user, get_federacao_id, get_supabase, require_papel
from app.ia.briefing import Redator, RedatorCompativel, gerar_briefing
from app.models.analise import AnaliseMes, Briefing
from app.services.analise_service import analisar_mes, analisar_mes_com_nomes
from app.services.federacao_service import buscar_nome_da_federacao

router = APIRouter(
    prefix="/api/v1/analise",
    tags=["Análise do mês"],
    dependencies=[Depends(get_current_user), Depends(require_papel("membro"))],
)


def get_tenant_analise(federacao_id: int | None = Depends(get_federacao_id)) -> int:
    if federacao_id is None:
        raise HTTPException(403, "Associe o usuário a uma federação para ver a análise do mês.")
    return federacao_id


@router.get(
    "",
    response_model=AnaliseMes,
    summary="Análise do mês",
    description=(
        "Resumo da federação no mês de referência, EJs em alerta e EJs em ascensão, "
        "com o motivo de cada uma. As regras são descritivas (não preditivas). "
        "Sem `mes`, usa o último mês com monitoramento carregado."
    ),
)
def get_analise(
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    sb: Client = Depends(get_supabase),
    federacao_id: int = Depends(get_tenant_analise),
) -> AnaliseMes:
    return analisar_mes(sb, ano=ano, mes=mes, federacao_id=federacao_id)


def get_redator() -> Redator:
    return RedatorCompativel()


def _briefing(sb, redator, *, ano, mes, federacao_id, forcar) -> Briefing:
    analise, nomes = analisar_mes_com_nomes(sb, ano=ano, mes=mes, federacao_id=federacao_id)
    return gerar_briefing(sb, redator, analise, federacao_id=federacao_id,
                          federacao_nome=buscar_nome_da_federacao(sb, federacao_id),
                          nomes_ejs=nomes, forcar=forcar)


@router.get(
    "/briefing",
    response_model=Briefing,
    summary="Resumo do mês redigido por IA",
    description=(
        "Resumo em 3 a 5 frases redigido pelo modelo a partir dos números da análise. "
        "O texto só é devolvido se passar nas guardas (números, nomes, vocabulário); "
        "caso contrário, ou sem IA configurada, devolve o resumo fixo (`gerado_por_ia=false`)."
    ),
)
def get_briefing(
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    sb: Client = Depends(get_supabase),
    federacao_id: int = Depends(get_tenant_analise),
    redator: Redator = Depends(get_redator),
) -> Briefing:
    return _briefing(sb, redator, ano=ano, mes=mes, federacao_id=federacao_id, forcar=False)


@router.post(
    "/briefing/regenerar",
    response_model=Briefing,
    summary="Redigir o resumo do mês de novo",
    dependencies=[Depends(require_papel("admin"))],
)
def post_regenerar_briefing(
    ano: int = Query(default=settings.ANO_DEFAULT, description="Ano de referência"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Mês de referência"),
    sb: Client = Depends(get_supabase),
    federacao_id: int = Depends(get_tenant_analise),
    redator: Redator = Depends(get_redator),
) -> Briefing:
    return _briefing(sb, redator, ano=ano, mes=mes, federacao_id=federacao_id, forcar=True)
