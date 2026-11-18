"""Métricas personalizadas: persistência sob RLS e cálculo com os dados autorizados.

Leitura e escrita usam o cliente DA REQUISIÇÃO (JWT do usuário). Quem decide o
que cada um vê e grava é a RLS de infra/db/init/27-metricas-personalizadas.sql;
o filtro de tenant daqui é a segunda camada, independente (app/services/tenant.py).

O cálculo nunca recebe nada da IA além de uma `DefinicaoMetrica` já validada:
a expressão é reanalisada aqui antes de cada execução.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.database import Client
from app.metricas.avaliacao import agregar, calcular_janela, explicar, texto_periodo
from app.metricas.catalogo import VARIAVEIS, colunas_de
from app.metricas.expressao import analisar, formatar, variaveis
from app.models.metricas import (DefinicaoMetrica, LinhaMetrica, Metrica, MetricaEntrada,
                                 PontoMetrica, ResultadoMetrica)
from app.services.cluster_service import buscar_historico_do_ano, buscar_ids_por_cluster
from app.services.leitura import ler_todas
from app.services.tenant import filtrar_por_tenant

TABELA = "metrica_personalizada"
LIMITE_ATIVAS = 50
_COLUNAS = ("id,federacao_id,nome,descricao,visual,definicao,no_painel,ordem,versao,"
            "criado_em,atualizado_em,arquivada_em")


class ErroMetrica(ValueError):
    """Pedido válido no formato, mas recusado pela regra (mensagem legível)."""


class MetricaNaoEncontrada(LookupError):
    pass


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _para_modelo(linha: dict) -> Metrica:
    definicao = DefinicaoMetrica.model_validate(linha["definicao"])
    return Metrica(
        id=linha["id"], nome=linha["nome"], descricao=linha.get("descricao"), visual=linha["visual"],
        no_painel=linha["no_painel"], ordem=linha["ordem"], versao=linha["versao"],
        arquivada=linha.get("arquivada_em") is not None, definicao=definicao,
        formula_legivel=formatar(analisar(definicao.expressao), legivel=True),
        criado_em=linha["criado_em"], atualizado_em=linha["atualizado_em"],
    )


# ── Leitura e escrita ────────────────────────────────────────


def _ler_metricas(sb: Client, federacao_id: int) -> list[dict]:
    return ler_todas(sb, TABELA, _COLUNAS, lambda q: q.eq("federacao_id", federacao_id))


def listar(sb: Client, federacao_id: int, *, arquivadas: bool = False) -> list[Metrica]:
    linhas = [m for m in _ler_metricas(sb, federacao_id) if (m.get("arquivada_em") is not None) == arquivadas]
    linhas.sort(key=lambda m: (m["ordem"], m["id"]))
    return [_para_modelo(m) for m in linhas]


def _buscar_linha(sb: Client, federacao_id: int, metrica_id: int) -> dict:
    linha = (sb.table(TABELA).select(_COLUNAS).eq("federacao_id", federacao_id).eq("id", metrica_id)
             .maybe_single().execute().data)
    if not linha:
        # Mesma resposta para inexistente e de outra federação: não confirma existência.
        raise MetricaNaoEncontrada("Métrica não encontrada na sua federação.")
    return linha


def buscar(sb: Client, federacao_id: int, metrica_id: int) -> Metrica:
    return _para_modelo(_buscar_linha(sb, federacao_id, metrica_id))


def _nome_em_uso(ativas: list[dict], nome: str, *, exceto: int | None = None) -> bool:
    chave = nome.strip().casefold()
    return any(m["nome"].strip().casefold() == chave and m["id"] != exceto for m in ativas)


def criar(sb: Client, federacao_id: int, usuario_id: str, entrada: MetricaEntrada) -> Metrica:
    ativas = [m for m in _ler_metricas(sb, federacao_id) if m.get("arquivada_em") is None]
    if len(ativas) >= LIMITE_ATIVAS:
        raise ErroMetrica(f"A federação já tem {LIMITE_ATIVAS} métricas ativas. Arquive alguma antes de criar outra.")
    if _nome_em_uso(ativas, entrada.nome):
        raise ErroMetrica("Já existe uma métrica ativa com esse nome na federação.")
    ordem = max((m["ordem"] for m in ativas), default=-1) + 1
    linha = sb.table(TABELA).insert({
        "federacao_id": federacao_id, "nome": entrada.nome, "descricao": entrada.descricao,
        "visual": entrada.visual, "definicao": entrada.definicao.model_dump(), "no_painel": entrada.no_painel,
        "ordem": min(ordem, 10000), "criado_por": usuario_id,
    }).execute().data
    return _para_modelo(linha[0])


def _atualizar(sb: Client, federacao_id: int, metrica_id: int, usuario_id: str, dados: dict) -> Metrica:
    linhas = (sb.table(TABELA).update({**dados, "atualizado_por": usuario_id})
              .eq("federacao_id", federacao_id).eq("id", metrica_id).execute().data)
    if not linhas:
        raise MetricaNaoEncontrada("Métrica não encontrada na sua federação.")
    return _para_modelo(linhas[0])


def atualizar(sb: Client, federacao_id: int, metrica_id: int, usuario_id: str, entrada: MetricaEntrada) -> Metrica:
    atual = _buscar_linha(sb, federacao_id, metrica_id)
    if atual.get("arquivada_em") is not None:
        raise ErroMetrica("Restaure a métrica antes de editá-la.")
    ativas = [m for m in _ler_metricas(sb, federacao_id) if m.get("arquivada_em") is None]
    if _nome_em_uso(ativas, entrada.nome, exceto=metrica_id):
        raise ErroMetrica("Já existe uma métrica ativa com esse nome na federação.")
    return _atualizar(sb, federacao_id, metrica_id, usuario_id, {
        "nome": entrada.nome, "descricao": entrada.descricao, "visual": entrada.visual,
        "definicao": entrada.definicao.model_dump(), "no_painel": entrada.no_painel,
    })


def definir_painel(sb: Client, federacao_id: int, metrica_id: int, usuario_id: str, no_painel: bool) -> Metrica:
    atual = _buscar_linha(sb, federacao_id, metrica_id)
    if atual.get("arquivada_em") is not None:
        raise ErroMetrica("Restaure a métrica antes de colocá-la no painel.")
    return _atualizar(sb, federacao_id, metrica_id, usuario_id, {"no_painel": no_painel})


def arquivar(sb: Client, federacao_id: int, metrica_id: int, usuario_id: str) -> Metrica:
    _buscar_linha(sb, federacao_id, metrica_id)
    return _atualizar(sb, federacao_id, metrica_id, usuario_id, {"arquivada_em": _agora(), "no_painel": False})


def restaurar(sb: Client, federacao_id: int, metrica_id: int, usuario_id: str) -> Metrica:
    atual = _buscar_linha(sb, federacao_id, metrica_id)
    if atual.get("arquivada_em") is None:
        return _para_modelo(atual)
    ativas = [m for m in _ler_metricas(sb, federacao_id) if m.get("arquivada_em") is None]
    if len(ativas) >= LIMITE_ATIVAS:
        raise ErroMetrica(f"A federação já tem {LIMITE_ATIVAS} métricas ativas. Arquive alguma antes de restaurar.")
    if _nome_em_uso(ativas, atual["nome"]):
        raise ErroMetrica("Já existe uma métrica ativa com esse nome. Renomeie a outra antes de restaurar.")
    return _atualizar(sb, federacao_id, metrica_id, usuario_id, {"arquivada_em": None})


def excluir(sb: Client, federacao_id: int, metrica_id: int) -> None:
    atual = _buscar_linha(sb, federacao_id, metrica_id)
    if atual.get("arquivada_em") is None:
        raise ErroMetrica("Só é possível excluir de vez uma métrica arquivada. Arquive-a primeiro.")
    apagadas = sb.table(TABELA).delete().eq("federacao_id", federacao_id).eq("id", metrica_id).execute().data
    if not apagadas:
        raise MetricaNaoEncontrada("Métrica não encontrada na sua federação.")


def reordenar(sb: Client, federacao_id: int, usuario_id: str, ids: list[int]) -> list[Metrica]:
    if len(set(ids)) != len(ids):
        raise ErroMetrica("A nova ordem repete uma métrica.")
    existentes = {m["id"] for m in _ler_metricas(sb, federacao_id) if m.get("arquivada_em") is None}
    if not set(ids) <= existentes:
        raise MetricaNaoEncontrada("Alguma métrica da nova ordem não está ativa na sua federação.")
    for posicao, metrica_id in enumerate(ids):
        _atualizar(sb, federacao_id, metrica_id, usuario_id, {"ordem": posicao})
    return listar(sb, federacao_id)


# ── Cálculo ──────────────────────────────────────────────────


def _base(definicao: DefinicaoMetrica, no, mes_fim: int | None) -> dict:
    return dict(ano=definicao.ano, mes_inicio=definicao.mes_inicio, mes_fim=mes_fim, unidade=definicao.unidade,
                formula=formatar(no), formula_legivel=formatar(no, legivel=True),
                explicacao=explicar(no, texto_periodo(definicao.ano, definicao.mes_inicio, mes_fim)),
                agregacao_rede=definicao.agregacao_rede, ordem=definicao.ordem)


def calcular(sb: Client, federacao_id: int, definicao: DefinicaoMetrica) -> ResultadoMetrica:
    if federacao_id is None:
        raise ValueError("Cálculo exige federação autenticada.")
    no = analisar(definicao.expressao)
    usadas = variaveis(no)
    exige_mensal = any(VARIAVEIS[n].origem == "monitoramento" for n in usadas)

    empresas = ler_todas(sb, "empresa_junior", "id,id_ej,nome", lambda q: filtrar_por_tenant(q, federacao_id))
    if definicao.cluster is not None:
        no_cluster = set(buscar_ids_por_cluster(sb, ano=definicao.ano, cluster=definicao.cluster))
        empresas = [e for e in empresas if e["id_ej"] in no_cluster]
    recorte = f" do cluster {definicao.cluster}" if definicao.cluster is not None else ""
    if not empresas:
        return ResultadoMetrica(status="sem_dados", **_base(definicao, no, definicao.mes_fim),
                                mensagem=f"Nenhuma EJ{recorte} na sua federação em {definicao.ano}.")
    ids = [e["id_ej"] for e in empresas]
    nomes = {e["id_ej"]: e["nome"] for e in empresas}

    colunas = ",".join(["id", "id_ej", "mes", *colunas_de("monitoramento", usadas)])
    limite_mes = definicao.mes_fim or 12
    mensais = ler_todas(sb, "monitoramento", colunas, lambda q: q.eq("ano", definicao.ano).in_("id_ej", ids)
                        .gte("mes", definicao.mes_inicio).lte("mes", limite_mes))
    meses_com_dados = sorted({m["mes"] for m in mensais})
    mes_fim = definicao.mes_fim or (meses_com_dados[-1] if meses_com_dados else None)
    if mes_fim is None and not exige_mensal:
        mes_fim = definicao.mes_inicio  # só metas anuais: o período não muda o valor
    if mes_fim is None:
        return ResultadoMetrica(status="sem_dados", **_base(definicao, no, None), mensagem=(
            f"Não há monitoramento{recorte} na sua federação {texto_periodo(definicao.ano, definicao.mes_inicio, None)}."))
    periodo = texto_periodo(definicao.ano, definicao.mes_inicio, mes_fim)
    faltando = [m for m in range(definicao.mes_inicio, mes_fim + 1) if m not in meses_com_dados]
    if exige_mensal and faltando:
        disponiveis = ", ".join(f"{m:02d}/{definicao.ano}" for m in meses_com_dados) or "nenhum"
        return ResultadoMetrica(status="sem_dados", **_base(definicao, no, mes_fim), total_ejs=len(ids), mensagem=(
            f"Não há monitoramento{recorte} em {', '.join(f'{m:02d}/{definicao.ano}' for m in faltando)}. "
            f"Não troquei o período por outro. Meses com dados no intervalo pedido: {disponiveis}."))

    por_ej: dict[int, dict[int, dict]] = {}
    for linha in mensais:
        por_ej.setdefault(linha["id_ej"], {})[linha["mes"]] = linha
    metas: dict[int, dict] = {}
    colunas_metas = colunas_de("metas", usadas)
    if colunas_metas:
        for linha in ler_todas(sb, "metas", ",".join(["id", "id_ej", *colunas_metas]),
                               lambda q: q.eq("ano", definicao.ano).in_("id_ej", ids)):
            metas[linha["id_ej"]] = linha

    calculo = calcular_janela(no, ids_ej=ids, monitoramento=por_ej, metas=metas,
                              mes_inicio=definicao.mes_inicio, mes_fim=mes_fim)
    reverso = definicao.ordem == "desc"
    ordenadas = sorted(calculo.valores.items(),
                       key=lambda item: (-item[1] if reverso else item[1], nomes[item[0]].casefold()))
    topo = ordenadas[:definicao.limite]
    clusters = buscar_historico_do_ano(sb, ano=definicao.ano, ids_ej=[i for i, _ in topo])
    linhas = [LinhaMetrica(posicao=pos, id_ej=i, nome=nomes[i], cluster=clusters.get(i), valor=round(v, 4))
              for pos, (i, v) in enumerate(topo, start=1)]

    serie = []
    for mes in range(definicao.mes_inicio, mes_fim + 1):
        do_mes = calcular_janela(no, ids_ej=ids, monitoramento=por_ej, metas=metas, mes_inicio=mes, mes_fim=mes)
        valor = agregar(list(do_mes.valores.values()), definicao.agregacao_rede)
        serie.append(PontoMetrica(mes=mes, valor=None if valor is None else round(valor, 4), ejs=len(do_mes.valores)))

    valor_rede = agregar(list(calculo.valores.values()), definicao.agregacao_rede)
    avaliadas = len(calculo.valores)
    fora = []
    if calculo.sem_cobertura:
        fora.append(f"{calculo.sem_cobertura} sem monitoramento em todos os meses do período")
    if calculo.sem_valor:
        fora.append(f"{calculo.sem_valor} sem valor em alguma variável")
    mensagem = (f"{avaliadas} de {len(ids)} EJs{recorte} com valor {periodo}."
                + (f" Ficaram fora: {'; '.join(fora)}." if fora else ""))
    return ResultadoMetrica(
        status="ok" if avaliadas else "sem_dados", mensagem=mensagem, **_base(definicao, no, mes_fim),
        linhas=linhas, total_ejs=len(ids), avaliadas=avaliadas, sem_cobertura=calculo.sem_cobertura,
        sem_valor=calculo.sem_valor, valor_rede=None if valor_rede is None else round(valor_rede, 4), serie=serie,
    )
