"""Painel de métricas personalizadas.

QUEM ENTRA (decisão de 12/11/2026)

* Ler o catálogo, a lista e os resultados: qualquer usuário autenticado da
  federação (`membro` em diante).
* Criar, editar, prévia, texto livre, tirar do painel, arquivar, restaurar,
  excluir e reordenar: só `admin` ou `plataforma` (admin master) ativo e vinculado
  À federação, com o papel lido do BANCO (`public.usuario_atual()`), não do token.
  O `plataforma` não ganha outras federações aqui. A RLS (27 e 28) repete a regra.

O tenant vem sempre da autenticação; nenhum corpo, pergunta ou definição o escolhe.
"""

from __future__ import annotations

import logging
from time import monotonic

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from postgrest.exceptions import APIError
from pydantic import ValidationError

from app.config import settings
from app.database import Client
from app.dependencies import get_current_user, get_federacao_id, get_supabase, require_papel
from app.ia.metricas_interprete import (IdentidadeInativa, InterpreteCompativel, InterpreteMetricas,
                                        LimiteMetricasIA, propor)
from app.ia.provedor import ProvedorIndisponivel
from app.metricas.catalogo import VARIAVEIS
from app.metricas.expressao import ErroExpressao
from app.models.metricas import (Catalogo, Metrica, MetricaEntrada, OrdemEntrada, PainelEntrada, PreviaEntrada,
                                 PropostaMetrica, ResultadoMetrica, TextoLivreEntrada, VariavelCatalogo)
from app.services import admin_service, metricas_service
from app.services.federacao_service import buscar_federacao_do_usuario
from app.services.metricas_service import ErroMetrica, MetricaNaoEncontrada

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metricas", tags=["Métricas personalizadas"],
                   dependencies=[Depends(get_current_user), Depends(require_papel("membro"))])


def get_tenant(federacao_id: int | None = Depends(get_federacao_id)) -> int:
    if federacao_id is None:
        raise HTTPException(403, "Associe o usuário a uma federação para usar o painel de métricas.")
    return federacao_id


def get_interprete() -> InterpreteMetricas:
    return InterpreteCompativel()


def _eh_admin(sb: Client, tenant: int) -> bool:
    linha = admin_service.usuario_atual(sb)
    return bool(linha and linha.get("papel") in ("admin", "plataforma") and linha.get("federacao_id") == tenant)


def exigir_admin(tenant: int = Depends(get_tenant), sb: Client = Depends(get_supabase)) -> int:
    try:
        permitido = _eh_admin(sb, tenant)
    except (APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc
    if not permitido:
        raise HTTPException(403, "Só administradores da federação (ou o admin master dela) criam ou alteram métricas.")
    return tenant


def _traduzir(exc: Exception) -> HTTPException:
    if isinstance(exc, MetricaNaoEncontrada):
        return HTTPException(404, str(exc))
    if isinstance(exc, (ErroMetrica, ErroExpressao)):
        return HTTPException(422, str(exc))
    if isinstance(exc, APIError):
        codigo = exc.code or ""
        if codigo == "42501":
            return HTTPException(403, "Sem permissão para esta operação.")
        if codigo == "23505":
            return HTTPException(409, "Já existe uma métrica ativa com esse nome na federação.")
        if codigo in ("23514", "23502", "22P02", "23503", "22023"):
            return HTTPException(422, "Valor recusado pelo banco. Confira os campos da métrica.")
        return HTTPException(400, "Operação recusada pelo banco.")
    if isinstance(exc, httpx.ConnectError):
        return HTTPException(503, "Banco indisponível no momento.")
    return HTTPException(500, "Erro inesperado.")


def _executar(funcao, *args, **kwargs):
    try:
        return funcao(*args, **kwargs)
    except (MetricaNaoEncontrada, ErroMetrica, ErroExpressao, APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc


def _validar_ano(entrada_ano: int) -> None:
    if entrada_ano != settings.ANO_DEFAULT:
        raise HTTPException(422, f"Nesta versão, as métricas usam só o ano de {settings.ANO_DEFAULT}.")


# ── Leitura (todos da federação) ─────────────────────────────


@router.get("/catalogo", response_model=Catalogo)
def get_catalogo(tenant: int = Depends(get_tenant), sb: Client = Depends(get_supabase)) -> Catalogo:
    pode = _executar(_eh_admin, sb, tenant)
    return Catalogo(pode_editar=pode, ano=settings.ANO_DEFAULT,
                    texto_livre_disponivel=pode and InterpreteCompativel().configurado,
                    variaveis=[VariavelCatalogo(nome=v.nome, rotulo=v.rotulo, descricao=v.descricao, unidade=v.unidade)
                               for v in VARIAVEIS.values()])


@router.get("", response_model=list[Metrica])
def get_metricas(arquivadas: bool = Query(False), tenant: int = Depends(get_tenant),
                 sb: Client = Depends(get_supabase)) -> list[Metrica]:
    return _executar(metricas_service.listar, sb, tenant, arquivadas=arquivadas)


@router.get("/{metrica_id}/resultado", response_model=ResultadoMetrica)
def get_resultado(metrica_id: int, tenant: int = Depends(get_tenant),
                  sb: Client = Depends(get_supabase)) -> ResultadoMetrica:
    metrica = _executar(metricas_service.buscar, sb, tenant, metrica_id)
    return _executar(metricas_service.calcular, sb, tenant, metrica.definicao)


# ── Escrita e prévia (admin ou plataforma da federação) ──────────────────────────────


@router.post("/previa", response_model=ResultadoMetrica)
def post_previa(entrada: PreviaEntrada, tenant: int = Depends(exigir_admin),
                sb: Client = Depends(get_supabase)) -> ResultadoMetrica:
    _validar_ano(entrada.definicao.ano)
    return _executar(metricas_service.calcular, sb, tenant, entrada.definicao)


@router.post("/interpretar", response_model=PropostaMetrica)
def post_interpretar(entrada: TextoLivreEntrada, tenant: int = Depends(exigir_admin),
                     user=Depends(get_current_user), sb: Client = Depends(get_supabase),
                     interprete: InterpreteMetricas = Depends(get_interprete)) -> PropostaMetrica:
    inicio = monotonic()
    try:
        proposta = propor(sb, interprete, entrada.texto, federacao_id=tenant, ano=settings.ANO_DEFAULT,
                          federacao=buscar_federacao_do_usuario(sb, tenant),
                          calcular=lambda definicao: metricas_service.calcular(sb, tenant, definicao))
    except LimiteMetricasIA as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "60"}) from None
    except IdentidadeInativa as exc:
        raise HTTPException(403, str(exc)) from None
    except ProvedorIndisponivel as exc:
        raise HTTPException(503, str(exc)) from None
    except ValidationError:
        raise HTTPException(502, "A interpretação voltou com parâmetros inválidos. Reformule o pedido.") from None
    except (MetricaNaoEncontrada, ErroMetrica, ErroExpressao, APIError, httpx.ConnectError) as exc:
        raise _traduzir(exc) from exc
    except Exception:
        logger.exception("metricas_interpretar_falhou tenant=%s", tenant)
        raise HTTPException(503, "Não foi possível interpretar o pedido agora. Use o construtor.") from None
    # Sem o texto do pedido no log: só metadados.
    logger.info("metricas_interpretar tenant=%s usuario=%s modelo=%s status=%s duracao_ms=%.0f",
                tenant, user.id, proposta.modelo, proposta.status, (monotonic() - inicio) * 1000)
    return proposta


