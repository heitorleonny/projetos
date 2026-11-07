"""Aplica o schema canônico em PostgreSQL próprio usando o ledger existente.

Executado somente pelo serviço de migração, com credencial de proprietário que
não é fornecida à API. Não adota banco legado sem ledger.
"""
from pathlib import Path
import os
import sys
import psycopg
from psycopg import sql

sys.path.insert(0, '/app/scripts')
from migrar_banco import aplicar, arquivos  # noqa: E402


def main():
    with psycopg.connect(
        host='postgres', dbname=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'],
        autocommit=True, connect_timeout=10,
    ) as conn:
        # O shim histórico instala roles e auth.jwt()/uid(). Executá-lo somente
        # no banco vazio: não recriar/alterar funções de um ambiente já existente.
        tem_auth = conn.execute("SELECT to_regprocedure('auth.jwt()') IS NOT NULL").fetchone()[0]
        tem_tabelas = conn.execute("SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public')").fetchone()[0]
        if not tem_auth:
            if tem_tabelas:
                raise RuntimeError('Banco existente sem auth: migração manual necessária.')
            with conn.transaction():
                conn.execute(Path('/infra/db/init/00-shim-auth-local.sql').read_text(), prepare=False)
        aplicar(conn, arquivos(Path('/infra/db/init')))
        for role, variavel in [('portal_app','APP_DB_PASSWORD'),('portal_auth','AUTH_DB_PASSWORD')]:
            senha = os.environ[variavel]
            if len(senha)<32: raise RuntimeError('Senha de banco insuficiente')
            conn.execute(sql.SQL('ALTER ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role),sql.Literal(senha)))
        # Desabilita o login histórico com senha pública do laboratório.
        conn.execute('ALTER ROLE app_authenticated NOLOGIN')
        # Conta de ingestão conserva o papel restrito, mas recebe senha privada.
        conn.execute(sql.SQL('ALTER ROLE app_ingestao LOGIN PASSWORD {}').format(
            sql.Literal(os.environ['INGESTAO_DB_PASSWORD'])))
    print('Schema PostgreSQL aplicado e credenciais de laboratório desabilitadas.')

if __name__ == '__main__':
    try:
        main()
    except (psycopg.Error, KeyError, RuntimeError):
        raise SystemExit('Migração falhou. Verifique configuração e schema; valores privados omitidos.') from None
