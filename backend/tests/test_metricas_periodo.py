"""Crescimento anual compara o mesmo período e o acumulado mais recente."""

from unittest.mock import MagicMock

from app.services.empresa_service import _calcular_crescimento_anual
from app.services.rede_service import _calcular_crescimento_rede


def test_crescimento_ej_filtra_mes_equivalente_do_ano_anterior():
    sb = MagicMock()
    query = sb.table.return_value.select.return_value
    query.eq.return_value = query
    query.lte.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value.data = [{"faturamento_acumulado": 100}]

    crescimento = _calcular_crescimento_anual(
        sb, 101, 2026, 150, mes_referencia=3
    )

    assert crescimento == 50.0
    query.lte.assert_called_once_with("mes", 3)
    query.order.assert_called_once_with("mes", desc=True)


def test_crescimento_ej_sem_mes_atual_e_indisponivel():
    sb = MagicMock()

    assert _calcular_crescimento_anual(
        sb, 101, 2026, 0, mes_referencia=None
    ) is None
    sb.table.assert_not_called()


def test_crescimento_rede_usa_ultimo_mes_mesmo_apos_ajuste_negativo(monkeypatch):
    sb = MagicMock()
    chamadas = []

    def ler_anterior(_sb, *, ano, mes, ids_ej, colunas):
        chamadas.append((ano, mes, ids_ej, colunas))
        return [
            {"id_ej": 101, "mes": 1, "faturamento_acumulado": 100},
            {"id_ej": 101, "mes": 2, "faturamento_acumulado": 90},
            {"id_ej": 102, "mes": 2, "faturamento_acumulado": 10},
        ]

    monkeypatch.setattr("app.services.rede_service._ler_monitoramento", ler_anterior)

    crescimento = _calcular_crescimento_rede(
        sb, [101, 102], 2026, 120, mes_referencia=2
    )

    assert crescimento == 20.0
    assert chamadas[0][:3] == (2025, 2, [101, 102])


def test_crescimento_rede_sem_mes_atual_e_indisponivel():
    assert _calcular_crescimento_rede(
        MagicMock(), [101], 2026, 0, mes_referencia=None
    ) is None
