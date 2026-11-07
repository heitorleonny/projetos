"""
Testes de Row Level Security — isolamento entre federações no banco.

Diferente do resto da suíte, estes testes NÃO usam mock: eles falam SQL direto
com o Postgres do laboratório (`make lab`), porque RLS é comportamento do banco
e mock nenhum consegue verificá-lo.

Dois detalhes que fazem o teste valer alguma coisa:

1. A conexão é aberta como `app_authenticated`, um role de login comum criado em
   `infra/db/init/00-shim-auth-local.sql`. NÃO como `portal`, que é dono das
   tabelas e superusuário — e para quem a RLS simplesmente não se aplica.
   Conectando como dono, todo teste aqui passaria mesmo com política errada ou
   com política nenhuma.

2. O claim do JWT é simulado com `set_config('request.jwt.claims', ..., true)`,
   que é o equivalente parametrizável do `SET LOCAL request.jwt.claims` — é
   exatamente o que o PostgREST faz por requisição em produção. O `true` final
   deixa o valor local à transação: cada consulta começa limpa.

Organização, no mesmo padrão de tests/test_seguranca.py:

    TestBugCondition*   comportamento novo que precisa passar a funcionar
                        (isolamento por tenant, claim ausente não vaza nada).
    TestPreservacao*    comportamento antigo que não pode quebrar
                        (carga/migração continuam enxergando tudo, catálogo
                        segue legível, colunas preservadas seguem lá).

Sem o laboratório no ar, o módulo inteiro é pulado — `pytest -q` continua verde
para quem não subiu o Docker. Para rodar de verdade:

    make lab            # na raiz do repositório
    python -m pytest tests/test_rls.py -v
"""

import json
import os

import pytest

psycopg = pytest.importorskip(
    "psycopg",
    reason="psycopg não instalado; é dependência de teste (ver requirements.txt)",
)

# Credenciais do laboratório local. Não são segredo: são os defaults públicos do
# `docker-compose.yml` (perfil `lab`), de um Postgres que não guarda dado real.
# Nenhuma credencial do Supabase entra aqui — estes testes não tocam a nuvem.
# A porta é 55432, não 5432: um Postgres instalado na máquina (Homebrew,
# Postgres.app) ocupa a 5432 e, por ligar em 127.0.0.1 especificamente, vence o
# bind coringa do container — a conexão iria para o banco errado.
PORTA = os.getenv("POSTGRES_PORT", "55432")
DSN_DONO = os.getenv("LAB_DSN_DONO", f"postgresql://portal:portal@localhost:{PORTA}/portal_lab")
DSN_APP = os.getenv("LAB_DSN_APP", f"postgresql://app_authenticated:app_authenticated@localhost:{PORTA}/portal_lab")

# Tenants usados nos cenários: FEJEPE é a federação de hoje; FEJEPAR é a segunda
# já escolhida para o projeto, e a que tem núcleo real (Núcleo Maringá).
FEJEPE = 12
FEJEPAR = 4

# IDs sintéticos numa faixa alta, para não colidir com dado real que venha a ser
# carregado no laboratório e para que a limpeza (`WHERE id >= 900000`) seja segura.
BASE = 900_000
EJ_PE = BASE + 12          # EJ de FEJEPE
EJ_PAR = BASE + 4          # EJ de FEJEPAR
NUCLEO_PAR = BASE + 1      # núcleo de FEJEPAR
META_EJ_PE = BASE + 112
META_EJ_PAR = BASE + 104
META_NUCLEO_PAR = BASE + 204   # meta pendurada no NÚCLEO, não na EJ
META_FED_PAR = BASE + 304      # meta pendurada na FEDERAÇÃO, direto
MON_EJ_PE = BASE + 112
MON_EJ_PAR = BASE + 104
MON_NUCLEO_PAR = BASE + 204

TABELAS_DE_TENANT = [
    "empresa_junior",
    "metas",
    "monitoramento",
    "nucleo",
    "federacao",
    "usuario",
    "cluster_historico",
]


# ── Infraestrutura dos testes ────────────────────────────────


