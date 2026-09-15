"""
Injeção de dependência do cliente Supabase e da autenticação.

Uso nos routers:
    from app.dependencies import get_current_user, get_supabase

    router = APIRouter(
        prefix="/api/v1/...",
        dependencies=[Depends(get_current_user)],
    )

    @router.get("/...")
    def endpoint(sb: Client = Depends(get_supabase)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from supabase import Client, create_client

from app.config import settings

# Cliente Supabase instanciado uma única vez (singleton)
_supabase_client: Client | None = None

# Esquema Bearer sem erro automático: assim controlamos a resposta 401
# (com auto_error=True o FastAPI devolveria 403 quando o header está ausente).
_bearer_scheme = HTTPBearer(auto_error=False)


def get_supabase() -> Client:
    """Retorna o cliente Supabase singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )
    return _supabase_client


def _nao_autorizado(detalhe: str) -> HTTPException:
    """Monta o erro 401 com o header `WWW-Authenticate` esperado."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalhe,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    sb: Client = Depends(get_supabase),
):
    """
    Valida o JWT do Supabase enviado em `Authorization: Bearer <token>`.

    Levanta `HTTPException(401)` quando o header está ausente, o esquema não é
    Bearer, ou o token é inválido, expirado ou malformado. Em caso de sucesso,
    retorna o usuário autenticado (objeto User do Supabase Auth).
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _nao_autorizado("Não autenticado")

    try:
        resposta = sb.auth.get_user(credentials.credentials)
    except Exception as exc:  # qualquer falha do Auth significa token não confiável
        raise _nao_autorizado("Token inválido ou expirado") from exc

    if resposta is None or getattr(resposta, "user", None) is None:
        raise _nao_autorizado("Token inválido ou expirado")

    return resposta.user
