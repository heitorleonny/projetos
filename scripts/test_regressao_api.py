"""Contrato de comparação privada, sem rede e sem dados reais."""
import unittest
import json
from unittest.mock import MagicMock, patch
from regressao_api import SemRedirect, comparar, consultar, validar_url


class RegressaoApiTest(unittest.TestCase):
    def test_tolerancia_nao_oculta_grandes_diferencas(self):
        resultado = comparar({"valor": 1000000}, {"valor": 1000001}, 0.01)
        self.assertEqual(resultado[0]["status"], "divergente")

    def test_aninhado_ausente_null_e_limite(self):
        resultado = comparar({"x": {"1": 2}, "null": None, "total": 1.0},
                             {"x": {"1": 2, "2": 0}, "null": 0, "total": 1.005}, 0.01)
        self.assertEqual({r["metrica"]: r["status"] for r in resultado},
                         {"x.1": "igual", "x.2": "campo_ausente", "null": "divergente", "total": "igual"})
        self.assertNotIn("valor", str(resultado))

    def test_nao_finito_rejeitado(self):
        self.assertEqual(comparar({"x": float("nan")}, {"x": float("nan")}, 1)[0]["status"], "divergente")

    def test_urls_seguras(self):
        self.assertEqual(validar_url("https://example.org/api/v1/"), "https://example.org/api/v1")
        self.assertEqual(validar_url("http://localhost:8000/api/v1"), "http://localhost:8000/api/v1")
        for url in ("http://example.org", "https://user:secret@example.org", "https://example.org?token=x", "file:///tmp/a"):
            with self.assertRaises(ValueError):
                validar_url(url)

    def test_redirect_nao_repassa_token(self):
        self.assertIsNone(SemRedirect().redirect_request(None, None, 302, "", {}, "https://outro.example"))

    def resposta(self, payload):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return patch("regressao_api.build_opener", return_value=opener)

    def test_sde_e_ranking_removem_nomes_fotos_e_preservam_comparacao(self):
        dados = {"ano": 2026, "mes": 10, "total_ejs": 1, "cenarios": [
            {"nome": "Cenario", "sde": 0.3, "subindo": [{"id_ej": 12, "nome": "Nome privado",
             "cluster_atual": 1, "cluster_calculado": 2}], "mantendo": [], "descendo": []}]}
        with self.resposta(dados):
            saida = consultar("https://example.org/api/v1", "token", 2026, 10, "sde")
        self.assertNotIn("Nome privado", str(saida))
        with self.resposta([{"posicao": 1, "id_ej": 12, "nome": "Nome privado", "cluster": 1, "valor": 4}]):
            ranking = consultar("https://example.org/api/v1", "token", 2026, 10, "ranking")
        self.assertEqual(ranking["ordem_e_valores"], [(1, 12, 1, 4)])
        self.assertNotIn("12", str(comparar(ranking, ranking, 0.01)))

    def test_periodo_divergente_e_rota_livre_recusados(self):
        with self.resposta({"ano": 2025, "mes": 10}):
            with self.assertRaises(ValueError):
                consultar("https://example.org", "token", 2026, 10, "sde")
        with self.assertRaises(ValueError):
            consultar("https://example.org", "token", 2026, 10, "usuarios")


if __name__ == "__main__":
    unittest.main()