def _claims(**campos) -> str:
    """Monta o JSON de claims que o PostgREST injetaria na sessão."""
    return json.dumps(campos)


def _consultar(conexao, sql: str, *, claims: str | None = None, params: tuple = ()):
    """
    Roda uma consulta com (ou sem) claim de JWT e devolve as linhas.

    `claims=None` simula token sem claim nenhum: o `set_config` nem é chamado.
    O rollback no fim encerra a transação e, com ela, o claim local.
    """
    with conexao.cursor() as cur:
        if claims is not None:
            cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (claims,))
        cur.execute(sql, params)
        linhas = cur.fetchall()
    conexao.rollback()
    return linhas


def _ids(linhas) -> set:
    """Extrai a primeira coluna de cada linha como conjunto."""
    return {linha[0] for linha in linhas}


@pytest.fixture(scope="module")
def lab():
    """
    Conexão de dono: semeia os dados sintéticos e limpa no fim.

    Pula o módulo inteiro (em vez de falhar) quando o laboratório não está no ar
    ou quando o volume ainda está no schema antigo, sem as migrações 03-07.
    """
    try:
        conexao = psycopg.connect(DSN_DONO, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres do laboratório indisponível em {DSN_DONO!r}. Rode `make lab`. ({exc})")

    with conexao:
        with conexao.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'empresa_junior' AND column_name = 'federacao_id'"
            )
            if cur.fetchone()[0] == 0:
                pytest.skip(
                    "O laboratório está com o schema antigo (sem `empresa_junior.federacao_id`). "
                    "Os scripts de init/ só rodam com o volume vazio: rode `make clean && make lab`."
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
    """Remove tudo que estes testes criam. Na ordem das FKs."""
    with conexao.cursor() as cur:
        cur.execute("DELETE FROM cluster_historico WHERE id_ej >= %s", (BASE,))
        cur.execute("DELETE FROM monitoramento WHERE id >= %s", (BASE,))
        cur.execute("DELETE FROM metas WHERE id >= %s", (BASE,))
        cur.execute("DELETE FROM empresa_junior WHERE id >= %s", (BASE,))
        cur.execute("DELETE FROM usuario WHERE id >= %s", (BASE,))
        cur.execute("DELETE FROM nucleo WHERE id >= %s", (BASE,))


def _semear(conexao) -> None:
    """
    Cenário mínimo que exercita os três caminhos até o tenant.

    Uma EJ em cada federação, um núcleo em FEJEPAR, e fatos pendurados em cada
    um dos três níveis (EJ, núcleo, federação).
    """
    with conexao.cursor() as cur:
        cur.execute(
            "INSERT INTO nucleo (id, federacao_id, nome) VALUES (%s, %s, %s)",
            (NUCLEO_PAR, FEJEPAR, "Núcleo sintético de teste"),
        )
        cur.executemany(
            "INSERT INTO empresa_junior (id, id_ej, nome, federacao_id, nucleo_id) "
            "VALUES (%s, %s, %s, %s, %s)",
            [
                (EJ_PE, EJ_PE, "EJ sintética de FEJEPE", FEJEPE, None),
                (EJ_PAR, EJ_PAR, "EJ sintética de FEJEPAR", FEJEPAR, NUCLEO_PAR),
            ],
        )
        cur.executemany(
            "INSERT INTO metas (id, id_ej, id_nucleo, id_federacao, ano, meta_faturamento) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            [
                (META_EJ_PE, EJ_PE, None, None, 2026, 120_000),
                (META_EJ_PAR, EJ_PAR, None, None, 2026, 300_000),
                (META_NUCLEO_PAR, None, NUCLEO_PAR, None, 2026, 900_000),
                (META_FED_PAR, None, None, FEJEPAR, 2026, 5_000_000),
            ],
        )
        cur.executemany(
            "INSERT INTO monitoramento (id, id_ej, id_nucleo, ano, mes, faturamento_mes) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            [
                (MON_EJ_PE, EJ_PE, None, 2026, 1, 10_000),
                (MON_EJ_PAR, EJ_PAR, None, 2026, 1, 25_000),
                (MON_NUCLEO_PAR, None, NUCLEO_PAR, 2026, 1, 80_000),
            ],
        )
        cur.executemany(
            "INSERT INTO cluster_historico (id_ej, ano, cluster) VALUES (%s, %s, %s)",
            [
                (EJ_PE, 2026, 3),
                (EJ_PAR, 2026, 5),
            ],
        )
        cur.executemany(
            "INSERT INTO usuario (id, federacao_id, nome, email, papel) VALUES (%s, %s, %s, %s, %s)",
            [
                (BASE + 12, FEJEPE, "Usuária de teste PE", "teste-pe@example.invalid", "admin"),
                (BASE + 4, FEJEPAR, "Usuário de teste PR", "teste-pr@example.invalid", "membro"),
            ],
        )


