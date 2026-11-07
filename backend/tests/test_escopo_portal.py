"""O escopo simplificado mantém Nexo e encerra a API de dashboards gerados."""

import pytest
from fastapi.testclient import TestClient

from app.main import criar_app


@pytest.mark.parametrize("metodo, caminho", [
    ("GET", "/api/v1/ia/dashboards"),
    ("GET", "/api/v1/ia/dashboards/creditos"),
    ("POST", "/api/v1/ia/dashboards"),
    ("PATCH", "/api/v1/ia/dashboards/qualquer-id"),
    ("GET", "/api/v1/ia/dashboards/publicos/qualquer-chave"),
])
def test_dashboard_ia_nao_esta_disponivel(metodo, caminho):
    with TestClient(criar_app()) as cliente:
        assert cliente.request(metodo, caminho).status_code == 404


def test_nexo_e_paineis_convencionais_continuam_registrados():
    caminhos = criar_app().openapi()["paths"]
    assert "/api/v1/ia/perguntar" in caminhos
    assert "/api/v1/rede/indicadores" in caminhos
    assert "/api/v1/eventos" in caminhos
    assert not any(c.startswith("/api/v1/ia/dashboards") for c in caminhos)
