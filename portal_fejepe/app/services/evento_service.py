"""
Serviço de cálculo para a aba de Eventos.

Reaproveita os indicadores já calculados das EJs para montar
os cards operacionais do evento vigente.
"""

from __future__ import annotations

from math import ceil

from pydantic import BaseModel
from supabase import Client

from app.config import settings
from app.models.evento import (
    EventoDetalheResponse,
    EventoMetaParticipante,
    EventoMetaResultado,
    EventoMetaTipo,
    EventoResumo,
)
from app.models.empresa import EmpresaComIndicadores
from app.services.empresa_service import listar_empresas


class _EventoDef(BaseModel):
    id_evento: str
    nome: str
    descricao: str
    ativo: bool
    ano: int
    mes_referencia: int


class _MetaDef(BaseModel):
    tipo: EventoMetaTipo
    titulo: str
    descricao: str
    meta_percentual: float
    submeta_titulo: str | None = None
    submeta_percentual: float | None = None


EVENTOS: list[_EventoDef] = [
    _EventoDef(
        id_evento="ciranda-mej-26",
        nome="CirandaMEJ'26: O Que Ecoa Entre Nós?",
        descricao="Monitoramento das metas do CirandaMEJ'26 — evento de fevereiro a maio de 2026.",
        ativo=True,
        ano=settings.ANO_DEFAULT,
        mes_referencia=5,
    ),
]

EVENTOS_POR_ID = {evento.id_evento: evento for evento in EVENTOS}

METAS_EVENTO: dict[str, list[_MetaDef]] = {
    "ciranda-mej-26": [
        _MetaDef(
            tipo=EventoMetaTipo.faturamento_zero,
            titulo="Fora do zero de faturamento",
            descricao="EJs com faturamento acumulado maior que zero.",
            meta_percentual=72,
        ),
        _MetaDef(
            tipo=EventoMetaTipo.colab_zero,
            titulo="Fora do zero de colab",
            descricao="EJs com faturamento colaborativo acumulado maior que zero.",
            meta_percentual=34,
        ),
        _MetaDef(
            tipo=EventoMetaTipo.verde_mes,
            titulo="No verde de maio",
            descricao="EJs que bateram a meta de faturamento acumulado até maio.",
            meta_percentual=30,
        ),
        _MetaDef(
            tipo=EventoMetaTipo.cluster_tracking,
            titulo="Se mantendo ou subindo de cluster",
            descricao="EJs com tendência de cluster estável ou crescente.",
            meta_percentual=67,
        ),
    ],
}


def listar_eventos() -> list[EventoResumo]:
    """Retorna o catálogo de eventos disponíveis na aba."""
    return [
        EventoResumo(
            id_evento=evento.id_evento,
            nome=evento.nome,
            descricao=evento.descricao,
            ativo=evento.ativo,
            ano=evento.ano,
            mes_referencia=evento.mes_referencia,
        )
        for evento in EVENTOS
    ]


def obter_evento(evento_id: str) -> EventoResumo | None:
    evento = EVENTOS_POR_ID.get(evento_id)
    if evento is None:
        return None
    return EventoResumo(
        id_evento=evento.id_evento,
        nome=evento.nome,
        descricao=evento.descricao,
        ativo=evento.ativo,
        ano=evento.ano,
        mes_referencia=evento.mes_referencia,
    )


def calcular_evento(
    sb: Client,
    evento_id: str,
    *,
    ano: int | None = None,
    mes: int | None = None,
) -> EventoDetalheResponse | None:
    """Calcula o resultado atual das metas de um evento."""
    evento = EVENTOS_POR_ID.get(evento_id)
    if evento is None:
        return None

    ano_ref = ano or evento.ano
    mes_ref = mes or evento.mes_referencia

    empresas = _listar_empresas_evento(sb, ano_ref, mes_ref)
    total_ejs = len(empresas)
    metas = [_calcular_meta(meta_def, empresas, total_ejs, mes_ref) for meta_def in METAS_EVENTO[evento_id]]

    return EventoDetalheResponse(
        evento=EventoResumo(
            id_evento=evento.id_evento,
            nome=evento.nome,
            descricao=evento.descricao,
            ativo=evento.ativo,
            ano=ano_ref,
            mes_referencia=mes_ref,
        ),
        total_ejs=total_ejs,
        metas=metas,
    )