@pytest.fixture
def app_conexao(lab):
    """Conexão como `app_authenticated` — o role sujeito às políticas."""
    with psycopg.connect(DSN_APP, connect_timeout=3) as conexao:
        yield conexao


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 1: cada tenant só enxerga as próprias linhas
# ══════════════════════════════════════════════════════════════


class TestBugConditionIsolamentoEntreTenants:
    """Property 1 — o claim `federacao_id` delimita tudo o que a sessão enxerga."""

    def test_empresa_junior_so_do_proprio_tenant(self, app_conexao):
        """A EJ da outra federação não aparece, nos dois sentidos."""
        vistas_pe = _ids(_consultar(
            app_conexao,
            "SELECT id FROM empresa_junior WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE)),
            params=(BASE,),
        ))
        vistas_par = _ids(_consultar(
            app_conexao,
            "SELECT id FROM empresa_junior WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPAR)),
            params=(BASE,),
        ))
        assert vistas_pe == {EJ_PE}, "FEJEPE enxergou EJ que não é dela"
        assert vistas_par == {EJ_PAR}, "FEJEPAR enxergou EJ que não é dela"

    def test_metas_seguem_o_tenant_da_ej(self, app_conexao):
        """Meta pendurada em EJ só aparece para a federação daquela EJ."""
        vistas_pe = _ids(_consultar(
            app_conexao,
            "SELECT id FROM metas WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE)),
            params=(BASE,),
        ))
        assert vistas_pe == {META_EJ_PE}
        assert META_EJ_PAR not in vistas_pe

    def test_monitoramento_segue_o_tenant_da_ej(self, app_conexao):
        """Idem para a série mensal — é a tabela com mais linha por EJ."""
        vistos_pe = _ids(_consultar(
            app_conexao,
            "SELECT id FROM monitoramento WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE)),
            params=(BASE,),
        ))
        assert vistos_pe == {MON_EJ_PE}

    def test_meta_via_nucleo_so_para_a_federacao_do_nucleo(self, app_conexao):
        """
        O caminho via NÚCLEO, testado sozinho.

        `META_NUCLEO_PAR` tem `id_ej` NULL: só chega ao tenant pelo JOIN em
        `nucleo`. Se a política tivesse só o ramo do `id_ej`, esta linha
        sumiria para todo mundo — e o bug passaria despercebido, porque
        "sumir" parece seguro.
        """
        vistas_par = _ids(_consultar(
            app_conexao,
            "SELECT id FROM metas WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPAR)),
            params=(BASE,),
        ))
        vistas_pe = _ids(_consultar(
            app_conexao,
            "SELECT id FROM metas WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE)),
            params=(BASE,),
        ))
        assert META_NUCLEO_PAR in vistas_par, "meta de núcleo não chegou à federação dona do núcleo"
        assert META_NUCLEO_PAR not in vistas_pe, "meta de núcleo vazou para outra federação"

    def test_monitoramento_via_nucleo_so_para_a_federacao_do_nucleo(self, app_conexao):
        """Mesmo caminho, na tabela mensal."""
        vistos_par = _ids(_consultar(
            app_conexao,
            "SELECT id FROM monitoramento WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPAR)),
            params=(BASE,),
        ))
        vistos_pe = _ids(_consultar(
            app_conexao,
            "SELECT id FROM monitoramento WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE)),
            params=(BASE,),
        ))
        assert MON_NUCLEO_PAR in vistos_par
        assert MON_NUCLEO_PAR not in vistos_pe

    def test_meta_via_federacao_direta(self, app_conexao):
        """O terceiro caminho: linha pendurada direto na federação."""
        vistas_par = _ids(_consultar(
            app_conexao,
            "SELECT id FROM metas WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPAR)),
            params=(BASE,),
        ))
        vistas_pe = _ids(_consultar(
            app_conexao,
            "SELECT id FROM metas WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE)),
            params=(BASE,),
        ))
        assert META_FED_PAR in vistas_par
        assert META_FED_PAR not in vistas_pe

    def test_os_tres_caminhos_juntos(self, app_conexao):
        """FEJEPAR enxerga exatamente as suas três metas, uma de cada nível."""
        vistas_par = _ids(_consultar(
            app_conexao,
            "SELECT id FROM metas WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPAR)),
            params=(BASE,),
        ))
        assert vistas_par == {META_EJ_PAR, META_NUCLEO_PAR, META_FED_PAR}

    def test_nucleo_so_da_propria_federacao(self, app_conexao):
        vistos_pe = _ids(_consultar(
            app_conexao,
            "SELECT id FROM nucleo WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE)),
            params=(BASE,),
        ))
        vistos_par = _ids(_consultar(
            app_conexao,
            "SELECT id FROM nucleo WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPAR)),
            params=(BASE,),
        ))
        assert vistos_pe == set()
        assert vistos_par == {NUCLEO_PAR}

    def test_usuario_so_da_propria_federacao(self, app_conexao):
        """Dado de usuário (inclui e-mail) não atravessa tenant."""
        vistos_pe = _ids(_consultar(
            app_conexao,
            "SELECT id FROM usuario WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE)),
            params=(BASE,),
        ))
        assert vistos_pe == {BASE + FEJEPE}

    def test_federacao_so_enxerga_a_si_mesma(self, app_conexao):
        """Das 27 federações do seed, a sessão vê uma: a sua."""
        vistas = _ids(_consultar(
            app_conexao,
            "SELECT id FROM federacao",
            claims=_claims(federacao_id=str(FEJEPE)),
        ))
        assert vistas == {FEJEPE}

    def test_claim_numerico_tambem_funciona(self, app_conexao):
        """
        O claim pode chegar como número JSON, não só como string — depende de
        como o hook escreveu. `->>` devolve texto nos dois casos.
        """
        vistas = _ids(_consultar(
            app_conexao,
            "SELECT id FROM empresa_junior WHERE id >= %s",
            claims=_claims(federacao_id=FEJEPE),  # inteiro, sem aspas no JSON
            params=(BASE,),
        ))
        assert vistas == {EJ_PE}


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 2: sem tenant no token, conjunto vazio
# O requisito mais importante desta fase.
# ══════════════════════════════════════════════════════════════


