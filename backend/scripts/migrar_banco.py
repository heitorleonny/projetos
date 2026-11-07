"""Migrações revisáveis, com ledger privado e checksums; nunca reaplica schema legado."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import psycopg

RAIZ = Path(__file__).resolve().parents[2]


def arquivos(diretorio: Path):
    return [(p.name, hashlib.sha256(p.read_bytes()).hexdigest(), p.read_text())
            for p in sorted(diretorio.glob('[0-9][0-9]-*.sql')) if not p.name.startswith('00-')]


def revisar(conexao, migracoes):
    existe = conexao.execute("SELECT to_regclass('portal_operacao.migracao') IS NOT NULL").fetchone()[0]
    ledger = dict(conexao.execute('SELECT arquivo, checksum FROM portal_operacao.migracao').fetchall()) if existe else {}
    if not existe and conexao.execute("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public')").fetchone()[0]:
        raise ValueError('Banco existente sem ledger: interrompido. Não reaplique 04; inventarie o schema e aplique somente pendências explicitamente revisadas.')
    conhecidos = {nome for nome, _, _ in migracoes}
    if set(ledger) - conhecidos:
        raise ValueError('Ledger contém migrações ausentes no código; use a mesma versão do projeto.')
    for nome, checksum, _ in migracoes:
        if nome in ledger and ledger[nome] != checksum:
            raise ValueError(f'Checksum divergente: {nome}; não altere migrações já aplicadas.')
    aplicadas = [nome in ledger for nome, _, _ in migracoes]
    if any(aplicadas[i] and not all(aplicadas[:i]) for i in range(len(aplicadas))):
        raise ValueError('Ledger fora de ordem; revisão manual necessária.')
    return [(nome, checksum, sql) for nome, checksum, sql in migracoes if nome not in ledger]


def executar_sql(conexao, nome, texto):
    # Migrações históricas transferem funções ao definer ia_limitador e revogam
    # membership antes de terminar as ACLs. No Supabase o dono não é superuser.
    # Preservamos somente a concessão do próprio executor, inclusive flags PG16;
    # memberships concedidas por outros grantors permanecem intactas.
    usuario = conexao.execute('SELECT current_user').fetchone()[0]
    dedicado = nome[:3] in ('18-', '19-', '20-', '23-')
    versao = conexao.info.server_version
    previo = None
    role_existia = conexao.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ia_limitador')").fetchone()[0]
    if dedicado and role_existia:
        colunas = 'm.admin_option,m.inherit_option,m.set_option' if versao >= 160000 else 'm.admin_option'
        previo = conexao.execute(f"SELECT {colunas} FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles u ON u.oid=m.member JOIN pg_roles g ON g.oid=m.grantor WHERE r.rolname='ia_limitador' AND u.rolname=current_user AND g.rolname=current_user").fetchone()
    if dedicado:
        # 18 cria o role e já concede membership, 19/20 precisam precondição.
        if role_existia:
            opcoes = ' WITH INHERIT TRUE, SET TRUE' if versao >= 160000 else ''
            conexao.execute(psycopg.sql.SQL('GRANT ia_limitador TO {}' + opcoes).format(psycopg.sql.Identifier(usuario)))
        rev = "DO $$ BEGIN\n    EXECUTE 'REVOKE ia_limitador FROM ' || quote_ident(current_user);\nEND $$;"
        texto = texto.replace(rev, '')
    if nome.startswith('24-'):
        # Roles são globais no cluster; outro banco pode já usá-los.
        for role in ('portal_app','portal_auth'):
            if conexao.execute('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)',(role,)).fetchone()[0]:
                texto=re.sub(r'CREATE ROLE '+role+r'[^;]*;', '', texto)
    conexao.execute(texto, prepare=False)
    if dedicado:
        executor = psycopg.sql.Identifier(usuario)
        if previo is None:
            conexao.execute(psycopg.sql.SQL('REVOKE ia_limitador FROM {}').format(executor))
        elif versao >= 160000:
            opcoes = f" WITH ADMIN {'TRUE' if previo[0] else 'FALSE'}, INHERIT {'TRUE' if previo[1] else 'FALSE'}, SET {'TRUE' if previo[2] else 'FALSE'}"
            conexao.execute(psycopg.sql.SQL('GRANT ia_limitador TO {}' + opcoes).format(executor))
        elif previo[0]:
            conexao.execute(psycopg.sql.SQL('GRANT ia_limitador TO {} WITH ADMIN OPTION').format(executor))
        else:
            conexao.execute(psycopg.sql.SQL('REVOKE ADMIN OPTION FOR ia_limitador FROM {}').format(executor))


def aplicar(conexao, migracoes):
    # Lock de sessão protege também a revisão contra dois operadores simultâneos.
    conexao.execute("SELECT pg_advisory_lock(hashtextextended('portal-operacao-migracoes', 0))")
    try:
        pendentes = revisar(conexao, migracoes)
        with conexao.transaction():
            conexao.execute('CREATE SCHEMA IF NOT EXISTS portal_operacao')
            conexao.execute('REVOKE ALL ON SCHEMA portal_operacao FROM PUBLIC, anon, authenticated')
            conexao.execute('CREATE TABLE IF NOT EXISTS portal_operacao.migracao (arquivo text PRIMARY KEY, checksum text NOT NULL, aplicada_em timestamptz NOT NULL DEFAULT now())')
            conexao.execute('REVOKE ALL ON portal_operacao.migracao FROM PUBLIC, anon, authenticated')
        for nome, checksum, sql in pendentes:
            # Alguns arquivos envolvem sua própria transação; o executor assume
            # esse controle para inserir o ledger na mesma transação do schema.
            sql = re.sub(r'^\s*(?:BEGIN|COMMIT)\s*;\s*$', '', sql, flags=re.MULTILINE | re.IGNORECASE)
            with conexao.transaction():
                executar_sql(conexao, nome, sql)
                conexao.execute('INSERT INTO portal_operacao.migracao (arquivo, checksum) VALUES (%s, %s)', (nome, checksum))
            print(f'Aplicada: {nome}')
    finally:
        conexao.execute("SELECT pg_advisory_unlock(hashtextextended('portal-operacao-migracoes', 0))")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Autoriza escrita; sem flag somente revisão.')
    parser.add_argument('--confirm-database', help='Nome exato do banco de destino; obrigatório com --apply.')
    args = parser.parse_args()
    dsn = os.environ.get('PORTAL_DATABASE_URL')
    if not dsn:
        parser.error('Configure PORTAL_DATABASE_URL (não passe credenciais em argumentos).')
    try:
        with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conexao:
            destino = conexao.execute('SELECT current_database()').fetchone()[0]
            if args.apply:
                if args.confirm_database != destino:
                    raise ValueError('Confirmação do banco não corresponde ao destino.')
                aplicar(conexao, arquivos(RAIZ / 'infra/db/init'))
            else:
                conexao.execute('SET default_transaction_read_only = on')
                pendentes = revisar(conexao, arquivos(RAIZ / 'infra/db/init'))
                print(f'Revisão somente leitura: {len(pendentes)} migrações pendentes.')
                for nome, checksum, _ in pendentes:
                    print(f'{nome} sha256={checksum}')
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except psycopg.Error:
        print('Falha SQL/conexão. Revise o destino e o arquivo pendente; nenhuma credencial foi impressa.', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
