"""
Testes da ingestão da planilha de EJ do Portal BJ (app/ingestao/).

A planilha é GERADA no próprio teste — 3 federações × 4 EJs × 3 meses —, nunca
a exportação real de 13 mil linhas: teste tem de rodar rápido e não depender de
arquivo fora do repositório.

Dois grupos, como em tests/test_rls.py:

    Sem banco      contrato e regras de transformação. Rodam sempre.
    Com banco      a carga de verdade, no Postgres do laboratório (`make lab`).
                   A carga conecta como `app_ingestao` — o papel sujeito a RLS
                   que ela usa em produção —, e o preparo e as conferências
                   usam o dono (`portal`), que enxerga tudo. Sem o laboratório
                   no ar, este grupo é pulado e `pytest -q` segue verde.

Os `id_ej` sintéticos ficam em 800.000–800.999: longe do dado real do Portal BJ
(hoje até ~3.700), que pode estar carregado no laboratório, e fora da faixa que
tests/test_rls.py apaga na limpeza (>= 900.000). A limpeza daqui só toca essa
faixa, os núcleos "Núcleo Teste Ingestão…" e as cargas "teste-ingestao-…".
"""

from __future__ import annotations

import json
import os

import pandas as pd
import pytest

from app.ingestao.contrato import ErroContrato
from app.ingestao.leitor import ler_planilha
from app.ingestao.transform import csat_para_gravar

psycopg = pytest.importorskip("psycopg", reason="psycopg não instalado (ver requirements.txt)")

from app.ingestao.carga import ErroCarga, ErroPapel, aplicar, RegistroCarga  # noqa: E402
from app.ingestao.importacao import Escopo, importar  # noqa: E402
from app.ingestao.transform import Fatia, Transformacao  # noqa: E402

PORTA = os.getenv("POSTGRES_PORT", "55432")
DSN_DONO = os.getenv("LAB_DSN_DONO", f"postgresql://portal:portal@localhost:{PORTA}/portal_lab")
DSN_INGESTAO = os.getenv("LAB_DSN_INGESTAO", f"postgresql://app_ingestao:app_ingestao@localhost:{PORTA}/portal_lab")
DSN_APP = os.getenv("LAB_DSN_APP", f"postgresql://app_authenticated:app_authenticated@localhost:{PORTA}/portal_lab")

ANO = 2026
BASE = 800_000
FAIXA = (BASE, BASE + 999)

# (nome em FEDERACAO, federacao.id, slug) — nomes exatamente como no seed de 02.
FEDERACOES = [("FEJEPE", 12, "fejepe"), ("FEJEPAR", 4, "fejepar"), ("FEJEMG", 7, "fejemg")]
EJS_POR_FEDERACAO = 4
MESES = (1, 2, 3)


def _id_ej(indice_federacao: int, k: int) -> int:
    return BASE + indice_federacao * 10 + k


EJ_CSAT_SEM_COLETA = _id_ej(0, 0)     # FEJEPE: CSAT 0 com coleta 0 no mês 1
EJ_CSAT_ZERO_REAL = _id_ej(0, 1)      # FEJEPE: CSAT 0 com coleta 100 no mês 1
EJ_MARINGA = _id_ej(1, 0)             # FEJEPAR, Núcleo Maringá (id 12 no seed)
EJ_NUCLEO_NOVO = _id_ej(2, 0)         # FEJEMG, núcleo que não está no seed
NUCLEO_NOVO = "Núcleo Teste Ingestão"


# ── A planilha sintética ─────────────────────────────────────


