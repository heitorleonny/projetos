"""
Leitura da planilha: .xlsx → DataFrame validado contra o contrato.

Só lê e valida. Não conhece o schema do banco, não resolve federação, não
transforma valor — CSAT 0 sai daqui como 0, acumulado vazio sai como `None`.
As regras de transformação moram em `transform.py`; as de escrita, em `carga.py`.

O que "validado" garante a quem recebe o DataFrame:

    * todas as colunas do contrato existem (senão: "faltam as colunas: ...");
    * cada célula dessas colunas tem o tipo declarado, já convertida para
      `int`, `float`, `str` ou `None` do Python — nunca `NaN`, nunca `numpy.int64`;
    * célula vazia só onde o contrato aceita vazio;
    * valores de domínio fechado (MES, cluster, META_DE_DI_POLITICS) dentro do
      domínio;
    * cada (ID, MES) aparece uma vez, e cada ID pertence a uma federação só.

Todos os problemas encontrados vão numa única `ErroContrato`, com a linha do
Excel de cada exemplo. Consertar um arquivo de 13 mil linhas um erro por vez,
rodando a carga de novo a cada um, é o tipo de atrito que faz alguém desistir
da validação.

As colunas fora do contrato seguem no DataFrame como vieram (sem validação):
vão para a staging em jsonb. E_MAIL, SITE e FACEBOOK saem aqui, antes de tudo.
"""

from __future__ import annotations

import hashlib
import math
import numbers
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from app.ingestao.contrato import (
    ABA_PADRAO,
    COLUNAS_DESCARTADAS,
    Coluna,
    ErroContrato,
    Tipo,
    colunas_de_cluster,
    colunas_obrigatorias,
    verificar_cabecalho,
)

# Quantos exemplos de valor inválido citar por coluna na mensagem de erro.
EXEMPLOS_POR_PROBLEMA = 5

# O Excel numera a partir de 1 e o cabeçalho ocupa a linha 1: o primeiro dado
# está na linha 2. É o número que aparece na tela de quem abre o arquivo.
PRIMEIRA_LINHA_DE_DADOS = 2


@dataclass
class Planilha:
    """Planilha lida e validada, pronta para a transformação."""

    arquivo_nome: str
    arquivo_hash: str            # SHA-256 do arquivo, em hexadecimal
    aba: str
    ano: int                     # informado de fora (--ano): a planilha não tem coluna de ano
    exportado_em: date | None    # derivado do nome do arquivo, quando dá
    dados: pd.DataFrame          # índice = linha no Excel
    colunas_cluster: dict[int, str]  # ano → nome da coluna (CLUSTER_2025, ...)


# ── Metadados que vêm do arquivo, não do conteúdo ────────────


