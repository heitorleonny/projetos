"""
Router da federação — onde mora o único endpoint público da API (`/branding`).

POR QUE ESTE ROUTER NÃO TEM `Depends(get_current_user)`

Todos os outros exigem JWT, e continuam exigindo. Este não pode: a tela de
login mostra o nome e o logo da federação ANTES de existir qualquer token.
Se o branding dependesse de autenticação, a primeira tela do portal seria a
única que nunca conseguiria se apresentar.

A ausência de dependência aqui é, portanto, deliberada — não é esquecimento.
Quem adicionar um segundo endpoint neste router precisa decidir explicitamente
se ele também é público; o default do projeto é que NÃO seja.

O segundo endpoint público é `GET /logo` (migração 25), decidido em 07/11/2026:
devolve só o arquivo da logo de uma federação ativa, pelo slug, para a mesma
tela de login. A escrita (`PUT/DELETE /minha/logo`) exige admin, como a paleta.

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
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile

from app.database import Client
from postgrest.exceptions import APIError

from app.config import settings
from app.dependencies import get_current_user, get_federacao_id, get_supabase, get_supabase_anon, require_papel
from app.models.federacao import FederacaoBranding, PaletaFederacao
from app.services.federacao_service import (TAMANHO_MAXIMO_LOGO, buscar_federacao_do_usuario, buscar_logo_publica,
                                           definir_logo, definir_paleta, detectar_tipo_logo, remover_logo)

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
            .select("slug, nome, logo_url, cor_primaria, cor_secundaria, cor_acento, slogan")
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

    return _branding(linhas[0])


@router.get(
    "/minha",
    response_model=FederacaoBranding,
    summary="Branding da federação do usuário logado",
    description=(
        "O mesmo contrato de `/branding`, mas da federação do TOKEN, não do "
        "deploy. É o que deixa uma instância servir várias federações: antes do "
        "login vale o slug do deploy; depois, a federação de quem entrou."
    ),
    # NÃO é público, ao contrário do vizinho: exige token, como o resto da API.
    dependencies=[Depends(get_current_user), Depends(require_papel("membro"))],
)
def get_branding_do_usuario(
    sb: Client = Depends(get_supabase),
    federacao_id: int | None = Depends(get_federacao_id),
) -> FederacaoBranding:
    """Branding da federação de quem chamou. 404 se o usuário não tem federação."""
    try:
        linha = buscar_federacao_do_usuario(sb, federacao_id)
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao Supabase no momento. Tente novamente em instantes.",
        ) from exc
    if linha is None:
        raise HTTPException(status_code=404, detail="Usuário sem federação associada.")
    return _branding(linha)


@router.put("/minha/paleta", response_model=FederacaoBranding,
            dependencies=[Depends(get_current_user), Depends(require_papel("admin"))])
def put_paleta(entrada: PaletaFederacao, sb: Client = Depends(get_supabase),
               federacao_id: int | None = Depends(get_federacao_id)) -> FederacaoBranding:
    if federacao_id is None:
        raise HTTPException(403, "Usuário sem federação associada.")
    try:
        linha = definir_paleta(sb, entrada.model_dump())
    except APIError as exc:
        if exc.code == "42501":
            raise HTTPException(403, "Seu vínculo atual não permite alterar a paleta.") from None
        raise HTTPException(503, "Não foi possível salvar a paleta agora.") from None
    except httpx.HTTPError:
        raise HTTPException(503, "Não foi possível salvar a paleta agora.") from None
    if linha is None:
        raise HTTPException(403, "Seu vínculo atual não permite alterar a paleta.")
    return _branding(linha)


@router.get(
    "/logo",
    summary="Logo enviada pela federação",
    description=(
        "Arquivo da logo (PNG, JPEG ou WebP) de uma federação ativa. Endpoint PÚBLICO, "
        "pelo mesmo motivo de `/branding`: a tela de login mostra a logo antes do token. "
        "O parâmetro `v` vem de `logo_url` e só serve para renovar o cache."
    ),
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}}}, 404: {"description": "Sem logo enviada"}},
)
def get_logo(
    slug: str = Query(min_length=1, max_length=120),
    v: str | None = Query(default=None, max_length=32),
    sb: Client = Depends(get_supabase_anon),
) -> Response:
    try:
        logo = buscar_logo_publica(sb, slug.strip().lower())
    except (APIError, httpx.HTTPError):
        raise HTTPException(503, "Não foi possível carregar a logo agora.") from None
    if logo is None:
        raise HTTPException(404, "Federação sem logo enviada.")
    # Versão certa na URL: o arquivo daquele endereço nunca muda.
    cache = "public, max-age=31536000, immutable" if v == logo["versao"] else "public, max-age=300"
    return Response(content=bytes(logo["conteudo"]), media_type=logo["tipo"], headers={
        "Cache-Control": cache, "ETag": f'"{logo["versao"]}"',
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
    })


def _erro_de_escrita(exc: Exception, acao: str) -> HTTPException:
    if isinstance(exc, APIError) and exc.code == "42501":
        return HTTPException(403, f"Seu vínculo atual não permite {acao} a logo.")
    if isinstance(exc, APIError) and exc.code == "22023":
        return HTTPException(422, "Use uma imagem PNG, JPEG ou WebP de até 512 KB.")
    return HTTPException(503, f"Não foi possível {acao} a logo agora.")


@router.put("/minha/logo", response_model=FederacaoBranding,
            summary="Envia a logo da federação do usuário",
            dependencies=[Depends(get_current_user), Depends(require_papel("admin"))])
async def put_logo(arquivo: UploadFile = File(description="PNG, JPEG ou WebP de até 512 KB."),
                   sb: Client = Depends(get_supabase),
                   federacao_id: int | None = Depends(get_federacao_id)) -> FederacaoBranding:
    if federacao_id is None:
        raise HTTPException(403, "Usuário sem federação associada.")
    # Lê no máximo um byte além do limite: arquivo grande não ocupa memória.
    conteudo = await arquivo.read(TAMANHO_MAXIMO_LOGO + 1)
    if not conteudo:
        raise HTTPException(422, "Escolha um arquivo de imagem.")
    if len(conteudo) > TAMANHO_MAXIMO_LOGO:
        raise HTTPException(413, "A logo deve ter até 512 KB.")
    tipo = detectar_tipo_logo(conteudo)
    if tipo is None:
        raise HTTPException(422, "Use uma imagem PNG, JPEG ou WebP. SVG não é aceito.")
    try:
        linha = definir_logo(sb, conteudo, tipo)
    except (APIError, httpx.HTTPError) as exc:
        raise _erro_de_escrita(exc, "salvar") from None
    if linha is None:
        raise HTTPException(403, "Seu vínculo atual não permite salvar a logo.")
    return _branding(linha)


@router.delete("/minha/logo", response_model=FederacaoBranding,
               summary="Remove a logo enviada pela federação do usuário",
               dependencies=[Depends(get_current_user), Depends(require_papel("admin"))])
def delete_logo(sb: Client = Depends(get_supabase),
                federacao_id: int | None = Depends(get_federacao_id)) -> FederacaoBranding:
    if federacao_id is None:
        raise HTTPException(403, "Usuário sem federação associada.")
    try:
        linha = remover_logo(sb)
    except (APIError, httpx.HTTPError) as exc:
        raise _erro_de_escrita(exc, "remover") from None
    if linha is None:
        raise HTTPException(403, "Seu vínculo atual não permite remover a logo.")
    return _branding(linha)


def _branding(linha: dict) -> FederacaoBranding:
    return FederacaoBranding(
        slug=linha["slug"],
        nome=linha["nome"],
        logo_url=linha.get("logo_url"),
        cor_primaria=linha.get("cor_primaria"),
        cor_secundaria=linha.get("cor_secundaria"),
        cor_acento=linha.get("cor_acento"),
        slogan=linha.get("slogan"),
        # Não vem do banco: é configuração da plataforma, igual para todas as
        # federações. Mora aqui para que o frontend pare de manter a própria cópia.
        ano_default=settings.ANO_DEFAULT,
    )