def _linhas_base() -> list[dict]:
    """3 federações × 4 EJs × 3 meses, com todas as colunas do contrato e mais algumas."""
    linhas = []
    for i, (nome_fed, _, _) in enumerate(FEDERACOES):
        for k in range(EJS_POR_FEDERACAO):
            id_ej = _id_ej(i, k)
            acumulado = 0.0
            for mes in MESES:
                faturamento = 1000.0 * (k + 1) * mes
                acumulado += faturamento
                linhas.append({
                    "ID": id_ej,
                    "EMPRESA_JUNIOR": f"EJ Teste {id_ej}",
                    "CNPJ": f"00.000.{id_ej % 1000:03d}/0001-00",
                    "FEDERACAO": nome_fed,
                    "NUCLEOS": {EJ_MARINGA: "Núcleo Maringá", EJ_NUCLEO_NOVO: NUCLEO_NOVO}.get(id_ej),
                    "E_FEDERADA": "Sim",
                    "ANO_DE_FEDERACAO": 2020,
                    "ESTADO": "PE",
                    "CIDADE": "Recife",
                    "UNIVERSIDADE": "Universidade de Teste",
                    "CURSOS": "Sistemas de Informação",
                    "MEMBROS": 20,
                    "CLUSTER_2025": 2,
                    "CLUSTER_2026": 3,
                    "META_DE_REVENUE": 120000.0,
                    "META_DE_IMPACT_PROJECTS": 1,
                    "META_DE_MEJ_ENGAGED_MEMBERS": 60.0,
                    "META_DE_COLLABORATIVE_RATE": 25.0,
                    "META_DE_LENGTH_OF_STAY": 50.0,
                    "META_DE_CSAT": 4.0,
                    "META_DE_DI_POLITICS": 1,
                    "MES": mes,
                    "FATURAMENTO": faturamento,
                    "FATURAMENTO_ACUMULADO": acumulado,
                    "FATURAMENTO_COLABORATIVO": 0.0,
                    "FATURAMENTO_COLABORATIVO_ACUMULADO": 0.0,
                    "CONTRATOS": 1,
                    "NUMERO_DE_CONTRATOS_QUE_REALIZOU_ACAO_COLABORATIVA": 1 if mes == 2 else 0,
                    "SOLUCOES": 1,
                    "CSAT": 4.5,
                    "PORCENTAGEM_DE_COLETA_CSAT": 50.0,
                    "QUANTIDADE_DE_MEMBROS_ENGAJADOS_COM_MEJ": 2,
                    # Fora do contrato: vai para a staging como veio...
                    "NPS": 10.0,
                    # ...e estas três não podem chegar a lugar nenhum.
                    "E_MAIL": "contato@example.invalid",
                    "SITE": "https://example.invalid",
                    "FACEBOOK": "https://facebook.example.invalid",
                })
    for linha in linhas:
        if linha["MES"] == 1 and linha["ID"] == EJ_CSAT_SEM_COLETA:
            linha["CSAT"], linha["PORCENTAGEM_DE_COLETA_CSAT"] = 0.0, 0.0
        if linha["MES"] == 1 and linha["ID"] == EJ_CSAT_ZERO_REAL:
            linha["CSAT"], linha["PORCENTAGEM_DE_COLETA_CSAT"] = 0.0, 100.0
    return linhas


def _gravar_xlsx(tmp_path, nome: str, linhas: list[dict], *, sem_colunas: tuple[str, ...] = ()):
    caminho = tmp_path / f"teste-ingestao-{nome}.xlsx"
    pd.DataFrame(linhas).drop(columns=list(sem_colunas)).to_excel(caminho, sheet_name="EMPRESAS_JUNIORES", index=False)
    return caminho


# ══════════════════════════════════════════════════════════════
# SEM BANCO — contrato e regras de transformação
# ══════════════════════════════════════════════════════════════


