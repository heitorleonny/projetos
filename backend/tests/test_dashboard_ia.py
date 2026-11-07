"""Testes determinísticos para o catálogo e a agregação dos dashboards."""

import pytest
from pydantic import ValidationError

from app.models.dashboard_ia import PlanoDashboard
from app.services import dashboard_ia_service


def _plano(**alteracoes) -> PlanoDashboard:
    valores = {
        "titulo": "Faturamento no bimestre",
        "metrica": "faturamento_mes",
        "agregacao": "soma",
        "dimensao": "ej",
        "visualizacao": "ranking",
        "ano": 2026,
        "mes_inicio": 9,
        "mes_fim": 10,
        "limite": 10,
    }
    valores.update(alteracoes)
    return PlanoDashboard(**valores)


def test_agrega_faturamento_mensal_existente_no_recorte(monkeypatch):
    def ler_todas(_sb, tabela, _colunas, _filtro):
        if tabela == "empresa_junior":
            return [
                {"id_ej": 1, "nome": "EJ Aurora"},
                {"id_ej": 2, "nome": "EJ Boreal"},
            ]
        assert tabela == "monitoramento"
        return [
            {"id_ej": 1, "ano": 2026, "mes": 9, "faturamento_mes": 1200},
            {"id_ej": 1, "ano": 2026, "mes": 10, "faturamento_mes": 800},
            {"id_ej": 2, "ano": 2026, "mes": 9, "faturamento_mes": 900},
            {"id_ej": 2, "ano": 2026, "mes": 10, "faturamento_mes": 0},
            # Fora da janela: o serviço consulta setembro e outubro apenas.
        ]

    monkeypatch.setattr(dashboard_ia_service, "ler_todas", ler_todas)
    pontos = dashboard_ia_service.calcular_pontos(object(), _plano(), federacao_id=7)

    assert [(p.rotulo, p.valor) for p in pontos] == [
        ("EJ Aurora", 2000.0),
        ("EJ Boreal", 900.0),
    ]


def test_janela_sem_registro_permanece_sem_valor(monkeypatch):
    chamadas = 0

    def ler_todas(_sb, tabela, _colunas, _filtro):
        nonlocal chamadas
        chamadas += 1
        return [{"id_ej": 1, "nome": "EJ Aurora"}] if tabela == "empresa_junior" else []

    monkeypatch.setattr(dashboard_ia_service, "ler_todas", ler_todas)
    pontos = dashboard_ia_service.calcular_pontos(
        object(), _plano(dimensao="mes", visualizacao="linha"), federacao_id=7
    )

    assert chamadas == 2
    assert [(p.rotulo, p.valor) for p in pontos] == [("9", None), ("10", None)]


def test_periodo_nao_pode_inverter_meses():
    with pytest.raises(ValidationError, match="mês final"):
        _plano(mes_inicio=10, mes_fim=9)


def test_catalogo_rejeita_calculo_ou_visualizacao_livre():
    with pytest.raises(ValidationError):
        _plano(agregacao="contagem")
    with pytest.raises(ValidationError):
        _plano(metrica="formula_personalizada")