class TestBugConditionClaimAusente:
    """
    Property 2 — nenhum claim de tenant ⇒ nenhuma linha. Nunca a tabela inteira.

    O modo de falha que isto persegue é o pior possível: uma política mal escrita
    (por exemplo com `USING (true)` de rascunho, ou comparando com uma coluna que
    é NULL dos dois lados) devolve a base inteira para quem não provou nada.
    """

    @pytest.mark.parametrize("tabela", TABELAS_DE_TENANT)
    def test_sem_nenhum_claim_na_sessao(self, app_conexao, tabela):
        """Nem `set_config` é chamado: é o estado de uma conexão crua."""
        linhas = _consultar(app_conexao, f"SELECT count(*) FROM {tabela}")
        assert linhas[0][0] == 0, f"{tabela} devolveu linhas sem claim nenhum"

    @pytest.mark.parametrize("tabela", TABELAS_DE_TENANT)
    def test_claim_string_vazia(self, app_conexao, tabela):
        """`request.jwt.claims` setado como string vazia."""
        linhas = _consultar(app_conexao, f"SELECT count(*) FROM {tabela}", claims="")
        assert linhas[0][0] == 0, f"{tabela} devolveu linhas com claims vazio"

    @pytest.mark.parametrize("tabela", TABELAS_DE_TENANT)
    def test_claim_sem_federacao_id(self, app_conexao, tabela):
        """Token legítimo de um usuário sem vínculo: tem `sub`, não tem tenant."""
        claims = _claims(sub="00000000-0000-0000-0000-000000000001", role="authenticated")
        linhas = _consultar(app_conexao, f"SELECT count(*) FROM {tabela}", claims=claims)
        assert linhas[0][0] == 0, f"{tabela} devolveu linhas para token sem federacao_id"

    @pytest.mark.parametrize("tabela", TABELAS_DE_TENANT)
    def test_claim_com_federacao_id_vazio_ou_nulo(self, app_conexao, tabela):
        """`federacao_id` presente mas vazio, e presente mas null."""
        for claims in (_claims(federacao_id=""), _claims(federacao_id=None)):
            linhas = _consultar(app_conexao, f"SELECT count(*) FROM {tabela}", claims=claims)
            assert linhas[0][0] == 0, f"{tabela} devolveu linhas com claims={claims}"

    def test_claim_de_federacao_inexistente_nao_ve_nada(self, app_conexao):
        """Um id que não existe em `federacao` não é um curinga."""
        linhas = _consultar(
            app_conexao,
            "SELECT count(*) FROM empresa_junior",
            claims=_claims(federacao_id="999999"),
        )
        assert linhas[0][0] == 0

    def test_claim_nao_numerico_falha_fechado(self, app_conexao):
        """
        `federacao_id` com lixo não-numérico: o cast estoura e a query morre.

        Falhar alto é aceitável aqui — o que não pode acontecer é devolver
        linha. O teste aceita os dois desfechos seguros (erro ou vazio) e
        rejeita só o inseguro.
        """
        try:
            linhas = _consultar(
                app_conexao,
                "SELECT count(*) FROM empresa_junior",
                claims=_claims(federacao_id="' OR 1=1 --"),
            )
        except psycopg.errors.InvalidTextRepresentation:
            app_conexao.rollback()
        else:
            assert linhas[0][0] == 0, "claim malformado devolveu linhas"


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 3: papel não amplia tenant
# ══════════════════════════════════════════════════════════════


