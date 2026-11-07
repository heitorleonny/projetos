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


# ── Item 3b: ranking dos menores valores ───────────────────────────────────

from app.ia.adaptadores import compativel
from app.ia.assistente import perguntar
from app.services.rede_service import gerar_ranking, gerar_ranking_com_exclusoes
from tests.test_ia import provedor_falso


def banco_ranking():
    banco = Banco()
    banco.tabelas["empresa_junior"] = [
        {"id": i, "id_ej": i, "nome": f"EJ Sintética {i}", "federacao_id": 12} for i in (101, 103, 104, 105)
    ] + [{"id": 102, "id_ej": 102, "nome": "EJ Sintética MG", "federacao_id": 7}]
    banco.tabelas["monitoramento"] = [
        {"id": 1, "id_ej": 101, "ano": 2026, "mes": 10, "faturamento_acumulado": 100, "csat": 4.0, "projetos_vendidos_mes": 2},
        {"id": 3, "id_ej": 103, "ano": 2026, "mes": 10, "faturamento_acumulado": 0, "csat": None, "projetos_vendidos_mes": None},
        {"id": 4, "id_ej": 104, "ano": 2026, "mes": 10, "faturamento_acumulado": 50, "csat": 2.0, "projetos_vendidos_mes": 0},
        {"id": 5, "id_ej": 105, "ano": 2026, "mes": 10, "faturamento_acumulado": None, "csat": 5.0, "projetos_vendidos_mes": 1},
        {"id": 2, "id_ej": 102, "ano": 2026, "mes": 10, "faturamento_acumulado": 1, "csat": 1.0, "projetos_vendidos_mes": 0},
    ]
    return banco


@pytest.mark.parametrize("criterio", ["faturamento", "csat", "projetos", "colab"])
def test_ranking_padrao_continua_desc_com_ausencia_como_zero(criterio):
    banco = banco_ranking()
    padrao = gerar_ranking(banco, ano=2026, mes=10, criterio=criterio, federacao_id=12)
    explicito, sem_coleta = gerar_ranking_com_exclusoes(banco, ano=2026, mes=10, criterio=criterio, federacao_id=12, ordem="desc")
    assert padrao == explicito and sem_coleta == 0
    assert len(padrao) == 4  # ausência da métrica conta zero, como antes
    assert [i.valor for i in padrao] == sorted((i.valor for i in padrao), reverse=True)


@pytest.mark.parametrize("criterio,ids,excluidas", [
    ("faturamento", [103, 104, 101], 1),  # zero entra; acumulado nulo fica fora
    ("csat", [104, 101, 105], 1),
    ("projetos", [104, 105, 101], 1),
])
def test_ranking_asc_exclui_e_conta_sem_coleta(criterio, ids, excluidas):
    itens, sem_coleta = gerar_ranking_com_exclusoes(banco_ranking(), ano=2026, mes=10, criterio=criterio,
                                                   federacao_id=12, ordem="asc")
    assert [i.id_ej for i in itens] == ids and sem_coleta == excluidas


def test_ordem_invalida_no_service_falha():
    with pytest.raises(ValueError):
        gerar_ranking(banco_ranking(), ano=2026, criterio="faturamento", ordem="aleatoria")


def test_ferramenta_asc_informa_exclusoes_e_so_tenant():
    resposta = executar_consulta(banco_ranking(), plano(ferramenta="ranking", criterio="csat", ordem="asc"),
                                 federacao_id=12, ano_padrao=2026)
    assert resposta.status == "respondida"
    assert [l.id_ej for l in resposta.linhas] == [104, 101, 105]
    assert "Menores valores de csat" in resposta.resposta and "1 EJ sem coleta de csat" in resposta.resposta
    assert 102 not in [l.id_ej for l in resposta.linhas]


def test_ferramenta_sem_ordem_mantem_texto_e_ordem_atuais():
    resposta = executar_consulta(banco_ranking(), plano(ferramenta="ranking", criterio="faturamento"),
                                 federacao_id=12, ano_padrao=2026)
    assert resposta.resposta.startswith("Ranking por faturamento") and resposta.linhas[0].id_ej == 101


@pytest.mark.parametrize("valor", ["crescente", "ASC", 1, ""])
def test_ordem_fora_do_literal_rejeitada(valor):
    with pytest.raises(ValidationError):
        plano(ferramenta="ranking", criterio="faturamento", ordem=valor)


@pytest.mark.parametrize("ferramenta", ["fora_do_zero", "indicadores_rede", "sde", "ritmo_mensal"])
def test_asc_fora_do_ranking_recusa_sem_ler_banco(ferramenta):
    banco = Mock()
    resposta = executar_consulta(banco, plano(ferramenta=ferramenta, ordem="asc"), federacao_id=12, ano_padrao=2026)
    assert resposta.status == "fora_do_catalogo"
    banco.table.assert_not_called()


@pytest.mark.parametrize("pergunta", ["Quais são as piores EJs?", "Piores EJs do cluster 2 em setembro de 2026"])
def test_piores_sem_metrica_continua_esclarecendo(pergunta):
    banco, modelo = Mock(), provedor_falso(plano(ferramenta="ranking", criterio="faturamento", ordem="asc"))
    resposta = perguntar(banco, modelo, pergunta, federacao_id=12, usuario_id="fake", ano_padrao=2026)
    assert resposta.status == "esclarecimento" and resposta.esclarecimento.opcoes
    modelo.interpretar.assert_not_called()
    banco.table.assert_not_called()


def test_prompt_permite_menores_valores_com_exemplos(monkeypatch):
    import httpx, json
    capturado = {}

    def tratar(request):
        capturado["sistema"] = json.loads(request.content)["messages"][0]["content"]
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": plano().model_dump_json()}}]})
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(tratar), **kwargs))
    compativel.ProvedorCompativel(url="https://provedor.invalid/v1", chave="fake", modelo="teste", timeout=1).interpretar("teste", 2026)
    assert "ranking de menores" not in capturado["sistema"]
    assert "ordem=asc" in capturado["sistema"] and "menores faturamentos" in capturado["sistema"]
