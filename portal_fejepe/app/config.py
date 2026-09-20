"""
Configurações do Portal FEJEPE.

Carrega variáveis de ambiente via pydantic-settings.
Copie `.env.example` para `.env` e preencha com suas credenciais do Supabase.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente ou arquivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str

    # Duas chaves, com poderes diferentes — a separação é o ponto:
    #
    #   ANON     respeita Row Level Security. É a chave do caminho de request:
    #            o cliente é criado com ela e recebe o JWT do usuário, então o
    #            PostgREST enxerga os claims e as políticas filtram por tenant.
    #
    #   SERVICE  IGNORA Row Level Security (é `service_role`, com BYPASSRLS).
    #            Só para script administrativo rodando fora de requisição:
    #            carga, migração, backfill. Se esta chave entrar em
    #            app/routers/ ou app/services/, todas as políticas de
    #            infra/db/init/07-rls-policies.sql viram decoração.
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Nome antigo, antes de existirem duas chaves. Mantido só para que um `.env`
    # já existente continue subindo: quando `SUPABASE_ANON_KEY` está vazia, o
    # valor daqui é usado no lugar dela. Migre o `.env` e apague esta variável.
    SUPABASE_KEY: str = ""

    @model_validator(mode="after")
    def _resolver_chave_do_caminho_de_request(self):
        """
        Garante que existe uma chave anônima, aceitando o nome antigo.

        Falha alto quando não há nenhuma: subir a API sem chave produziria um
        erro obscuro na primeira consulta, não no start.
        """
        if not self.SUPABASE_ANON_KEY and self.SUPABASE_KEY:
            self.SUPABASE_ANON_KEY = self.SUPABASE_KEY
        if not self.SUPABASE_ANON_KEY:
            raise ValueError(
                "Defina SUPABASE_ANON_KEY (a chave anônima do projeto Supabase). "
                "SUPABASE_KEY ainda é aceita como nome legado."
            )
        return self

    # ── Multi-tenant ──────────────────────────────────────────
    # Quando `True`, uma requisição cujo JWT não traz `federacao_id` é recusada
    # com 403 em vez de seguir sem filtro de tenant.
    #
    # O default é `False` porque o claim só passa a existir depois que alguém
    # ativa manualmente o Custom Access Token Hook no Dashboard do Supabase
    # (ver infra/db/init/06-usuario.sql). Ligar isto antes disso tranca todo
    # mundo para fora. Vire para `True` no mesmo dia em que o hook for ativado.
    TENANT_CLAIM_OBRIGATORIO: bool = False

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        """Retorna a lista de origens CORS como lista de strings."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── Documentação interativa ───────────────────────────────
    # Controla /docs, /redoc e /openapi.json. Ligada por padrão para não
    # atrapalhar o desenvolvimento; desligue em produção, onde o schema da
    # API não precisa ser público.
    DOCS_ENABLED: bool = True

    # ── Defaults da plataforma ────────────────────────────────
    ANO_DEFAULT: int = 2026


settings = Settings()  # type: ignore[call-arg]
