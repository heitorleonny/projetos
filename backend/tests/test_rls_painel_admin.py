"""
Testes de Row Level Security do painel administrativo (infra/db/init/13-painel-admin.sql).

Mesmo método de tests/test_rls.py: SQL direto no Postgres do laboratório, como
`app_authenticated` (sujeito às políticas), com o claim do JWT simulado por
`set_config('request.jwt.claims', ...)`. Sem o laboratório no ar, o módulo é
pulado.

O que estes testes fixam, em ordem de importância:

  1. `plataforma` enxerga o CADASTRO de todas as federações, e só o cadastro:
     EJ de outra federação continua invisível para ele.
  2. `admin` gere usuários da própria federação e de nenhuma outra, não cria
     operador e não move usuário de federação.
  3. Ninguém pelo caminho de request escreve `auth_user_id` — é o que impediria
     um admin de se apropriar da conta de outra pessoa.
  4. Para escrever, vale o papel do BANCO, não o do token: um admin rebaixado
     com token ainda válido não escreve mais.

    make lab
    psql "postgresql://portal:portal@localhost:55432/portal_lab" -f infra/db/init/13-painel-admin.sql
    python -m pytest tests/test_rls_painel_admin.py -v
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

# Faixa própria, acima da de tests/test_rls.py (>= 900.000), que também é
# apagada pela limpeza de lá — os dois módulos não pisam um no outro porque
# cada um semeia e limpa o que usa.
BASE = 950_000
EJ_PE = BASE + 12
EJ_PAR = BASE + 4
CARGA_NACIONAL = BASE + 1
CARGA_PAR = BASE + 2


def _uuid(n: int) -> str:
    return f"00000000-0000-0000-0000-{n:012d}"


# (id, auth_user_id, federação, papel, ativo, último login)
PLAT = (BASE + 1, _uuid(1), FEJEPE, "plataforma", True, "2026-09-28 10:00:00+00")
ADM_PE = (BASE + 2, _uuid(2), FEJEPE, "admin", True, "2026-09-27 09:00:00+00")
MEMB_PE = (BASE + 3, _uuid(3), FEJEPE, "membro", True, None)
MEMB_PAR = (BASE + 4, _uuid(4), FEJEPAR, "membro", True, "2026-09-20 08:00:00+00")
ADM_PAR = (BASE + 5, _uuid(5), FEJEPAR, "admin", True, None)
PLAT_INATIVO = (BASE + 6, _uuid(6), FEJEPE, "plataforma", False, None)
USUARIOS = (PLAT, ADM_PE, MEMB_PE, MEMB_PAR, ADM_PAR, PLAT_INATIVO)


def _token(usuario, *, papel: str | None = None) -> str:
    """Claims como o hook de 06 os escreveria para este usuário."""
    _, sub, federacao, papel_banco, *_ = usuario
    return json.dumps({"sub": sub, "federacao_id": str(federacao), "papel": papel or papel_banco})


def _rodar(conexao, sql: str, *, claims: str, params: tuple = ()):
    """Roda com o claim, devolve as linhas (ou [] se não houver resultado) e desfaz."""
    try:
        with conexao.cursor() as cur:
            cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (claims,))
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else []
    finally:
        conexao.rollback()


def _ids(linhas) -> set:
    return {linha[0] for linha in linhas}


# ── Infraestrutura ───────────────────────────────────────────


@pytest.fixture(scope="module")
def lab():
    try:
        conexao = psycopg.connect(DSN_DONO, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres do laboratório indisponível em {DSN_DONO!r}. Rode `make lab`. ({exc})")

    with conexao:
        existe = conexao.execute("SELECT to_regprocedure('public.admin_listar_usuarios()')").fetchone()[0]
        if existe is None:
            pytest.skip(
                "A migração 13 não está aplicada no laboratório. Aplique com "
                "`psql ... -f infra/db/init/13-painel-admin.sql` ou recrie o volume (`make clean && make lab`)."
            )
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
        cur.execute("DELETE FROM ingestao_carga WHERE id >= %s", (BASE,))
        cur.execute("DELETE FROM empresa_junior WHERE id >= %s", (BASE,))
        cur.execute("DELETE FROM usuario WHERE id >= %s", (BASE,))
        cur.execute("DELETE FROM auth.users WHERE id = ANY(%s::uuid[])", ([u[1] for u in USUARIOS],))


def _semear(conexao) -> None:
    with conexao.cursor() as cur:
        for id_, sub, federacao, papel, ativo, login in USUARIOS:
            cur.execute(
                "INSERT INTO auth.users (id, email, last_sign_in_at) VALUES (%s, %s, %s)",
                (sub, f"u{id_}@example.invalid", login),
            )
            cur.execute(
                "INSERT INTO usuario (id, federacao_id, nome, email, papel, ativo, auth_user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (id_, federacao, f"Usuário {id_}", f"u{id_}@example.invalid", papel, ativo, sub),
            )
        cur.executemany(
            "INSERT INTO empresa_junior (id, id_ej, nome, federacao_id) VALUES (%s, %s, %s, %s)",
            [(EJ_PE, EJ_PE, "EJ sintética PE", FEJEPE), (EJ_PAR, EJ_PAR, "EJ sintética PAR", FEJEPAR)],
        )
        for id_, escopo, federacao in ((CARGA_NACIONAL, "nacional", None), (CARGA_PAR, "federacao", FEJEPAR)):
            cur.execute(
                "INSERT INTO ingestao_carga (id, arquivo_nome, arquivo_hash, aba, ano, origem, escopo, "
                "federacao_id, status) VALUES (%s, 'teste.xlsx', %s, 'EMPRESAS_JUNIORES', 2026, 'cli', %s, %s, 'sucesso')",
                (id_, "0" * 64, escopo, federacao),
            )


@pytest.fixture
def app(lab):
    with psycopg.connect(DSN_APP, connect_timeout=3) as conexao:
        yield conexao


# ══════════════════════════════════════════════════════════════
# O papel `plataforma`: cadastro de todas, gestão de nenhuma
# ══════════════════════════════════════════════════════════════


class TestPlataforma:
    def test_ve_todas_as_federacoes(self, app):
        vistas = _rodar(app, "SELECT count(*) FROM federacao", claims=_token(PLAT))
        assert vistas[0][0] >= 27

    def test_nao_ve_ej_de_outra_federacao(self, app):
        """A exceção é estreita: o cadastro da plataforma, nunca o dado de gestão."""
        vistas = _ids(_rodar(app, "SELECT id FROM empresa_junior WHERE id >= %s", claims=_token(PLAT), params=(BASE,)))
        assert vistas == {EJ_PE}

    def test_ve_usuarios_de_todas_as_federacoes(self, app):
        vistos = _ids(_rodar(app, "SELECT id FROM usuario WHERE id >= %s", claims=_token(PLAT), params=(BASE,)))
        assert vistos == {u[0] for u in USUARIOS}

    def test_ve_a_carga_nacional(self, app):
        vistas = _ids(_rodar(app, "SELECT id FROM ingestao_carga WHERE id >= %s", claims=_token(PLAT), params=(BASE,)))
        assert vistas == {CARGA_NACIONAL, CARGA_PAR}

    def test_edita_status_e_branding(self, app):
        linhas = _rodar(
            app,
            "UPDATE federacao SET status = 'piloto', cor_primaria = '#112233' WHERE id = %s RETURNING id",
            claims=_token(PLAT),
            params=(FEJEPAR,),
        )
        assert _ids(linhas) == {FEJEPAR}

    def test_nao_edita_slug(self, app):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, "UPDATE federacao SET slug = 'x' WHERE id = %s", claims=_token(PLAT), params=(FEJEPAR,))

    def test_promove_usuario_a_admin_em_outra_federacao(self, app):
        linhas = _rodar(
            app, "UPDATE usuario SET papel = 'admin' WHERE id = %s RETURNING id",
            claims=_token(PLAT), params=(MEMB_PAR[0],),
        )
        assert _ids(linhas) == {MEMB_PAR[0]}

    def test_inativo_nao_e_plataforma(self, app):
        """`ativo = false` desliga o papel, mesmo com o token ainda dizendo `plataforma`."""
        vistas = _rodar(app, "SELECT count(*) FROM federacao", claims=_token(PLAT_INATIVO))
        assert vistas[0][0] == 1


# ══════════════════════════════════════════════════════════════
# O papel `admin`: só a própria federação
# ══════════════════════════════════════════════════════════════


class TestAdmin:
    def test_ve_so_a_propria_federacao(self, app):
        vistas = _ids(_rodar(app, "SELECT id FROM federacao", claims=_token(ADM_PE)))
        assert vistas == {FEJEPE}

    def test_nao_edita_federacao(self, app):
        assert _rodar(
            app, "UPDATE federacao SET status = 'inativa' WHERE id = %s RETURNING id",
            claims=_token(ADM_PE), params=(FEJEPE,),
        ) == []

    def test_edita_usuario_da_propria_federacao(self, app):
        linhas = _rodar(
            app, "UPDATE usuario SET nome = 'Novo nome', ativo = false WHERE id = %s RETURNING id",
            claims=_token(ADM_PE), params=(MEMB_PE[0],),
        )
        assert _ids(linhas) == {MEMB_PE[0]}

    def test_nao_alcanca_usuario_de_outra_federacao(self, app):
        assert _rodar(
            app, "UPDATE usuario SET nome = 'x' WHERE id = %s RETURNING id",
            claims=_token(ADM_PE), params=(MEMB_PAR[0],),
        ) == []

    def test_nao_alcanca_o_operador_da_propria_federacao(self, app):
        assert _rodar(
            app, "UPDATE usuario SET ativo = false WHERE id = %s RETURNING id",
            claims=_token(ADM_PE), params=(PLAT[0],),
        ) == []

    def test_nao_promove_a_plataforma(self, app):
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
            _rodar(app, "UPDATE usuario SET papel = 'plataforma' WHERE id = %s",
                   claims=_token(ADM_PE), params=(MEMB_PE[0],))

    def test_nao_move_usuario_para_outra_federacao(self, app):
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
            _rodar(app, "UPDATE usuario SET federacao_id = %s WHERE id = %s",
                   claims=_token(ADM_PE), params=(FEJEPAR, MEMB_PE[0]))

    def test_cadastra_na_propria_federacao(self, app):
        linhas = _rodar(
            app,
            "INSERT INTO usuario (federacao_id, nome, email, papel) VALUES (%s, 'Nova', 'nova@example.invalid', 'membro') RETURNING federacao_id",
            claims=_token(ADM_PE), params=(FEJEPE,),
        )
        assert linhas == [(FEJEPE,)]

    def test_nao_cadastra_em_outra_federacao(self, app):
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
            _rodar(app, "INSERT INTO usuario (federacao_id, nome, email, papel) VALUES (%s, 'X', 'x@example.invalid', 'membro')",
                   claims=_token(ADM_PE), params=(FEJEPAR,))

    def test_nao_ve_a_carga_nacional(self, app):
        vistas = _ids(_rodar(app, "SELECT id FROM ingestao_carga WHERE id >= %s", claims=_token(ADM_PAR), params=(BASE,)))
        assert vistas == {CARGA_PAR}


# ══════════════════════════════════════════════════════════════
# O que ninguém faz pelo caminho de request
# ══════════════════════════════════════════════════════════════


class TestNinguem:
    @pytest.mark.parametrize("usuario", [PLAT, ADM_PE], ids=["plataforma", "admin"])
    def test_escreve_auth_user_id(self, app, usuario):
        """Seria apontar uma linha da própria federação para a conta de outra pessoa."""
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, "UPDATE usuario SET auth_user_id = %s WHERE id = %s",
                   claims=_token(usuario), params=(_uuid(99), MEMB_PE[0]))

    @pytest.mark.parametrize("usuario", [PLAT, ADM_PE], ids=["plataforma", "admin"])
    def test_apaga_usuario(self, app, usuario):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, "DELETE FROM usuario WHERE id = %s", claims=_token(usuario), params=(MEMB_PE[0],))

    def test_membro_nao_edita_ninguem(self, app):
        assert _rodar(
            app, "UPDATE usuario SET nome = 'x' WHERE id >= %s RETURNING id",
            claims=_token(MEMB_PE), params=(BASE,),
        ) == []

    def test_vale_o_papel_do_banco_e_nao_o_do_token(self, app):
        """Membro com token forjado/antigo dizendo `admin` não escreve."""
        assert _rodar(
            app, "UPDATE usuario SET nome = 'x' WHERE id = %s RETURNING id",
            claims=_token(MEMB_PE, papel="admin"), params=(MEMB_PE[0],),
        ) == []


# ══════════════════════════════════════════════════════════════
# Último login
# ══════════════════════════════════════════════════════════════


class TestListarUsuarios:
    SQL = "SELECT id, papel, vinculado, ultimo_login FROM admin_listar_usuarios() WHERE id >= %s"

    def test_plataforma_lista_todos_com_ultimo_login(self, app):
        linhas = {linha[0]: linha for linha in _rodar(app, self.SQL, claims=_token(PLAT), params=(BASE,))}
        assert set(linhas) == {u[0] for u in USUARIOS}
        assert linhas[PLAT[0]][3] is not None
        assert linhas[MEMB_PE[0]][3] is None      # vinculado, nunca entrou
        assert linhas[MEMB_PE[0]][2] is True

    def test_admin_lista_a_propria_federacao_sem_operadores(self, app):
        vistos = _ids(_rodar(app, self.SQL, claims=_token(ADM_PE), params=(BASE,)))
        assert vistos == {ADM_PE[0], MEMB_PE[0]}

    def test_membro_nao_lista_ninguem(self, app):
        assert _rodar(app, self.SQL, claims=_token(MEMB_PE), params=(BASE,)) == []

    def test_sem_claim_nao_lista_ninguem(self, app):
        assert _rodar(app, self.SQL, claims="{}", params=(BASE,)) == []

    def test_usuario_atual_responde_so_sobre_quem_chama(self, app):
        linhas = _rodar(app, "SELECT id, papel FROM usuario_atual()", claims=_token(ADM_PAR))
        assert linhas == [(ADM_PAR[0], "admin")]


class TestMasterPlanos:
    def test_totais_incluem_inativos_e_federacao_sem_usuarios(self, lab, app):
        linhas = _rodar(app, 'SELECT id, usuarios_total, usuarios_ativos FROM public.master_resumo_federacoes()', claims=_token(PLAT))
        pe = next(l for l in linhas if l[0] == FEJEPE)
        assert pe[1] >= 4 and pe[2] >= 3 and pe[1] > pe[2]
        esperado = lab.execute('SELECT f.id, count(u.id), count(u.id) FILTER (WHERE u.ativo) FROM federacao f LEFT JOIN usuario u ON u.federacao_id = f.id GROUP BY f.id').fetchall()
        assert sorted(linhas) == sorted(esperado)
        assert any(total == 0 for _, total, _ in linhas)

    @pytest.mark.parametrize('usuario', [ADM_PE, MEMB_PE, PLAT_INATIVO])
    @pytest.mark.parametrize('sql', [
        'SELECT * FROM public.master_resumo_federacoes()',
        "SELECT * FROM public.master_salvar_plano(NULL, 'Indevido', NULL, NULL, NULL)",
        'SELECT public.master_vincular_plano(12, 1)',
        'UPDATE public.federacao SET plano_id = 1 WHERE id = 12',
    ])
    def test_nao_master_negado_mesmo_com_claim_falso(self, lab, app, usuario, sql):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _rodar(app, sql, claims=_token(usuario, papel='plataforma'))

    def test_master_cria_edita_vincula_remove_em_transacao(self, lab, app):
        try:
            app.execute("SELECT set_config('request.jwt.claims', %s, true)", (_token(PLAT),))
            plano = app.execute("SELECT id FROM public.master_salvar_plano(NULL, 'Teste master', 10, 50, 99)").fetchone()[0]
            assert app.execute("SELECT preco_mensal FROM public.master_salvar_plano(%s, 'Teste editado', NULL, 0, 149)", (plano,)).fetchone()[0] == 149
            app.execute('SELECT public.master_vincular_plano(%s, %s)', (FEJEPAR, plano))
            assert app.execute('SELECT plano_id FROM federacao WHERE id = %s', (FEJEPAR,)).fetchone()[0] == plano
            app.execute('SELECT public.master_vincular_plano(%s, NULL)', (FEJEPAR,))
            assert app.execute('SELECT plano_id FROM federacao WHERE id = %s', (FEJEPAR,)).fetchone()[0] is None
        finally:
            app.rollback()

    def test_rpc_direta_valida_limites(self, lab, app):
        with pytest.raises(psycopg.errors.CheckViolation):
            _rodar(app, "SELECT * FROM public.master_salvar_plano(NULL, 'Inválido', -1, 0, 0)", claims=_token(PLAT))

    def test_anon_sem_rpc(self, lab):
        for assinatura in ['master_resumo_federacoes()', 'master_vincular_plano(bigint,bigint)', 'master_salvar_plano(bigint,text,integer,integer,numeric)']:
            assert not lab.execute('SELECT has_function_privilege(%s, %s, %s)', ('anon', 'public.' + assinatura, 'EXECUTE')).fetchone()[0]
