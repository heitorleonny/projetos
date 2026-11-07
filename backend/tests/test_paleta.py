"""Contrato de paleta e autorização real da RPC estreita, sem service key."""
import json
from unittest.mock import MagicMock
from types import SimpleNamespace

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.dependencies import get_current_user, get_federacao_id, get_supabase
from app.main import app as aplicacao
from tests.test_federacao import _supabase_com, BRANDING_FEJEPE
from tests.test_rls_painel_admin import lab, app, ADM_PE, MEMB_PE, MEMB_PAR, ADM_PAR, PLAT, _token, _rodar

ROTA = '/api/v1/federacao/minha/paleta'
CORES = {'cor_primaria':'#124433','cor_secundaria':'#334455','cor_acento':None}

@pytest.fixture
def cliente_paleta():
    sb = _supabase_com([BRANDING_FEJEPE])
    sb.rpc.return_value.execute.return_value = MagicMock(data=[{**BRANDING_FEJEPE, **CORES}])
    aplicacao.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id='teste',app_metadata={'papel':'admin'})
    aplicacao.dependency_overrides[get_federacao_id] = lambda: 12
    aplicacao.dependency_overrides[get_supabase] = lambda: sb
    yield TestClient(aplicacao), sb
    aplicacao.dependency_overrides.clear()


def test_contrato_salva_apenas_cores_sem_id(cliente_paleta):
    cliente,sb=cliente_paleta
    resposta=cliente.put(ROTA,json=CORES)
    assert resposta.status_code==200
    assert resposta.json()['cor_secundaria']=='#334455'
    sb.rpc.assert_called_once_with('definir_paleta_da_federacao', {'p_'+k:v for k,v in CORES.items()})

@pytest.mark.parametrize('extra', [{'federacao_id':7},{'status':'ativa'},{'cores':['#111111']},{'cor_acento':'red'}])
def test_corpo_nao_escolhe_tenant_ou_status(cliente_paleta,extra):
    cliente,sb=cliente_paleta
    assert cliente.put(ROTA,json={**CORES,**extra}).status_code==422
    sb.rpc.assert_not_called()


def test_membro_nao_salva(cliente_paleta):
    aplicacao.dependency_overrides[get_current_user]=lambda:SimpleNamespace(id='teste',app_metadata={'papel':'membro'})
    cliente,sb=cliente_paleta
    assert cliente.put(ROTA,json=CORES).status_code==403
    sb.rpc.assert_not_called()


def test_sem_tenant_nao_salva(cliente_paleta):
    aplicacao.dependency_overrides[get_federacao_id]=lambda:None
    cliente,sb=cliente_paleta
    assert cliente.put(ROTA,json=CORES).status_code==403
    sb.rpc.assert_not_called()


def test_paleta_exige_login():
    assert TestClient(aplicacao).put(ROTA,json=CORES).status_code==401

@pytest.mark.parametrize('usuario', [ADM_PE,ADM_PAR,PLAT])
def test_rpc_admin_salva_somente_propria_federacao(app,usuario):
    linhas=_rodar(app,'SELECT slug,cor_primaria,cor_secundaria,cor_acento FROM public.definir_paleta_da_federacao(%s,%s,%s)',claims=_token(usuario),params=tuple(CORES.values()))
    assert linhas==[('fejepe' if usuario[2]==12 else 'fejepar','#124433','#334455',None)]


def test_rpc_membro_ou_claim_forjado_nao_amplia_autorizacao(app):
    for claims in [_token(MEMB_PE,papel='admin'),json.dumps({'sub':ADM_PE[1],'papel':'admin','federacao_id':'4'}),json.dumps({'sub':ADM_PE[1],'papel':'admin'})]:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app,'SELECT * FROM public.definir_paleta_da_federacao(%s,%s,%s)',claims=claims,params=tuple(CORES.values()))


def test_admin_nao_recebe_update_amplo_por_causa_paleta(app):
    linhas=_rodar(app,"UPDATE federacao SET status='inativa' WHERE id=12 RETURNING id",claims=_token(ADM_PE))
    assert linhas==[]


def test_cor_salva_e_compartilhada_com_membro_sem_alterar_outro_tenant(app):
    try:
        def claims(usuario):
            app.execute("SELECT set_config('request.jwt.claims',%s,true)",(_token(usuario),))
        claims(MEMB_PAR)
        anterior=app.execute('SELECT cor_primaria,cor_secundaria,cor_acento FROM federacao').fetchall()
        claims(ADM_PE)
        app.execute('SELECT * FROM public.definir_paleta_da_federacao(%s,%s,%s)',tuple(CORES.values()))
        claims(MEMB_PE)
        assert app.execute('SELECT cor_primaria,cor_secundaria,cor_acento FROM federacao').fetchall()==[tuple(CORES.values())]
        claims(MEMB_PAR)
        assert app.execute('SELECT cor_primaria,cor_secundaria,cor_acento FROM federacao').fetchall()==anterior
    finally:app.rollback()


def test_rpc_rebaixamento_no_banco_revoga_sem_renovar_jwt(lab,app):
    try:
        lab.execute("UPDATE usuario SET papel='membro' WHERE id=%s",(ADM_PE[0],));lab.commit()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app,'SELECT * FROM public.definir_paleta_da_federacao(%s,%s,%s)',claims=_token(ADM_PE),params=tuple(CORES.values()))
    finally:
        lab.execute("UPDATE usuario SET papel='admin' WHERE id=%s",(ADM_PE[0],));lab.commit()


def test_rpc_nao_executavel_por_anon_e_hex_validado(lab,app):
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        _rodar(app,'SELECT * FROM public.definir_paleta_da_federacao(%s,%s,%s)',claims=_token(ADM_PE),params=('red',None,None))
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            lab.execute('SET LOCAL ROLE anon');lab.execute("SELECT * FROM public.definir_paleta_da_federacao(NULL,NULL,NULL)")
    finally:lab.rollback()


def test_tres_cores_publicas_para_login_mas_nenhum_status(lab):
    try:
        lab.execute('SET LOCAL ROLE anon')
        assert len(lab.execute("SELECT cor_primaria,cor_secundaria,cor_acento FROM federacao WHERE slug='fejepe'").fetchall())==1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):lab.execute('SELECT status FROM federacao')
    finally:lab.rollback()