class TestBugConditionPapelNaoAmpliaTenant:
    """
    Property 3 — `papel` é ortogonal ao tenant.

    Ser admin dá mais verbos dentro da própria federação, nunca alcance em outra.
    A política de RLS sequer lê `papel`: o isolamento acontece antes, e é isso
    que este teste fixa.
    """

    @pytest.mark.parametrize("papel", ["admin", "membro"])
    def test_nenhum_papel_alcanca_outro_tenant(self, app_conexao, papel):
        vistas = _ids(_consultar(
            app_conexao,
            "SELECT id FROM empresa_junior WHERE id >= %s",
            claims=_claims(federacao_id=str(FEJEPE), papel=papel),
            params=(BASE,),
        ))
        assert EJ_PAR not in vistas, f"papel {papel!r} alcançou a EJ de outra federação"
        assert vistas == {EJ_PE}

    def test_admin_e_membro_enxergam_o_mesmo_conjunto(self, app_conexao):
        """Hoje o papel não muda uma linha do que é LIDO. Se mudar, foi acidente."""
        def visiveis(papel):
            return _ids(_consultar(
                app_conexao,
                "SELECT id FROM metas WHERE id >= %s",
                claims=_claims(federacao_id=str(FEJEPAR), papel=papel),
                params=(BASE,),
            ))

        assert visiveis("admin") == visiveis("membro")


# ══════════════════════════════════════════════════════════════
# PRESERVAÇÃO — o que não pode ter quebrado
# ══════════════════════════════════════════════════════════════


