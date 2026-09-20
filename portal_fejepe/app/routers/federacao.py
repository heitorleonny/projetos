"""
Router da federação — o único endpoint público da API.

POR QUE ESTE ROUTER NÃO TEM `Depends(get_current_user)`

Todos os outros exigem JWT, e continuam exigindo. Este não pode: a tela de
login mostra o nome e o logo da federação ANTES de existir qualquer token.
Se o branding dependesse de autenticação, a primeira tela do portal seria a
única que nunca conseguiria se apresentar.

A ausência de dependência aqui é, portanto, deliberada — não é esquecimento.
Quem adicionar um segundo endpoint neste router precisa decidir explicitamente
se ele também é público; o default do projeto é que NÃO seja.

O que sustenta essa abertura do lado do banco: `anon` só tem GRANT nas quatro
colunas de branding das federações ativas (infra/db/init/09-federacao-branding.sql).
Mesmo que este código pedisse mais, o Postgres recusaria.

Uma consequência de usar `get_supabase`: se a requisição *trouxer* um token, o
cliente o repassa e o PostgREST atende como `authenticated` — aí quem filtra é
a política de tenant, e a federação de outro alguém volta vazia (404). O
frontend chama este endpoint sem token de propósito (src/services/brandingService.ts),
justamente para não depender de qual usuário está logado.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from supabase import Client

from app.config import settings
from app.dependencies import get_supabase
from app.models.federacao import FederacaoBranding

router = APIRouter(prefix="/api/v1/federacao", tags=["Federação"])


@router.get(
    "/branding",
    response_model=FederacaoBranding,
    summary="Branding da federação",
    description=(
        "Nome de exibição, logo, cor primária e ano de referência da federação. "
        "Endpoint PÚBLICO: responde sem autenticação, porque é consumido antes "
        "do login. Só devolve federações com status 'ativa'."
    ),
)
def get_branding(
    slug: str = Query(
        min_length=1,
        max_length=120,
        description="Slug da federação, como em `federacao.slug` (ex.: 'fejepe').",
    ),
    sb: Client = Depends(get_supabase),
) -> FederacaoBranding:
    """Busca o branding pelo slug. 404 quando não existe ou não está ativa."""
    slug_normalizado = slug.strip().lower()

    try:
        resposta = (
            sb.table("federacao")
            .select("slug, nome, logo_url, cor_primaria")
            .eq("slug", slug_normalizado)
            .limit(1)
            .execute()
        )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao Supabase no momento. Tente novamente em instantes.",
        ) from exc

    linhas = resposta.data or []
    if not linhas:
        # Mesma resposta para "slug inexistente" e "federação inativa": de fora,
        # as duas situações são a mesma — não há branding a mostrar.
        raise HTTPException(
            status_code=404,
            detail=f'Federação "{slug_normalizado}" não encontrada ou inativa.',
        )

    linha = linhas[0]
    return FederacaoBranding(
        slug=linha["slug"],
        nome=linha["nome"],
        logo_url=linha.get("logo_url"),
        cor_primaria=linha.get("cor_primaria"),
        # Não vem do banco: é configuração da plataforma, igual para todas as
        # federações. Mora aqui para que o frontend pare de manter a própria cópia.
        ano_default=settings.ANO_DEFAULT,
    )