class TestContrato:
    def test_contrato_quebrado_nomeia_as_colunas_que_faltam(self, tmp_path):
        """Coluna renomeada na origem vira erro de validação nomeando a coluna — não KeyError."""
        caminho = _gravar_xlsx(tmp_path, "sem-colunas", _linhas_base(), sem_colunas=("META_DE_CSAT", "CLUSTER_2026"))
        with pytest.raises(ErroContrato) as erro:
            ler_planilha(caminho, ano=ANO)
        mensagem = str(erro.value)
        assert "faltam as colunas" in mensagem
        assert "META_DE_CSAT" in mensagem
        assert "CLUSTER_2026" in mensagem

    def test_tipo_errado_nomeia_coluna_e_linha(self, tmp_path):
        """Texto numa coluna numérica: a mensagem diz qual coluna e em que linha do Excel."""
        linhas = _linhas_base()
        linhas[4]["FATURAMENTO"] = "1.234,56"
        caminho = _gravar_xlsx(tmp_path, "tipo-errado", linhas)
        with pytest.raises(ErroContrato) as erro:
            ler_planilha(caminho, ano=ANO)
        assert "coluna FATURAMENTO" in str(erro.value)
        assert "linha 6" in str(erro.value)   # índice 4 + cabeçalho + base 1

    def test_contato_nunca_sai_do_leitor(self, tmp_path):
        """E_MAIL, SITE e FACEBOOK são descartados na leitura; coluna fora do contrato segue."""
        planilha = ler_planilha(_gravar_xlsx(tmp_path, "contato", _linhas_base()), ano=ANO)
        assert not {"E_MAIL", "SITE", "FACEBOOK"} & set(planilha.dados.columns)
        assert "NPS" in planilha.dados.columns

    def test_ano_errado_no_nome_do_arquivo_e_recusado(self, tmp_path):
        caminho = tmp_path / "monitoring_acumulated_2025_1220250921-1-abc123.xlsx"
        pd.DataFrame(_linhas_base()).to_excel(caminho, sheet_name="EMPRESAS_JUNIORES", index=False)
        with pytest.raises(ErroContrato, match="indica o ano 2025"):
            ler_planilha(caminho, ano=ANO)


class TestRegraCsat:
    """9.8: CSAT 0 sem coleta é ausência de dado; com coleta, é nota zero."""

    def test_csat_zero_sem_coleta_vira_nulo(self):
        assert csat_para_gravar(0.0, 0.0) is None

    def test_csat_zero_com_coleta_continua_zero(self):
        assert csat_para_gravar(0.0, 100.0) == 0.0

    def test_csat_positivo_passa_como_veio(self):
        assert csat_para_gravar(4.5, 0.0) == 4.5


# ══════════════════════════════════════════════════════════════
# COM BANCO — a carga de verdade, no laboratório
# ══════════════════════════════════════════════════════════════


def _limpar(conexao) -> None:
    """Remove tudo que estes testes criam, na ordem das FKs. Só a faixa sintética."""
    with conexao.cursor() as cur:
        cur.execute(
            "DELETE FROM ingestao_staging_ej WHERE carga_id IN "
            "(SELECT id FROM ingestao_carga WHERE arquivo_nome LIKE 'teste-ingestao-%')"
        )
        cur.execute("DELETE FROM ingestao_carga WHERE arquivo_nome LIKE 'teste-ingestao-%'")
        for tabela in ("monitoramento", "metas", "cluster_historico", "empresa_junior"):
            cur.execute(f"DELETE FROM {tabela} WHERE id_ej BETWEEN %s AND %s", FAIXA)
        cur.execute("DELETE FROM nucleo WHERE nome LIKE 'Núcleo Teste Ingestão%'")
    conexao.commit()


