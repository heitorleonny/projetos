"""Prompt do Lamps: em sincronia com o contrato e sem identidade ou dados."""
import typing

from app.ia.prompt import instrucoes_do_interprete
from app.models.ia import PlanoConsulta
from app.utils import constants


def _valores(anotacao) -> set[str]:
    """Strings de um Literal, inclusive dentro de `Literal[...] | None`."""
    if typing.get_origin(anotacao) is typing.Literal:
        return {v for v in typing.get_args(anotacao) if isinstance(v, str)}
    return set().union(*(_valores(arg) for arg in typing.get_args(anotacao)))


def test_prompt_apresenta_o_lamps_e_o_ano_padrao():
    texto = instrucoes_do_interprete(2031)
    assert texto.startswith("Você é o Lamps") and "Nexo" not in texto
    assert "Ano padrão do portal: 2031." in texto


def test_todo_valor_do_contrato_aparece_no_prompt():
    texto = instrucoes_do_interprete(2026)
    for campo in ("ferramenta", "criterio", "conceito", "faixa", "esclarecimento", "ordem"):
        valores = _valores(PlanoConsulta.model_fields[campo].annotation)
        assert valores, campo
        if campo == "ordem":
            # "desc" é aceito, mas o prompt pede null para os maiores valores (mesmo
            # pedido para o backend e o runner), mantendo o gabarito antigo comparável.
            valores.discard("desc")
        for valor in valores:
            assert valor in texto, f"{campo}={valor} não é explicado no prompt"


def test_limiares_de_meta_vem_das_constantes(monkeypatch):
    monkeypatch.setattr(constants, "LIMIAR_META_PARCIAL", 40.0)
    texto = instrucoes_do_interprete(2026)
    assert "meta_abaixo (abaixo de 40%)" in texto and "abaixo de 50%" not in texto


def test_prompt_nao_carrega_tenant_usuario_nem_dados():
    texto = instrucoes_do_interprete(2026).casefold()
    for proibido in ("federacao_id", "usuario_id", "jwt", "token", "select ", "id_ej"):
        assert proibido not in texto, proibido