def _listar_empresas_evento(sb: Client, ano: int, mes: int) -> list[EmpresaComIndicadores]:
    response = listar_empresas(
        sb,
        ano=ano,
        mes=mes,
        page=1,
        page_size=5000,
    )
    return [empresa for empresa in response.data if _is_ej_ativa(empresa)]


def _calcular_meta(
    meta_def: _MetaDef,
    empresas: list[EmpresaComIndicadores],
    total_ejs: int,
    mes_ref: int,
) -> EventoMetaResultado:
    meta_contagem = ceil((meta_def.meta_percentual / 100) * total_ejs) if total_ejs > 0 else 0

    participantes = _filtrar_participantes(meta_def.tipo, empresas, mes_ref)
    resultado_contagem = len(participantes)
    resultado_percentual = round((resultado_contagem / total_ejs) * 100, 1) if total_ejs > 0 else 0
    gap_contagem = max(meta_contagem - resultado_contagem, 0)
    gap_percentual = max(round(meta_def.meta_percentual - resultado_percentual, 1), 0)

    submeta_contagem = None
    subresultado_contagem = None
    subgap_contagem = None
    submeta_titulo = meta_def.submeta_titulo
    submeta_percentual = meta_def.submeta_percentual

    if meta_def.tipo == EventoMetaTipo.verde_mes and meta_contagem > 0:
        submeta_contagem = ceil(((submeta_percentual or 0) / 100) * meta_contagem)
        subresultado_contagem = sum(1 for ej in participantes if ej.cluster in (1, 2))
        subgap_contagem = max(submeta_contagem - subresultado_contagem, 0)

    return EventoMetaResultado(
        tipo=meta_def.tipo,
        titulo=meta_def.titulo,
        descricao=meta_def.descricao,
        meta_percentual=meta_def.meta_percentual,
        meta_contagem=meta_contagem,
        resultado_percentual=resultado_percentual,
        resultado_contagem=resultado_contagem,
        gap_percentual=gap_percentual,
        gap_contagem=gap_contagem,
        submeta_titulo=submeta_titulo,
        submeta_percentual=submeta_percentual,
        submeta_contagem=submeta_contagem,
        subresultado_contagem=subresultado_contagem,
        subgap_contagem=subgap_contagem,
        participantes=[_to_participante(ej) for ej in participantes],
    )


def _filtrar_participantes(
    tipo: EventoMetaTipo,
    empresas: list[EmpresaComIndicadores],
    mes_ref: int,
) -> list[EmpresaComIndicadores]:
    if tipo == EventoMetaTipo.faturamento_zero:
        return [empresa for empresa in empresas if empresa.faturamento_acumulado > 0]

    if tipo == EventoMetaTipo.colab_zero:
        return [empresa for empresa in empresas if empresa.faturamento_colab_acumulado > 0]

    if tipo == EventoMetaTipo.verde_mes:
        limiar_percentual = (mes_ref / 12) * 100
        return [
            empresa
            for empresa in empresas
            if empresa.percentual_meta is not None and empresa.percentual_meta >= limiar_percentual
        ]

    if tipo == EventoMetaTipo.cluster_tracking:
        return [
            empresa for empresa in empresas
            if empresa.tracking_cluster_calculado is not None
            and empresa.tracking_cluster_calculado >= (empresa.cluster or 1)
        ]

    return []


def _to_participante(ej: EmpresaComIndicadores) -> EventoMetaParticipante:
    return EventoMetaParticipante(
        id_ej=ej.id_ej,
        nome=ej.nome,
        comunidade=ej.comunidade,
        cluster=ej.cluster,
        status=ej.status,
        faturamento_acumulado=ej.faturamento_acumulado,
        faturamento_colab_acumulado=ej.faturamento_colab_acumulado,
        percentual_meta=ej.percentual_meta,
        projetos_colab_totais=ej.projetos_colab_totais,
        atende_cluster_1_2=ej.cluster in (1, 2),
        tendencia_cluster=ej.tendencia_cluster.value if ej.tendencia_cluster is not None else None,
    )


def _is_ej_ativa(ej: EmpresaComIndicadores) -> bool:
    status = (ej.status or "").strip().lower()
    if not status:
        return True
    return status not in {"inativa", "inativo", "desativada", "desativado"}