@router.post("", response_model=Metrica, status_code=201)
def post_metrica(entrada: MetricaEntrada, tenant: int = Depends(exigir_admin), user=Depends(get_current_user),
                 sb: Client = Depends(get_supabase)) -> Metrica:
    _validar_ano(entrada.definicao.ano)
    return _executar(metricas_service.criar, sb, tenant, str(user.id), entrada)


@router.put("/ordem", response_model=list[Metrica])
def put_ordem(entrada: OrdemEntrada, tenant: int = Depends(exigir_admin), user=Depends(get_current_user),
              sb: Client = Depends(get_supabase)) -> list[Metrica]:
    return _executar(metricas_service.reordenar, sb, tenant, str(user.id), entrada.ids)


@router.put("/{metrica_id}", response_model=Metrica)
def put_metrica(metrica_id: int, entrada: MetricaEntrada, tenant: int = Depends(exigir_admin),
                user=Depends(get_current_user), sb: Client = Depends(get_supabase)) -> Metrica:
    _validar_ano(entrada.definicao.ano)
    return _executar(metricas_service.atualizar, sb, tenant, metrica_id, str(user.id), entrada)


@router.post("/{metrica_id}/painel", response_model=Metrica)
def post_painel(metrica_id: int, entrada: PainelEntrada, tenant: int = Depends(exigir_admin),
                user=Depends(get_current_user), sb: Client = Depends(get_supabase)) -> Metrica:
    return _executar(metricas_service.definir_painel, sb, tenant, metrica_id, str(user.id), entrada.no_painel)


@router.post("/{metrica_id}/arquivar", response_model=Metrica)
def post_arquivar(metrica_id: int, tenant: int = Depends(exigir_admin), user=Depends(get_current_user),
                  sb: Client = Depends(get_supabase)) -> Metrica:
    return _executar(metricas_service.arquivar, sb, tenant, metrica_id, str(user.id))


@router.post("/{metrica_id}/restaurar", response_model=Metrica)
def post_restaurar(metrica_id: int, tenant: int = Depends(exigir_admin), user=Depends(get_current_user),
                   sb: Client = Depends(get_supabase)) -> Metrica:
    return _executar(metricas_service.restaurar, sb, tenant, metrica_id, str(user.id))


@router.delete("/{metrica_id}", status_code=204)
def delete_metrica(metrica_id: int, tenant: int = Depends(exigir_admin),
                   sb: Client = Depends(get_supabase)) -> Response:
    _executar(metricas_service.excluir, sb, tenant, metrica_id)
    return Response(status_code=204)
