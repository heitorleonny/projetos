"""Perguntas aos dados com a identidade do usuário e tenant obrigatório."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from app.database import Client

from app.config import settings
from app.services.federacao_service import buscar_federacao_do_usuario
from app.dependencies import get_current_user, get_federacao_id, get_supabase, require_papel
from app.ia.fabrica import criar_provedor
from app.ia.assistente import perguntar
from app.ia.limites import ProvedorComLimite, LimitePortalIA, IdentidadeIAInativa
from app.ia.provedor import Provedor, ProvedorIndisponivel
from app.models.ia import PerguntaRede, RespostaRede

router = APIRouter(prefix="/api/v1/ia", tags=["Pergunte à Rede"],
                   dependencies=[Depends(require_papel("membro"))])


def get_tenant_ia(federacao_id: int | None = Depends(get_federacao_id)) -> int:
    # Aqui não há compatibilidade sem claim: falha antes de chamar o modelo.
    if federacao_id is None:
        raise HTTPException(403, "Associe o usuário a uma federação para consultar os dados.")
    return federacao_id


def get_provedor() -> Provedor:
    return criar_provedor()


@router.post("/perguntar", response_model=RespostaRede)
def post_perguntar(entrada: PerguntaRede, tenant: int = Depends(get_tenant_ia),
                   user=Depends(get_current_user), sb: Client = Depends(get_supabase),
                   provedor: Provedor = Depends(get_provedor)) -> RespostaRede:
    try:
        return perguntar(sb, ProvedorComLimite(sb, provedor), entrada.pergunta, federacao_id=tenant,
                         usuario_id=str(user.id), ano_padrao=settings.ANO_DEFAULT, contexto=entrada.contexto,
                         federacao=buscar_federacao_do_usuario(sb, tenant))
    except LimitePortalIA as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "60"}) from None
    except IdentidadeIAInativa as exc:
        raise HTTPException(403, str(exc)) from None
    except ProvedorIndisponivel as exc:
        raise HTTPException(503, str(exc)) from None
    except ValidationError:
        raise HTTPException(502, "A interpretação retornou parâmetros inválidos. Reformule a pergunta.") from None
    except Exception:
        raise HTTPException(503, "Não foi possível consultar os dados agora. Tente novamente.") from None
