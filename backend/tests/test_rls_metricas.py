"""
RLS e privilégios de `metrica_personalizada` (infra/db/init/27-metricas-personalizadas.sql).

Mesmo método de tests/test_rls_painel_admin.py: SQL direto no Postgres do
laboratório como `app_authenticated`, com o claim simulado. Sem o laboratório,
o módulo é pulado (e `--require-lab` transforma o pulo em falha).

O que fica fixado:
  1. Todos da federação leem; ninguém lê métrica de outra federação.
  2. Só `admin` ou `plataforma` ATIVO vinculado à federação, segundo o BANCO,
     cria, edita e apaga (28). O `plataforma` não ganha outras federações.
  3. Excluir de vez só métrica arquivada.
  4. Tenant, autoria e versão não são escolhidos pelo cliente.
"""

import json
import os

import pytest

psycopg = pytest.importorskip("psycopg", reason="psycopg não instalado; é dependência de teste")

PORTA = os.getenv("POSTGRES_PORT", "55432")
DSN_DONO = os.getenv("LAB_DSN_DONO", f"postgresql://portal:portal@localhost:{PORTA}/portal_lab")
DSN_APP = os.getenv("LAB_DSN_APP", f"postgresql://app_authenticated:app_authenticated@localhost:{PORTA}/portal_lab")

FEJEPE = 12
FEJEPAR = 4
BASE = 970_000
MET_PE = BASE + 1
MET_PE_ARQ = BASE + 2
MET_PAR = BASE + 3
DEF = json.dumps({"expressao": "faturamento", "ano": 2026, "mes_inicio": 1})


def _uuid(n: int) -> str:
    return f"00000000-0000-0000-0000-{970000000 + n:012d}"


# (id, auth_user_id, federação, papel no banco, ativo)
ADM_PE = (BASE + 1, _uuid(1), FEJEPE, "admin", True)
MEMB_PE = (BASE + 2, _uuid(2), FEJEPE, "membro", True)
ADM_PAR = (BASE + 3, _uuid(3), FEJEPAR, "admin", True)
ADM_INATIVO = (BASE + 4, _uuid(4), FEJEPE, "admin", False)
PLAT = (BASE + 5, _uuid(5), FEJEPE, "plataforma", True)
PLAT_INATIVO = (BASE + 6, _uuid(6), FEJEPE, "plataforma", False)
USUARIOS = (ADM_PE, MEMB_PE, ADM_PAR, ADM_INATIVO, PLAT, PLAT_INATIVO)


def _token(usuario, *, papel: str | None = None, federacao: int | None = None) -> str:
    _, sub, fed, papel_banco, _ = usuario
    return json.dumps({"sub": sub, "federacao_id": str(federacao or fed), "papel": papel or papel_banco})


def _rodar(conexao, *comandos, claims: str):
    """Roda os comandos numa transação com o claim, devolve as linhas do último e desfaz."""
    try:
        with conexao.cursor() as cur:
            cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (claims,))
            for sql, params in comandos:
                cur.execute(sql, params)
            return cur.fetchall() if cur.description else []
    finally:
        conexao.rollback()


def _inserir(federacao, criado_por, nome="Nova métrica"):
    return ("INSERT INTO metrica_personalizada (federacao_id, nome, definicao, criado_por) "
            "VALUES (%s, %s, %s::jsonb, %s) RETURNING id, versao", (federacao, nome, DEF, criado_por))


