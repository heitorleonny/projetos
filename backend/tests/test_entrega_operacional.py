"""Migrações em DB descartável real e compensação do bootstrap Auth."""
import os
from pathlib import Path
from uuid import uuid4
import httpx
import psycopg
from psycopg import sql
import pytest
from scripts.migrar_banco import arquivos, aplicar, revisar
from scripts.criar_operador import criar

RAIZ = Path(__file__).resolve().parents[2]
DSN = os.getenv('LAB_DSN_DONO', 'postgresql://portal:portal@localhost:55432/portal_lab')

@pytest.fixture
def novo_banco():
    try:
        admin = psycopg.connect(DSN, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip('Postgres de testes indisponível; rode make test')
    nome = 'entrega_' + uuid4().hex
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(nome)))
    conn = psycopg.connect(DSN, dbname=nome, autocommit=True)
    # Shim somente no banco descartável; a rotina de produção nunca o aplica.
    conn.execute((RAIZ / 'infra/db/init/00-shim-auth-local.sql').read_text())
    try:
        yield conn
    finally:
        conn.close()
        admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(nome)))
        admin.close()


def test_migracoes_todas_ledger_reaplicacao_e_checksum(novo_banco):
    migracoes = arquivos(RAIZ / 'infra/db/init')
    assert len(revisar(novo_banco, migracoes)) == len(migracoes)
    aplicar(novo_banco, migracoes)
    assert revisar(novo_banco, migracoes) == []
    # 04 não é idempotente: se fosse reaplicada, esta chamada falharia.
    aplicar(novo_banco, migracoes)
    assert novo_banco.execute('SELECT count(*) FROM portal_operacao.migracao').fetchone()[0] == len(migracoes)
    assert novo_banco.execute("SELECT to_regprocedure('public.master_resumo_federacoes()') IS NOT NULL").fetchone()[0]
    assert not novo_banco.execute("SELECT has_table_privilege('authenticated','public.usuario','TRUNCATE')").fetchone()[0]
    for papel in ('anon', 'authenticated'):
        assert not novo_banco.execute("SELECT has_schema_privilege(%s,'portal_operacao','USAGE')", (papel,)).fetchone()[0]
    alteradas = list(migracoes)
    nome, _, texto = alteradas[0]
    alteradas[0] = (nome, 'checksum-alterado', texto)
    with pytest.raises(ValueError, match='Checksum'):
        revisar(novo_banco, alteradas)


def test_migrador_recusa_banco_legado_sem_ledger(novo_banco):
    novo_banco.execute('CREATE TABLE public.dado_existente(id int)')
    novo_banco.execute('INSERT INTO public.dado_existente VALUES (1)')
    with pytest.raises(ValueError, match='Não reaplique 04'):
        aplicar(novo_banco, arquivos(RAIZ / 'infra/db/init'))
    assert novo_banco.execute('SELECT count(*) FROM public.dado_existente').fetchone()[0] == 1
    assert novo_banco.execute("SELECT to_regclass('portal_operacao.migracao')").fetchone()[0] is None


def test_migracao_e_ledger_rollback_juntos(novo_banco):
    with pytest.raises(psycopg.Error):
        aplicar(novo_banco, [('01-falha.sql', 'abc', 'CREATE TABLE public.parcial(id int); SELECT 1/0;')])
    assert novo_banco.execute("SELECT to_regclass('public.parcial')").fetchone()[0] is None
    assert novo_banco.execute('SELECT count(*) FROM portal_operacao.migracao').fetchone()[0] == 0


def test_bootstrap_vincula_conta_nova_e_compensa_falha(novo_banco):
    novo_banco.execute("CREATE TABLE public.federacao(id bigint,slug text); INSERT INTO public.federacao VALUES (12,'fejepe')")
    novo_banco.execute('CREATE TABLE public.usuario(federacao_id bigint,nome text,email text UNIQUE,papel text,auth_user_id uuid,conta_principal bool)')
    novo_banco.execute('CREATE TABLE auth.users(id uuid PRIMARY KEY,email text)')
    chamadas = []
    uid = str(uuid4())
    def auth(request):
        chamadas.append(request.method)
        assert request.headers['apikey'] == 'segredo-nao-logado'
        if request.method == 'POST':
            import json
            body = json.loads(request.content)
            id_novo = uid if len(chamadas) == 1 else str(uuid4())
            novo_banco.execute('INSERT INTO auth.users VALUES (%s,%s)', (id_novo,body['email']))
            return httpx.Response(200, json={'id':id_novo})
        novo_banco.execute('DELETE FROM auth.users WHERE id=%s', (request.url.path.split('/')[-1],))
        return httpx.Response(200, json={})
    with httpx.Client(transport=httpx.MockTransport(auth)) as cliente:
        criar(novo_banco, cliente, 'https://example.test', 'segredo-nao-logado', 'novo@example.test', 'Operador', 'fejepe', 'senha-nao-logada')
        assert novo_banco.execute('SELECT papel,federacao_id,auth_user_id FROM public.usuario').fetchone() == ('plataforma',12, __import__('uuid').UUID(uid))
        with pytest.raises(ValueError, match='Conta existente'):
            criar(novo_banco, cliente, 'https://example.test', 'segredo-nao-logado', 'novo@example.test', 'Operador', 'fejepe', 'senha-nao-logada')
        assert chamadas == ['POST']
        novo_banco.execute("ALTER TABLE public.usuario ADD CONSTRAINT falha CHECK(nome <> 'Falhar')")
        with pytest.raises(ValueError, match='foi removida'):
            criar(novo_banco, cliente, 'https://example.test', 'segredo-nao-logado', 'falha@example.test', 'Falhar', 'fejepe', 'senha-nao-logada')
        assert chamadas == ['POST', 'POST', 'DELETE']
        assert novo_banco.execute('SELECT count(*) FROM public.usuario').fetchone()[0] == 1


