"""Regressões de configuração com valores sintéticos; sem rede/segredos reais."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('check_env', Path(__file__).with_name('check-env.py'))
modulo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modulo)


class ConfiguracaoDeploy(unittest.TestCase):
    def validar(self, **alteracoes):
        valores = dict(SUPABASE_URL='https://fixture.supabase.co',
                       SUPABASE_ANON_KEY='sb_publishable_fixture',
                       SUPABASE_SERVICE_KEY='sb_secret_fixture',
                       INGESTAO_DSN='postgresql://ingestor:fixture@db.fixture.test/postgres?sslmode=require',
                       CORS_ORIGINS='https://portal.fixture.test',
                       CONVITE_REDIRECT_URL='https://portal.fixture.test/definir-senha',
                       DOCS_ENABLED='false', TENANT_CLAIM_OBRIGATORIO='true')
        valores.update(alteracoes)
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / 'config'
            arquivo.write_text('\n'.join(f'{k}={v}' for k, v in valores.items()))
            return modulo.validar(arquivo, 'render')

    def test_configuracao_valida_sem_ia(self):
        self.assertEqual(self.validar(), [])

    def test_chave_secreta_no_caminho_publico(self):
        self.assertTrue(self.validar(SUPABASE_ANON_KEY='sb_secret_fixture'))

    def test_origens_perigosas(self):
        for origem in ('*', 'http://portal.fixture.test', 'https://portal.fixture.test/path',
                       'https://*.fixture.test', 'https://user:pass@portal.fixture.test'):
            with self.subTest(origem=origem):
                self.assertTrue(self.validar(CORS_ORIGINS=origem))

    def test_convite_fora_da_origem(self):
        self.assertTrue(self.validar(CONVITE_REDIRECT_URL='https://outro.fixture.test/definir-senha'))

    def test_producao_exige_claim_e_docs_fechadas(self):
        self.assertTrue(self.validar(DOCS_ENABLED='true'))
        self.assertTrue(self.validar(TENANT_CLAIM_OBRIGATORIO='false'))

    def test_login_privilegiado_codificado(self):
        self.assertTrue(self.validar(INGESTAO_DSN='postgresql://%70ostgres:fixture@db.fixture.test/postgres?sslmode=require'))

    def test_ia_exige_par_completo(self):
        self.assertTrue(self.validar(IA_MODELO='fixture'))
        self.assertTrue(self.validar(IA_API_KEY='fixture'))
        self.assertEqual(self.validar(IA_MODELO='fixture', IA_API_KEY='fixture'), [])


if __name__ == '__main__':
    unittest.main()
