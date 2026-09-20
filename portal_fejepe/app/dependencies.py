"""
Injeção de dependência do cliente Supabase, da autenticação e do tenant.

Uso nos routers:
    from app.dependencies import get_current_user, get_federacao_id, get_supabase, require_papel

    router = APIRouter(
        prefix="/api/v1/...",
        dependencies=[Depends(get_current_user), Depends(require_papel("membro"))],
    )

    @router.get("/...")
    def endpoint(
        sb: Client = Depends(get_supabase),
        federacao_id: int | None = Depends(get_federacao_id),
    ):
        ...

As três camadas, na ordem em que agem:

    1. `get_current_user`  — o token é válido?      (401 se não)
    2. `get_federacao_id`  — de que federação ele é? (filtro de tenant)
    3. `require_papel`     — pode fazer isto?        (403 se não)

A ordem importa e não é negociável: papel NUNCA amplia tenant. Um admin da
federação 12 continua sem alcançar dado da federação 4 — a checagem de papel
acontece depois que o tenant já delimitou o conjunto, nunca no lugar dela.
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from supabase import Client, create_client

from app.config import settings

# Esquema Bearer sem erro automático: assim controlamos a resposta 401
# (com auto_error=True o FastAPI devolveria 403 quando o header está ausente).
_bearer_scheme = HTTPBearer(auto_error=False)

# ── Papéis ───────────────────────────────────────────────────
#
# Dois papéis, e só dois: `admin` e `membro`. Os nomes antigos
# (admin_federacao, gestor, visualizador) saíram de circulação — não
# reintroduzir em código novo.
#
# A hierarquia é um número só porque a regra é linear: quem é admin pode tudo
# que um membro pode.
HIERARQUIA_PAPEIS: dict[str, int] = {"membro": 1, "admin": 2}

# Papel assumido quando o JWT não traz claim de papel.
#
# Por que `membro` e não recusar: o claim só existe depois que o Custom Access
# Token Hook for ativado manualmente no Dashboard do Supabase — até lá, NENHUM
# token tem papel. Assumir o papel mais fraco preserva exatamente o
# comportamento de hoje (todo autenticado lê) e nega o que ainda não existe
# (escrita, que vai exigir `admin`). O erro, se houver, é para o lado restritivo.
PAPEL_PADRAO = "membro"


def get_supabase(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> Client:
    """
    Cria um cliente Supabase POR REQUISIÇÃO, com a chave anônima e o token de
    quem fez a chamada.

    Era um singleton global com uma chave só. Isso não sobrevive à
    multi-tenancy por dois motivos:

      * um cliente compartilhado entre requisições carregaria o token de quem
        chegou antes — e, com RLS ligada, isso é vazamento entre federações;
      * sem `postgrest.auth(token)`, o PostgREST não recebe claim nenhum e
        `auth.jwt()` dentro das políticas devolve vazio: a RLS ou bloqueia
        tudo, ou (se a chave for a de serviço) não filtra nada.

    Requisição sem token recebe um cliente sem sessão — as políticas não casam
    com nada e ele não lê linha alguma. Quem devolve o 401 é `get_current_user`.
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

    if credentials is not None and credentials.scheme.lower() == "bearer" and credentials.credentials:
        # É isto que faz o JWT do usuário chegar ao PostgREST, e portanto às
        # políticas de RLS. Sem esta linha, o resto da multi-tenancy é enfeite.
        client.postgrest.auth(credentials.credentials)

    return client


def get_supabase_admin() -> Client:
    """
    Cliente com a SERVICE KEY — ignora Row Level Security.

    NÃO É DEPENDÊNCIA DE ROTA, e não deve virar uma. Existe para script
    administrativo rodando fora do ciclo de requisição (carga de dados,
    backfill, migração). Um único uso disto em `app/routers/` ou
    `app/services/` desliga o isolamento entre federações da aplicação inteira.

    Coberto por teste: tests/test_papeis.py garante que nem a service key nem
    esta função aparecem no caminho de request.
    """
    if not settings.SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "SUPABASE_SERVICE_KEY não configurada. Ela só é necessária para "
            "scripts administrativos — a API não usa esta chave."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


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


def _app_metadata(user) -> dict:
    """
    Claims que o Custom Access Token Hook copiou de `usuario` para o token.

    É sempre leitura. A fonte da verdade é a tabela `usuario` no banco; o token
    é uma fotografia dela no momento do login.
    """
    return getattr(user, "app_metadata", None) or {}


def get_federacao_id(user=Depends(get_current_user)) -> int | None:
    """
    Tenant de quem fez a requisição, lido do claim `federacao_id`.

    Devolve `None` quando o token não traz o claim — que é o estado de todos os
    tokens até o hook ser ativado no Supabase. Nesse caso os services não
    aplicam o filtro por federação e o isolamento fica inteiramente por conta da
    RLS, que é onde ele é obrigatório de qualquer forma.

    Com `settings.TENANT_CLAIM_OBRIGATORIO = True`, a mesma situação vira 403.
    """
    bruto = _app_metadata(user).get("federacao_id")

    if bruto is None or bruto == "":
        if settings.TENANT_CLAIM_OBRIGATORIO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário sem federação associada.",
            )
        return None

    try:
        return int(bruto)
    except (TypeError, ValueError):
        # Claim presente mas ilegível é pior que ausente: alguém montou um token
        # torto. Recusa sempre, independentemente da flag.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Federação do usuário inválida no token.",
        ) from None


def get_papel(user=Depends(get_current_user)) -> str:
    """Papel de quem fez a requisição, ou `PAPEL_PADRAO` quando o claim falta."""
    papel = _app_metadata(user).get("papel")
    # Valor desconhecido (um papel antigo, um erro de digitação) cai no papel
    # mais fraco — nunca no mais forte.
    if papel not in HIERARQUIA_PAPEIS:
        return PAPEL_PADRAO
    return papel


def require_papel(minimo: str) -> Callable:
    """
    Dependência que exige pelo menos o papel `minimo` ('membro' ou 'admin').

    A FONTE DA VERDADE DO PAPEL É `usuario.papel`, no banco. O claim que esta
    função lê (`app_metadata.papel`) é só o que o Custom Access Token Hook
    copiou de lá no último login — uma fotografia, que fica velha se o papel
    mudar no meio da sessão.

    O sentido é sempre banco → JWT. Não existe, e não deve passar a existir,
    código que escreva `usuario.papel` a partir do que veio no token: seria
    deixar o portador do token editar a própria permissão.

    Esta dependência NÃO olha tenant e não substitui o filtro por federação.
    Papel diz o que se pode fazer dentro da própria federação; nunca em outra.
    """
    if minimo not in HIERARQUIA_PAPEIS:
        raise ValueError(f"Papel desconhecido: {minimo!r}. Use um de {sorted(HIERARQUIA_PAPEIS)}.")

    def _verificar_papel(user=Depends(get_current_user)):
        papel = get_papel(user)
        if HIERARQUIA_PAPEIS[papel] < HIERARQUIA_PAPEIS[minimo]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requer papel '{minimo}'.",
            )
        return user

    return _verificar_papel
