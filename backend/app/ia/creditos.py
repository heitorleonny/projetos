"""Leitura da cota e gravação atômica de dashboards com consumo de créditos."""

from postgrest.exceptions import APIError


class IdentidadeCreditosIAInvalida(RuntimeError):
    """RPC recusou a identidade/tenant da sessão autenticada."""


class LimiteCreditosIA(RuntimeError):
    """Cota mensal da federação esgotada."""


def consultar_creditos_ia(sb) -> dict:
    """Retorna cota, consumo e saldo derivados exclusivamente do JWT no banco."""
    try:
        resposta = sb.rpc("consultar_creditos_dashboard_ia").execute()
    except APIError as exc:
        if str(getattr(exc, "code", "")) == "42501":
            raise IdentidadeCreditosIAInvalida(
                "Usuário sem vínculo ativo com a federação autenticada."
            ) from None
        raise

    dados = getattr(resposta, "data", None)
    if isinstance(dados, list) and dados:
        linha = dados[0]
    else:
        linha = dados
    if not isinstance(linha, dict):
        raise RuntimeError("O banco não retornou a cota de dashboards.")
    return linha


def persistir_dashboard_com_credito(sb, dados: dict) -> dict:
    """Persiste um dashboard e debita uma unidade na mesma transação Postgres."""
    try:
        resposta = sb.rpc("persistir_dashboard_evento_ia", dados).execute()
    except APIError as exc:
        codigo = str(getattr(exc, "code", ""))
        if codigo == "54000":
            raise LimiteCreditosIA(
                "A federação esgotou os créditos mensais para criar dashboards."
            ) from None
        if codigo == "42501":
            raise IdentidadeCreditosIAInvalida(
                "Usuário sem vínculo ativo ou papel de gestor na federação autenticada."
            ) from None
        raise
    resultado = getattr(resposta, "data", None)
    linha = resultado[0] if isinstance(resultado, list) and resultado else resultado
    if not isinstance(linha, dict):
        raise RuntimeError("O banco não confirmou a persistência do dashboard.")
    return linha
