"""
Importação de uma planilha do Portal BJ: o ponto de entrada da ingestão.

Costura `leitor` → `transform` → `carga` e concentra as decisões que não são de
nenhum dos três: o ESCOPO da carga, o recorte por federação, a simulação e o
registro de falha. Fica aqui, e não na CLI, para que a porta HTTP (próxima
fase) chame a mesma função e herde as mesmas regras.

O ESCOPO VEM DE FORA DO ARQUIVO, NUNCA DE DENTRO

    Escopo.nacional()          as 27 federações; é o operador da plataforma.
    Escopo.federacao("slug")   só as linhas daquela federação; o resto é
                               descartado e contado em linhas_ignoradas.

Não há default. Exigir a escolha evita que alguém carregue o país inteiro
achando que carregou uma federação. No recorte, descartar as linhas das outras
26 não é perda: é o isolamento funcionando — uma federação que sobe a
exportação nacional não escreve nada fora da própria fatia. (E se o filtro
daqui falhar, a RLS recusa: ver `carga.py`.)

TUDO OU NADA

Uma transação só para o dado de gestão. Carga pela metade é pior que carga
nenhuma, porque ninguém percebe. A simulação (`simular=True`) é a MESMA carga,
com as mesmas instruções, terminando em ROLLBACK: as contagens de novas e
atualizadas que ela mostra são as que o banco de fato produziria, e não uma
estimativa feita à parte.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
import psycopg

from app.ingestao import carga, leitor, transform
from app.ingestao.contrato import ABA_PADRAO, ErroContrato


class ErroEscopo(ValueError):
    """O escopo pedido não existe (slug de federação desconhecido)."""


@dataclass(frozen=True)
class Escopo:
    federacao_slug: str | None   # None = nacional

    @classmethod
    def nacional(cls) -> Escopo:
        return cls(None)

    @classmethod
    def federacao(cls, slug: str) -> Escopo:
        return cls(slug)

    @property
    def eh_nacional(self) -> bool:
        return self.federacao_slug is None


@dataclass
class Relatorio:
    """O que a carga fez (ou faria, na simulação). Vai para o terminal e para `ingestao_carga.resumo`."""

    simulacao: bool
    carga_id: int | None
    reenvio_de: int | None
    arquivo_nome: str
    arquivo_hash: str
    aba: str
    ano: int
    exportado_em: str | None
    escopo: str
    federacao: str | None
    linhas_lidas: int
    linhas_aplicadas: int
    linhas_ignoradas: int
    ignoradas_por_federacao: dict[str, int]
    federacoes: list[str]
    ejs: int
    meses: list[int]
    tabelas: dict[str, dict[str, int]]
    staging_gravada: int
    nucleos_criados: list[str]
    csat_sem_coleta: int
    csat_zero_com_coleta: int
    cluster_zero: dict[int, int]
    cluster_vazio: dict[int, int]
    avisos: list[str]
    divergencias_acumulado: list[dict]
    membros_constantes: int
    duracao_s: float = 0.0
    papel: str = ""

    def para_json(self) -> dict:
        return asdict(self)


def importar(
    conexao: psycopg.Connection,
    caminho: str | Path,
    *,
    ano: int,
    escopo: Escopo,
    origem: str = "cli",
    carregado_por: int | None = None,
    simular: bool = False,
    aba: str = ABA_PADRAO,
) -> Relatorio:
    """
    Importa a planilha no escopo pedido e devolve o relatório.

    Levanta:
        ErroEscopo      — slug de federação que não existe. Nada é registrado.
        ErroContrato    — planilha fora do contrato, ou federação desconhecida
                          em FEDERACAO. A carga é registrada como 'rejeitada'.
        carga.ErroCarga — o banco recusou a carga. Registrada como 'erro', com
                          a staging para diagnóstico.
        carga.ErroPapel — a conexão é de um papel que ignora RLS.

    `conexao` precisa estar em autocommit: esta função controla a própria
    transação (e, na simulação, desfaz tudo no fim). Na simulação nada é
    registrado — nem as falhas.
    """
    inicio = time.monotonic()
    if not conexao.autocommit:
        raise ValueError("a importação controla a própria transação: abra a conexão com autocommit=True")

    papel = carga.verificar_papel(conexao)
    federacoes = carga.ler_federacoes(conexao)

    alvo_id: int | None = None
    if not escopo.eh_nacional:
        alvo_id = federacoes.por_slug.get(escopo.federacao_slug)
        if alvo_id is None:
            raise ErroEscopo(
                f"federação {escopo.federacao_slug!r} não existe. Slugs válidos: "
                + ", ".join(sorted(federacoes.por_slug))
            )

    caminho = Path(caminho).expanduser()
    registro = carga.RegistroCarga(
        arquivo_nome=caminho.name,
        arquivo_hash=leitor.hash_arquivo(caminho) if caminho.is_file() else "",
        aba=aba,
        ano=ano,
        exportado_em=leitor.data_exportacao_do_nome(caminho.name),
        origem=origem,
        escopo="nacional" if escopo.eh_nacional else "federacao",
        federacao_id=alvo_id,
        carregado_por=carregado_por,
    )

    def rejeitar(exc: ErroContrato):
        # Arquivo inexistente não é "carga rejeitada": não houve arquivo.
        if not simular and registro.arquivo_hash:
            carga.registrar_falha(conexao, registro, status="rejeitada", mensagem=str(exc))
        raise exc

    try:
        planilha = leitor.ler_planilha(caminho, ano=ano, aba=aba)
        registro.linhas_lidas = len(planilha.dados)
        federacao_ids = transform.rotear(planilha.dados, federacoes.por_nome)
    except ErroContrato as exc:
        rejeitar(exc)

    # ── Recorte pelo escopo ──
    dados = planilha.dados
    no_escopo = (
        pd.Series(True, index=dados.index) if alvo_id is None else federacao_ids == alvo_id
    )
    registro.linhas_aplicadas = int(no_escopo.sum())
    registro.linhas_ignoradas = int((~no_escopo).sum())
    ignoradas_por_federacao = {
        str(nome): int(n) for nome, n in dados.loc[~no_escopo, "FEDERACAO"].value_counts().items()
    }
    if registro.linhas_aplicadas == 0:
        rejeitar(ErroContrato([
            f"o arquivo não tem nenhuma linha da federação {federacoes.nome_por_id[alvo_id]} "
            f"(FEDERACAO = {federacoes.nome_por_id[alvo_id]!r}); confira se é o arquivo certo"
        ]))

    transformacao = transform.transformar(
        dados[no_escopo],
        federacao_ids[no_escopo],
        ano=ano,
        colunas_cluster=planilha.colunas_cluster,
    )

    # ── A transação: tudo ou nada ──
    relatorio: Relatorio | None = None
    try:
        with conexao.transaction():
            resultado = carga.aplicar(conexao, transformacao, registro)
            relatorio = _relatorio(
                planilha, registro, transformacao, resultado, federacoes,
                ignoradas_por_federacao=ignoradas_por_federacao, simular=simular, papel=papel,
            )
            relatorio.duracao_s = round(time.monotonic() - inicio, 1)
            carga.finalizar(conexao, registro, resultado.carga_id, relatorio.para_json())
            if simular:
                raise psycopg.Rollback()
    except psycopg.Error as exc:
        mensagem = carga.traduzir_erro(exc)
        carga_id = None
        if not simular:
            carga_id = carga.registrar_falha(
                conexao, registro, status="erro", mensagem=mensagem,
                fatias=list(transformacao.fatias.values()),
            )
        raise carga.ErroCarga(mensagem, carga_id) from exc

    if simular:
        relatorio.carga_id = None
    relatorio.duracao_s = round(time.monotonic() - inicio, 1)
    return relatorio


def _relatorio(planilha, registro, transformacao, resultado, federacoes, *, ignoradas_por_federacao, simular, papel):
    return Relatorio(
        simulacao=simular,
        carga_id=resultado.carga_id,
        reenvio_de=resultado.reenvio_de,
        arquivo_nome=planilha.arquivo_nome,
        arquivo_hash=planilha.arquivo_hash,
        aba=planilha.aba,
        ano=planilha.ano,
        exportado_em=planilha.exportado_em.isoformat() if planilha.exportado_em else None,
        escopo=registro.escopo,
        federacao=federacoes.nome_por_id.get(registro.federacao_id),
        linhas_lidas=registro.linhas_lidas,
        linhas_aplicadas=registro.linhas_aplicadas,
        linhas_ignoradas=registro.linhas_ignoradas,
        ignoradas_por_federacao=ignoradas_por_federacao,
        federacoes=sorted(federacoes.nome_por_id[f] for f in transformacao.fatias),
        ejs=transformacao.ejs,
        meses=transformacao.meses,
        tabelas={
            nome: {"enviadas": c.enviadas, "novas": c.novas, "atualizadas": c.atualizadas, "inalteradas": c.inalteradas}
            for nome, c in resultado.tabelas.items()
        },
        staging_gravada=resultado.staging_gravada,
        nucleos_criados=[
            f"{nome} ({federacoes.nome_por_id[fed]}) → id {id_}" for fed, nome, id_ in resultado.nucleos_criados
        ],
        csat_sem_coleta=transformacao.csat_sem_coleta,
        csat_zero_com_coleta=transformacao.csat_zero_com_coleta,
        cluster_zero=transformacao.cluster_zero,
        cluster_vazio=transformacao.cluster_vazio,
        avisos=transformacao.avisos,
        divergencias_acumulado=[asdict(d) for d in transformacao.divergencias_acumulado],
        membros_constantes=transformacao.membros_constantes,
        papel=papel,
    )


# ── Relatório em texto ───────────────────────────────────────


def _n(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _reais(valor: float | None) -> str:
    if valor is None:
        return "vazio"
    texto = f"{abs(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return ("−" if valor < 0 else "") + "R$ " + texto


def como_texto(r: Relatorio) -> str:
    """O resumo que a CLI imprime. Silêncio não é sucesso: tudo o que a carga decidiu aparece aqui."""
    linhas: list[str] = []
    add = linhas.append

    if r.simulacao:
        add("SIMULAÇÃO (--dry-run) — nada foi gravado: a carga rodou inteira e a transação foi desfeita.")
    elif r.reenvio_de:
        add(f"Carga #{r.carga_id} — sucesso. REENVIO: mesmo arquivo (SHA-256) da carga #{r.reenvio_de}; staging não duplicada.")
    else:
        add(f"Carga #{r.carga_id} — sucesso.")

    escopo = "nacional (--todas-federacoes)" if r.escopo == "nacional" else f"federação {r.federacao} (--federacao)"
    add(f"Arquivo:  {r.arquivo_nome}")
    add(f"          aba {r.aba}, sha256 {r.arquivo_hash[:16]}…, exportado em {r.exportado_em or 'data não identificada'}")
    add(f"Escopo:   {escopo}; ano {r.ano}; papel de banco {r.papel}")
    add("")
    add(f"Linhas:   {_n(r.linhas_lidas)} lidas, {_n(r.linhas_aplicadas)} aplicadas, {_n(r.linhas_ignoradas)} ignoradas")
    if r.ignoradas_por_federacao:
        partes = [f"{nome} {_n(n)}" for nome, n in sorted(r.ignoradas_por_federacao.items(), key=lambda x: -x[1])]
        mostrar = partes[:6] + ([f"e mais {len(partes) - 6} federações"] if len(partes) > 6 else [])
        add(f"          ignoradas por estarem fora do recorte: {', '.join(mostrar)}")
    meses = f"{r.meses[0]} a {r.meses[-1]}" if len(r.meses) > 1 else str(r.meses[0])
    add(f"Conteúdo: {len(r.federacoes)} federação(ões), {_n(r.ejs)} EJs, {len(r.meses)} meses ({meses})")
    add("")
    add(f"  {'tabela':<20}{'enviadas':>10}{'novas':>10}{'atualizadas':>13}{'inalteradas':>13}")
    for nome, c in r.tabelas.items():
        add(f"  {nome:<20}{_n(c['enviadas']):>10}{_n(c['novas']):>10}{_n(c['atualizadas']):>13}{_n(c['inalteradas']):>13}")
    add(f"  {'ingestao_staging_ej':<20}{_n(r.staging_gravada):>10}")
    add("")
    add("Transformações:")
    add(f"  CSAT 0 sem coleta gravado como NULL (9.8): {_n(r.csat_sem_coleta)} linhas; "
        f"CSAT 0 com coleta mantido: {_n(r.csat_zero_com_coleta)}")
    for ano_c in sorted(set(r.cluster_zero) | set(r.cluster_vazio)):
        add(f"  cluster {ano_c}: {_n(r.cluster_zero.get(ano_c, 0))} EJs com 0 e "
            f"{_n(r.cluster_vazio.get(ano_c, 0))} vazias — sem linha em cluster_historico (sem cluster)")
    add("  SOLUCOES só na staging (valor do mês, não total); projetos_totais não é gravado")

    if r.nucleos_criados or r.avisos:
        add("")
        add("Avisos:")
        for criado in r.nucleos_criados:
            add(f"  núcleo criado sem ID do Portal BJ, reconciliar: {criado}")
        for aviso in r.avisos:
            add(f"  {aviso}")

    add("")
    add(f"Diagnóstico 9.23 — acumulado ≠ soma dos meses: {_n(len(r.divergencias_acumulado))} de {_n(r.ejs)} EJs "
        "(coluna gravada como veio; vazio lido como 0)")
    for d in r.divergencias_acumulado[:10]:
        causa = f"; faturamento negativo no(s) mês(es) {', '.join(map(str, d['meses_negativos']))}" if d["meses_negativos"] else ""
        add(f"  EJ {d['id_ej']} {d['nome']} ({d['federacao']}): a partir do mês {d['mes']}, "
            f"coluna {_reais(d['coluna'])} × soma {_reais(d['soma'])}{causa}")
    if len(r.divergencias_acumulado) > 10:
        add(f"  … e mais {len(r.divergencias_acumulado) - 10}")
    add(f"Diagnóstico MEMBROS: igual em todos os meses em {_n(r.membros_constantes)} de {_n(r.ejs)} EJs "
        "— é foto do cadastro, não série mensal")
    add("")
    add(f"Tempo: {str(r.duracao_s).replace('.', ',')} s")
    return "\n".join(linhas)
