"""
Escrita da ingestão: upsert idempotente, em lote, sob Row Level Security.

Só escreve — e lê o mínimo que a escrita exige: o catálogo de federações, os
núcleos já cadastrados e se o arquivo já foi carregado antes. Não valida a
planilha e não transforma valor: recebe as fatias prontas de `transform.py`.

AS TRÊS REGRAS QUE ESTE MÓDULO GARANTE

  1. Upsert por chave natural, nunca append. `id_ej` no cadastro, (id_ej, ano)
     em metas e cluster, (id_ej, ano, mes) no fato mensal. Rodar o mesmo
     arquivo duas vezes deixa o banco idêntico — e o relatório mostra isso:
     0 novas, 0 atualizadas.
  2. Correção retroativa é o caso normal. A exportação é acumulada no ano; a de
     outubro traz de novo os meses 1 a 9, possivelmente corrigidos. O mês que
     mudou é sobrescrito, sem erro de duplicidade.
  3. Não inventa linha, não apaga linha. Só grava o que veio; o que deixou de
     vir fica como estava. O papel `ingestao` nem tem DELETE (ver 10 e 11).

COMO O UPSERT É FEITO, E POR QUE NÃO É `INSERT ... ON CONFLICT`

Uma instrução por tabela por federação, com os valores em arrays (`unnest`) —
nunca linha a linha. Dentro dela, um UPDATE só das linhas que MUDARAM
(`IS DISTINCT FROM`) e um INSERT só das chaves que ainda não existem.

  * `ON CONFLICT` consome um valor da identity por linha PROPOSTA, inclusive as
    que conflitam: 13.563 ids queimados a cada carga mensal, por nada.
  * "Atualizadas" passa a contar o que mudou de verdade, e não "tudo que já
    existia". É isso que torna a idempotência e a correção retroativa visíveis
    no relatório.
  * EJ que já existe sob OUTRA federação fica invisível sob o claim da carga
    (RLS), o NOT EXISTS a trata como nova, e o INSERT esbarra na unicidade de
    `id_ej`. A carga para, nomeando a EJ: mudar EJ de federação é decisão
    humana, não efeito colateral de carga.

RLS: A CARGA NÃO PASSA POR CIMA DELA

A conexão é de um papel sujeito a RLS (`app_ingestao` no laboratório);
`verificar_papel` recusa superusuário, BYPASSRLS e dono das tabelas — que é o
equivalente local da service key. Antes de gravar a fatia de uma federação, a
carga define o claim da sessão com o `federacao_id` dela, como o PostgREST faz
por requisição. Se o filtro em Python errar e uma linha de outra federação
chegar aqui, o banco recusa.

Este módulo não abre nem fecha transação: quem chama (`importacao.py`) decide o
que é "tudo ou nada", e a simulação é a mesma carga terminando em ROLLBACK.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date

import psycopg
from psycopg import sql

from app.ingestao.transform import Fatia, Transformacao


class ErroPapel(RuntimeError):
    """A conexão usa um papel que ignora RLS. A carga se recusa a seguir."""


class ErroCarga(RuntimeError):
    """O banco recusou a carga. Nada do dado de gestão foi gravado."""

    def __init__(self, mensagem: str, carga_id: int | None = None):
        self.carga_id = carga_id
        super().__init__(mensagem)


# ── Papel e catálogo ─────────────────────────────────────────


def verificar_papel(conexao: psycopg.Connection) -> str:
    """
    Recusa conexão de papel que ignora RLS e devolve o nome do papel em uso.

    Superusuário, BYPASSRLS e dono das tabelas passam por cima de toda política
    — no laboratório, é o que a service key é no Supabase. Carga com um deles
    seria a porta dos fundos no isolamento entre federações.
    """
    linha = conexao.execute(
        """
        SELECT r.rolname, r.rolsuper, r.rolbypassrls,
               pg_has_role(current_user, c.relowner, 'USAGE')
          FROM pg_roles r, pg_class c
         WHERE r.rolname = current_user
           AND c.oid = 'public.empresa_junior'::regclass
        """
    ).fetchone()
    papel, superusuario, bypass, dono = linha
    motivos = [m for m, sim in (("superusuário", superusuario), ("BYPASSRLS", bypass), ("dono das tabelas", dono)) if sim]
    if motivos:
        raise ErroPapel(
            f"a carga não roda como {papel!r} ({', '.join(motivos)}): esse papel ignora Row Level Security, "
            "como a service key. Use um papel sujeito a RLS — no laboratório, app_ingestao "
            "(variável INGESTAO_DSN)."
        )
    return papel


@dataclass(frozen=True)
class Federacoes:
    por_nome: dict[str, int]
    por_slug: dict[str, int]
    nome_por_id: dict[int, str]


def ler_federacoes(conexao: psycopg.Connection) -> Federacoes:
    """O catálogo inteiro: a carga precisa dele para rotear e para recusar federação desconhecida."""
    linhas = conexao.execute("SELECT id, slug, nome FROM federacao").fetchall()
    return Federacoes(
        por_nome={nome: id_ for id_, _, nome in linhas},
        por_slug={slug: id_ for id_, slug, _ in linhas},
        nome_por_id={id_: nome for id_, _, nome in linhas},
    )


def definir_claim(cur: psycopg.Cursor, *, federacao_id: int | None = None, nacional: bool = False) -> None:
    """
    Claim da sessão, local à transação — o mesmo mecanismo do PostgREST.

    `federacao_id` para gravar dado de um tenant; `nacional=True` só para a
    linha de `ingestao_carga` de uma carga nacional, que não é de tenant nenhum.
    """
    if nacional == (federacao_id is not None):
        raise ValueError("informe federacao_id OU nacional=True")
    claims = {"escopo": "nacional"} if nacional else {"federacao_id": federacao_id}
    cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))


# ── Registro da carga ────────────────────────────────────────


@dataclass
class RegistroCarga:
    """O que vai para `ingestao_carga`, fora o status e o resumo."""

    arquivo_nome: str
    arquivo_hash: str
    aba: str
    ano: int
    exportado_em: date | None
    origem: str                   # 'cli' | 'upload'
    escopo: str                   # 'nacional' | 'federacao'
    federacao_id: int | None      # None ⇔ nacional
    carregado_por: int | None = None
    linhas_lidas: int | None = None
    linhas_aplicadas: int | None = None
    linhas_ignoradas: int | None = None


def _claim_da_carga(cur: psycopg.Cursor, registro: RegistroCarga) -> None:
    if registro.federacao_id is None:
        definir_claim(cur, nacional=True)
    else:
        definir_claim(cur, federacao_id=registro.federacao_id)


_SQL_INSERIR_CARGA = """
    INSERT INTO ingestao_carga (
        arquivo_nome, arquivo_hash, aba, ano, exportado_em, carregado_por, origem,
        escopo, federacao_id, status, linhas_lidas, linhas_aplicadas, linhas_ignoradas,
        mensagem_erro, reenvio_de
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
"""


def _inserir_carga(cur, registro: RegistroCarga, *, status: str, mensagem: str | None, reenvio_de: int | None) -> int:
    cur.execute(_SQL_INSERIR_CARGA, (
        registro.arquivo_nome, registro.arquivo_hash, registro.aba, registro.ano, registro.exportado_em,
        registro.carregado_por, registro.origem, registro.escopo, registro.federacao_id, status,
        registro.linhas_lidas, registro.linhas_aplicadas, registro.linhas_ignoradas, mensagem, reenvio_de,
    ))
    return cur.fetchone()[0]


def _carga_anterior_igual(cur, registro: RegistroCarga) -> int | None:
    """Carga bem-sucedida do MESMO arquivo, no MESMO escopo — é o reenvio."""
    cur.execute(
        """
        SELECT id FROM ingestao_carga
         WHERE arquivo_hash = %s AND aba = %s AND ano = %s AND escopo = %s
           AND federacao_id IS NOT DISTINCT FROM %s::bigint
           AND status = 'sucesso'
         ORDER BY id
         LIMIT 1
        """,
        (registro.arquivo_hash, registro.aba, registro.ano, registro.escopo, registro.federacao_id),
    )
    linha = cur.fetchone()
    return linha[0] if linha else None


# ── Upsert em lote ───────────────────────────────────────────


@dataclass(frozen=True)
class _Tabela:
    nome: str
    chave: tuple[tuple[str, str], ...]              # (coluna, tipo SQL)
    valores: tuple[tuple[str, str], ...]            # atualizados quando mudam
    so_na_insercao: tuple[tuple[str, str], ...] = ()  # gravados ao inserir, nunca atualizados

    @property
    def colunas(self) -> tuple[tuple[str, str], ...]:
        return self.chave + self.valores + self.so_na_insercao


# `federacao_id` só na inserção: a carga não move EJ de federação (e nem tem
# GRANT de UPDATE nessa coluna — ver 11).
EMPRESA_JUNIOR = _Tabela(
    "empresa_junior",
    chave=(("id_ej", "bigint"),),
    valores=(
        ("nome", "text"), ("cnpj", "text"), ("ano_federacao", "integer"), ("estado", "text"),
        ("cidade", "text"), ("universidade", "text"), ("curso", "text"), ("nucleo_id", "bigint"),
    ),
    so_na_insercao=(("federacao_id", "bigint"),),
)

METAS = _Tabela(
    "metas",
    chave=(("id_ej", "bigint"), ("ano", "integer")),
    valores=(
        ("meta_faturamento", "numeric"), ("meta_taxa_colaboracao", "numeric"), ("meta_csat", "numeric"),
        ("meta_projetos_impacto", "integer"), ("meta_pdi", "boolean"), ("meta_engajamento_mej", "numeric"),
    ),
)

CLUSTER_HISTORICO = _Tabela(
    "cluster_historico",
    chave=(("id_ej", "bigint"), ("ano", "integer")),
    valores=(("cluster", "integer"),),
)

MONITORAMENTO = _Tabela(
    "monitoramento",
    chave=(("id_ej", "bigint"), ("ano", "integer"), ("mes", "integer")),
    valores=(
        ("faturamento_mes", "numeric"), ("faturamento_acumulado", "numeric"),
        ("faturamento_colab_mes", "numeric"), ("faturamento_colab_acumulado", "numeric"),
        ("projetos_vendidos_mes", "integer"), ("csat", "numeric"),
        ("numero_membros", "integer"), ("membros_engajados_mes", "integer"),
    ),
)


def _sql_upsert(t: _Tabela) -> sql.Composed:
    def lista(prefixo: str | None, colunas) -> sql.Composable:
        return sql.SQL(", ").join(
            sql.Identifier(prefixo, c) if prefixo else sql.Identifier(c) for c, _ in colunas
        )

    junta = sql.SQL(" AND ").join(
        sql.SQL("{} = {}").format(sql.Identifier("t", c), sql.Identifier("e", c)) for c, _ in t.chave
    )
    return sql.SQL(
        """
        WITH entrada ({colunas}) AS (
            SELECT * FROM unnest({arrays})
        ),
        atualizadas AS (
            UPDATE {tabela} AS t
               SET {atribuicoes}
              FROM entrada AS e
             WHERE {junta}
               AND ({t_valores}) IS DISTINCT FROM ({e_valores})
            RETURNING 1
        ),
        novas AS (
            INSERT INTO {tabela} ({colunas})
            SELECT {e_colunas} FROM entrada AS e
             WHERE NOT EXISTS (SELECT 1 FROM {tabela} AS t WHERE {junta})
            RETURNING 1
        )
        SELECT (SELECT count(*) FROM novas), (SELECT count(*) FROM atualizadas)
        """
    ).format(
        tabela=sql.Identifier(t.nome),
        colunas=lista(None, t.colunas),
        e_colunas=lista("e", t.colunas),
        arrays=sql.SQL(", ").join(sql.SQL("%s::{}[]").format(sql.SQL(tipo)) for _, tipo in t.colunas),
        atribuicoes=sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(c), sql.Identifier("e", c)) for c, _ in t.valores
        ),
        junta=junta,
        t_valores=lista("t", t.valores),
        e_valores=lista("e", t.valores),
    )


@dataclass
class Contagem:
    enviadas: int = 0
    novas: int = 0
    atualizadas: int = 0

    @property
    def inalteradas(self) -> int:
        return self.enviadas - self.novas - self.atualizadas


def _upsert(cur, t: _Tabela, linhas: list[dict], contagem: Contagem) -> None:
    if not linhas:
        return
    arrays = [[linha[c] for linha in linhas] for c, _ in t.colunas]
    cur.execute(_sql_upsert(t), arrays)
    novas, atualizadas = cur.fetchone()
    contagem.enviadas += len(linhas)
    contagem.novas += novas
    contagem.atualizadas += atualizadas


def _resolver_nucleos(cur, fatia: Fatia) -> tuple[dict[str, int], list[tuple[str, int]]]:
    """
    `nucleo_id` de cada nome de núcleo da fatia; cria os que faltam.

    Os 26 núcleos de hoje estão semeados com o ID do Portal BJ (12). Um nome novo
    é cadastro legítimo, não erro — mas o id dele é gerado (a partir de 100.000)
    e não vem do Portal BJ, então volta na lista de criados para virar aviso.
    """
    if not fatia.nucleos:
        return {}, []
    nomes = sorted(fatia.nucleos)
    # O `federacao_id = %s` repete o que a RLS já faz, de propósito — mesmo
    # raciocínio de app/services/tenant.py.
    cur.execute(
        "SELECT nome, id FROM nucleo WHERE federacao_id = %s AND nome = ANY(%s::text[])",
        (fatia.federacao_id, nomes),
    )
    mapa = dict(cur.fetchall())
    faltando = [n for n in nomes if n not in mapa]
    criados: list[tuple[str, int]] = []
    if faltando:
        cur.execute(
            "INSERT INTO nucleo (federacao_id, nome) SELECT %s, n FROM unnest(%s::text[]) AS n RETURNING nome, id",
            (fatia.federacao_id, faltando),
        )
        criados = cur.fetchall()
        mapa.update(criados)
    return mapa, criados


def _gravar_staging(cur, carga_id: int, ano: int, fatia: Fatia) -> int:
    if not fatia.staging:
        return 0
    cur.execute(
        """
        INSERT INTO ingestao_staging_ej (carga_id, federacao_id, linha_arquivo, ano, linha)
        SELECT %s, %s, u.linha_arquivo, %s, u.linha::jsonb
          FROM unnest(%s::integer[], %s::text[]) AS u(linha_arquivo, linha)
        """,
        (
            carga_id, fatia.federacao_id, ano,
            [s["linha_arquivo"] for s in fatia.staging],
            # allow_nan=False: NaN não é JSON válido, e se chegar até aqui é bug do leitor.
            [json.dumps(s["linha"], ensure_ascii=False, allow_nan=False) for s in fatia.staging],
        ),
    )
    return len(fatia.staging)


@dataclass
class ResultadoCarga:
    carga_id: int
    reenvio_de: int | None
    tabelas: dict[str, Contagem] = field(default_factory=dict)
    staging_gravada: int = 0
    nucleos_criados: list[tuple[int, str, int]] = field(default_factory=list)  # (federacao_id, nome, id)


def aplicar(conexao: psycopg.Connection, transformacao: Transformacao, registro: RegistroCarga) -> ResultadoCarga:
    """
    Grava tudo o que a transformação produziu. DEVE rodar dentro de uma transação.

    Ordem: a linha de `ingestao_carga` (sob o claim da carga), e depois, para
    cada federação, sob o claim DELA: núcleos, cadastro, metas, cluster, fato
    mensal e staging.
    """
    tabelas = {t.nome: Contagem() for t in (EMPRESA_JUNIOR, METAS, CLUSTER_HISTORICO, MONITORAMENTO)}
    with conexao.cursor() as cur:
        _claim_da_carga(cur, registro)
        reenvio_de = _carga_anterior_igual(cur, registro)
        carga_id = _inserir_carga(cur, registro, status="sucesso", mensagem=None, reenvio_de=reenvio_de)
        resultado = ResultadoCarga(carga_id=carga_id, reenvio_de=reenvio_de, tabelas=tabelas)

        for federacao_id in sorted(transformacao.fatias):
            fatia = transformacao.fatias[federacao_id]
            definir_claim(cur, federacao_id=federacao_id)

            nucleos, criados = _resolver_nucleos(cur, fatia)
            resultado.nucleos_criados.extend((federacao_id, nome, id_) for nome, id_ in criados)
            empresas = [
                {**{k: v for k, v in e.items() if k != "nucleo"}, "nucleo_id": nucleos.get(e["nucleo"])}
                for e in fatia.empresas
            ]

            _upsert(cur, EMPRESA_JUNIOR, empresas, tabelas["empresa_junior"])
            _upsert(cur, METAS, fatia.metas, tabelas["metas"])
            _upsert(cur, CLUSTER_HISTORICO, fatia.clusters, tabelas["cluster_historico"])
            _upsert(cur, MONITORAMENTO, fatia.monitoramentos, tabelas["monitoramento"])

            # Reenvio do mesmo arquivo: a staging da carga original já tem
            # exatamente estas linhas. Não duplicar é o ganho 3 de 10.
            if reenvio_de is None:
                resultado.staging_gravada += _gravar_staging(cur, carga_id, transformacao.ano, fatia)

        _claim_da_carga(cur, registro)
    return resultado


def finalizar(conexao: psycopg.Connection, registro: RegistroCarga, carga_id: int, resumo: dict) -> None:
    """Grava o relatório no registro da carga. Dentro da mesma transação de `aplicar`."""
    with conexao.cursor() as cur:
        _claim_da_carga(cur, registro)
        cur.execute(
            "UPDATE ingestao_carga SET resumo = %s::jsonb WHERE id = %s",
            (json.dumps(resumo, ensure_ascii=False, default=str), carga_id),
        )


# ── Falhas ───────────────────────────────────────────────────


def registrar_falha(
    conexao: psycopg.Connection,
    registro: RegistroCarga,
    *,
    status: str,
    mensagem: str,
    fatias: list[Fatia] | None = None,
) -> int | None:
    """
    Registra uma carga que não entrou, em transação própria.

    Com `fatias`, grava também a staging — a linha que falhou fica em mãos para
    diagnóstico (ganho 4 de 10), enquanto o dado de gestão já voltou atrás
    inteiro. Se nem isso entrar, tenta ao menos o registro. Devolve o id da
    carga registrada, ou None se o banco recusou até o registro.
    """
    for com_staging in ((True, False) if fatias else (False,)):
        try:
            with conexao.transaction(), conexao.cursor() as cur:
                _claim_da_carga(cur, registro)
                carga_id = _inserir_carga(cur, registro, status=status, mensagem=mensagem, reenvio_de=None)
                if com_staging:
                    for fatia in fatias:
                        definir_claim(cur, federacao_id=fatia.federacao_id)
                        _gravar_staging(cur, carga_id, registro.ano, fatia)
                return carga_id
        except psycopg.Error:
            continue
    return None


_CHAVE_DUPLICADA = re.compile(r"Key \(id_ej\)=\((\d+)\)")


def traduzir_erro(exc: psycopg.Error) -> str:
    """Mensagem para quem roda a carga, a partir do erro do banco."""
    diag = getattr(exc, "diag", None)
    detalhe = (diag.message_detail if diag else None) or ""
    tabela = (diag.table_name if diag else None) or ""

    if isinstance(exc, psycopg.errors.UniqueViolation) and tabela == "empresa_junior":
        achado = _CHAVE_DUPLICADA.search(detalhe)
        ej = f"a EJ {achado.group(1)}" if achado else "uma EJ da planilha"
        return (
            f"{ej} já existe no banco sob OUTRA federação — a planilha a coloca numa federação diferente. "
            "Mudança de federação pede decisão humana; a carga não move EJ entre tenants. Nada foi gravado."
        )
    if isinstance(exc, psycopg.errors.InsufficientPrivilege) and "row-level security" in str(exc):
        return (
            f"o banco recusou uma escrita fora do tenant da sessão (Row Level Security): {exc}. "
            "A política segurou um erro do filtro em Python — é bug da carga, não do arquivo. Nada foi gravado."
        )
    return f"o banco recusou a carga ({type(exc).__name__}: {str(exc).strip()}). Nada foi gravado."
