"""Reserva compartilhada no banco imediatamente antes de chamar o provedor."""

from postgrest.exceptions import APIError


class LimitePortalIA(RuntimeError):
    """Janela operacional do portal esgotada; resposta HTTP 429."""


class IdentidadeIAInativa(RuntimeError):
    """RPC recusou vínculo atual da identidade autenticada."""


class ProvedorComLimite:
    def __init__(self, sb, provedor):
        self.sb, self.provedor = sb, provedor

    def interpretar(self, pergunta: str, ano_padrao: int):
        try:
            permitido = self.sb.rpc("reservar_consulta_ia").execute().data
        except APIError as exc:
            if str(exc.code) == "42501":
                raise IdentidadeIAInativa("Associe um usuário ativo à federação para usar o Lamps.") from None
            raise
        if permitido is False:
            raise LimitePortalIA("O Lamps atingiu o limite de consultas do usuário ou da federação neste minuto. Tente novamente em até um minuto.")
        if permitido is not True:
            # Falha fechada: nunca faz chamada paga com reserva não confirmada.
            raise RuntimeError("Reserva de consulta não confirmada.")
        return self.provedor.interpretar(pergunta, ano_padrao)
