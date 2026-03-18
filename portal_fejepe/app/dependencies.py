"""
Injeção de dependência do cliente Supabase.

Uso nos routers:
    from app.dependencies import get_supabase
    @router.get("/...")
    def endpoint(sb: Client = Depends(get_supabase)):
        ...
"""

from supabase import Client, create_client

from app.config import settings

# Cliente Supabase instanciado uma única vez (singleton)
_supabase_client: Client | None = None


def get_supabase() -> Client:
    """Retorna o cliente Supabase singleton."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )
    return _supabase_client
