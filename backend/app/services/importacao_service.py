"""
Porta HTTP da ingestão: a planilha enviada pelo painel entra por aqui.

É um adaptador fino sobre `app.ingestao.importacao.importar` — a mesma função
que a CLI (`make importar`) chama, com as mesmas regras de escopo, recorte,
simulação e registro. O que muda é só a origem (`'upload'`), quem carregou
(`carregado_por`) e de onde vem o arquivo.

POR QUE psycopg E NÃO O CLIENTE SUPABASE

A carga escreve 13 mil linhas em lote, numa transação só, sob o papel
`ingestao` (sujeito a RLS e sem DELETE, ver infra/db/init/10 e 11). PostgREST
não faz nem uma coisa nem outra. A conexão vem de `settings.INGESTAO_DSN`, e
`carga.verificar_papel` recusa dono de tabela, superusuário e BYPASSRLS — a
porta HTTP herda essa trava sem precisar repeti-la.

QUEM DECIDE O ESCOPO

O router. Um `admin` só importa a própria federação; o recorte é aplicado pela
carga com o claim da federação fixo, então linhas de outras federações que
viessem no arquivo são ignoradas e, se escapassem, recusadas pela RLS. Só o
`plataforma` pede o escopo nacional.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import psycopg

from app.config import settings
from app.ingestao.importacao import Escopo, Relatorio, como_texto, importar


class IngestaoIndisponivel(RuntimeError):
    """`INGESTAO_DSN` não configurada ou banco inacessível."""


class ArquivoInvalido(ValueError):
    """Nome, extensão ou tamanho fora do aceito."""


_NOME_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")


def nome_seguro(nome: str | None) -> str:
    """
    Nome do arquivo sem diretório e sem caractere estranho.

    O nome importa para a carga: a data de exportação é lida DELE
    (`leitor.data_exportacao_do_nome`), então é preservado o quanto der — só
    o que não é letra, número, ponto, hífen ou sublinhado vira `_`.
    """
    base = Path(nome or "").name
    base = _NOME_SEGURO.sub("_", base).strip("._")
    if not base.lower().endswith(".xlsx"):
        raise ArquivoInvalido("envie a exportação do Portal BJ em .xlsx")
    return base


def importar_upload(
    conteudo: bytes,
    nome_arquivo: str,
    *,
    ano: int,
    escopo: Escopo,
    carregado_por: int | None,
    simular: bool,
) -> tuple[Relatorio, str]:
    """
    Grava o upload num diretório temporário e roda a importação.

    Devolve o relatório e o mesmo texto que a CLI imprime. Deixa passar as
    exceções da ingestão (`ErroContrato`, `ErroEscopo`, `ErroCarga`,
    `ErroPapel`) para o router traduzir em HTTP.
    """
    if not settings.INGESTAO_DSN:
        raise IngestaoIndisponivel(
            "importação por planilha não configurada neste ambiente (INGESTAO_DSN vazia)"
        )
    if not conteudo:
        raise ArquivoInvalido("o arquivo enviado está vazio")

    nome = nome_seguro(nome_arquivo)
    with tempfile.TemporaryDirectory(prefix="upload-") as diretorio:
        caminho = Path(diretorio) / nome
        caminho.write_bytes(conteudo)
        try:
            conexao = psycopg.connect(settings.INGESTAO_DSN, autocommit=True, connect_timeout=5)
        except psycopg.OperationalError as exc:
            raise IngestaoIndisponivel("não foi possível conectar ao banco da importação") from exc
        with conexao:
            relatorio = importar(
                conexao,
                caminho,
                ano=ano,
                escopo=escopo,
                origem="upload",
                carregado_por=carregado_por,
                simular=simular,
            )
    return relatorio, como_texto(relatorio)
