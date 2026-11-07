"""Quota operacional compartilhada, com Postgres e concorrência reais."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock
import pytest
from postgrest.exceptions import APIError
from app.dependencies import get_supabase
from app.ia.limites import ProvedorComLimite, LimitePortalIA, IdentidadeIAInativa
from tests.test_ia import cliente, plano, provedor_falso
from tests.test_rls import lab, DSN_APP
psycopg = pytest.importorskip('psycopg')


def test_reserva_negada_nao_chama_modelo():
    sb, modelo = Mock(), provedor_falso(plano())
    sb.rpc.return_value.execute.return_value.data = False
    with pytest.raises(LimitePortalIA):
        ProvedorComLimite(sb, modelo).interpretar('fora do zero', 2026)
    sb.rpc.assert_called_once_with('reservar_consulta_ia')
    modelo.interpretar.assert_not_called()


def test_identidade_recusada_nao_chama_modelo():
    sb, modelo = Mock(), provedor_falso(plano())
    sb.rpc.return_value.execute.side_effect = APIError({'code':'42501','message':'negado','hint':'','details':''})
    with pytest.raises(IdentidadeIAInativa):
        ProvedorComLimite(sb, modelo).interpretar('fora do zero', 2026)
    modelo.interpretar.assert_not_called()


@pytest.mark.parametrize('reserva', [None, 1, 'true', {}])
def test_reserva_sem_booleano_falha_fechada(reserva):
    sb, modelo = Mock(), provedor_falso(plano())
    sb.rpc.return_value.execute.return_value.data = reserva
    with pytest.raises(RuntimeError, match='não confirmada'):
        ProvedorComLimite(sb, modelo).interpretar('fora do zero', 2026)
    modelo.interpretar.assert_not_called()


def test_rota_limite_portal_429(cliente):
    client, app = cliente
    sb = app.dependency_overrides[get_supabase]()
    sb.rpc = Mock(return_value=SimpleNamespace(execute=lambda: SimpleNamespace(data=False)))
    resposta = client.post('/api/v1/ia/perguntar', headers={'Authorization':'Bearer fake'}, json={'pergunta':'fora do zero'})
    assert resposta.status_code == 429 and resposta.headers['retry-after'] == '60'
    assert 'neste minuto' in resposta.json()['detail']


def test_respostas_locais_nao_reservam(cliente):
    client, app = cliente
    sb = app.dependency_overrides[get_supabase]()
    sb.rpc = Mock()
    for pergunta in ('Quais são as melhores EJs?', 'Consulte todas as federações'):
        resposta = client.post('/api/v1/ia/perguntar', headers={'Authorization':'Bearer fake'}, json={'pergunta':pergunta})
        assert resposta.status_code == 200
    sb.rpc.assert_not_called()


@pytest.fixture
def cenario(lab):
    federacoes = (990980, 990981)
    usuarios = [uuid4() for _ in range(8)]
    with lab.cursor() as cur:
        cur.execute('SELECT limite_usuario,limite_federacao FROM ia_controle_config')
        config = cur.fetchone()
        cur.execute('UPDATE ia_controle_config SET limite_usuario=6,limite_federacao=30')
        cur.executemany('INSERT INTO federacao (id,slug,nome,uf) VALUES (%s,%s,%s,%s)',
                        [(f, f'ia-limite-{f}', 'Federação sintética de limite', 'PE') for f in federacoes])
        cur.executemany('INSERT INTO usuario (federacao_id,nome,email,papel,auth_user_id) VALUES (%s,%s,%s,%s,%s)',
                        [(federacoes[0] if i < 7 else federacoes[1], 'Usuário sintético de limite',
                          f'{uid}@limite.teste.local', 'membro', uid) for i,uid in enumerate(usuarios)])
        cur.execute('SELECT extract(second FROM clock_timestamp())')
        segundo = float(cur.fetchone()[0])
    lab.commit()
    if segundo > 55:
        time.sleep(60 - segundo + 0.05)
    try:
        yield lab, federacoes, usuarios
    finally:
        with lab.cursor() as cur:
            cur.execute('DELETE FROM usuario WHERE federacao_id = ANY(%s)', (list(federacoes),))
            cur.execute('DELETE FROM federacao WHERE id = ANY(%s)', (list(federacoes),))
            cur.execute('UPDATE ia_controle_config SET limite_usuario=%s,limite_federacao=%s', config)
        lab.commit()


def reservar(uid, fed, papel='membro'):
    with psycopg.connect(DSN_APP, connect_timeout=3) as conexao:
        with conexao.cursor() as cur:
            cur.execute("SELECT set_config('request.jwt.claims',%s,true)",
                        (json.dumps({'sub':str(uid),'federacao_id':fed,'papel':papel}),))
            cur.execute('SELECT reservar_consulta_ia()')
            return cur.fetchone()[0]


def test_burst_concorrente_atomico_mesmo_usuario(cenario):
    dono, (fed,_), usuarios = cenario
    with ThreadPoolExecutor(max_workers=12) as executor:
        resultados = list(executor.map(lambda _: reservar(usuarios[0],fed), range(24)))
    assert sum(resultados) == 6
    with dono.cursor() as cur:
        cur.execute('SELECT chamadas FROM ia_controle_janela WHERE federacao_id=%s ORDER BY chave', (fed,))
        assert cur.fetchall() == [(6,), (6,)]


def test_limite_federacao_entre_usuarios_e_isolado(cenario):
    dono, (fed,outra), usuarios = cenario
    tarefas = [(uid,fed) for uid in usuarios[:7] for _ in range(6)]
    with ThreadPoolExecutor(max_workers=12) as executor:
        resultados = list(executor.map(lambda item: reservar(*item), tarefas))
    assert sum(resultados) == 30
    assert reservar(usuarios[7], outra) is True
    with dono.cursor() as cur:
        cur.execute("SELECT chamadas FROM ia_controle_janela WHERE federacao_id=%s AND chave='fed'", (fed,))
        assert cur.fetchone()[0] == 30


@pytest.mark.parametrize('modo', ['inativo','vinculo_alterado','sem_tenant','sem_usuario'])
def test_identidade_banco_nao_claim_papel(cenario, modo):
    dono, (fed,outra), usuarios = cenario
    usuario = usuarios[0]
    if modo in ('inativo','vinculo_alterado'):
        with dono.cursor() as cur:
            if modo == 'inativo':
                cur.execute('UPDATE usuario SET ativo=false WHERE auth_user_id=%s', (usuario,))
            else:
                cur.execute('UPDATE usuario SET federacao_id=%s WHERE auth_user_id=%s', (outra,usuario))
        dono.commit()
    if modo == 'sem_tenant':
        fed = None
    if modo == 'sem_usuario':
        usuario = uuid4()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        reservar(usuario, fed, papel='plataforma')
    with dono.cursor() as cur:
        cur.execute('SELECT count(*) FROM ia_controle_janela WHERE federacao_id=ANY(%s)', ([fed,outra],))
        assert cur.fetchone()[0] == 0


def test_claim_papel_nao_altera_limite(cenario):
    _, (fed,_), usuarios = cenario
    assert all(reservar(usuarios[0],fed,'plataforma') for _ in range(6))
    assert reservar(usuarios[0],fed,'plataforma') is False


def test_janela_antiga_reutilizada_sem_historico(cenario):
    dono, (fed,_), usuarios = cenario
    assert reservar(usuarios[0],fed)
    with dono.cursor() as cur:
        cur.execute("UPDATE ia_controle_janela SET inicio=date_trunc('minute',clock_timestamp())-interval '1 minute',chamadas=100 WHERE federacao_id=%s", (fed,))
    dono.commit()
    assert reservar(usuarios[0],fed)
    with dono.cursor() as cur:
        cur.execute('SELECT chamadas FROM ia_controle_janela WHERE federacao_id=%s', (fed,))
        assert cur.fetchall() == [(1,), (1,)]


@pytest.mark.parametrize('consulta', ['SELECT * FROM ia_controle_janela', "INSERT INTO ia_controle_janela VALUES (12,'fed',now(),0)",
                                    'UPDATE ia_controle_config SET limite_usuario=100', 'DELETE FROM ia_controle_janela'])
def test_cliente_nao_acessa_contadores_ou_config(cenario, consulta):
    with psycopg.connect(DSN_APP) as conexao:
        with conexao.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(consulta)


def test_rpc_nao_aceita_identidade_ou_limites(cenario):
    with psycopg.connect(DSN_APP) as conexao:
        with conexao.cursor() as cur:
            with pytest.raises(psycopg.errors.UndefinedFunction):
                cur.execute('SELECT reservar_consulta_ia(12,10000)')


def test_config_operacional_editavel_apenas_sql_dono(cenario):
    dono, (fed,_), usuarios = cenario
    with dono.cursor() as cur:
        cur.execute('UPDATE ia_controle_config SET limite_usuario=2,limite_federacao=5')
    dono.commit()
    assert [reservar(usuarios[0],fed) for _ in range(3)] == [True,True,False]
    assert [reservar(usuarios[1],fed) for _ in range(2)] == [True,True]
    assert reservar(usuarios[2],fed) is True
    assert reservar(usuarios[3],fed) is False


def test_role_definer_dedicado_sem_bypass_ou_login(cenario):
    dono, _, _ = cenario
    with dono.cursor() as cur:
        cur.execute("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,rolcanlogin,rolinherit FROM pg_roles WHERE rolname='ia_limitador'")
        assert cur.fetchone() == (False,False,False,False,False,False,False)
        cur.execute("SELECT has_table_privilege('ia_limitador','monitoramento','SELECT')")
        assert cur.fetchone()[0] is False
        cur.execute("SELECT r.rolname FROM pg_proc p JOIN pg_roles r ON p.proowner=r.oid WHERE p.oid='reservar_consulta_ia()'::regprocedure")
        assert cur.fetchone()[0] == 'ia_limitador'



@pytest.mark.parametrize('helper', ['ia_identidade_usuario','ia_identidade_federacao'])
def test_helpers_privados_sem_execute_cliente(cenario, helper):
    dono, _, _ = cenario
    with dono.cursor() as cur:
        cur.execute("SELECT has_function_privilege('authenticated', %s, 'EXECUTE'),has_function_privilege('anon', %s, 'EXECUTE'),has_function_privilege('ia_limitador', %s, 'EXECUTE')", (helper+'()',)*3)
        assert cur.fetchone() == (False,False,True)
    with psycopg.connect(DSN_APP) as conexao:
        with conexao.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute('SELECT ' + helper + '()')


def test_rpc_funciona_sem_usage_schema_auth(cenario):
    dono, (fed,_), usuarios = cenario
    with dono.cursor() as cur:
        cur.execute("SELECT has_schema_privilege('ia_limitador','auth','USAGE')")
        anterior = cur.fetchone()[0]
        cur.execute('REVOKE USAGE ON SCHEMA auth FROM ia_limitador')
    dono.commit()
    try:
        with dono.cursor() as cur:
            cur.execute("SELECT has_schema_privilege('ia_limitador','auth','USAGE')")
            assert cur.fetchone()[0] is False
        assert reservar(usuarios[0],fed) is True
    finally:
        if anterior:
            with dono.cursor() as cur:
                cur.execute('GRANT USAGE ON SCHEMA auth TO ia_limitador')
            dono.commit()
