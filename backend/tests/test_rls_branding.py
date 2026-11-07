"""
Testes da exceção de RLS do branding — o que `anon` pode e não pode ler.

Por que num módulo separado de tests/test_rls.py: aquele arquivo testa o
isolamento por tenant com um cenário sintético semeado (EJs, metas,
monitoramento). Este aqui não precisa de semente nenhuma — a tabela `federacao`
já vem populada pela migração 02 — e testa a regra oposta: a única leitura sem
autenticação que existe no schema inteiro.

A regra sob teste, de infra/db/init/09-federacao-branding.sql:

    `anon` lê slug, nome, logo_url e cor_primaria das federações ATIVAS.
    Nada mais, em tabela nenhuma.

Como o papel é simulado: `SET LOCAL ROLE anon` dentro da transação. É o
equivalente local do que o PostgREST faz por requisição quando não há JWT. Não
dá para abrir conexão como `anon` (o role é NOLOGIN, tanto aqui quanto no
Supabase), e o `LOCAL` garante que o rollback devolve a sessão ao dono.

Vale o mesmo aviso do test_rls.py: sem o laboratório no ar o módulo é pulado.

    make lab            # na raiz do repositório
    python -m pytest tests/test_rls_branding.py -v
"""

import os

import pytest

psycopg = pytest.importorskip(
    "psycopg",
    reason="psycopg não instalado; é dependência de teste (ver requirements.txt)",
)

PORTA = os.getenv("POSTGRES_PORT", "55432")
DSN_DONO = os.getenv("LAB_DSN_DONO", f"postgresql://portal:portal@localhost:{PORTA}/portal_lab")
DSN_APP = os.getenv("LAB_DSN_APP", f"postgresql://app_authenticated:app_authenticated@localhost:{PORTA}/portal_lab")

FEJEPE = 12

COLUNAS_DE_BRANDING = "slug, nome, logo_url, cor_primaria"


@pytest.fixture(scope="module")
def lab():
    """Conexão de dono. Pula o módulo quando o laboratório não está no ar."""
    try:
        conexao = psycopg.connect(DSN_DONO, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres do laboratório indisponível em {DSN_DONO!r}. Rode `make lab`. ({exc})")

    with conexao:
        with conexao.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'federacao' AND column_name = 'cor_primaria'"
            )
            if cur.fetchone()[0] == 0:
                pytest.skip(
                    "A migração 09-federacao-branding.sql não foi aplicada neste volume. "
                    "Os scripts de init/ só rodam com o volume vazio: `make clean && make lab`."
                )
        yield conexao


def _como_anon(conexao, sql: str, params: tuple = ()):
    """Roda a consulta como `anon` e devolve as linhas. Sempre faz rollback."""
    try:
        with conexao.cursor() as cur:
            cur.execute("SET LOCAL ROLE anon")
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conexao.rollback()


def _negado_para_anon(conexao, sql: str) -> bool:
    """Verdadeiro quando o Postgres recusa a consulta a `anon` por privilégio."""
    try:
        _como_anon(conexao, sql)
    except psycopg.errors.InsufficientPrivilege:
        return True
    return False


# ── O branding precisa ser legível sem token ─────────────────


