"""Integração real da autenticação própria, sessão, convite e RLS independente."""
import os
import uuid
import pytest
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from fastapi.testclient import TestClient
from app.config import settings
from app.auth_native import hash_senha, hash_token
from app.database import Client
from app.main import app

SENHA='Uma-senha-sintetica-2026'

@pytest.fixture(scope='module')
def ambiente():
    dsn=os.getenv('LAB_DSN_DONO','postgresql://portal:portal@localhost:55432/portal_lab')
    try: conn=psycopg.connect(dsn,autocommit=True)
    except psycopg.Error: pytest.skip('Banco de integração indisponível')
    params=conninfo_to_dict(dsn)
    anterior=(settings.DATABASE_DSN,settings.AUTH_DATABASE_DSN)
    for role in ['portal_app','portal_auth']:
        conn.execute(psycopg.sql.SQL('ALTER ROLE {} LOGIN PASSWORD {}').format(psycopg.sql.Identifier(role),psycopg.sql.Literal('teste-nativo')))
    settings.DATABASE_DSN=make_conninfo(**{**params,'user':'portal_app','password':'teste-nativo'})
    settings.AUTH_DATABASE_DSN=make_conninfo(**{**params,'user':'portal_auth','password':'teste-nativo'})
    feds=[r[0] for r in conn.execute('SELECT id FROM federacao ORDER BY id LIMIT 2').fetchall()]
    ids=[uuid.uuid4(),uuid.uuid4()]
    for i,uid in enumerate(ids):
        email=f'nativo-{i}@teste.local'
        conn.execute('INSERT INTO auth.users(id,email,password_hash) VALUES(%s,%s,%s)',(uid,email,hash_senha(SENHA)))
        conn.execute("INSERT INTO usuario(nome,email,papel,federacao_id,auth_user_id) VALUES('Teste nativo',%s,'admin',%s,%s)",(email,feds[i],uid))
    try: yield conn,feds,ids
    finally:
        conn.execute("DELETE FROM auth.portal_sessao WHERE user_id IN (SELECT id FROM auth.users WHERE email LIKE 'nativo-%@teste.local')")
        conn.execute("DELETE FROM auth.portal_convite WHERE user_id IN (SELECT id FROM auth.users WHERE email LIKE 'nativo-%@teste.local')")
        conn.execute("DELETE FROM usuario WHERE email LIKE 'nativo-%@teste.local'")
        conn.execute("DELETE FROM auth.users WHERE email LIKE 'nativo-%@teste.local'")
        conn.execute("DELETE FROM auth.portal_tentativa WHERE email LIKE 'nativo-%@teste.local'")
        settings.DATABASE_DSN,settings.AUTH_DATABASE_DSN=anterior
        conn.close()

@pytest.fixture
def cliente(ambiente):
    with TestClient(app) as c: yield c


def login(c,i=0):
    r=c.post('/api/v1/auth/login',json={'email':f'nativo-{i}@teste.local','password':SENHA})
    assert r.status_code==200,r.text
    return r.json()['access_token']

def headers(token): return {'Authorization':f'Bearer {token}'}


def test_login_sem_jwt_me_e_logout(cliente,ambiente):
    token=login(cliente)
    assert '.' not in token
    assert cliente.get('/api/v1/auth/me',headers=headers(token)).json()['app_metadata']['federacao_id']==ambiente[1][0]
    assert cliente.post('/api/v1/auth/logout',headers=headers(token)).status_code==204
    assert cliente.get('/api/v1/auth/me',headers=headers(token)).status_code==401


def test_senha_errada_e_token_inventado(cliente):
    assert cliente.post('/api/v1/auth/login',json={'email':'nativo-0@teste.local','password':'errada'}).status_code==401
    assert cliente.get('/api/v1/admin/usuarios',headers=headers('token-inventado')).status_code==401
    assert cliente.get('/api/v1/admin/usuarios').status_code==401


def test_banco_atualiza_papel_e_desativa_sem_relogin(cliente,ambiente):
    conn,_,ids=ambiente
    token=login(cliente)
    try:
        conn.execute("UPDATE usuario SET papel='membro' WHERE auth_user_id=%s",(ids[0],))
        assert cliente.get('/api/v1/auth/me',headers=headers(token)).json()['app_metadata']['papel']=='membro'
        assert cliente.get('/api/v1/admin/usuarios',headers=headers(token)).status_code==403
        conn.execute('UPDATE usuario SET ativo=false WHERE auth_user_id=%s',(ids[0],))
        assert cliente.get('/api/v1/auth/me',headers=headers(token)).status_code==401
    finally: conn.execute("UPDATE usuario SET papel='admin',ativo=true WHERE auth_user_id=%s",(ids[0],))


def test_rls_usuario_sem_filtro_python_e_sem_vazamento(cliente,ambiente):
    _,feds,_=ambiente
    a,b=login(cliente),login(cliente,1)
    for token,fed in [(a,feds[0]),(b,feds[1]),(a,feds[0])]:
        linhas=Client(token).table('usuario').select('id,federacao_id').execute().data
        assert linhas and all(l['federacao_id']==fed for l in linhas)
        outra=feds[1] if fed==feds[0] else feds[0]
        assert Client(token).table('usuario').select('id').eq('federacao_id',outra).execute().data==[]


def test_token_no_banco_e_hash_e_expiracao(cliente,ambiente):
    token=login(cliente);conn=ambiente[0]
    assert conn.execute('SELECT count(*) FROM auth.portal_sessao WHERE token_hash=%s',(token,)).fetchone()[0]==0
    conn.execute("UPDATE auth.portal_sessao SET expira_em=now()-interval '1 second' WHERE token_hash=%s",(hash_token(token),))
    assert cliente.get('/api/v1/auth/me',headers=headers(token)).status_code==401


def test_convite_isolado_uso_unico_e_senha(cliente,ambiente):
    token=login(cliente);feds=ambiente[1]
    dados={'nome':'Convidado sintético','email':'nativo-convite@teste.local','papel':'membro','federacao_id':feds[1]}
    assert cliente.post('/api/v1/admin/usuarios',json=dados,headers=headers(token)).status_code==403
    dados['federacao_id']=feds[0]
    r=cliente.post('/api/v1/admin/usuarios',json=dados,headers=headers(token))
    assert r.status_code==201,r.text
    convite=r.json()['convite_url'].split('#convite=')[1]
    body={'password':SENHA,'convite':convite}
    assert cliente.post('/api/v1/auth/senha',json=body).status_code==204
    assert cliente.post('/api/v1/auth/senha',json=body).status_code==401
    assert cliente.post('/api/v1/auth/login',json={'email':dados['email'],'password':SENHA}).status_code==200


def test_anon_nao_le_sessoes_ou_usuarios(cliente):
    from postgrest.exceptions import APIError
    with pytest.raises(APIError) as erro: Client().table('usuario').select('id').execute()
    assert erro.value.code=='42501'
    with pytest.raises(ValueError): Client().table('portal_sessao')
    with pytest.raises(ValueError): Client().rpc('portal_conta')
    with pytest.raises(ValueError): Client().table('usuario; DROP TABLE usuario')


def test_trocar_senha_revoga_todas_sessoes(cliente):
    a,b=login(cliente),login(cliente)
    assert cliente.post('/api/v1/auth/senha',json={'password':SENHA},headers=headers(a)).status_code==204
    for token in [a,b]: assert cliente.get('/api/v1/auth/me',headers=headers(token)).status_code==401
