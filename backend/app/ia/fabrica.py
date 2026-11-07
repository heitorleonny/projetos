"""Seleção de provedor e modelo sem alterar as ferramentas de leitura."""

from app.config import settings
from app.ia.adaptadores.compativel import ProvedorCompativel
from app.ia.provedor import Provedor


def criar_provedor() -> Provedor:
    endpoints = {"openrouter": "https://openrouter.ai/api/v1", "openai": "https://api.openai.com/v1"}
    return ProvedorCompativel(
        url=settings.IA_BASE_URL or endpoints.get(settings.IA_PROVEDOR, ""),
        chave=settings.IA_API_KEY.get_secret_value(), modelo=settings.IA_MODELO,
        timeout=settings.IA_TIMEOUT_SEGUNDOS, max_tokens=settings.IA_MAX_TOKENS_SAIDA,
        exigir_parametros=settings.IA_PROVEDOR == "openrouter",
        desativar_raciocinio=settings.IA_RACIOCINIO == "desativado",
    )