@pytest.fixture(scope="module")
def lab():
    try:
        conexao = psycopg.connect(DSN_DONO, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres do laboratório indisponível em {DSN_DONO!r}. Rode `make lab`. ({exc})")
    with conexao:
        if conexao.execute("SELECT to_regprocedure('public.pode_gerir_metricas(bigint)')").fetchone()[0] is None:
            pytest.skip("As migrações 27 e 28 não estão aplicadas no laboratório.")
        _limpar(conexao)
        _semear(conexao)
        conexao.commit()
        try:
            yield conexao
        finally:
            _limpar(conexao)
            conexao.commit()


def _limpar(conexao) -> None:
    with conexao.cursor() as cur:
        cur.execute("DELETE FROM metrica_personalizada WHERE id >= %s OR criado_por = ANY(%s::uuid[])",
                    (BASE, [u[1] for u in USUARIOS]))
        cur.execute("DELETE FROM usuario WHERE id >= %s AND id < %s", (BASE, BASE + 1000))
        cur.execute("DELETE FROM auth.users WHERE id = ANY(%s::uuid[])", ([u[1] for u in USUARIOS],))


def _semear(conexao) -> None:
    with conexao.cursor() as cur:
        for id_, sub, federacao, papel, ativo in USUARIOS:
            cur.execute("INSERT INTO auth.users (id, email) VALUES (%s, %s)", (sub, f"m{id_}@example.invalid"))
            cur.execute("INSERT INTO usuario (id, federacao_id, nome, email, papel, ativo, auth_user_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (id_, federacao, f"Usuário {id_}", f"m{id_}@example.invalid", papel, ativo, sub))
        cur.executemany(
            "INSERT INTO metrica_personalizada (id, federacao_id, nome, definicao, criado_por, arquivada_em) "
            "VALUES (%s, %s, %s, %s::jsonb, %s, %s)",
            [(MET_PE, FEJEPE, "Métrica PE", DEF, ADM_PE[1], None),
             (MET_PE_ARQ, FEJEPE, "Arquivada PE", DEF, ADM_PE[1], None),
             (MET_PAR, FEJEPAR, "Métrica PAR", DEF, ADM_PAR[1], None)])
        # O trigger zera `arquivada_em` na criação; arquivar é sempre um UPDATE.
        cur.execute("UPDATE metrica_personalizada SET arquivada_em = now() WHERE id = %s", (MET_PE_ARQ,))


@pytest.fixture
def app(lab):
    with psycopg.connect(DSN_APP, connect_timeout=3) as conexao:
        yield conexao


def _ids(linhas):
    return {linha[0] for linha in linhas}


VISIVEIS = ("SELECT id FROM metrica_personalizada WHERE id >= %s", (BASE,))


class TestLeitura:
    def test_membro_le_as_da_propria_federacao(self, app):
        assert _ids(_rodar(app, VISIVEIS, claims=_token(MEMB_PE))) == {MET_PE, MET_PE_ARQ}

    def test_admin_de_outra_federacao_nao_ve(self, app):
        assert _ids(_rodar(app, VISIVEIS, claims=_token(ADM_PAR))) == {MET_PAR}

    def test_sem_claim_nao_ve_nada(self, app):
        assert _rodar(app, VISIVEIS, claims="{}") == []

    def test_anon_sem_privilegio(self, lab):
        assert lab.execute("SELECT has_table_privilege('anon', 'public.metrica_personalizada', 'SELECT')").fetchone()[0] is False
        lab.rollback()


class TestEscrita:
    def test_admin_cria_com_versao_do_banco(self, app):
        linhas = _rodar(app, _inserir(FEJEPE, ADM_PE[1]), claims=_token(ADM_PE))
        assert len(linhas) == 1 and linhas[0][1] == 1

    @pytest.mark.parametrize("usuario, papel_token", [
        (MEMB_PE, None),            # membro
        (MEMB_PE, "admin"),         # membro com claim adulterado/antigo de admin
        (ADM_INATIVO, None),        # admin desativado
        (PLAT_INATIVO, None),       # admin master desativado
    ])
    def test_quem_nao_e_admin_ativo_nao_cria(self, app, usuario, papel_token):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, _inserir(FEJEPE, usuario[1]), claims=_token(usuario, papel=papel_token))

    def test_admin_master_cria_e_exclui_na_propria_federacao(self, app):
        linhas = _rodar(app, _inserir(FEJEPE, PLAT[1]), claims=_token(PLAT))
        assert len(linhas) == 1
        assert _ids(_rodar(app, ("DELETE FROM metrica_personalizada WHERE id = %s RETURNING id", (MET_PE_ARQ,)),
                           claims=_token(PLAT))) == {MET_PE_ARQ}

    def test_admin_master_nao_alcanca_outra_federacao(self, app):
        # Nem forjando o claim: o vínculo do banco é com a FEJEPE.
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, _inserir(FEJEPAR, PLAT[1]), claims=_token(PLAT, federacao=FEJEPAR))
        assert _rodar(app, ("UPDATE metrica_personalizada SET nome = 'X' WHERE id = %s RETURNING id", (MET_PAR,)),
                      claims=_token(PLAT)) == []

    def test_admin_nao_cria_em_outra_federacao(self, app):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, _inserir(FEJEPE, ADM_PAR[1]), claims=_token(ADM_PAR))
        # Nem forjando o claim de federação: o papel do banco é da FEJEPAR.
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, _inserir(FEJEPE, ADM_PAR[1]), claims=_token(ADM_PAR, federacao=FEJEPE))

    def test_autoria_e_de_quem_esta_na_sessao(self, app):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, _inserir(FEJEPE, MEMB_PE[1]), claims=_token(ADM_PE))

    def test_admin_edita_e_versao_sobe_so_com_definicao(self, app):
        linhas = _rodar(app,
                        ("UPDATE metrica_personalizada SET nome = 'Renomeada' WHERE id = %s", (MET_PE,)),
                        ("UPDATE metrica_personalizada SET definicao = %s::jsonb WHERE id = %s RETURNING versao, nome",
                         (json.dumps({"expressao": "csat", "ano": 2026}), MET_PE)),
                        claims=_token(ADM_PE))
        assert linhas == [(2, "Renomeada")]

    @pytest.mark.parametrize("usuario", [MEMB_PE, ADM_PAR])
    def test_quem_nao_e_admin_da_federacao_nao_edita(self, app, usuario):
        linhas = _rodar(app, ("UPDATE metrica_personalizada SET nome = 'X' WHERE id = %s RETURNING id", (MET_PE,)),
                        claims=_token(usuario))
        assert linhas == []

    @pytest.mark.parametrize("coluna, valor", [("federacao_id", FEJEPAR), ("versao", 99), ("criado_por", _uuid(3)),
                                               ("criado_em", "2020-01-01")])
    def test_colunas_protegidas(self, app, coluna, valor):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, (f"UPDATE metrica_personalizada SET {coluna} = %s WHERE id = %s", (valor, MET_PE)),
                   claims=_token(ADM_PE))


class TestExclusao:
    def test_ativa_nao_e_excluida(self, app):
        assert _rodar(app, ("DELETE FROM metrica_personalizada WHERE id = %s RETURNING id", (MET_PE,)),
                      claims=_token(ADM_PE)) == []

    def test_arquivada_e_excluida_pelo_admin(self, app):
        assert _ids(_rodar(app, ("DELETE FROM metrica_personalizada WHERE id = %s RETURNING id", (MET_PE_ARQ,)),
                           claims=_token(ADM_PE))) == {MET_PE_ARQ}

    @pytest.mark.parametrize("usuario", [MEMB_PE, ADM_PAR])
    def test_outros_nao_excluem(self, app, usuario):
        assert _rodar(app, ("DELETE FROM metrica_personalizada WHERE id = %s RETURNING id", (MET_PE_ARQ,)),
                      claims=_token(usuario)) == []

    def test_truncate_negado(self, app):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, ("TRUNCATE metrica_personalizada", ()), claims=_token(ADM_PE))
