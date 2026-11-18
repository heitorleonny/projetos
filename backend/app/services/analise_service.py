"""
Análise do mês: resumo da federação, EJs em alerta e EJs em ascensão.

Referência: docs/plano-analise-do-mes-2026-11-17.md §3.

As regras são DESCRITIVAS: dizem o que já aconteceu nos dados do mês ("sem vendas
há 3 meses", "caiu de cluster no Cluster Track"). Não há previsão nem modelo.
Os indicadores por EJ vêm do mesmo cálculo da listagem de EJs
(`empresa_service._calcular_indicadores_ej`), aplicado duas vezes: com as linhas
até o mês de referência `m` e com as linhas até `m − 1`.

`classificar_ejs` é pura (sem banco) para ser testada regra a regra.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.database import Client
from app.models.analise import (
    AnaliseMes,
    Briefing,
    Comparativo,
    EjDestaque,
    Gravidade,
    MotivoAlerta,
    MotivoAscensao,
    MotivoDestaque,
    ResumoAnalise,
)
from app.models.empresa import EmpresaComIndicadores, Ritmo
from app.services.calculo_service import calcular_crescimento, classificar_faixa_meta
from app.services.cluster_service import buscar_historico_do_ano
# Reuso deliberado do cálculo da listagem: a Análise não pode divergir dos
# números que o gestor vê no painel e no perfil da EJ.
from app.services.empresa_service import _calcular_indicadores_ej
from app.services.leitura import ler_todas
from app.services.tenant import filtrar_por_tenant
from app.utils.constants import (
    ALERTA_JANELA_TRIMESTRE_MESES,
    ALERTA_MESES_SEM_VENDAS,
    ALERTA_QUEDA_FATURAMENTO_PCT,
    ASCENSAO_TOP_CRESCIMENTO,
    MESES_ANO,
)

MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"]

_STATUS_INATIVOS = {"inativa", "inativo", "desativada", "desativado"}

_GRAVIDADE_ALERTA = {
    MotivoAlerta.sem_vendas_seguidas: Gravidade.alta,
    MotivoAlerta.caiu_cluster: Gravidade.alta,
    MotivoAlerta.saiu_do_verde: Gravidade.media,
    MotivoAlerta.queda_faturamento: Gravidade.media,
    MotivoAlerta.sem_reporte: Gravidade.media,
}
_ORDEM_GRAVIDADE = {Gravidade.alta: 0, Gravidade.media: 1, Gravidade.baixa: 2}


@dataclass
class EntradaEj:
    """Tudo que as regras precisam de uma EJ, já calculado."""

    atual: EmpresaComIndicadores
    anterior: EmpresaComIndicadores | None
    faturamento_por_mes: dict[int, float] = field(default_factory=dict)  # só meses com linha
    csat_por_mes: dict[int, float | None] = field(default_factory=dict)


# ── Formatação em linguagem de gestor ────────────────────────


def _pct(valor: float) -> str:
    return f"{valor:.0f}%"


def _decimal(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def _moeda(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def nome_mes(mes: int) -> str:
    return MESES_PT[mes - 1]


# ── Predicados ───────────────────────────────────────────────


def limiar_verde(mes: int) -> float:
    """% da meta esperado até o mês (regras-de-negocio §8.1): mês ÷ 12 × 100."""
    return mes / MESES_ANO * 100


def no_verde(percentual_meta: float | None, mes: int) -> bool:
    return percentual_meta is not None and percentual_meta >= limiar_verde(mes)


def _ativa(ej: EmpresaComIndicadores) -> bool:
    return (ej.status or "").strip().lower() not in _STATUS_INATIVOS


def _meses_seguidos_sem_venda(fat: dict[int, float], mes: int) -> int:
    n = 0
    for k in range(mes, 0, -1):
        if fat.get(k, 0) > 0:
            break
        n += 1
    return n


# ── Regras ───────────────────────────────────────────────────


def _motivos_alerta(e: EntradaEj, mes: int) -> list[tuple[MotivoAlerta, str]]:
    atual, anterior, fat = e.atual, e.anterior, e.faturamento_por_mes
    if mes not in fat:
        # Sem linha no mês, qualquer outra regra leria dados de meses passados.
        if _ativa(atual):
            return [(MotivoAlerta.sem_reporte, f"Sem reporte de monitoramento em {nome_mes(mes)}")]
        return []

    motivos: list[tuple[MotivoAlerta, str]] = []

    # A1 — sem vendas há N meses seguidos (contando o mês de referência), só para
    # quem já vendeu no ano. Quem nunca vendeu fica no número "fora do zero" do
    # resumo: ficaria em alerta o ano inteiro (calibração de 17/11, plano §12–13).
    seguidos = _meses_seguidos_sem_venda(fat, mes)
    vendeu_no_ano = any(fat.get(k, 0) > 0 for k in range(1, mes + 1))
    if vendeu_no_ano and seguidos >= ALERTA_MESES_SEM_VENDAS:
        motivos.append((MotivoAlerta.sem_vendas_seguidas, f"Sem vendas há {seguidos} meses seguidos"))

    # A2 — caiu de cluster no Cluster Track (efetivo), mês a mês
    if (anterior is not None and anterior.tem_dados_no_ano
            and atual.tracking_cluster_efetivo is not None and anterior.tracking_cluster_efetivo is not None
            and atual.tracking_cluster_efetivo < anterior.tracking_cluster_efetivo):
        motivos.append((MotivoAlerta.caiu_cluster,
                        f"Caiu do cluster {anterior.tracking_cluster_efetivo} para o "
                        f"{atual.tracking_cluster_efetivo} no Cluster Track"))

    # A3 — saiu do verde
    if (anterior is not None and no_verde(anterior.percentual_meta, mes - 1)
            and not no_verde(atual.percentual_meta, mes) and atual.percentual_meta is not None):
        motivos.append((MotivoAlerta.saiu_do_verde,
                        f"Saiu do verde: {_pct(atual.percentual_meta)} da meta, abaixo dos "
                        f"{_pct(limiar_verde(mes))} esperados até {nome_mes(mes)}"))

    # A4 — queda forte por trimestre móvel: soma dos últimos N meses (até m) contra
    # a soma dos N anteriores. Comparar um mês isolado com a média gerava "queda de
    # 100%" para qualquer EJ que vende em pulsos (calibração de 17/11).
    # Com A1 ativo, os últimos meses estão zerados e o A4 só repetiria a mesma coisa
    # como "queda de 100%": fica um motivo só (decisão de Heitor, 17/11).
    n = ALERTA_JANELA_TRIMESTRE_MESES
    ja_sem_vendas = any(c == MotivoAlerta.sem_vendas_seguidas for c, _ in motivos)
    if not ja_sem_vendas and mes - 2 * n + 1 >= 1:
        recente = sum(fat.get(k, 0) for k in range(mes - n + 1, mes + 1))
        anterior_tri = sum(fat.get(k, 0) for k in range(mes - 2 * n + 1, mes - n + 1))
        if anterior_tri > 0:
            queda = (anterior_tri - recente) / anterior_tri * 100
            if queda >= ALERTA_QUEDA_FATURAMENTO_PCT:
                motivos.append((MotivoAlerta.queda_faturamento,
                                f"Faturamento dos últimos {n} meses {_pct(queda)} abaixo "
                                f"dos {n} meses anteriores"))

    # A5 (CSAT do mês abaixo da meta) foi retirada na calibração de 17/11: o CSAT
    # mensal oscila e marcava EJs sem problema persistente.

    return motivos


def _motivos_ascensao(e: EntradaEj, mes: int) -> list[tuple[MotivoAscensao, str]]:
    atual, anterior, fat = e.atual, e.anterior, e.faturamento_por_mes
    if mes not in fat:
        return []
    motivos: list[tuple[MotivoAscensao, str]] = []

    # S1 — subiu de cluster no Cluster Track
    if (anterior is not None and anterior.tem_dados_no_ano
            and atual.tracking_cluster_efetivo is not None and anterior.tracking_cluster_efetivo is not None
            and atual.tracking_cluster_efetivo > anterior.tracking_cluster_efetivo):
        motivos.append((MotivoAscensao.subiu_cluster,
                        f"Subiu do cluster {anterior.tracking_cluster_efetivo} para o "
                        f"{atual.tracking_cluster_efetivo} no Cluster Track"))

    # S2 — entrou no verde
    if (anterior is not None and not no_verde(anterior.percentual_meta, mes - 1)
            and no_verde(atual.percentual_meta, mes)):
        motivos.append((MotivoAscensao.entrou_no_verde,
                        f"Entrou no verde: {_pct(atual.percentual_meta)} da meta"))

    # S3 — ritmo significativo no mês
    if atual.ritmo == Ritmo.significativo:
        motivos.append((MotivoAscensao.ritmo_significativo,
                        "Ritmo significativo: faturou no mês ao menos 1/12 da meta anual"))

    # S4 — bateu a meta anual neste mês
    if classificar_faixa_meta(atual.percentual_meta) == "meta_atingida" and (
            anterior is None or classificar_faixa_meta(anterior.percentual_meta) != "meta_atingida"):
        motivos.append((MotivoAscensao.bateu_meta,
                        f"Bateu a meta anual de faturamento ({_pct(atual.percentual_meta)})"))

    # S6 — primeira venda do ano
    acumulado_antes = anterior.faturamento_acumulado if anterior is not None else 0
    if fat.get(mes, 0) > 0 and atual.faturamento_acumulado > 0 and acumulado_antes <= 0:
        motivos.append((MotivoAscensao.primeira_venda, "Primeira venda do ano"))

    return motivos


def _crescimento_mes(e: EntradaEj, mes: int) -> float | None:
    if mes < 2 or mes not in e.faturamento_por_mes:
        return None
    return calcular_crescimento(e.faturamento_por_mes.get(mes, 0), e.faturamento_por_mes.get(mes - 1, 0))


def _destaque(e: EntradaEj, mes: int, motivos, gravidade: Gravidade | None) -> EjDestaque:
    return EjDestaque(
        id_ej=e.atual.id_ej, nome=e.atual.nome, foto_url=e.atual.foto_url, gravidade=gravidade,
        motivos=[MotivoDestaque(codigo=c.value, descricao=d) for c, d in motivos],
        # Faturamento do próprio mês de referência (0 se a EJ não reportou).
        faturamento_mes=e.faturamento_por_mes.get(mes, 0),
        percentual_meta=e.atual.percentual_meta,
    )


def classificar_ejs(entradas: list[EntradaEj], mes: int) -> tuple[list[EjDestaque], list[EjDestaque]]:
    """Aplica A1–A6 e S1–S6. Devolve (alertas, ascensão), já ordenados."""
    alertas: list[EjDestaque] = []
    for e in entradas:
        motivos = _motivos_alerta(e, mes)
        if motivos:
            gravidade = min((_GRAVIDADE_ALERTA[c] for c, _ in motivos), key=_ORDEM_GRAVIDADE.__getitem__)
            alertas.append(_destaque(e, mes, motivos, gravidade))
    alertas.sort(key=lambda d: (_ORDEM_GRAVIDADE[d.gravidade], -len(d.motivos), d.nome.casefold()))

    # S5 — maiores altas do mês (só crescimento positivo, mês anterior > 0)
    crescimentos = [(c, e) for e in entradas if (c := _crescimento_mes(e, mes)) is not None and c > 0]
    crescimentos.sort(key=lambda x: (-x[0], x[1].atual.nome.casefold()))
    top = {id(e): c for c, e in crescimentos[:ASCENSAO_TOP_CRESCIMENTO]}

    ascensao: list[EjDestaque] = []
    for e in entradas:
        motivos = _motivos_ascensao(e, mes)
        if id(e) in top:
            motivos.append((MotivoAscensao.maior_crescimento,
                            f"Entre as maiores altas do mês: +{_pct(top[id(e)])} vs. {nome_mes(mes - 1)}"))
        if motivos:
            ascensao.append(_destaque(e, mes, motivos, None))
    ascensao.sort(key=lambda d: (-len(d.motivos), -d.faturamento_mes, d.nome.casefold()))
    return alertas, ascensao


# ── Resumo e briefing fixo ───────────────────────────────────


def montar_resumo(entradas: list[EntradaEj], mes: int) -> ResumoAnalise:
    atuais = [e.atual for e in entradas]
    anteriores = [e.anterior for e in entradas if e.anterior is not None]
    tem_anterior = mes > 1

    def _contar(lista, pred) -> int:
        return sum(1 for ej in lista if pred(ej))

    def _comp(pred) -> Comparativo:
        return Comparativo(atual=_contar(atuais, pred),
                           anterior=_contar(anteriores, pred) if tem_anterior else None)

    metas = [ej.meta_faturamento for ej in atuais if ej.meta_faturamento]
    meta_total = round(sum(metas), 2) if metas else None
    fat_total = round(sum(ej.faturamento_acumulado for ej in atuais), 2)
    return ResumoAnalise(
        total_ejs=len(atuais),
        fora_do_zero=_comp(lambda ej: ej.faturamento_acumulado > 0),
        ritmo_significativo=_comp(lambda ej: ej.ritmo == Ritmo.significativo),
        no_verde=Comparativo(
            atual=_contar(atuais, lambda ej: no_verde(ej.percentual_meta, mes)),
            anterior=_contar(anteriores, lambda ej: no_verde(ej.percentual_meta, mes - 1)) if tem_anterior else None),
        faturamento_acumulado=Comparativo(
            atual=fat_total,
            anterior=round(sum(ej.faturamento_acumulado for ej in anteriores), 2) if tem_anterior else None),
        meta_faturamento_total=meta_total,
        percentual_meta_rede=round(fat_total / meta_total * 100, 1) if meta_total else None,
    )


def briefing_fixo(resumo: ResumoAnalise, mes: int, n_alertas: int, n_ascensao: int,
                  *, parcial: bool = False) -> Briefing:
    """Resumo em frases fixas, sem IA. Também é o fallback do briefing gerado."""
    if resumo.total_ejs == 0:
        return Briefing(frases=[])
    fz = resumo.fora_do_zero
    frase = f"Em {nome_mes(mes)}, {int(fz.atual)} das {resumo.total_ejs} EJs estão fora do zero"
    if fz.anterior is not None:
        delta = int(fz.atual - fz.anterior)
        frase += f" ({delta:+d} em relação a {nome_mes(mes - 1)})" if delta else f" (mesmo número de {nome_mes(mes - 1)})"
    frases = [frase + "."]

    fat = _moeda(resumo.faturamento_acumulado.atual)
    if resumo.percentual_meta_rede is not None:
        frases.append(f"O faturamento acumulado da federação é {fat}, "
                      f"{_decimal(resumo.percentual_meta_rede)}% da soma das metas anuais "
                      f"(o esperado até {nome_mes(mes)} é {_pct(limiar_verde(mes))}).")
    else:
        frases.append(f"O faturamento acumulado da federação é {fat}.")

    frases.append(f"{int(resumo.no_verde.atual)} EJs estão no verde e "
                  f"{int(resumo.ritmo_significativo.atual)} tiveram ritmo significativo no mês.")
    frases.append(f"{n_alertas} EJs pedem atenção e {n_ascensao} se destacaram em {nome_mes(mes)}.")
    if parcial:
        frases.insert(0, f"{nome_mes(mes).capitalize()} ainda está em andamento: os dados são parciais.")
    return Briefing(frases=frases, gerado_por_ia=False)


# ── Leitura e orquestração ───────────────────────────────────


def _hoje() -> date:
    """Data de referência do portal (substituída nos testes)."""
    return datetime.now(ZoneInfo("America/Recife")).date()


def escolher_mes(meses_com_dados: list[int], ano: int, pedido: int | None) -> tuple[int | None, bool]:
    """Mês de referência e se ele está em andamento.

    Sem pedido, usa o último mês FECHADO com dados: o mês corrente do calendário
    ainda está sendo reportado (em 17/11 só 4 de 43 EJs tinham venda em novembro)
    e abriria a tela com quase todas as EJs em alerta. O mês corrente continua
    disponível quando pedido explicitamente, marcado como parcial.
    """
    hoje = _hoje()
    corrente = hoje.month if ano == hoje.year else None
    if pedido is not None:
        return pedido, pedido == corrente
    candidatos = [m for m in meses_com_dados if corrente is None or m < corrente]
    if candidatos:
        return max(candidatos), False
    # Só há dados do mês corrente (ex.: janeiro): mostra, avisando que é parcial.
    if meses_com_dados:
        mes = max(meses_com_dados)
        return mes, mes == corrente
    return None, False


def analisar_mes(sb: Client, *, ano: int, mes: int | None, federacao_id: int) -> AnaliseMes:
    """Análise do mês da federação. `mes=None` usa o último mês com monitoramento."""
    return analisar_mes_com_nomes(sb, ano=ano, mes=mes, federacao_id=federacao_id)[0]


def analisar_mes_com_nomes(sb: Client, *, ano: int, mes: int | None,
                           federacao_id: int) -> tuple[AnaliseMes, list[str]]:
    """Como `analisar_mes`, devolvendo também os nomes de todas as EJs da federação
    (o briefing usa a lista para recusar texto que cite EJ pelo nome)."""
    empresas = ler_todas(sb, "empresa_junior", "*", lambda q: filtrar_por_tenant(q, federacao_id))
    nomes = [e.get("nome") or "" for e in empresas]
    if not empresas:
        return AnaliseMes(ano=ano, mes=mes), nomes
    ids = [e["id_ej"] for e in empresas]

    monitoramentos = ler_todas(sb, "monitoramento", "*", lambda q: q.eq("ano", ano).in_("id_ej", ids))
    mes, parcial = escolher_mes(sorted({m["mes"] for m in monitoramentos}), ano, mes)
    if mes is None:
        return AnaliseMes(ano=ano), nomes
    metas = ler_todas(sb, "metas", "*", lambda q: q.eq("ano", ano).in_("id_ej", ids))
    historico = buscar_historico_do_ano(sb, ano=ano, ids_ej=ids)

    mons_por_ej: dict[int, list[dict]] = {}
    for m in monitoramentos:
        if m["mes"] <= mes:
            mons_por_ej.setdefault(m["id_ej"], []).append(m)
    meta_por_ej = {mt["id_ej"]: mt for mt in metas}

    entradas: list[EntradaEj] = []
    for ej in empresas:
        mons = mons_por_ej.get(ej["id_ej"], [])
        meta = meta_por_ej.get(ej["id_ej"])
        atual = _calcular_indicadores_ej(ej, mons, meta, ano, mes, historico)
        anterior = None
        if mes > 1:
            anterior = _calcular_indicadores_ej(ej, [m for m in mons if m["mes"] <= mes - 1],
                                                meta, ano, mes - 1, historico)
        entradas.append(EntradaEj(
            atual=atual, anterior=anterior,
            faturamento_por_mes={m["mes"]: float(m.get("faturamento_mes") or 0) for m in mons},
            csat_por_mes={m["mes"]: float(m["csat"]) if m.get("csat") is not None else None for m in mons},
        ))

    alertas, ascensao = classificar_ejs(entradas, mes)
    resumo = montar_resumo(entradas, mes)
    return AnaliseMes(
        ano=ano, mes=mes, mes_anterior=mes - 1 if mes > 1 else None, mes_parcial=parcial,
        resumo=resumo, alertas=alertas, ascensao=ascensao,
        briefing=briefing_fixo(resumo, mes, len(alertas), len(ascensao), parcial=parcial),
    ), nomes
