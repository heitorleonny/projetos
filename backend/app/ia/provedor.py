"""Interface substituível; o provedor não recebe cliente de banco nem token."""

from dataclasses import dataclass
from typing import Protocol

from app.models.ia import PlanoConsulta


class ProvedorIndisponivel(RuntimeError):
    """Configuração ausente, timeout ou resposta inválida do modelo."""


@dataclass(frozen=True)
class Interpretacao:
    plano: PlanoConsulta
    modelo: str
    tokens_entrada: int = 0
    tokens_saida: int = 0


class Provedor(Protocol):
    def interpretar(self, pergunta: str, ano_padrao: int) -> Interpretacao: ...
