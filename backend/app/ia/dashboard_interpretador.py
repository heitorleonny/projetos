"""Interpreta pedidos de visualização sem consultar dados nem receber resultados."""

import httpx
from pydantic import ValidationError

from app.config import settings
from app.ia.provedor import ProvedorIndisponivel
from app.models.dashboard_ia import InterpretacaoDashboard, PlanoDashboard


class PedidoDashboardNaoSuportado(ValueError):
    """Pedido não pode ser resolvido sem inventar métrica ou escopo."""


def interpretar_dashboard(pedido: str, ano_padrao: int) -> tuple[PlanoDashboard, str]:
    if not settings.IA_BASE_URL and settings.IA_PROVEDOR == "compativel":
        url = ""
    else:
        url = settings.IA_BASE_URL or {
            "openrouter": "https://openrouter.ai/api/v1",
            "openai": "https://api.openai.com/v1",
        }.get(settings.IA_PROVEDOR, "")
    chave = settings.IA_API_KEY.get_secret_value()
    modelo = settings.IA_MODELO
    if not url or not chave or not modelo:
        raise ProvedorIndisponivel("A montagem de dashboards ainda não está configurada.")

    esquema = InterpretacaoDashboard.model_json_schema()
    esquema["required"] = list(esquema["properties"])
    for definicao in esquema.get("$defs", {}).values():
        if isinstance(definicao.get("properties"), dict):
            definicao["required"] = list(definicao["properties"])
    instrucoes = (
        "Converta o pedido para um plano de dashboard do Portal das Federações. "
        "Se faltar métrica ou período essencial, status=esclarecer e plano=null. "
        "Se pedirem métrica/corte fora do catálogo, status=fora_do_catalogo e plano=null. "
        "Pedido suportado tem status=pronto, plano preenchido e mensagem=null. "
        "Você escolhe apenas visualização, métrica existente, agregação, dimensão e período. "
        "Nunca calcule números, gere SQL, invente métricas ou peça dados individuais. "
        "Catálogo de métricas: faturamento_mes (R$ realizado em cada mês), "
        "projetos_vendidos_mes (contagem já registrada por EJ/mês), csat (nota registrada). "
        "Agregações: soma, media. "
        "Dimensões: ej para ranking, mes para série mensal agregada. Visualizações: "
        "ranking, barras, linha, cartao. Use ranking somente com dimensão ej. "
        "CSAT usa media; faturamento_mes e projetos_vendidos_mes normalmente usam soma. "
        "Período sempre dentro de um único ano, meses inclusivos 1–12. "
        "Para 'setembro e outubro', use mes_inicio=9 e mes_fim=10; o backend soma "
        "os valores mensais registrados dentro da janela. Se mês não for indicado, "
        f"use o ano {ano_padrao} e o intervalo 1–12. Limite padrão 10, máximo 50. "
        "Título curto em português. Responda estritamente no schema."
    )
    try:
        with httpx.Client(timeout=settings.IA_TIMEOUT_SEGUNDOS) as cliente:
            resposta = cliente.post(
                url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {chave}"},
                json={
                    "model": modelo,
                    "messages": [
                        {"role": "system", "content": instrucoes},
                        {"role": "user", "content": pedido},
                    ],
                    "max_tokens": 350,
                    **({"provider": {"require_parameters": True}} if settings.IA_PROVEDOR == "openrouter" else {}),
                    **({"reasoning": {"enabled": False}} if settings.IA_PROVEDOR == "openrouter" and settings.IA_RACIOCINIO == "desativado" else {}),
                    "response_format": {"type": "json_schema", "json_schema": {
                        "name": "interpretacao_dashboard", "strict": True, "schema": esquema,
                    }},
                },
            )
            if resposta.status_code == 429:
                raise ProvedorIndisponivel("O provedor de IA atingiu o limite de uso. Tente novamente mais tarde.")
            resposta.raise_for_status()
            dados = resposta.json()
        escolha = dados["choices"][0]
        mensagem = escolha["message"]
        if escolha["finish_reason"] != "stop" or mensagem.get("refusal"):
            raise ProvedorIndisponivel("A IA não conseguiu montar esse dashboard.")
        resultado = InterpretacaoDashboard.model_validate_json(mensagem["content"])
        if resultado.status != "pronto" or resultado.plano is None:
            raise PedidoDashboardNaoSuportado(resultado.mensagem or "Reformule com uma métrica do catálogo.")
        plano = PlanoDashboard.model_validate(resultado.plano.model_dump())
        _validar_combinacao(plano)
        return plano, str(dados.get("model") or modelo)
    except (ProvedorIndisponivel, PedidoDashboardNaoSuportado):
        raise
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, ValidationError) as exc:
        raise ProvedorIndisponivel("Não foi possível interpretar o pedido agora. Tente reformular.") from exc


def _validar_combinacao(plano: PlanoDashboard) -> None:
    if plano.metrica == "csat" and plano.agregacao != "media":
        raise ProvedorIndisponivel("O CSAT só pode ser agregado pela média.")
    if plano.visualizacao == "ranking" and plano.dimensao != "ej":
        raise ProvedorIndisponivel("Ranking exige a dimensão de EJs.")
    if plano.visualizacao == "linha" and plano.dimensao != "mes":
        raise ProvedorIndisponivel("Gráfico de linha exige a dimensão por mês.")
