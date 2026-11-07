from decimal import Decimal
from app.database import normalizar_resultado


def test_resultado_postgresql_mantem_contrato_numerico_json():
    linhas = [{"meta": Decimal("120000.50"), "meses": [{"faturamento": Decimal("1000.25")}], "ausente": None, "zero": Decimal("0"), "id": 12}]
    resultado = normalizar_resultado(linhas)
    assert resultado[0]["meses"][0]["faturamento"] / resultado[0]["meta"] > 0
    assert isinstance(resultado[0]["meta"], float)
    assert resultado[0]["zero"] == 0
    assert resultado[0]["ausente"] is None
    assert resultado[0]["id"] == 12


def test_datas_postgresql_sao_serializadas_como_no_contrato_json():
    from datetime import date, datetime, timezone
    from app.models.admin import Carga
    dados = normalizar_resultado({"id":1,"arquivo_nome":"sintetico.xlsx","ano":2026,
        "exportado_em":date(2026,11,5),"carregado_em":datetime(2026,11,5,tzinfo=timezone.utc),
        "origem":"upload","escopo":"federacao","status":"aplicada"})
    assert dados["exportado_em"] == "2026-11-05"
    assert Carga.model_validate(dados).exportado_em == "2026-11-05"
    assert normalizar_resultado({"exportado_em":None})["exportado_em"] is None
