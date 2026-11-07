"""
Router do painel administrativo — federações, usuários e importação de planilha.

QUEM ENTRA

Todo endpoint exige token válido (`get_current_user`). Fora `/sessao`, que só
diz quem é quem chama, todos exigem papel `admin` ou `plataforma` — e o papel
vem do BANCO (`public.usuario_atual()`), não do claim do token. O claim é uma
fotografia do último login; para administrar, vale o que `usuario` diz agora.

QUEM DECIDE O QUE CADA UM ALCANÇA

A RLS de infra/db/init/13-painel-admin.sql. As checagens daqui só antecipam o
erro com uma mensagem legível; se alguma falhar, o banco recusa igual.

    plataforma  todas as federações, todos os usuários, todas as cargas, e
                importação nacional ou de qualquer federação;
    admin       usuários e cargas da própria federação, e importação só dela;
                não vê a aba de federações.

A exceção à regra "papel nunca amplia tenant" é SÓ o cadastro da plataforma.
Nenhum endpoint daqui devolve dado de gestão de EJ. Ver docs/adr-003-painel-admin.md.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from postgrest.exceptions import APIError

from app.database import Client

from app.config import settings
from app.dependencies import get_current_user, get_supabase
from app.ingestao.carga import ErroCarga, ErroPapel
from app.ingestao.contrato import ErroContrato
from app.ingestao.importacao import ErroEscopo, Escopo
from app.models.admin import (
    FederacaoMaster, Plano, PlanoDados, VinculoPlano,
    Carga,
    Convite,
    Federacao,
    FederacaoAtualizacao,
    ResultadoImportacao,
    Sessao,
    Usuario,
    UsuarioAtualizacao,
)
from app.services import admin_service, convite_service, importacao_service

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administração"],
    dependencies=[Depends(get_current_user)],
)


# ── Erros do banco em HTTP ───────────────────────────────────


def _traduzir(exc: Exception) -> HTTPException:
    """PostgREST/Postgres → HTTP. 42501 é RLS ou GRANT recusando."""
    if isinstance(exc, httpx.ConnectError):
        return HTTPException(503, "Não foi possível conectar ao Supabase no momento.")
    if isinstance(exc, APIError):
        codigo = exc.code or ""
        if codigo == "42501":
            return HTTPException(403, "Sem permissão para esta operação.")
        if codigo == "23505":
            return HTTPException(409, "Já existe um cadastro com esse valor (provavelmente o e-mail).")
        if codigo == "P0002":
            return HTTPException(404, exc.message)
        if codigo in ("23514", "23502", "22P02", "23503"):
            return HTTPException(422, f"Valor recusado pelo banco: {exc.message}")
        return HTTPException(400, exc.message or "Operação recusada pelo banco.")
    return HTTPException(500, "Erro inesperado.")


# ── Sessão e permissões ──────────────────────────────────────


def get_sessao(sb: Client = Depends(get_supabase)) -> Sessao:
    try:
        linha = admin_service.usuario_atual(sb)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc
    if linha is None:
        return Sessao(usuario_id=None, papel=None, pode_administrar=False, eh_plataforma=False)
    papel = linha["papel"]
    return Sessao(
        usuario_id=linha["id"],
        nome=linha["nome"],
        papel=papel,
        federacao_id=linha["federacao_id"],
        pode_administrar=papel in ("admin", "plataforma"),
        eh_plataforma=papel == "plataforma",
    )


def exigir_gestor(sessao: Sessao = Depends(get_sessao)) -> Sessao:
    if not sessao.pode_administrar:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requer papel 'admin' ou 'plataforma'.")
    return sessao


def exigir_plataforma(sessao: Sessao = Depends(get_sessao)) -> Sessao:
    if not sessao.eh_plataforma:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requer papel 'plataforma'.")
    return sessao


@router.get("/sessao", response_model=Sessao, summary="Quem está usando o painel")
def sessao_atual(sessao: Sessao = Depends(get_sessao)) -> Sessao:
    """Papel e federação segundo o banco. O frontend usa para mostrar (ou não) o painel."""
    return sessao


# ── Federações ───────────────────────────────────────────────


@router.get("/federacoes", response_model=list[Federacao], summary="Federações visíveis")
def listar_federacoes(
    _: Sessao = Depends(exigir_gestor),
    sb: Client = Depends(get_supabase),
) -> list[dict]:
    try:
        return admin_service.listar_federacoes(sb)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc


@router.patch("/federacoes/{federacao_id}", response_model=Federacao, summary="Edita status e branding")
def atualizar_federacao(
    federacao_id: int,
    corpo: FederacaoAtualizacao,
    _: Sessao = Depends(exigir_plataforma),
    sb: Client = Depends(get_supabase),
) -> dict:
    dados = corpo.model_dump(exclude_unset=True)
    if not dados:
        raise HTTPException(422, "Nada para atualizar.")
    try:
        linha = admin_service.atualizar_federacao(sb, federacao_id, dados)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc
    if linha is None:
        raise HTTPException(404, "Federação não encontrada.")
    return linha


# ── Usuários ─────────────────────────────────────────────────


@router.get("/usuarios", response_model=list[Usuario], summary="Usuários com o último login")
def listar_usuarios(
    federacao_id: int | None = Query(default=None, description="Filtra por federação (útil para o operador)."),
    _: Sessao = Depends(exigir_gestor),
    sb: Client = Depends(get_supabase),
) -> list[dict]:
    try:
        return admin_service.listar_usuarios(sb, federacao_id)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc


@router.post(
    "/usuarios",
    response_model=Usuario,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra e gera link de convite",
)
def convidar_usuario(
    corpo: Convite,
    sessao: Sessao = Depends(exigir_gestor),
    sb: Client = Depends(get_supabase),
) -> dict:
    if sessao.eh_plataforma:
        if corpo.federacao_id is None:
            raise HTTPException(422, "Informe a federação do novo usuário.")
        federacao_id = corpo.federacao_id
    else:
        if corpo.federacao_id not in (None, sessao.federacao_id):
            raise HTTPException(403, "Um admin só cadastra usuários da própria federação.")
        if corpo.papel == "plataforma":
            raise HTTPException(403, "Só o operador da plataforma cria outro operador.")
        federacao_id = sessao.federacao_id

    try:
        usuario_id = convite_service.convidar(
            sb, nome=corpo.nome, email=corpo.email, papel=corpo.papel, federacao_id=federacao_id,
        )
        criado = admin_service.buscar_usuario(sb, usuario_id)
    except convite_service.ConviteIndisponivel as exc:
        raise HTTPException(503, str(exc)) from exc
    except convite_service.ErroConvite as exc:
        raise HTTPException(409, str(exc)) from exc
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc
    if criado is None:
        raise HTTPException(500, "Usuário criado, mas não foi possível relê-lo.")
    criado["convite_url"] = sb.convite_url if isinstance(getattr(sb, "convite_url", None), str) else None
    return criado


@router.patch("/usuarios/{usuario_id}", response_model=Usuario, summary="Edita papel, status e federação")
def atualizar_usuario(
    usuario_id: int,
    corpo: UsuarioAtualizacao,
    sessao: Sessao = Depends(exigir_gestor),
    sb: Client = Depends(get_supabase),
) -> dict:
    dados = corpo.model_dump(exclude_unset=True)
    if not dados:
        raise HTTPException(422, "Nada para atualizar.")

    # Ninguém mexe no próprio acesso pelo painel: é o jeito mais curto de uma
    # federação ficar sem admin, ou de a plataforma ficar sem operador.
    if usuario_id == sessao.usuario_id and dados.keys() & {"papel", "ativo", "federacao_id"}:
        raise HTTPException(422, "Você não pode alterar o próprio papel, status ou federação.")
    if not sessao.eh_plataforma:
        if "federacao_id" in dados and dados["federacao_id"] != sessao.federacao_id:
            raise HTTPException(403, "Só o operador da plataforma move usuário de federação.")
        if dados.get("papel") == "plataforma":
            raise HTTPException(403, "Só o operador da plataforma cria outro operador.")

    try:
        gravou = admin_service.atualizar_usuario(sb, usuario_id, dados)
        linha = admin_service.buscar_usuario(sb, usuario_id) if gravou else None
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc
    if linha is None:
        raise HTTPException(404, "Usuário não encontrado.")
    return linha


# ── Importação ───────────────────────────────────────────────


@router.get("/importacoes", response_model=list[Carga], summary="Cargas recentes")
def listar_importacoes(
    limite: int = Query(default=50, ge=1, le=200),
    _: Sessao = Depends(exigir_gestor),
    sb: Client = Depends(get_supabase),
) -> list[dict]:
    try:
        return admin_service.listar_cargas(sb, limite)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc


@router.post(
    "/importacoes",
    response_model=ResultadoImportacao,
    summary="Importa a planilha de EJ do Portal BJ",
    description=(
        "Com `simular=true` (o padrão), roda a carga inteira e desfaz no fim: as contagens são as "
        "reais e nada é gravado. Reenvie com `simular=false` para gravar. Sem `federacao_slug`, "
        "o escopo é nacional — só para o operador da plataforma."
    ),
)
def importar_planilha(
    arquivo: UploadFile = File(description="Exportação .xlsx do Portal BJ (aba EMPRESAS_JUNIORES)."),
    ano: int = Form(ge=2016, le=2100, description="Ano de referência — a planilha não traz."),
    federacao_slug: str | None = Form(default=None, description="Recorte por federação; vazio = nacional."),
    simular: bool = Form(default=True),
    sessao: Sessao = Depends(exigir_gestor),
    sb: Client = Depends(get_supabase),
) -> ResultadoImportacao:
    slug = (federacao_slug or "").strip().lower() or None

    if sessao.eh_plataforma:
        escopo = Escopo.nacional() if slug is None else Escopo.federacao(slug)
    else:
        try:
            propria = admin_service.slug_da_federacao(sb, sessao.federacao_id)
        except (APIError, httpx.ConnectError) as exc:
            raise _traduzir(exc) from exc
        if propria is None:
            raise HTTPException(403, "Sua federação não está visível para esta sessão; entre de novo.")
        if slug not in (None, propria):
            raise HTTPException(403, "Um admin só importa dados da própria federação.")
        escopo = Escopo.federacao(propria)

    limite = settings.UPLOAD_MAX_MB * 1024 * 1024
    conteudo = arquivo.file.read(limite + 1)
    if len(conteudo) > limite:
        raise HTTPException(413, f"Arquivo acima de {settings.UPLOAD_MAX_MB} MB.")

    try:
        relatorio, texto = importacao_service.importar_upload(
            conteudo,
            arquivo.filename or "",
            ano=ano,
            escopo=escopo,
            carregado_por=sessao.usuario_id,
            simular=simular,
        )
    except importacao_service.ArquivoInvalido as exc:
        raise HTTPException(422, str(exc)) from exc
    except importacao_service.IngestaoIndisponivel as exc:
        raise HTTPException(503, str(exc)) from exc
    except ErroEscopo as exc:
        raise HTTPException(422, str(exc)) from exc
    except ErroContrato as exc:
        raise HTTPException(
            422,
            {"mensagem": "A planilha não cumpre o contrato de entrada.", "problemas": exc.problemas,
             "carga_id": getattr(exc, "carga_id", None)},
        ) from exc
    except ErroCarga as exc:
        raise HTTPException(
            422 if exc.status == "rejeitada" else 409,
            {"mensagem": str(exc), "problemas": [], "carga_id": exc.carga_id},
        ) from exc
    except ErroPapel as exc:
        # Configuração errada do ambiente (INGESTAO_DSN aponta para um papel que
        # ignora RLS). Não é culpa de quem enviou; o texto vai para o log.
        raise HTTPException(500, "A importação está mal configurada neste ambiente.") from exc

    return ResultadoImportacao(relatorio=relatorio.para_json(), texto=texto)


@router.get("/master/federacoes", response_model=list[FederacaoMaster])
def resumo_master(_: Sessao = Depends(exigir_plataforma), sb: Client = Depends(get_supabase)):
    try:
        return admin_service.resumo_master(sb)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc


@router.get("/master/planos", response_model=list[Plano])
def planos_master(_: Sessao = Depends(exigir_plataforma), sb: Client = Depends(get_supabase)):
    try:
        return admin_service.listar_planos(sb)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc


@router.post("/master/planos", response_model=Plano, status_code=201)
def criar_plano(corpo: PlanoDados, _: Sessao = Depends(exigir_plataforma), sb: Client = Depends(get_supabase)):
    try:
        return admin_service.salvar_plano(sb, None, corpo.model_dump())
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc


@router.put("/master/planos/{plano_id}", response_model=Plano)
def editar_plano(plano_id: int, corpo: PlanoDados, _: Sessao = Depends(exigir_plataforma), sb: Client = Depends(get_supabase)):
    try:
        return admin_service.salvar_plano(sb, plano_id, corpo.model_dump())
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc


@router.put("/master/federacoes/{federacao_id}/plano", status_code=204)
def vincular_plano(federacao_id: int, corpo: VinculoPlano, _: Sessao = Depends(exigir_plataforma), sb: Client = Depends(get_supabase)):
    try:
        admin_service.vincular_plano(sb, federacao_id, corpo.plano_id)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc
