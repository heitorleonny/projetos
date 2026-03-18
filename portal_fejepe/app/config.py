"""
Configurações do Portal FEJEPE.

Carrega variáveis de ambiente via pydantic-settings.
Copie `.env.example` para `.env` e preencha com suas credenciais do Supabase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente ou arquivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        """Retorna a lista de origens CORS como lista de strings."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── Defaults da plataforma ────────────────────────────────
    ANO_DEFAULT: int = 2026


settings = Settings()  # type: ignore[call-arg]