class TestBugConditionBrandingPublico:
    """A tela de login mostra nome e logo antes de existir qualquer JWT."""

    def test_anon_le_o_branding_da_fejepe(self, lab):
        linhas = _como_anon(
            lab,
            f"SELECT {COLUNAS_DE_BRANDING} FROM federacao WHERE slug = %s",
            ("fejepe",),
        )
        assert len(linhas) == 1, "sem esta linha a tela de login fica sem marca nenhuma"

        slug, nome, logo_url, cor_primaria = linhas[0]
        assert slug == "fejepe"
        assert nome == "FEJEPE"
        assert logo_url == "/logo_fejepe.svg"
        assert cor_primaria == "#0D6EFD"

    def test_anon_le_o_slogan(self, lab):
        """Migração 14: o subtítulo do Dashboard saiu do código e virou branding."""
        linhas = _como_anon(lab, "SELECT slogan FROM federacao WHERE slug = %s", ("fejepe",))
        assert linhas == [("RNN 7 - Acreditamos e trabalhamos por uma federação de impacto.",)]

    def test_anon_enxerga_apenas_federacoes_ativas(self, lab):
        """Federação inativa ou em piloto não se anuncia."""
        with lab.cursor() as cur:
            cur.execute("SELECT count(*) FROM federacao WHERE status = 'ativa'")
            ativas = cur.fetchone()[0]
        lab.rollback()

        visiveis = _como_anon(lab, "SELECT count(*) FROM federacao")[0][0]
        assert visiveis == ativas

    def test_federacao_inativa_some_para_anon(self, lab):
        """Muda o status numa transação, confere, e desfaz."""
        try:
            with lab.cursor() as cur:
                cur.execute("UPDATE federacao SET status = 'inativa' WHERE id = %s", (FEJEPE,))
                cur.execute("SET LOCAL ROLE anon")
                cur.execute("SELECT count(*) FROM federacao WHERE slug = 'fejepe'")
                assert cur.fetchone()[0] == 0
        finally:
            lab.rollback()

        # A transação foi desfeita: a FEJEPE continua ativa e visível.
        assert len(_como_anon(lab, "SELECT slug FROM federacao WHERE slug = 'fejepe'")) == 1


# ── ...e nada além disso ─────────────────────────────────────


class TestBugConditionBrandingNaoVazaOResto:
    """A liberação é por coluna. `anon` esbarra no GRANT, não na aplicação."""

    @pytest.mark.parametrize("coluna", ["id", "uf", "status", "created_at", "updated_at"])
    def test_anon_nao_le_coluna_fora_do_branding(self, lab, coluna):
        assert _negado_para_anon(lab, f"SELECT {coluna} FROM federacao LIMIT 1")

    def test_anon_nao_le_a_tabela_inteira(self, lab):
        """`SELECT *` pede todas as colunas — e a maioria delas é negada."""
        assert _negado_para_anon(lab, "SELECT * FROM federacao LIMIT 1")

    @pytest.mark.parametrize(
        "tabela",
        ["empresa_junior", "metas", "monitoramento", "nucleo", "usuario", "plano"],
    )
    def test_anon_continua_sem_acesso_as_demais_tabelas(self, lab, tabela):
        """
        A exceção do branding é da `federacao` e só dela.

        Se este teste quebrar, alguém deu GRANT a `anon` em algum lugar — e a
        ausência proposital de GRANT descrita em 07-rls-policies.sql virou
        acidente.
        """
        assert _negado_para_anon(lab, f"SELECT count(*) FROM {tabela}")


# ── O que já existia não pode ter mudado ─────────────────────


class TestPreservacaoIsolamentoPorTenant:
    """A política nova é ADICIONAL. A de `authenticated` continua valendo."""

    @pytest.fixture(scope="class")
    def app(self):
        try:
            conexao = psycopg.connect(DSN_APP, connect_timeout=3)
        except psycopg.OperationalError as exc:
            pytest.skip(f"Role de aplicação indisponível em {DSN_APP!r}. ({exc})")
        with conexao:
            yield conexao

    def test_authenticated_sem_claim_nao_ve_federacao_nenhuma(self, app):
        """
        Token sem `federacao_id` continua vendo conjunto vazio.

        Este é o teste que pegaria o erro mais fácil de cometer aqui: abrir o
        branding para `authenticated` em vez de `anon` — o que transformaria
        a tabela de tenants num catálogo aberto a qualquer usuário logado.
        """
        try:
            with app.cursor() as cur:
                cur.execute(f"SELECT {COLUNAS_DE_BRANDING} FROM federacao")
                assert cur.fetchall() == []
        finally:
            app.rollback()

    def test_authenticated_com_claim_ve_so_a_propria(self, app):
        try:
            with app.cursor() as cur:
                cur.execute(
                    "SELECT set_config('request.jwt.claims', %s, true)",
                    ('{"federacao_id": "12"}',),
                )
                cur.execute("SELECT slug FROM federacao")
                assert [linha[0] for linha in cur.fetchall()] == ["fejepe"]
        finally:
            app.rollback()
