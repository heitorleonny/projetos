"""Logo enviada pela federação: contrato das rotas e autorização real das RPCs (migração 25)."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, get_federacao_id, get_supabase, get_supabase_anon
from app.main import app as aplicacao
from app.services.federacao_service import TAMANHO_MAXIMO_LOGO, detectar_tipo_logo
from tests.test_federacao import BRANDING_FEJEPE
from tests.test_rls_painel_admin import lab, app, ADM_PE, MEMB_PE, ADM_PAR, PLAT, _token, _rodar  # noqa: F401

ROTA = '/api/v1/federacao/minha/logo'
PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64
JPEG = b'\xff\xd8\xff\xe0' + b'\x00' * 64
WEBP = b'RIFF\x24\x00\x00\x00WEBPVP8 ' + b'\x00' * 64
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
URL_ENVIADA = '/api/v1/federacao/logo?slug=fejepe&v=0123456789abcdef'


# ── Assinatura do arquivo ──────────────────────────────────────────────────

@pytest.mark.parametrize('dados,tipo', [(PNG, 'image/png'), (JPEG, 'image/jpeg'), (WEBP, 'image/webp')])
def test_detecta_formatos_aceitos_pelos_bytes(dados, tipo):
    assert detectar_tipo_logo(dados) == tipo


@pytest.mark.parametrize('dados', [SVG, b'GIF89a' + b'\x00' * 10, b'%PDF-1.7', b'RIFF\x00\x00\x00\x00WAVE', b'', b'\x89PN'])
def test_recusa_svg_e_outros_formatos(dados):
    assert detectar_tipo_logo(dados) is None


# ── Rotas com cliente falso ────────────────────────────────────────────────

@pytest.fixture
def cliente_logo():
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(data=[{**BRANDING_FEJEPE, 'logo_url': URL_ENVIADA}])
    aplicacao.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id='teste', app_metadata={'papel': 'admin'})
    aplicacao.dependency_overrides[get_federacao_id] = lambda: 12
    aplicacao.dependency_overrides[get_supabase] = lambda: sb
    aplicacao.dependency_overrides[get_supabase_anon] = lambda: sb
    yield TestClient(aplicacao), sb
    aplicacao.dependency_overrides.clear()


def _enviar(cliente, dados, nome='logo.png', tipo='image/png'):
    return cliente.put(ROTA, files={'arquivo': (nome, dados, tipo)})


@pytest.mark.parametrize('dados,tipo', [(PNG, 'image/png'), (JPEG, 'image/jpeg'), (WEBP, 'image/webp')])
def test_admin_envia_logo_e_recebe_branding(cliente_logo, dados, tipo):
    cliente, sb = cliente_logo
    resposta = _enviar(cliente, dados)
    assert resposta.status_code == 200 and resposta.json()['logo_url'] == URL_ENVIADA
    # O tipo vem dos bytes, não do nome nem do Content-Type do cliente.
    sb.rpc.assert_called_once_with('definir_logo_da_federacao', {'p_conteudo': dados, 'p_tipo': tipo})


@pytest.mark.parametrize('dados,nome,tipo', [
    (SVG, 'logo.svg', 'image/svg+xml'),
    (SVG, 'logo.png', 'image/png'),          # extensão e tipo mentem
    (b'<html><script>x</script></html>', 'logo.webp', 'image/webp'),
])
def test_svg_ou_arquivo_disfarcado_nao_chega_ao_banco(cliente_logo, dados, nome, tipo):
    cliente, sb = cliente_logo
    resposta = _enviar(cliente, dados, nome, tipo)
    assert resposta.status_code == 422 and 'SVG' in resposta.json()['detail']
    sb.rpc.assert_not_called()


def test_arquivo_grande_recusado_sem_chamar_banco(cliente_logo):
    cliente, sb = cliente_logo
    assert _enviar(cliente, PNG + b'\x00' * TAMANHO_MAXIMO_LOGO).status_code == 413
    assert _enviar(cliente, b'').status_code == 422
    sb.rpc.assert_not_called()


def test_corpo_nao_escolhe_tenant(cliente_logo):
    cliente, sb = cliente_logo
    resposta = cliente.put(ROTA, files={'arquivo': ('logo.png', PNG, 'image/png')}, data={'federacao_id': '7'})
    assert resposta.status_code == 200
    assert set(sb.rpc.call_args.args[1]) == {'p_conteudo', 'p_tipo'}


def test_membro_nao_envia_nem_remove(cliente_logo):
    aplicacao.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id='teste', app_metadata={'papel': 'membro'})
    cliente, sb = cliente_logo
    assert _enviar(cliente, PNG).status_code == 403
    assert cliente.delete(ROTA).status_code == 403
    sb.rpc.assert_not_called()


def test_sem_tenant_nao_envia(cliente_logo):
    aplicacao.dependency_overrides[get_federacao_id] = lambda: None
    cliente, sb = cliente_logo
    assert _enviar(cliente, PNG).status_code == 403
    sb.rpc.assert_not_called()


def test_escrita_exige_login():
    cliente = TestClient(aplicacao)
    assert cliente.put(ROTA, files={'arquivo': ('logo.png', PNG, 'image/png')}).status_code == 401
    assert cliente.delete(ROTA).status_code == 401


@pytest.mark.parametrize('codigo,status', [('42501', 403), ('22023', 422), ('08000', 503)])
def test_erros_do_banco_traduzidos(cliente_logo, codigo, status):
    from postgrest.exceptions import APIError
    cliente, sb = cliente_logo
    sb.rpc.return_value.execute.side_effect = APIError({'code': codigo, 'message': 'x', 'details': None, 'hint': None})
    assert _enviar(cliente, PNG).status_code == status


def test_admin_remove_logo(cliente_logo):
    cliente, sb = cliente_logo
    sb.rpc.return_value.execute.return_value = MagicMock(data=[{**BRANDING_FEJEPE, 'logo_url': None}])
    resposta = cliente.delete(ROTA)
    assert resposta.status_code == 200 and resposta.json()['logo_url'] is None
    sb.rpc.assert_called_once_with('remover_logo_da_federacao', {})


def test_leitura_publica_devolve_imagem_com_cabecalhos_seguros(cliente_logo):
    cliente, sb = cliente_logo
    sb.rpc.return_value.execute.return_value = MagicMock(data=[{'conteudo': PNG, 'tipo': 'image/png', 'versao': '0123456789abcdef'}])
    aplicacao.dependency_overrides.pop(get_current_user)
    resposta = cliente.get('/api/v1/federacao/logo', params={'slug': ' FEJEPE ', 'v': '0123456789abcdef'})
    assert resposta.status_code == 200 and resposta.content == PNG
    assert resposta.headers['content-type'] == 'image/png'
    assert resposta.headers['x-content-type-options'] == 'nosniff'
    assert "sandbox" in resposta.headers['content-security-policy']
    assert 'immutable' in resposta.headers['cache-control']
    sb.rpc.assert_called_once_with('logo_da_federacao', {'p_slug': 'fejepe'})
    # Versão antiga ou ausente: cache curto, para não prender a logo trocada.
    assert 'immutable' not in cliente.get('/api/v1/federacao/logo', params={'slug': 'fejepe'}).headers['cache-control']


def test_leitura_publica_sem_logo_e_404(cliente_logo):
    cliente, sb = cliente_logo
    sb.rpc.return_value.execute.return_value = MagicMock(data=[])
    assert cliente.get('/api/v1/federacao/logo', params={'slug': 'fejepe'}).status_code == 404


# ── RPCs no PostgreSQL real ────────────────────────────────────────────────

DEFINIR = 'SELECT slug, logo_url FROM public.definir_logo_da_federacao(%s, %s)'


@pytest.mark.parametrize('usuario', [ADM_PE, ADM_PAR, PLAT])
def test_rpc_admin_define_logo_so_da_propria_federacao(app, usuario):  # noqa: F811
    linhas = _rodar(app, DEFINIR, claims=_token(usuario), params=(PNG, 'image/png'))
    slug = 'fejepe' if usuario[2] == 12 else 'fejepar'
    assert len(linhas) == 1 and linhas[0][0] == slug
    assert linhas[0][1].startswith(f'/api/v1/federacao/logo?slug={slug}&v=')


def test_rpc_membro_ou_claim_forjado_nao_define(app):  # noqa: F811
    for claims in [_token(MEMB_PE, papel='admin'),
                   json.dumps({'sub': ADM_PE[1], 'papel': 'admin', 'federacao_id': '4'}),
                   json.dumps({'sub': ADM_PE[1], 'papel': 'admin'})]:
        for sql in (DEFINIR, 'SELECT * FROM public.remover_logo_da_federacao()'):
            params = (PNG, 'image/png') if sql == DEFINIR else ()
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                _rodar(app, sql, claims=claims, params=params)


@pytest.mark.parametrize('dados,tipo', [
    (SVG, 'image/png'), (SVG, 'image/svg+xml'), (JPEG, 'image/png'), (PNG + b'\x00' * TAMANHO_MAXIMO_LOGO, 'image/png'),
])
def test_rpc_valida_formato_e_tamanho_mesmo_sem_a_api(app, dados, tipo):  # noqa: F811
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        _rodar(app, DEFINIR, claims=_token(ADM_PE), params=(dados, tipo))


def test_tabela_sem_acesso_direto_para_clientes(lab):  # noqa: F811
    for papel in ('anon', 'authenticated'):
        for comando in ('SELECT * FROM public.federacao_logo',
                        "INSERT INTO public.federacao_logo VALUES (12, '\\x00', 'image/png', '0123456789abcdef')"):
            try:
                lab.execute(f'SET LOCAL ROLE {papel}')
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    lab.execute(comando)
            finally:
                lab.rollback()


def test_anon_nao_escreve_mas_le_logo_de_federacao_ativa(lab):  # noqa: F811
    try:
        lab.execute('SET LOCAL ROLE authenticated')
        lab.execute("SELECT set_config('request.jwt.claims', %s, true)", (_token(ADM_PE),))
        versao = lab.execute(DEFINIR, (PNG, 'image/png')).fetchone()[1].rsplit('=', 1)[1]
        lab.execute('SET LOCAL ROLE anon')
        assert lab.execute("SELECT conteudo, tipo, versao FROM public.logo_da_federacao('FEJEPE')").fetchall() == [(PNG, 'image/png', versao)]
        assert lab.execute("SELECT * FROM public.logo_da_federacao('fejepar')").fetchall() == []
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            lab.execute(DEFINIR, (PNG, 'image/png'))
    finally:
        lab.rollback()


def test_logo_de_federacao_inativa_nao_e_servida(lab):  # noqa: F811
    try:
        lab.execute('SET LOCAL ROLE authenticated')
        lab.execute("SELECT set_config('request.jwt.claims', %s, true)", (_token(ADM_PE),))
        lab.execute(DEFINIR, (PNG, 'image/png'))
        lab.execute('RESET ROLE')
        lab.execute("UPDATE federacao SET status = 'inativa' WHERE id = 12")
        lab.execute('SET LOCAL ROLE anon')
        assert lab.execute("SELECT * FROM public.logo_da_federacao('fejepe')").fetchall() == []
    finally:
        lab.rollback()


def test_admin_de_uma_federacao_nao_altera_a_outra(lab):  # noqa: F811
    try:
        lab.execute('SET LOCAL ROLE authenticated')
        lab.execute("SELECT set_config('request.jwt.claims', %s, true)", (_token(ADM_PAR),))
        lab.execute(DEFINIR, (PNG, 'image/png'))
        lab.execute("SELECT set_config('request.jwt.claims', %s, true)", (_token(ADM_PE),))
        lab.execute(DEFINIR, (JPEG, 'image/jpeg'))
        lab.execute('SELECT * FROM public.remover_logo_da_federacao()')
        lab.execute('RESET ROLE')
        assert lab.execute('SELECT federacao_id, tipo FROM federacao_logo ORDER BY 1').fetchall() == [(ADM_PAR[2], 'image/png')]
        assert lab.execute('SELECT logo_url FROM federacao WHERE id = 12').fetchone()[0] is None
    finally:
        lab.rollback()


def test_remover_preserva_logo_externa_da_plataforma(lab):  # noqa: F811
    try:
        lab.execute("UPDATE federacao SET logo_url = 'https://exemplo.invalid/logo.png' WHERE id = 12")
        lab.execute('SET LOCAL ROLE authenticated')
        lab.execute("SELECT set_config('request.jwt.claims', %s, true)", (_token(ADM_PE),))
        assert lab.execute('SELECT logo_url FROM public.remover_logo_da_federacao()').fetchone()[0] == 'https://exemplo.invalid/logo.png'
    finally:
        lab.rollback()


def test_rebaixamento_no_banco_revoga_sem_renovar_token(lab, app):  # noqa: F811
    try:
        lab.execute("UPDATE usuario SET papel='membro' WHERE id=%s", (ADM_PE[0],)); lab.commit()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, DEFINIR, claims=_token(ADM_PE), params=(PNG, 'image/png'))
    finally:
        lab.execute("UPDATE usuario SET papel='admin' WHERE id=%s", (ADM_PE[0],)); lab.commit()