class TestPreservacaoLaboratorio:
    """Property 4 — ligar RLS não pode atrapalhar migração, carga nem catálogo."""

    def test_dono_continua_enxergando_tudo(self, lab):
        """
        RLS não se aplica ao dono: é o que mantém `\\copy`, migração e a
        modelagem do TCC funcionando sobre a base inteira.
        """
        with lab.cursor() as cur:
            cur.execute("SELECT count(*) FROM empresa_junior WHERE id >= %s", (BASE,))
            assert cur.fetchone()[0] == 2
        lab.rollback()

    def test_seed_das_27_federacoes_intacto(self, lab):
        with lab.cursor() as cur:
            cur.execute("SELECT count(*) FROM federacao")
            assert cur.fetchone()[0] == 27
        lab.rollback()

    def test_catalogo_de_planos_visivel_para_qualquer_tenant(self, app_conexao):
        """`plano` tem RLS ligada, mas é catálogo: não filtra por tenant."""
        for federacao_id in (FEJEPE, FEJEPAR):
            linhas = _consultar(
                app_conexao,
                "SELECT count(*) FROM plano",
                claims=_claims(federacao_id=str(federacao_id)),
            )
            assert linhas[0][0] >= 1

    def test_todas_as_tabelas_tem_rls_ligada(self, lab):
        """Defesa em profundidade: nenhuma tabela do schema fica de fora."""
        with lab.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND NOT rowsecurity ORDER BY tablename"
            )
            sem_rls = [linha[0] for linha in cur.fetchall()]
        lab.rollback()
        assert sem_rls == [], f"tabelas sem RLS: {sem_rls}"

    def test_colunas_de_cluster_viraram_legado(self, lab):
        """
        `cluster_2023..cluster_2026` foram normalizadas em `cluster_historico`
        (migração 08). As colunas antigas continuam existindo com sufixo
        `_legado` — renomeadas, não apagadas, como `federacao_legado`.

        Este teste era o inverso disto enquanto o destino das colunas estava em
        aberto. A decisão foi tomada; o teste acompanha o schema.
        """
        with lab.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'empresa_junior' AND column_name LIKE 'cluster%' "
                "ORDER BY column_name"
            )
            colunas = [linha[0] for linha in cur.fetchall()]
            cur.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_name = 'cluster_historico'"
            )
            existe_historico = cur.fetchone()[0]
        lab.rollback()
        assert colunas == [
            "cluster_2023_legado",
            "cluster_2024_legado",
            "cluster_2025_legado",
            "cluster_2026_legado",
            "cluster_legado",
        ]
        assert existe_historico == 1, "cluster_historico não foi criada"

    def test_federacao_legado_preservada(self, lab):
        """A coluna de texto antiga foi renomeada, não apagada."""
        with lab.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'empresa_junior' AND column_name = 'federacao_legado'"
            )
            assert cur.fetchone()[0] == 1
        lab.rollback()

    def test_tabelas_originais_nao_foram_renomeadas(self, lab):
        """`metas` continua `metas`, `monitoramento` continua `monitoramento`."""
        with lab.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            )
            tabelas = [linha[0] for linha in cur.fetchall()]
        lab.rollback()
        for esperada in ("empresa_junior", "metas", "monitoramento"):
            assert esperada in tabelas

    def test_conta_principal_e_unica_por_federacao(self, lab):
        """O índice único parcial de `usuario` é garantia de banco, não de app."""
        with lab.cursor() as cur:
            cur.execute(
                "INSERT INTO usuario (id, federacao_id, nome, email, papel, conta_principal) "
                "VALUES (%s, %s, %s, %s, %s, true)",
                (BASE + 900, FEJEPE, "Principal 1", "principal1@example.invalid", "admin"),
            )
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute(
                    "INSERT INTO usuario (id, federacao_id, nome, email, papel, conta_principal) "
                    "VALUES (%s, %s, %s, %s, %s, true)",
                    (BASE + 901, FEJEPE, "Principal 2", "principal2@example.invalid", "admin"),
                )
        lab.rollback()

    def test_check_de_tenant_exclusivo_rejeita_dois_niveis(self, lab):
        """`num_nonnulls(...) = 1`: nem zero, nem dois."""
        with lab.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO metas (id, id_ej, id_federacao, ano) VALUES (%s, %s, %s, %s)",
                    (BASE + 902, EJ_PE, FEJEPE, 2026),
                )
        lab.rollback()
        with lab.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO metas (id, ano) VALUES (%s, %s)",
                    (BASE + 903, 2026),
                )
        lab.rollback()