@pytest.fixture(scope="module")
def lab():
    """Conexão de dono, para preparar e conferir. Pula o grupo se o laboratório não está pronto."""
    try:
        conexao = psycopg.connect(DSN_DONO, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres do laboratório indisponível em {DSN_DONO!r}. Rode `make lab`. ({exc})")
    with conexao:
        existe = conexao.execute("SELECT to_regclass('public.ingestao_carga') IS NOT NULL").fetchone()[0]
        conexao.rollback()
        if not existe:
            pytest.skip(
                "O laboratório está sem as tabelas de ingestão (10-ingestao-staging.sql). "
                "Os scripts de init/ só rodam com o volume vazio: rode `make clean && make lab`."
            )
        _limpar(conexao)
        try:
            yield conexao
        finally:
            conexao.rollback()
            _limpar(conexao)


@pytest.fixture
def banco(lab):
    """Cada teste começa sem dado sintético — e termina sem ele."""
    _limpar(lab)
    yield lab
    lab.rollback()
    _limpar(lab)


def _importar(caminho, escopo: Escopo, **kwargs):
    """A carga como a CLI faz: papel app_ingestao, conexão em autocommit."""
    with psycopg.connect(DSN_INGESTAO, autocommit=True, connect_timeout=3) as conexao:
        return importar(conexao, caminho, ano=ANO, escopo=escopo, **kwargs)


def _consultar(conexao, consulta: str, params: tuple | None = None) -> list[tuple]:
    # Sem params, a consulta vai como está (o `%` do LIKE não precisa de escape).
    linhas = conexao.execute(consulta, params).fetchall()
    conexao.rollback()
    return linhas


def _foto(conexao) -> dict[str, list[tuple]]:
    """Estado completo das tabelas de gestão, na faixa sintética — inclusive os ids."""
    consultas = {
        "empresa_junior": "SELECT * FROM empresa_junior WHERE id_ej BETWEEN %s AND %s ORDER BY id_ej",
        "metas": "SELECT * FROM metas WHERE id_ej BETWEEN %s AND %s ORDER BY id_ej, ano",
        "cluster_historico": "SELECT * FROM cluster_historico WHERE id_ej BETWEEN %s AND %s ORDER BY id_ej, ano",
        "monitoramento": "SELECT * FROM monitoramento WHERE id_ej BETWEEN %s AND %s ORDER BY id_ej, ano, mes",
    }
    return {tabela: _consultar(conexao, sql, FAIXA) for tabela, sql in consultas.items()}


def _contar(conexao, tabela: str) -> int:
    return _consultar(conexao, f"SELECT count(*) FROM {tabela} WHERE id_ej BETWEEN %s AND %s", FAIXA)[0][0]


class TestCargaNoLaboratorio:
    """As oito garantias da fase, contra o banco de verdade."""

    def test_idempotencia_carregar_duas_vezes_deixa_o_banco_identico(self, banco, tmp_path):
        """O mais importante do conjunto: rodar de novo não muda uma linha, nem um id."""
        caminho = _gravar_xlsx(tmp_path, "base", _linhas_base())

        primeira = _importar(caminho, Escopo.nacional())
        foto_1 = _foto(banco)
        staging_1 = _consultar(banco, "SELECT count(*) FROM ingestao_staging_ej WHERE id_ej BETWEEN %s AND %s", FAIXA)

        segunda = _importar(caminho, Escopo.nacional())
        foto_2 = _foto(banco)
        staging_2 = _consultar(banco, "SELECT count(*) FROM ingestao_staging_ej WHERE id_ej BETWEEN %s AND %s", FAIXA)

        assert foto_1 == foto_2
        assert len(foto_1["monitoramento"]) == len(FEDERACOES) * EJS_POR_FEDERACAO * len(MESES)
        for tabela, contagem in segunda.tabelas.items():
            assert (contagem["novas"], contagem["atualizadas"]) == (0, 0), tabela
        # Mesmo arquivo, mesmo escopo: reconhecido pelo hash, staging não duplicada.
        assert segunda.reenvio_de == primeira.carga_id
        assert segunda.staging_gravada == 0
        assert staging_1 == staging_2

    def test_correcao_retroativa_sobrescreve_sem_duplicar(self, banco, tmp_path):
        """A exportação de outubro corrige março: o mês é sobrescrito, a contagem não muda."""
        linhas = _linhas_base()
        _importar(_gravar_xlsx(tmp_path, "setembro", linhas), Escopo.nacional())
        antes = _contar(banco, "monitoramento")

        alvo = _id_ej(0, 2)
        for linha in linhas:
            if linha["ID"] == alvo and linha["MES"] == 3:
                linha["FATURAMENTO"] = 99_999.0
        relatorio = _importar(_gravar_xlsx(tmp_path, "outubro", linhas), Escopo.nacional())

        assert _contar(banco, "monitoramento") == antes
        valor = _consultar(
            banco, "SELECT faturamento_mes FROM monitoramento WHERE id_ej = %s AND ano = %s AND mes = 3", (alvo, ANO)
        )
        assert valor == [(99_999,)]
        assert relatorio.tabelas["monitoramento"]["atualizadas"] == 1
        assert relatorio.tabelas["monitoramento"]["novas"] == 0

    def test_todas_federacoes_roteia_cada_ej_para_o_seu_tenant(self, banco, tmp_path):
        _importar(_gravar_xlsx(tmp_path, "nacional", _linhas_base()), Escopo.nacional())

        gravadas = dict(_consultar(
            banco, "SELECT id_ej, federacao_id FROM empresa_junior WHERE id_ej BETWEEN %s AND %s", FAIXA
        ))
        esperadas = {
            _id_ej(i, k): federacao_id
            for i, (_, federacao_id, _) in enumerate(FEDERACOES)
            for k in range(EJS_POR_FEDERACAO)
        }
        assert gravadas == esperadas

        # Núcleo resolvido por nome, dentro da federação: Maringá é o 12 do seed.
        nucleo = _consultar(banco, "SELECT nucleo_id FROM empresa_junior WHERE id_ej = %s", (EJ_MARINGA,))
        assert nucleo == [(12,)]

    def test_recorte_por_tenant_grava_so_a_fatia_da_federacao(self, banco, tmp_path):
        """--federacao fejepe num arquivo com 3 federações: só FEJEPE entra; o resto é contado e descartado."""
        relatorio = _importar(_gravar_xlsx(tmp_path, "recorte", _linhas_base()), Escopo.federacao("fejepe"))

        ejs = {linha[0] for linha in _consultar(
            banco, "SELECT DISTINCT federacao_id FROM empresa_junior WHERE id_ej BETWEEN %s AND %s", FAIXA
        )}
        assert ejs == {12}
        assert _contar(banco, "empresa_junior") == EJS_POR_FEDERACAO
        mon = _consultar(
            banco,
            "SELECT DISTINCT ej.federacao_id FROM monitoramento m JOIN empresa_junior ej USING (id_ej) "
            "WHERE m.id_ej BETWEEN %s AND %s",
            FAIXA,
        )
        assert mon == [(12,)]
        assert _contar(banco, "monitoramento") == EJS_POR_FEDERACAO * len(MESES)

        descartadas = 2 * EJS_POR_FEDERACAO * len(MESES)
        assert relatorio.linhas_ignoradas == descartadas
        assert relatorio.ignoradas_por_federacao == {"FEJEPAR": 12, "FEJEMG": 12}
        registro = _consultar(
            banco, "SELECT escopo, federacao_id, linhas_lidas, linhas_aplicadas, linhas_ignoradas "
                   "FROM ingestao_carga WHERE id = %s", (relatorio.carga_id,)
        )
        assert registro == [("federacao", 12, 36, 12, descartadas)]

    def test_csat_sem_coleta_grava_nulo_e_com_coleta_grava_zero(self, banco, tmp_path):
        _importar(_gravar_xlsx(tmp_path, "csat", _linhas_base()), Escopo.nacional())
        consulta = "SELECT csat FROM monitoramento WHERE id_ej = %s AND ano = %s AND mes = 1"
        assert _consultar(banco, consulta, (EJ_CSAT_SEM_COLETA, ANO)) == [(None,)]
        assert _consultar(banco, consulta, (EJ_CSAT_ZERO_REAL, ANO)) == [(0,)]

        # Na staging o dado continua como veio: 0, não nulo.
        bruto = _consultar(
            banco, "SELECT csat, linha FROM ingestao_staging_ej WHERE id_ej = %s AND mes = 1", (EJ_CSAT_SEM_COLETA,)
        )
        assert bruto[0][0] == 0
        assert not {"E_MAIL", "SITE", "FACEBOOK"} & set(bruto[0][1])
        assert bruto[0][1]["NPS"] == 10.0

    def test_contratos_colaborativos_entram_no_fato_mensal(self, banco, tmp_path):
        """O filtro de colaboração e a comparação leem este campo do fato, não da staging."""
        _importar(_gravar_xlsx(tmp_path, "colaboracao", _linhas_base()), Escopo.federacao("fejepe"))
        valores = _consultar(
            banco,
            "SELECT mes, projetos_colab_mes FROM monitoramento "
            "WHERE id_ej = %s AND ano = %s ORDER BY mes",
            (EJ_CSAT_SEM_COLETA, ANO),
        )
        assert valores == [(1, 0), (2, 1), (3, 0)]

    def test_cluster_de_anos_ausentes_e_preservado(self, banco, tmp_path):
        """Com 2022 no banco e um arquivo que só traz 2025/2026, o 2022 continua lá."""
        alvo = _id_ej(0, 3)
        with banco.cursor() as cur:
            cur.execute(
                "INSERT INTO empresa_junior (id_ej, nome, federacao_id) VALUES (%s, %s, %s)",
                (alvo, f"EJ Teste {alvo}", 12),
            )
            cur.execute("INSERT INTO cluster_historico (id_ej, ano, cluster) VALUES (%s, 2022, 4)", (alvo,))
        banco.commit()

        _importar(_gravar_xlsx(tmp_path, "cluster", _linhas_base()), Escopo.nacional())

        historico = _consultar(banco, "SELECT ano, cluster FROM cluster_historico WHERE id_ej = %s ORDER BY ano", (alvo,))
        assert historico == [(2022, 4), (2025, 2), (2026, 3)]

    def test_federacao_desconhecida_aborta_sem_gravar_nada(self, banco, tmp_path):
        linhas = _linhas_base()
        for linha in linhas:
            if linha["ID"] == _id_ej(2, 3):
                linha["FEDERACAO"] = "FEJE Inexistente"

        with pytest.raises(ErroContrato) as erro:
            _importar(_gravar_xlsx(tmp_path, "desconhecida", linhas), Escopo.nacional())

        assert "FEJE Inexistente" in str(erro.value)
        for tabela in ("empresa_junior", "metas", "cluster_historico", "monitoramento"):
            assert _contar(banco, tabela) == 0, tabela
        # A tentativa fica registrada — é para isso que existe o status 'rejeitada'.
        registro = _consultar(
            banco, "SELECT status, mensagem_erro FROM ingestao_carga WHERE arquivo_nome = %s",
            ("teste-ingestao-desconhecida.xlsx",),
        )
        assert registro[0][0] == "rejeitada"
        assert "FEJE Inexistente" in registro[0][1]


class TestGarantiasDeSeguranca:
    """O que a fase promete além das oito: RLS na escrita, papel certo, simulação real."""

    def test_simulacao_conta_de_verdade_e_nao_grava_nada(self, banco, tmp_path):
        relatorio = _importar(_gravar_xlsx(tmp_path, "simulacao", _linhas_base()), Escopo.nacional(), simular=True)

        assert relatorio.simulacao
        assert relatorio.tabelas["monitoramento"]["novas"] == 36
        assert _contar(banco, "empresa_junior") == 0
        assert _consultar(
            banco, "SELECT count(*) FROM ingestao_carga WHERE arquivo_nome LIKE 'teste-ingestao-%'"
        ) == [(0,)]

    def test_papel_que_ignora_rls_e_recusado(self, banco, tmp_path):
        """Dono das tabelas é o equivalente local da service key: a carga não roda com ele."""
        caminho = _gravar_xlsx(tmp_path, "dono", _linhas_base())
        with psycopg.connect(DSN_DONO, autocommit=True) as conexao:
            with pytest.raises(ErroPapel):
                importar(conexao, caminho, ano=ANO, escopo=Escopo.nacional())
        assert _contar(banco, "empresa_junior") == 0

    def test_rls_recusa_linha_de_outra_federacao_mesmo_se_o_filtro_falhar(self, banco):
        """
        Segunda camada: uma EJ de FEJEPAR dentro da fatia de FEJEPE (o bug que o
        recorte em Python existe para evitar) é recusada pelo banco.
        """
        fatia = Fatia(federacao_id=12, empresas=[{
            "id_ej": _id_ej(1, 3), "nome": "EJ intrusa", "cnpj": None, "ano_federacao": None,
            "estado": None, "cidade": None, "universidade": None, "curso": None,
            "federacao_id": 4, "nucleo": None,
        }])
        transformacao = Transformacao(fatias={12: fatia}, ano=ANO, ejs=1, meses=[1])
        registro = RegistroCarga(
            arquivo_nome="teste-ingestao-intrusa.xlsx", arquivo_hash="0" * 64, aba="EMPRESAS_JUNIORES",
            ano=ANO, exportado_em=None, origem="cli", escopo="federacao", federacao_id=12,
        )
        with psycopg.connect(DSN_INGESTAO, autocommit=True) as conexao:
            with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
                with conexao.transaction():
                    aplicar(conexao, transformacao, registro)
        assert _contar(banco, "empresa_junior") == 0

    def test_recorte_nao_troca_de_claim_mesmo_com_fatia_de_outra_federacao(self, banco):
        """
        O caso realista do bug: no recorte de FEJEPE, o filtro deixa passar a
        fatia INTEIRA de FEJEPAR. Se a carga trocasse o claim para o de cada
        fatia, a RLS aceitaria — cada linha estaria "no tenant certo". No
        recorte o claim é o da carga e não muda, então o banco recusa.
        """
        intrusa = _id_ej(1, 3)
        fatia = Fatia(federacao_id=4, empresas=[{
            "id_ej": intrusa, "nome": "EJ de FEJEPAR", "cnpj": None, "ano_federacao": None,
            "estado": None, "cidade": None, "universidade": None, "curso": None,
            "federacao_id": 4, "nucleo": None, "federacao_nome": "FEJEPAR",
        }])
        transformacao = Transformacao(fatias={4: fatia}, ano=ANO, ejs=1, meses=[1])
        registro = RegistroCarga(
            arquivo_nome="teste-ingestao-recorte-furado.xlsx", arquivo_hash="0" * 64, aba="EMPRESAS_JUNIORES",
            ano=ANO, exportado_em=None, origem="upload", escopo="federacao", federacao_id=12,
        )
        with psycopg.connect(DSN_INGESTAO, autocommit=True) as conexao:
            with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
                with conexao.transaction():
                    aplicar(conexao, transformacao, registro)
        assert _contar(banco, "empresa_junior") == 0

    def test_ej_de_outra_federacao_no_banco_nao_e_movida(self, banco, tmp_path):
        """A planilha põe em FEJEPE uma EJ que o banco tem em FEJEPAR: a carga para e nomeia a EJ."""
        alvo = _id_ej(0, 3)
        with banco.cursor() as cur:
            cur.execute("INSERT INTO empresa_junior (id_ej, nome, federacao_id) VALUES (%s, 'EJ de FEJEPAR', 4)", (alvo,))
        banco.commit()

        with pytest.raises(ErroCarga) as erro:
            _importar(_gravar_xlsx(tmp_path, "transferida", _linhas_base()), Escopo.nacional())

        assert str(alvo) in str(erro.value)
        assert _consultar(banco, "SELECT federacao_id FROM empresa_junior WHERE id_ej = %s", (alvo,)) == [(4,)]
        assert _contar(banco, "monitoramento") == 0
        # Registrada como erro, com a staging em mãos para diagnóstico.
        staging = _consultar(banco, "SELECT count(*) FROM ingestao_staging_ej WHERE carga_id = %s", (erro.value.carga_id,))
        assert staging == [(36,)]

    def test_carga_nacional_nao_aparece_para_federacao_nenhuma(self, banco, tmp_path):
        """ingestao_carga com federacao_id NULL é operação da plataforma; a de recorte é do tenant."""
        nacional = _importar(_gravar_xlsx(tmp_path, "vis-nacional", _linhas_base()), Escopo.nacional())
        recorte = _importar(_gravar_xlsx(tmp_path, "vis-recorte", _linhas_base()), Escopo.federacao("fejepe"))

        def visiveis(federacao_id: int) -> set[int]:
            with psycopg.connect(DSN_APP) as conexao:
                conexao.execute(
                    "SELECT set_config('request.jwt.claims', %s, true)", (json.dumps({"federacao_id": federacao_id}),)
                )
                return {linha[0] for linha in conexao.execute(
                    "SELECT id FROM ingestao_carga WHERE arquivo_nome LIKE 'teste-ingestao-%'"
                ).fetchall()}

        assert visiveis(12) == {recorte.carga_id}
        assert visiveis(4) == set()
        assert nacional.carga_id not in visiveis(12) | visiveis(4) | visiveis(7)
