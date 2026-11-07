"""Regressão da diferença entre defaults Supabase e laboratório, sem dados reais."""
import os
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("LAB_DSN_DONO", "postgresql://portal:portal@localhost:55432/portal_lab")
MIGRACAO = Path(__file__).resolve().parents[2] / "infra/db/init/21-privilegios-minimos.sql"


@pytest.fixture
def banco():
    try:
        conn = psycopg.connect(DSN, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("Postgres de testes indisponível; rode make test")
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.mark.parametrize("papel", ["anon", "authenticated"])
def test_truncate_recusado_pelo_banco(banco, papel):
    tabelas = banco.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public'"
    ).fetchall()
    for (tabela,) in tabelas:
        with banco.transaction():
            banco.execute(psycopg.sql.SQL("SET LOCAL ROLE {}").format(psycopg.sql.Identifier(papel)))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                # CASCADE evita que FK esconda uma concessão TRUNCATE indevida.
                # O savepoint garante rollback mesmo se a regressão permitir.
                with banco.transaction():
                    banco.execute(psycopg.sql.SQL("TRUNCATE {} CASCADE").format(psycopg.sql.Identifier(tabela)))
            banco.execute("RESET ROLE")


def test_migracao_corrige_defaults_supabase_e_preserva_acessos(banco):
    # Reproduz ALL que não existe no shim do laboratório e originou o defeito.
    banco.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated")
    banco.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated")
    banco.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated")
    banco.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated")
    banco.execute("ALTER DEFAULT PRIVILEGES GRANT ALL ON TABLES TO anon, authenticated")
    banco.execute("ALTER DEFAULT PRIVILEGES GRANT ALL ON SEQUENCES TO anon, authenticated")
    banco.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO anon, authenticated")
    banco.execute("ALTER DEFAULT PRIVILEGES GRANT EXECUTE ON FUNCTIONS TO PUBLIC, anon, authenticated")
    sql = MIGRACAO.read_text().replace("BEGIN;", "").replace("COMMIT;", "")
    banco.execute(sql)
    banco.execute(sql)  # reaplicação aditiva é idempotente

    tabelas = banco.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()
    for (tabela,) in tabelas:
        for papel in ("anon", "authenticated"):
            for privilegio in ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
                assert not banco.execute("SELECT has_table_privilege(%s,%s,%s)", (papel, tabela, privilegio)).fetchone()[0]
        if tabela.startswith(('ia_controle_', 'ia_creditos_')):
            for papel in ("anon", "authenticated"):
                assert not banco.execute("SELECT has_table_privilege(%s,%s,'SELECT')", (papel, tabela)).fetchone()[0]
                assert not banco.execute("SELECT has_any_column_privilege(%s,%s,'SELECT')", (papel, tabela)).fetchone()[0]
    assert banco.execute("SELECT has_column_privilege('anon','federacao','slug','SELECT')").fetchone()[0]
    assert not banco.execute("SELECT has_column_privilege('anon','federacao','id','SELECT')").fetchone()[0]
    assert banco.execute("SELECT has_column_privilege('authenticated','usuario','papel','UPDATE')").fetchone()[0]
    assert not banco.execute("SELECT has_column_privilege('authenticated','usuario','auth_user_id','UPDATE')").fetchone()[0]
    assert banco.execute("SELECT has_column_privilege('ingestao','empresa_junior','nome','UPDATE')").fetchone()[0]
    assert banco.execute("SELECT has_function_privilege('authenticated','public.admin_listar_usuarios()','EXECUTE')").fetchone()[0]
    assert not banco.execute("SELECT has_function_privilege('anon','public.admin_listar_usuarios()','EXECUTE')").fetchone()[0]

    banco.execute("CREATE TABLE public.privilegios_probe (id bigint)")
    banco.execute("CREATE SEQUENCE public.privilegios_probe_seq")
    banco.execute("CREATE FUNCTION public.privilegios_probe_fn() RETURNS int LANGUAGE sql AS 'SELECT 1'")
    for papel in ("anon", "authenticated"):
        for privilegio in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            assert not banco.execute("SELECT has_table_privilege(%s,'public.privilegios_probe',%s)", (papel, privilegio)).fetchone()[0]
        for privilegio in ("USAGE", "SELECT", "UPDATE"):
            assert not banco.execute("SELECT has_sequence_privilege(%s,'public.privilegios_probe_seq',%s)", (papel, privilegio)).fetchone()[0]
        assert not banco.execute("SELECT has_function_privilege(%s,'public.privilegios_probe_fn()','EXECUTE')", (papel,)).fetchone()[0]
