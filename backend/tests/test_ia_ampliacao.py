"""Ampliação do Nexo (nov/2026): série, ranking ascendente, perfil de EJ e metas."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.ia.ferramentas import executar_consulta
from app.models.ia import PerguntaRede, PontoSerie, RespostaRede
from tests.test_ia import Banco, plano


# ── Item 2: série opcional, preenchida só pelo backend ─────────────────────

def test_serie_e_opcional_e_ausente_nas_consultas_existentes():
    assert RespostaRede(status="respondida", resposta="ok").serie is None
    for ferramenta in ("fora_do_zero", "ranking", "indicadores_rede", "sde", "ritmo_mensal"):
        assert executar_consulta(Banco(), plano(ferramenta=ferramenta), federacao_id=12, ano_padrao=2026).serie is None


@pytest.mark.parametrize("ponto", [dict(mes=0, valor=1), dict(mes=13, valor=1), dict(mes=1)])
def test_ponto_da_serie_e_validado(ponto):
    with pytest.raises(ValidationError):
        PontoSerie.model_validate(ponto)


def test_cliente_nao_envia_serie_nem_resultado():
    with pytest.raises(ValidationError):
        PerguntaRede.model_validate({"pergunta": "e em setembro?", "serie": [{"mes": 1, "valor": 1}]})
    with pytest.raises(ValidationError):
        PerguntaRede.model_validate({"pergunta": "e em setembro?", "contexto": plano().model_dump() | {"serie": []}})
