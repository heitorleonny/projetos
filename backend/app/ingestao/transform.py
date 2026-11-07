"""
Transformação: linha da planilha → entidades do portal.

Só transforma; não lê arquivo e não escreve no banco. Recebe o DataFrame que
`leitor.py` já validou (cada célula no tipo do contrato) e devolve, por
federação, as linhas de cada tabela com as chaves iguais às colunas do banco.
É aqui, e só aqui, que o mapeamento planilha → schema está escrito.

AS REGRAS DE TRANSFORMAÇÃO, todas conferidas contra a exportação de 21/09/2026
(docs/regras-de-negocio.md, seção 9):

  CSAT sem coleta vira NULL (9.8). CSAT = 0 com PORCENTAGEM_DE_COLETA_CSAT = 0
      é "não houve coleta", não nota zero: 9.276 das 9.280 linhas com CSAT 0.
      O portal tira a média de CSAT ignorando nulos, então gravar esses zeros
      derrubaria a média de toda federação. Qualquer outro caso grava o valor
      — inclusive CSAT 0 com coleta, que é nota zero de verdade (4 linhas).

  Zero é dado; vazio é ausência (9.7). Toda EJ tem linha em todo mês, e
  FATURAMENTO = 0 é mês sem venda. Nenhum zero vira nulo (fora o CSAT acima),
  e nenhuma linha é criada para mês que não veio.

  Acumulado é gravado como vem (9.23). FATURAMENTO_ACUMULADO vem VAZIO quando a
      soma corrida da EJ ainda é ≤ 0 (5.509 linhas em 21/09, todas nesse caso).
      Grava-se NULL — e o portal já lê NULL como 0 (`or 0` nos services), então
      o número de tela é o mesmo. Recalcular a partir dos meses mudaria número
      de tela sem ganho: a coluna bate com a soma em 1.506 de 1.507 EJs.

  Meta de engajamento em escala 0–100 (9.1). META_DE_MEJ_ENGAGED_MEMBERS vai
      de 50 a 75 (média 61,4): é percentual, não fração. Grava-se como vem. Quem
      divide por 100 (Tracking, SDE) está certo; o cluster adaptativo, que não
      divide, infla os meses 1–6 — e é corrigido em OUTRA mudança, com teste
      próprio, para que se saiba qual das duas mexeu no número da tela.

  Cluster 0 não é gravado. As faixas oficiais são 1–5; o 0 vem para EJ sem
      cluster naquele ano (75 das 82 EJs com CLUSTER_2025 = 0 foram federadas em
      2025 ou 2026). Sem linha em `cluster_historico`, "sem cluster" fica
      distinguível de "cluster 1" (9.14). O 0 continua na staging.

  SOLUCOES não vai para `projetos_totais`. É valor do mês, não total — diminui
      de um mês para o outro em 2.377 casos —, e o portal lê `projetos_totais`
      como total. Fica só na staging; a 9.3 continua em aberto.

O cadastro, as metas e o cluster se repetem nos meses de uma EJ. Vale o mês mais
recente; se algum campo divergir entre meses, sai um aviso nomeando a EJ.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.ingestao.contrato import ErroContrato

# Tolerância, em reais, para dizer que o acumulado bate com a soma dos meses.
TOLERANCIA_ACUMULADO = 0.01

CAMPOS_INVARIANTES_NO_MES = (
    "EMPRESA_JUNIOR", "CNPJ", "NUCLEOS", "ANO_DE_FEDERACAO", "ESTADO", "CIDADE",
    "UNIVERSIDADE", "CURSOS", "META_DE_REVENUE", "META_DE_IMPACT_PROJECTS",
    "META_DE_MEJ_ENGAGED_MEMBERS", "META_DE_COLLABORATIVE_RATE", "META_DE_CSAT",
    "META_DE_DI_POLITICS",
)


class ErroFederacaoDesconhecida(ErroContrato):
    """FEDERACAO traz um nome que não está na tabela `federacao`. A carga para."""

    def __init__(self, desconhecidas: dict[str, int]):
        self.desconhecidas = desconhecidas
        lista = ", ".join(f"{nome!r} ({n} linha{'s' if n > 1 else ''})" for nome, n in sorted(desconhecidas.items()))
        super().__init__([
            f"a coluna FEDERACAO traz federação que não existe na tabela federacao: {lista}. "
            "Pode ser federação nova (cadastro faltando) ou mudança de nomenclatura na origem; "
            "as duas pedem decisão humana. Nada foi gravado."
        ])


@dataclass
class Fatia:
    """Tudo o que uma carga grava para UMA federação. As chaves dos dicts são colunas do banco."""

    federacao_id: int
    nucleos: set[str] = field(default_factory=set)
    empresas: list[dict] = field(default_factory=list)       # + `nucleo` e `federacao_nome`, que a carga consome
    metas: list[dict] = field(default_factory=list)
    clusters: list[dict] = field(default_factory=list)
    monitoramentos: list[dict] = field(default_factory=list)
    staging: list[dict] = field(default_factory=list)        # {linha_arquivo, linha}


@dataclass
class DivergenciaAcumulado:
    id_ej: int
    nome: str
    federacao: str
    mes: int                        # primeiro mês em que coluna e soma divergem
    coluna: float | None            # FATURAMENTO_ACUMULADO como veio (None = vazio)
    soma: float                     # soma corrida de FATURAMENTO até esse mês
    meses_negativos: list[int]      # meses com FATURAMENTO < 0 — a causa mais comum


@dataclass
class Transformacao:
    fatias: dict[int, Fatia]
    ano: int
    ejs: int
    meses: list[int]
    csat_sem_coleta: int = 0             # CSAT 0 + coleta 0 → NULL
    csat_zero_com_coleta: int = 0        # CSAT 0 mantido: houve coleta
    cluster_zero: dict[int, int] = field(default_factory=dict)   # ano → EJs com 0 (não gravado)
    cluster_vazio: dict[int, int] = field(default_factory=dict)  # ano → EJs sem valor
    avisos: list[str] = field(default_factory=list)
    divergencias_acumulado: list[DivergenciaAcumulado] = field(default_factory=list)
    membros_constantes: int = 0          # EJs com MEMBROS igual em todos os meses


# ── Roteamento ───────────────────────────────────────────────


def rotear(dados: pd.DataFrame, federacao_por_nome: dict[str, int]) -> pd.Series:
    """
    `federacao_id` de cada linha, a partir do nome em FEDERACAO.

    A coluna FEDERACAO não é validada contra um tenant esperado: é ela que
    decide para qual tenant a linha vai. Nome que não existe em `federacao`
    aborta a carga inteira (`ErroFederacaoDesconhecida`) — nos dois modos.
    Comparação exata: "PB Júnior" não é "PB júnior".
    """
    ids = dados["FEDERACAO"].map(federacao_por_nome)
    faltando = ids.isna()
    if faltando.any():
        raise ErroFederacaoDesconhecida(dados.loc[faltando, "FEDERACAO"].value_counts().to_dict())
    return ids.astype("int64")


# ── Regras de valor ──────────────────────────────────────────


def csat_para_gravar(csat: float | None, coleta: float | None) -> float | None:
    """CSAT 0 sem coleta é ausência de dado (9.8); o resto passa como veio."""
    if csat == 0 and coleta == 0:
        return None
    return csat


def _booleano(valor: int | None) -> bool | None:
    return None if valor is None else bool(valor)


def _float(valor) -> float | None:
    return None if valor is None else float(valor)


def _int(valor) -> int | None:
    # int() explícito: numpy.int64 não é aceito nem pelo psycopg nem pelo json.
    return None if valor is None else int(valor)


# ── Transformação ────────────────────────────────────────────


def _avisos_de_divergencia(dados: pd.DataFrame, ultima: pd.DataFrame) -> list[str]:
    """Campos que deveriam ser iguais em todos os meses e não são."""
    avisos = []
    variam = {
        campo: dados.groupby("ID")[campo].nunique(dropna=False)
        for campo in CAMPOS_INVARIANTES_NO_MES
    }
    tabela = pd.DataFrame(variam)
    for id_ej, linha in tabela[(tabela > 1).any(axis=1)].iterrows():
        campos = [c for c in CAMPOS_INVARIANTES_NO_MES if linha[c] > 1]
        recente = ultima.loc[id_ej]
        detalhes = []
        for campo in campos:
            valores = sorted({str(v) for v in dados.loc[dados["ID"] == id_ej, campo]})
            detalhes.append(f"{campo} ({', '.join(valores)})")
        avisos.append(
            f"EJ {id_ej} ({recente['EMPRESA_JUNIOR']}): varia entre os meses — {'; '.join(detalhes)}; "
            f"usado o mês {recente['MES']}"
        )
    return avisos


def diagnosticar_acumulado(dados: pd.DataFrame) -> list[DivergenciaAcumulado]:
    """
    EJs em que FATURAMENTO_ACUMULADO não bate com a soma corrida de FATURAMENTO.

    Diagnóstico, não correção: a carga grava a coluna como veio. Vazio conta
    como 0 — é como o portal lê. Se esse número subir de uma exportação para
    outra, é sinal de problema na origem.
    """
    ordenado = dados.sort_values(["ID", "MES"])
    faturamento = pd.to_numeric(ordenado["FATURAMENTO"]).fillna(0.0)
    soma = faturamento.groupby(ordenado["ID"]).cumsum()
    coluna = pd.to_numeric(ordenado["FATURAMENTO_ACUMULADO"])
    diverge = (soma - coluna.fillna(0.0)).abs() > TOLERANCIA_ACUMULADO

    divergencias = []
    for id_ej, linhas in ordenado[diverge].groupby("ID", sort=True):
        primeira = linhas.iloc[0]
        todas = ordenado[ordenado["ID"] == id_ej]
        negativos = todas.loc[pd.to_numeric(todas["FATURAMENTO"]).fillna(0.0) < 0, "MES"]
        divergencias.append(DivergenciaAcumulado(
            id_ej=int(id_ej),
            nome=primeira["EMPRESA_JUNIOR"],
            federacao=primeira["FEDERACAO"],
            mes=int(primeira["MES"]),
            coluna=_float(primeira["FATURAMENTO_ACUMULADO"]),
            soma=round(float(soma.loc[primeira.name]), 2),
            meses_negativos=[int(m) for m in negativos],
        ))
    return divergencias


def transformar(
    dados: pd.DataFrame,
    federacao_ids: pd.Series,
    *,
    ano: int,
    colunas_cluster: dict[int, str],
) -> Transformacao:
    """
    Transforma as linhas JÁ RECORTADAS pelo escopo da carga.

    `federacao_ids` é o resultado de `rotear`, alinhado pelo índice. Linhas fora
    do escopo não devem chegar aqui: quem recorta é `importacao.py`.
    """
    dados = dados.assign(_federacao_id=federacao_ids.loc[dados.index])
    # As colunas validadas são `object` (int/float/str/None do Python); idxmax
    # precisa de coluna numérica.
    mes_mais_recente = dados["MES"].astype("int64").groupby(dados["ID"]).idxmax()
    ultima = dados.loc[mes_mais_recente].set_index("ID", drop=False)

    resultado = Transformacao(
        fatias={},
        ano=ano,
        ejs=int(dados["ID"].nunique()),
        meses=sorted(int(m) for m in dados["MES"].unique()),
    )

    def fatia(federacao_id: int) -> Fatia:
        return resultado.fatias.setdefault(federacao_id, Fatia(federacao_id=federacao_id))

    # ── Por EJ: cadastro, metas e cluster (vale o mês mais recente) ──
    for id_ej, r in ultima.iterrows():
        id_ej = int(id_ej)
        f = fatia(int(r["_federacao_id"]))
        if r["NUCLEOS"] is not None:
            f.nucleos.add(r["NUCLEOS"])

        f.empresas.append({
            "id_ej": id_ej,
            "nome": r["EMPRESA_JUNIOR"],
            "cnpj": r["CNPJ"],
            "ano_federacao": _int(r["ANO_DE_FEDERACAO"]),
            "estado": r["ESTADO"],
            "cidade": r["CIDADE"],
            "universidade": r["UNIVERSIDADE"],
            "curso": r["CURSOS"],
            "federacao_id": int(r["_federacao_id"]),
            # Resolvido para `nucleo_id` na carga: depende do que já está no banco.
            "nucleo": r["NUCLEOS"],
            # Só para mensagens; não é coluna de `empresa_junior`.
            "federacao_nome": r["FEDERACAO"],
        })

        # META_DE_LENGTH_OF_STAY não tem coluna em `metas`: fica só na staging.
        f.metas.append({
            "id_ej": id_ej,
            "ano": ano,
            "meta_faturamento": _float(r["META_DE_REVENUE"]),
            "meta_taxa_colaboracao": _float(r["META_DE_COLLABORATIVE_RATE"]),
            "meta_csat": _float(r["META_DE_CSAT"]),
            "meta_projetos_impacto": _int(r["META_DE_IMPACT_PROJECTS"]),
            "meta_pdi": _booleano(r["META_DE_DI_POLITICS"]),
            # Escala 0–100, como vem (9.1) — ver o cabeçalho deste módulo.
            "meta_engajamento_mej": _float(r["META_DE_MEJ_ENGAGED_MEMBERS"]),
        })

        # Só os anos que vieram no arquivo. Anos que não vieram (2022, 2023...)
        # não são tocados: a carga faz upsert, nunca "apaga e recarrega".
        for ano_cluster, coluna in colunas_cluster.items():
            valor = r[coluna]
            if valor is None:
                resultado.cluster_vazio[ano_cluster] = resultado.cluster_vazio.get(ano_cluster, 0) + 1
            elif valor == 0:
                resultado.cluster_zero[ano_cluster] = resultado.cluster_zero.get(ano_cluster, 0) + 1
            else:
                f.clusters.append({"id_ej": id_ej, "ano": ano_cluster, "cluster": _int(valor)})

    # ── Por linha: o fato mensal e a staging ──
    colunas = [c for c in dados.columns if c != "_federacao_id"]
    for linha_arquivo, r in dados.iterrows():
        f = fatia(int(r["_federacao_id"]))
        csat = csat_para_gravar(r["CSAT"], r["PORCENTAGEM_DE_COLETA_CSAT"])
        if r["CSAT"] == 0:
            if csat is None:
                resultado.csat_sem_coleta += 1
            else:
                resultado.csat_zero_com_coleta += 1

        f.monitoramentos.append({
            "id_ej": _int(r["ID"]),
            "ano": ano,
            "mes": _int(r["MES"]),
            "faturamento_mes": _float(r["FATURAMENTO"]),
            "faturamento_acumulado": _float(r["FATURAMENTO_ACUMULADO"]),        # vazio ⇒ NULL (9.23)
            "faturamento_colab_mes": _float(r["FATURAMENTO_COLABORATIVO"]),
            "faturamento_colab_acumulado": _float(r["FATURAMENTO_COLABORATIVO_ACUMULADO"]),
            "projetos_vendidos_mes": _int(r["CONTRATOS"]),
            "projetos_colab_mes": _int(r["NUMERO_DE_CONTRATOS_QUE_REALIZOU_ACAO_COLABORATIVA"]),
            "csat": _float(csat),
            # MEMBROS é o mesmo em todos os meses da EJ: é a foto do cadastro no
            # dia da exportação, repetida — não o número de membros daquele mês.
            "numero_membros": _int(r["MEMBROS"]),
            "membros_engajados_mes": _int(r["QUANTIDADE_DE_MEMBROS_ENGAJADOS_COM_MEJ"]),
        })

        # A linha como veio: sem transformação nenhuma (CSAT 0 continua 0).
        f.staging.append({"linha_arquivo": int(linha_arquivo), "linha": {c: r[c] for c in colunas}})

    resultado.avisos = _avisos_de_divergencia(dados, ultima)
    resultado.divergencias_acumulado = diagnosticar_acumulado(dados)
    membros = dados.groupby("ID")["MEMBROS"].nunique(dropna=False)
    resultado.membros_constantes = int((membros == 1).sum())
    return resultado
