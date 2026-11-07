"""
Configurações do Portal FEJEPE.

Carrega variáveis de ambiente via pydantic-settings.
Copie `.env.example` para `.env` e preencha com suas credenciais do Supabase.
"""

import base64
import json
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente ou arquivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        hide_input_in_errors=True,
        extra="ignore",
    )

    DATABASE_DSN: str = ""
    AUTH_DATABASE_DSN: str = ""

    # ── Multi-tenant ──────────────────────────────────────────
    # Quando `True`, uma requisição cujo JWT não traz `federacao_id` é recusada
    # com 403 em vez de seguir sem filtro de tenant.
    #
    # O default é `False` porque o claim só passa a existir depois que alguém
    # ativa manualmente o Custom Access Token Hook no Dashboard do Supabase
    # (ver infra/db/init/06-usuario.sql). Ligar isto antes disso tranca todo
    # mundo para fora. Vire para `True` no mesmo dia em que o hook for ativado.
    TENANT_CLAIM_OBRIGATORIO: bool = True

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

    # ── Painel administrativo ─────────────────────────────────
    # Conexão Postgres da importação por planilha. É um papel SUJEITO a RLS
    # (`ingestao`, ver infra/db/init/10 e 11) — a carga se recusa a rodar como
    # dono das tabelas ou service role. Vazia, o upload responde 503 e o resto
    # do painel funciona normalmente.
    INGESTAO_DSN: str = ""
    # Tamanho máximo da planilha aceita no upload. A exportação nacional de
    # set/2026 (13.563 linhas) tem por volta de 3 MB.
    UPLOAD_MAX_MB: int = 20
    # Para onde o link do e-mail de convite leva. Vazio = o Site URL
    # configurado no Supabase Auth. A tela de destino é /definir-senha.
    CONVITE_REDIRECT_URL: str = ""

    # ── Defaults da plataforma ────────────────────────────────
    ANO_DEFAULT: int = 2026

    # Modelo e endpoint são configuração do servidor, nunca do browser.
    IA_MODELO: str = ""
    IA_PROVEDOR: Literal["openrouter", "openai", "compativel"] = "openrouter"
    IA_BASE_URL: str = ""
    IA_API_KEY: SecretStr = SecretStr("")
    IA_TIMEOUT_SEGUNDOS: float = Field(default=20, gt=0, le=60)
    IA_MAX_TOKENS_SAIDA: int = Field(default=1024, ge=100, le=4096)
    IA_RACIOCINIO: Literal["padrao", "desativado"] = "padrao"


settings = Settings()  # type: ignore[call-arg]