def test_definer_acls_com_dono_sem_superuser_e_membership_preservada(novo_banco):
    from scripts.migrar_banco import executar_sql
    import re
    migracoes = arquivos(RAIZ / 'infra/db/init')
    aplicar(novo_banco, migracoes[:18])
    role = 'owner_' + uuid4().hex
    ident = sql.Identifier(role)
    novo_banco.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS CREATEROLE').format(ident))
    novo_banco.execute(sql.SQL('GRANT ia_limitador TO {} WITH ADMIN TRUE, INHERIT FALSE, SET FALSE').format(ident))
    novo_banco.execute(sql.SQL('GRANT USAGE, CREATE ON SCHEMA public TO {}').format(ident))
    novo_banco.execute(sql.SQL('GRANT SELECT, REFERENCES ON ALL TABLES IN SCHEMA public TO {} WITH GRANT OPTION').format(ident))
    novo_banco.execute(sql.SQL('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {} WITH GRANT OPTION').format(ident))
    novo_banco.execute(sql.SQL('GRANT REFERENCES ON auth.users TO {}').format(ident))
    novo_banco.execute(sql.SQL('GRANT USAGE ON SCHEMA auth TO {}').format(ident))
    novo_banco.execute(sql.SQL('ALTER SCHEMA public OWNER TO {}').format(ident))
    for (tabela,) in novo_banco.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall():
        novo_banco.execute(sql.SQL('ALTER TABLE public.{} OWNER TO {}').format(sql.Identifier(tabela),ident))
    try:
        novo_banco.execute(sql.SQL('SET ROLE {}').format(ident))
        assert novo_banco.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone() == (False,)
        for nome, _, texto in migracoes[18:20]:
            texto = re.sub(r'^\s*(?:BEGIN|COMMIT)\s*;\s*$', '', texto, flags=re.MULTILINE | re.IGNORECASE)
            with novo_banco.transaction():
                executar_sql(novo_banco, nome, texto)
        # Auth pode usar RPCs públicas autenticadas; primitivas permanecem privadas.
        for assinatura in ('persistir_dashboard_evento_ia(text,text,jsonb,boolean,jsonb)', 'consultar_creditos_dashboard_ia()'):
            assert novo_banco.execute("SELECT has_function_privilege('authenticated',%s,'EXECUTE')", (assinatura,)).fetchone()[0]
            assert not novo_banco.execute("SELECT has_function_privilege('anon',%s,'EXECUTE')", (assinatura,)).fetchone()[0]
        assert not novo_banco.execute("SELECT has_function_privilege('authenticated','reservar_creditos_ia(bigint,uuid,text,integer)','EXECUTE')").fetchone()[0]
        # Concessão administrativa anterior (outro grantor) permanece com flags.
        assert novo_banco.execute("SELECT m.admin_option,m.inherit_option,m.set_option FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles u ON u.oid=m.member WHERE r.rolname='ia_limitador' AND u.rolname=current_user").fetchall() == [(True,False,False)]
    finally:
        novo_banco.execute('RESET ROLE')
        # Todos os objetos locais são descartáveis; limpa dependências globais.
        novo_banco.execute(sql.SQL('DROP OWNED BY {} CASCADE').format(ident))
        novo_banco.execute(sql.SQL('DROP ROLE {}').format(ident))


def test_bootstrap_recusa_auth_e_banco_desalinhados(novo_banco):
    novo_banco.execute("CREATE TABLE public.federacao(id bigint,slug text); INSERT INTO public.federacao VALUES (12,'fejepe')")
    novo_banco.execute('CREATE TABLE public.usuario(federacao_id bigint,nome text,email text,papel text,auth_user_id uuid,conta_principal bool)')
    novo_banco.execute('CREATE TABLE auth.users(id uuid PRIMARY KEY,email text)')
    chamadas = []
    def auth(request):
        chamadas.append(request.method)
        # Auth remoto retorna UUID que não existe neste banco.
        return httpx.Response(200, json={'id':str(uuid4())})
    with httpx.Client(transport=httpx.MockTransport(auth)) as cliente:
        with pytest.raises(ValueError, match='foi removida'):
            criar(novo_banco,cliente,'https://outro.example.test','chave','novo@example.test','Operador','fejepe','senha-segura-nova')
    assert chamadas == ['POST','DELETE']
    assert novo_banco.execute('SELECT count(*) FROM public.usuario').fetchone()[0] == 0
