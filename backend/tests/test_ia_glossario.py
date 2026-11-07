"""Glossário do Nexo: texto curado, sem banco, sem modelo e com limiares das constantes."""

import ast
import re
import typing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dependencies import get_supabase
from app.ia import glossario
from app.ia.assistente import perguntar
from app.ia.conversa import conceito_local
from app.ia.ferramentas import executar_consulta
from app.main import criar_app
from app.models.ia import Conceito, PlanoConsulta
from app.routers.ia import get_provedor
from app.utils import constants
from tests.test_ia import Banco, plano, provedor_falso

CONCEITOS = typing.get_args(Conceito)
BACKEND = Path(__file__).resolve().parents[1]


def test_catalogo_de_conceitos_tem_verbete_para_cada_valor():
    assert set(CONCEITOS) == set(glossario.VERBETES)
    assert len(CONCEITOS) == 12


@pytest.mark.parametrize("conceito", CONCEITOS)
def test_verbete_curto_com_ligacao_ao_dado(conceito):
    texto = glossario.texto_do_conceito(conceito)
    frases = [f for f in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", texto) if f.strip()]
    assert 3 <= len(frases) <= 6, (conceito, len(frases))
    resposta = glossario.explicar(conceito)
    assert resposta.status == "respondida" and resposta.fonte == "glossario"
    assert not resposta.linhas and 1 <= len(resposta.sugestoes) <= 2


@pytest.mark.parametrize("pergunta,conceito", [
    ("O que é SDE?", "sde"),
    ("como é calculado o cluster?", "cluster"),
    ("O que significa fora do zero?", "fora_do_zero"),
    ("O que é o tracking de cluster?", "tracking_cluster"),
    ("Como se calcula o ritmo necessário?", "ritmo_necessario"),
    ("o que é saldo de evolução da rede", "sde"),
    ("Explique o CSAT", "csat"),
    ("O que é % da meta?", "meta_atingida"),
])
def test_guarda_local_reconhece_definicoes(pergunta, conceito):
    assert conceito_local(pergunta) == conceito


@pytest.mark.parametrize("pergunta", [
    "Qual o SDE da rede?", "Como está o ritmo mensal em setembro?", "Quais EJs estão fora do zero?",
    "O que é o Nexo?", "Como funciona o cluster da minha EJ?", "O que é SDE e qual o valor em setembro?",
])
def test_guarda_local_deixa_pedidos_de_dado_para_o_interprete(pergunta):
    assert conceito_local(pergunta) is None


def test_pergunta_simples_nao_chama_modelo_nem_banco():
    banco, modelo = Mock(), provedor_falso(plano())
    contexto = plano(cluster=2, mes=9)
    resposta = perguntar(banco, modelo, "O que é SDE?", contexto=contexto,
                         federacao_id=12, usuario_id="fake", ano_padrao=2026)
    assert resposta.status == "respondida" and resposta.fonte == "glossario"
    assert "Saldo de Evolução da Rede" in resposta.resposta
    assert resposta.sugestoes == ["Qual o SDE da rede do cluster 2 em 09/2026?"]
    assert resposta.contexto == contexto  # continuação segue a consulta anterior
    modelo.interpretar.assert_not_called()
    banco.table.assert_not_called()
    banco.rpc.assert_not_called()


def test_rota_glossario_nao_consome_limitador():
    app = criar_app()
    banco = Banco()
    banco.auth = SimpleNamespace(get_user=lambda token: SimpleNamespace(user=SimpleNamespace(id="fake", app_metadata={"federacao_id": 12})))
    banco.rpc = Mock()
    modelo = provedor_falso(plano())
    app.dependency_overrides[get_supabase] = lambda: banco
    app.dependency_overrides[get_provedor] = lambda: modelo
    with TestClient(app) as client:
        resposta = client.post("/api/v1/ia/perguntar", headers={"Authorization": "Bearer fake"},
                               json={"pergunta": "Como é calculado o cluster?"})
    assert resposta.status_code == 200 and resposta.json()["fonte"] == "glossario"
    banco.rpc.assert_not_called()
    modelo.interpretar.assert_not_called()


def test_explicar_do_modelo_nao_abre_consulta_ao_banco():
    banco = Mock()
    resposta = executar_consulta(banco, plano(ferramenta="explicar", ano=None, mes=None, conceito="ritmo"),
                                 federacao_id=12, ano_padrao=2026)
    assert resposta.status == "respondida" and resposta.fonte == "glossario" and not resposta.linhas
    banco.table.assert_not_called()
    banco.rpc.assert_not_called()


def test_explicar_pelo_fluxo_preserva_contexto_e_nao_le_banco():
    banco = Mock()
    contexto = plano(cluster=3)
    resposta = perguntar(banco, provedor_falso(plano(ferramenta="explicar", ano=None, mes=None, conceito="cluster")),
                         "Me conta sobre a forma de classificar EJs", contexto=contexto,
                         federacao_id=12, usuario_id="fake", ano_padrao=2026)
    assert resposta.fonte == "glossario" and resposta.contexto == contexto
    banco.table.assert_not_called()


@pytest.mark.parametrize("alteracoes", [
    dict(conceito=None),
    dict(conceito="sde", busca="Sintética"),
    dict(conceito="sde", cluster=2),
    dict(conceito="csat", criterio="csat"),
])
def test_explicar_sem_conceito_ou_com_filtro_de_dado_recusa(alteracoes):
    banco = Mock()
    resposta = executar_consulta(banco, plano(ferramenta="explicar", ano=None, mes=None, **alteracoes),
                                 federacao_id=12, ano_padrao=2026)
    assert resposta.status == "fora_do_catalogo" and "Posso explicar" in resposta.resposta
    banco.table.assert_not_called()


@pytest.mark.parametrize("ferramenta", ["fora_do_zero", "ranking", "sde", "indicadores_rede"])
def test_conceito_em_outra_ferramenta_recusa_sem_ler_banco(ferramenta):
    banco = Mock()
    resposta = executar_consulta(banco, plano(ferramenta=ferramenta, conceito="sde"), federacao_id=12, ano_padrao=2026)
    assert resposta.status == "fora_do_catalogo"
    banco.table.assert_not_called()


@pytest.mark.parametrize("valor", ["indice_de_risco", "SDE", "", 1])
def test_conceito_fora_do_literal_e_rejeitado(valor):
    with pytest.raises(ValidationError):
        plano(ferramenta="explicar", conceito=valor)


def test_plano_explicar_rejeita_campos_extras():
    with pytest.raises(ValidationError):
        PlanoConsulta.model_validate(plano(ferramenta="explicar", conceito="sde").model_dump() | {"texto": "inventado"})


def test_conceito_desconhecido_pelo_fluxo_nao_vira_texto_do_modelo():
    resposta = perguntar(Mock(), provedor_falso(plano(ferramenta="recusar", ano=None, mes=None)),
                         "O que é índice de felicidade da EJ?", federacao_id=12, usuario_id="fake", ano_padrao=2026)
    assert resposta.status == "fora_do_catalogo" and resposta.fonte is None


def _numeros(texto: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d{3})*(?:,\d+)?", texto))


def test_limiares_do_texto_batem_com_constants():
    permitidos = {"1"}  # o "1 +" das fórmulas de pontos
    permitidos |= {f"{int(maximo):,}".replace(",", ".") for _min, maximo, _c in constants.CLUSTER_RANGES[:-1]}
    permitidos |= {str(cluster) for *_faixa, cluster in constants.CLUSTER_RANGES}
    permitidos |= {f"{peso:.2f}".replace(".", ",") for peso in constants.SDE_WEIGHTS}
    permitidos |= {str(constants.MESES_ANO), str(constants.FATOR_ESCALA_PONTOS),
                   f"{constants.LIMIAR_META_ATINGIDA:.0f}", f"{constants.LIMIAR_META_PARCIAL:.0f}"}
    for conceito in CONCEITOS:
        sobra = _numeros(glossario.texto_do_conceito(conceito)) - permitidos
        assert not sobra, (conceito, sobra)
    cluster = glossario.texto_do_conceito("cluster")
    for _min, maximo, _c in constants.CLUSTER_RANGES[:-1]:
        assert f"{int(maximo):,}".replace(",", ".") in cluster
    sde = glossario.texto_do_conceito("sde")
    for indice, peso in enumerate(constants.SDE_WEIGHTS, 1):
        assert f"C{indice} {peso:.2f}".replace(".", ",") in sde


def test_texto_e_montado_a_partir_das_constantes(monkeypatch):
    monkeypatch.setattr(constants, "SDE_WEIGHTS", [0.5, 0.2, 0.1, 0.1, 0.1])
    monkeypatch.setattr(constants, "MESES_ANO", 13)
    monkeypatch.setattr(constants, "LIMIAR_META_PARCIAL", 40.0)
    assert "C1 0,50" in glossario.texto_do_conceito("sde")
    assert "dividida por 13" in glossario.texto_do_conceito("ritmo")
    assert "de 40% a menos de 100%" in glossario.texto_do_conceito("meta_atingida")


def test_glossario_nao_depende_de_tenant_nem_de_banco():
    arvore = ast.parse((BACKEND / "app/ia/glossario.py").read_text())
    importados = {n.module for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom)}
    importados |= {a.name for n in ast.walk(arvore) if isinstance(n, ast.Import) for a in n.names}
    assert importados <= {"collections.abc", "app.models.ia", "app.utils"}
    a = perguntar(Mock(), provedor_falso(plano()), "O que é ritmo?", federacao_id=12, usuario_id="a", ano_padrao=2026)
    b = perguntar(Mock(), provedor_falso(plano()), "O que é ritmo?", federacao_id=7, usuario_id="b", ano_padrao=2026)
    assert a == b


def test_nome_errado_do_sde_nao_aparece_no_backend():
    # O frontend tem verificação equivalente em frontend/scripts/test-nexo.mjs.
    arquivos = list((BACKEND / "app").rglob("*.py"))
    assert arquivos
    for arquivo in arquivos:
        assert "Desenvolvimento Estratégico" not in arquivo.read_text(), arquivo
