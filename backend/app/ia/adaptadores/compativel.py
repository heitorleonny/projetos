"""Adaptador HTTP para endpoints com Chat Completions e JSON Schema estrito."""

import httpx
from pydantic import ValidationError

from app.ia.provedor import Interpretacao, ProvedorIndisponivel
from app.ia.prompt import instrucoes_do_interprete
from app.models.ia import PlanoConsulta


class ProvedorCompativel:
    def __init__(self, *, url: str, chave: str, modelo: str, timeout: float,
                 max_tokens: int = 1024, exigir_parametros: bool = False,
                 desativar_raciocinio: bool = False):
        self.url, self.chave, self.modelo, self.timeout = url, chave, modelo, timeout
        self.max_tokens, self.exigir_parametros = max_tokens, exigir_parametros
        self.desativar_raciocinio = desativar_raciocinio

    def interpretar(self, pergunta: str, ano_padrao: int) -> Interpretacao:
        if not self.url or not self.modelo or not self.chave:
            raise ProvedorIndisponivel("Assistente ainda não configurado no servidor.")
        instrucoes = instrucoes_do_interprete(ano_padrao)
        esquema = PlanoConsulta.model_json_schema()
        # Structured Outputs estrito exige todas as propriedades, inclusive anuláveis.
        esquema["required"] = list(esquema["properties"])
        try:
            with httpx.Client(timeout=self.timeout) as cliente:
                resposta = cliente.post(
                    self.url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {self.chave}"},
                    json={
                        "model": self.modelo,
                        "messages": [
                            {"role": "system", "content": instrucoes},
                            {"role": "user", "content": pergunta},
                        ],
                        # O gateway usa o nome canônico que os provedores anunciam.
                        "max_tokens" if self.exigir_parametros else "max_completion_tokens": self.max_tokens,
                        **({"provider": {"require_parameters": True}} if self.exigir_parametros else {}),
                        **({"reasoning": {"enabled": False}} if self.exigir_parametros and self.desativar_raciocinio else {}),
                        "response_format": {"type": "json_schema", "json_schema": {
                            "name": "consulta_rede", "strict": True,
                            "schema": esquema,
                        }},
                    },
                )
                if resposta.status_code == 429:
                    raise ProvedorIndisponivel(
                        "O provedor de IA atingiu o limite de uso. Aguarde a renovação "
                        "do limite ou peça ao administrador para revisar o modelo configurado."
                    )
                resposta.raise_for_status()
                dados = resposta.json()
            escolha = dados["choices"][0]
            mensagem = escolha["message"]
            if escolha["finish_reason"] != "stop" or mensagem.get("refusal"):
                raise ProvedorIndisponivel("O modelo não conseguiu interpretar a pergunta.")
            plano = PlanoConsulta.model_validate_json(mensagem["content"])
            uso = dados.get("usage") or {}
            return Interpretacao(plano, self.modelo, uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0))
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, ValidationError) as exc:
            # O corpo do erro do provedor pode conter a pergunta: não o exponha.
            raise ProvedorIndisponivel("Não foi possível interpretar a pergunta agora. Tente novamente.") from exc