def hash_arquivo(caminho: str | Path) -> str:
    """SHA-256 do arquivo inteiro — é o que detecta reenvio do mesmo arquivo."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# O Portal BJ nomeia as exportações como
#   monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx
#                        ^^^^ ^^^^^^^^^^
#                        ano  mm + AAAAMMDD da exportação
# Os 8 dígitos colados no primeiro hífen são a data da exportação; "_2026_12"
# é o período pedido (ano 2026, até o mês 12).
_DATA_NO_NOME = re.compile(r"(\d{4})(\d{2})(\d{2})-\d+-[0-9A-Za-z]+\.xlsx$")
_ANO_NO_NOME = re.compile(r"_(20\d{2})_\d{2}")


def data_exportacao_do_nome(nome: str) -> date | None:
    """Data de exportação embutida no nome do arquivo, ou `None` se não houver."""
    achado = _DATA_NO_NOME.search(nome)
    if not achado:
        return None
    try:
        return date(*(int(parte) for parte in achado.groups()))
    except ValueError:
        return None


def ano_do_nome(nome: str) -> int | None:
    """Ano de referência embutido no nome ("_2026_12"), ou `None`."""
    achado = _ANO_NO_NOME.search(nome)
    return int(achado.group(1)) if achado else None


# ── Conversão célula a célula ────────────────────────────────


class _Invalido:
    """Marca de célula que não converte para o tipo declarado."""


INVALIDO = _Invalido()


def eh_vazio(valor) -> bool:
    """None, NaN, NaT e texto em branco contam como vazio."""
    if valor is None:
        return True
    if isinstance(valor, str):
        return valor.strip() == ""
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _converter(valor, tipo: Tipo):
    """Converte uma célula já não vazia para o tipo do contrato, ou `INVALIDO`."""
    if tipo is Tipo.TEXTO:
        if isinstance(valor, str):
            return valor.strip()
        if isinstance(valor, bool):
            return INVALIDO
        if isinstance(valor, numbers.Integral):
            return str(int(valor))
        if isinstance(valor, numbers.Real) and float(valor).is_integer():
            # Número que o Excel guardou como float (ex.: um código numérico).
            return str(int(valor))
        return INVALIDO

    # Numéricos: só número de verdade. Texto numa coluna numérica é mudança de
    # formato na origem, e mudança de formato pede decisão, não conversão
    # silenciosa ("1.234,56" e "1,234.56" não são o mesmo número).
    if isinstance(valor, bool) or not isinstance(valor, numbers.Real):
        return INVALIDO
    numero = float(valor)
    if math.isinf(numero):
        return INVALIDO
    if tipo is Tipo.INTEIRO:
        return int(numero) if numero.is_integer() else INVALIDO
    return numero


def _exemplos(serie: pd.Series) -> str:
    itens = [f"linha {linha}: {valor!r}" for linha, valor in serie.head(EXEMPLOS_POR_PROBLEMA).items()]
    resto = len(serie) - len(itens)
    return "; ".join(itens) + (f"; e mais {resto}" if resto > 0 else "")


def _validar_coluna(bruta: pd.Series, coluna: Coluna) -> tuple[pd.Series, list[str]]:
    """Converte a coluna inteira e devolve (valores convertidos, problemas)."""
    problemas: list[str] = []
    vazio = bruta.map(eh_vazio)

    # Montada como lista do Python de propósito: `pd.Series(None, dtype=object)`
    # e atribuições parciais com `.loc` trocam None por NaN, e NaN não é None
    # para quem vem depois (`is None`, psycopg, json).
    valores = [None if vz else _converter(v, coluna.tipo) for v, vz in zip(bruta.tolist(), vazio.tolist())]
    convertida = pd.Series(valores, index=bruta.index, dtype=object)

    invalidas = pd.Series([v is INVALIDO for v in valores], index=bruta.index)
    if invalidas.any():
        problemas.append(
            f"coluna {coluna.nome}: {int(invalidas.sum())} valor(es) que não são {coluna.tipo.value} — "
            + _exemplos(bruta[invalidas])
        )

    if not coluna.aceita_vazio and vazio.any():
        linhas = ", ".join(str(i) for i in vazio[vazio].index[:EXEMPLOS_POR_PROBLEMA])
        problemas.append(f"coluna {coluna.nome}: {int(vazio.sum())} célula(s) vazia(s), e ela não aceita vazio — linhas {linhas}")

    if coluna.dominio is not None:
        validas = convertida[~vazio & ~invalidas]
        fora = validas[~validas.isin(coluna.dominio)]
        if len(fora):
            permitido = f"{min(coluna.dominio)} a {max(coluna.dominio)}"
            problemas.append(
                f"coluna {coluna.nome}: {len(fora)} valor(es) fora do domínio ({permitido}) — " + _exemplos(fora)
            )

    # Só chega aqui com INVALIDO quando há problema — e aí a planilha inteira é
    # recusada. Ainda assim, nada de INVALIDO sai desta função.
    limpa = pd.Series([None if v is INVALIDO else v for v in valores], index=bruta.index, dtype=object)
    return limpa, problemas


def _json_bruto(valor):
    """Célula de coluna FORA do contrato, em forma que o jsonb aceite."""
    if eh_vazio(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, numbers.Integral):
        return int(valor)
    if isinstance(valor, numbers.Real):
        numero = float(valor)
        return None if math.isinf(numero) else numero
    return valor if isinstance(valor, str) else str(valor)


# ── Validações que olham mais de uma coluna ──────────────────


def _validar_estrutura(dados: pd.DataFrame) -> list[str]:
    problemas: list[str] = []

    chave = dados[["ID", "MES"]].dropna()
    repetidas = chave[chave.duplicated(keep=False)]
    if len(repetidas):
        grupos = repetidas.groupby(["ID", "MES"]).groups
        exemplos = [
            f"ID {int(id_ej)} mês {int(mes)} (linhas {', '.join(str(i) for i in linhas)})"
            for (id_ej, mes), linhas in list(grupos.items())[:EXEMPLOS_POR_PROBLEMA]
        ]
        problemas.append(
            f"(ID, MES) repetido em {len(grupos)} caso(s) — a carga não sabe qual linha vale: " + "; ".join(exemplos)
        )

    por_ej = dados[["ID", "FEDERACAO"]].dropna().groupby("ID")["FEDERACAO"].unique()
    divididas = por_ej[por_ej.map(len) > 1]
    if len(divididas):
        exemplos = [
            f"ID {int(id_ej)} ({', '.join(sorted(feds))})"
            for id_ej, feds in divididas.head(EXEMPLOS_POR_PROBLEMA).items()
        ]
        problemas.append(
            f"{len(divididas)} EJ(s) aparecem em mais de uma federação, e a linha não tem como ser roteada: "
            + "; ".join(exemplos)
        )

    return problemas


# ── Ponto de entrada ─────────────────────────────────────────


def ler_planilha(caminho: str | Path, *, ano: int, aba: str = ABA_PADRAO) -> Planilha:
    """
    Lê a aba `aba` do arquivo e valida contra o contrato de `ano`.

    Levanta `ErroContrato` com todos os problemas encontrados — nunca devolve
    uma planilha parcialmente válida.
    """
    caminho = Path(caminho).expanduser()
    nome = caminho.name

    ano_nome = ano_do_nome(nome)
    if ano_nome is not None and ano_nome != ano:
        raise ErroContrato([
            f"o nome do arquivo indica o ano {ano_nome}, mas a carga foi chamada com --ano {ano}; "
            "confira o ano antes de gravar metas e cluster no ano errado"
        ])

    try:
        with pd.ExcelFile(caminho, engine="openpyxl") as xls:
            if aba not in xls.sheet_names:
                raise ErroContrato([f"a aba {aba} não existe no arquivo; abas encontradas: {', '.join(xls.sheet_names)}"])
            # dtype=object: cada célula chega como o openpyxl a leu (int, float,
            # str, datetime). Deixar o pandas inferir tipo por coluna esconderia
            # justamente o que o contrato quer ver — um texto no meio de números.
            bruto = xls.parse(aba, dtype=object)
    except ErroContrato:
        raise
    except FileNotFoundError:
        raise ErroContrato([f"arquivo não encontrado: {caminho}"]) from None
    except Exception as exc:  # zip corrompido, formato errado, arquivo que não é xlsx
        raise ErroContrato([f"o arquivo não pôde ser lido como .xlsx ({type(exc).__name__}: {exc})"]) from exc

    bruto.columns = [str(c) for c in bruto.columns]
    bruto = bruto.drop(columns=[c for c in COLUNAS_DESCARTADAS if c in bruto.columns])
    verificar_cabecalho(list(bruto.columns), ano)

    bruto.index = pd.RangeIndex(PRIMEIRA_LINHA_DE_DADOS, PRIMEIRA_LINHA_DE_DADOS + len(bruto), name="linha_arquivo")
    # Linha inteiramente em branco (sobra de formatação no fim da aba) não é dado.
    bruto = bruto[~bruto.isna().all(axis=1)]
    if bruto.empty:
        raise ErroContrato([f"a aba {aba} não tem nenhuma linha de dados"])

    problemas: list[str] = []
    dados = pd.DataFrame(index=bruto.index)
    contrato = {c.nome: c for c in colunas_obrigatorias(ano)}
    for nome_coluna in bruto.columns:
        if nome_coluna in contrato:
            dados[nome_coluna], achados = _validar_coluna(bruto[nome_coluna], contrato[nome_coluna])
            problemas.extend(achados)
        else:
            dados[nome_coluna] = pd.Series(
                [_json_bruto(v) for v in bruto[nome_coluna].tolist()], index=bruto.index, dtype=object
            )

    if not problemas:
        problemas.extend(_validar_estrutura(dados))
    if problemas:
        raise ErroContrato(problemas)

    # Colunas de cluster além do par obrigatório (se a origem passar a mandar
    # mais anos) também entram — validadas com o mesmo domínio.
    colunas_cluster = {int(c[len("CLUSTER_"):]): c for c in dados.columns if re.fullmatch(r"CLUSTER_\d{4}", c)}
    extras = {a: c for a, c in colunas_cluster.items() if c not in contrato}
    if extras:
        modelo = colunas_de_cluster(ano)[1]
        for c in extras.values():
            coluna = Coluna(c, modelo.tipo, modelo.aceita_vazio, modelo.dominio)
            dados[c], achados = _validar_coluna(bruto[c], coluna)
            problemas.extend(achados)
        if problemas:
            raise ErroContrato(problemas)

    return Planilha(
        arquivo_nome=nome,
        arquivo_hash=hash_arquivo(caminho),
        aba=aba,
        ano=ano,
        exportado_em=data_exportacao_do_nome(nome),
        dados=dados,
        colunas_cluster=dict(sorted(colunas_cluster.items())),
    )
