"""Persistência e montagem de dashboards usando somente valores já registrados."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from app.database import Client

from app.ia.dashboard_interpretador import interpretar_dashboard
from app.ia.creditos import persistir_dashboard_com_credito
from app.models.dashboard_ia import (
    DashboardResponse,
    DimensaoDashboard,
    PlanoDashboard,
    PontoDashboard,
)
from app.services.evento_service import obter_evento
from app.services.federacao_service import buscar_federacao_do_usuario
from app.services.leitura import ler_todas


def _validar_evento(sb: Client, evento_id: str, federacao_id: int) -> None:
    federacao = buscar_federacao_do_usuario(sb, federacao_id)
    evento = obter_evento(evento_id, federacao["slug"] if federacao else None)
    if evento is None:
        raise HTTPException(404, "Evento não encontrado para esta federação.")


def interpretar_pedido(pedido: str, ano_padrao: int):
    return interpretar_dashboard(pedido, ano_padrao)


def salvar_dashboard(
    sb: Client,
    *,
    pedido: str,
    evento_id: str,
    publico: bool,
    federacao_id: int,
    usuario_id: str,
    ano_padrao: int,
    interpretador=interpretar_pedido,
) -> DashboardResponse:
    _validar_evento(sb, evento_id, federacao_id)
    plano, _modelo = interpretador(pedido, ano_padrao)
    _validar_plano(plano, publico)
    pontos = calcular_pontos(sb, plano, federacao_id)
    registro = {
        "p_evento_id": evento_id,
        "p_titulo": plano.titulo,
        "p_plano": plano.model_dump(mode="json"),
        "p_publico": publico,
        "p_resultado_publico": _resultado_publico(plano, pontos, evento_id) if publico else None,
    }
    data = persistir_dashboard_com_credito(sb, registro)
    # Não registrar prompt ou conteúdo do conjunto de dados.
    return _response(data, pontos)


def listar_dashboards(sb: Client, federacao_id: int, usuario_id: str) -> list[DashboardResponse]:
    dados = ler_todas(sb, "dashboard_evento_ia", "*", lambda q: q.eq("federacao_id", federacao_id))
    resultado: list[DashboardResponse] = []
    for item in dados:
        # Toda a federação autenticada pode acompanhar; RLS filtra as linhas-fonte.
        pontos = calcular_pontos(sb, PlanoDashboard.model_validate(item["plano"]), federacao_id)
        resultado.append(_response(item, pontos))
    return resultado


def atualizar_publicacao(
    sb: Client, dashboard_id: UUID, *, publico: bool, federacao_id: int, usuario_id: str
) -> DashboardResponse:
    existente = (
        sb.table("dashboard_evento_ia").select("*").eq("id", str(dashboard_id))
        .eq("federacao_id", federacao_id).eq("criado_por", usuario_id).maybe_single().execute().data
    )
    if not existente:
        raise HTTPException(404, "Dashboard não encontrado.")
    plano = PlanoDashboard.model_validate(existente["plano"])
    _validar_plano(plano, publico)
    pontos = calcular_pontos(sb, plano, federacao_id)
    resposta = sb.rpc("atualizar_publicacao_dashboard_evento_ia", {
        "p_dashboard_id": str(dashboard_id),
        "p_publico": publico,
        "p_resultado_publico": _resultado_publico(plano, pontos, existente["evento_id"]) if publico else None,
    }).execute().data
    atual = resposta[0] if isinstance(resposta, list) and resposta else resposta
    if not isinstance(atual, dict):
        raise HTTPException(404, "Dashboard não encontrado.")
    return _response(atual, pontos)


def obter_dashboard_publico(sb: Client, chave: UUID) -> dict[str, Any] | None:
    # RPC anon-only expõe o snapshot previamente aprovado pela federação.
    resposta = sb.rpc("dashboard_evento_publico", {"p_chave": str(chave)}).execute()
    return resposta.data if isinstance(resposta.data, dict) else None


def calcular_pontos(sb: Client, plano: PlanoDashboard, federacao_id: int) -> list[PontoDashboard]:
    """Aplica somente agregações permitidas sobre campos armazenados por mês."""
    empresas = ler_todas(
        sb,
        "empresa_junior",
        "id_ej,nome",
        lambda q: q.eq("federacao_id", federacao_id),
    )
    if not empresas:
        return []
    ids = [empresa["id_ej"] for empresa in empresas]
    monitoramentos = ler_todas(
        sb,
        "monitoramento",
        f"id_ej,ano,mes,{plano.metrica}",
        lambda q: q.in_("id_ej", ids).eq("ano", plano.ano)
        .gte("mes", plano.mes_inicio).lte("mes", plano.mes_fim),
    )
    nomes = {empresa["id_ej"]: empresa["nome"] for empresa in empresas}
    por_grupo: dict[str, list[float]] = defaultdict(list)
    rotulos: dict[str, str] = {}
    if plano.dimensao == "mes":
        for mes in range(plano.mes_inicio, plano.mes_fim + 1):
            por_grupo[str(mes)] = []
    for registro in monitoramentos:
        valor = registro.get(plano.metrica)
        if valor is None:
            continue
        if plano.metrica == "csat":
            valor_num = float(valor)
        else:
            valor_num = float(valor or 0)
        if plano.dimensao == "ej":
            grupo = str(registro["id_ej"])
            rotulos[grupo] = nomes.get(registro["id_ej"], "EJ")
        else:
            grupo = str(registro["mes"])
            rotulos[grupo] = grupo
        por_grupo[grupo].append(valor_num)

    def agregar(valores: list[float]) -> float | None:
        if not valores:
            return None
        if plano.agregacao == "soma":
            return round(sum(valores), 2)
        if plano.agregacao == "media":
            return round(sum(valores) / len(valores), 2)
        raise ValueError("Agregação não catalogada.")

    pontos = [PontoDashboard(rotulo=rotulos.get(chave, chave), valor=agregar(valores)) for chave, valores in por_grupo.items()]
    if plano.dimensao == "ej":
        pontos.sort(key=lambda p: (p.valor is not None, p.valor or 0), reverse=True)
        pontos = pontos[:plano.limite]
    else:
        pontos.sort(key=lambda p: int(p.rotulo))
    return pontos


def _validar_plano(plano: PlanoDashboard, publico: bool) -> None:
    if plano.metrica == "csat" and plano.agregacao != "media":
        raise HTTPException(422, "CSAT só pode usar média.")
    if plano.visualizacao == "ranking" and plano.dimensao != "ej":
        raise HTTPException(422, "Ranking exige dimensão por EJ.")
    if plano.visualizacao == "linha" and plano.dimensao != "mes":
        raise HTTPException(422, "Gráfico de linha exige dimensão por mês.")
    # Publicar é uma autorização explícita do gestor para expor o snapshot
    # aprovado, inclusive nomes/valores se o plano for um ranking por EJ.


def _resultado_publico(plano: PlanoDashboard, pontos: list[PontoDashboard], evento_id: str) -> dict[str, Any]:
    return {
        "titulo": plano.titulo,
        "evento_id": evento_id,
        "unidade": _unidade(plano.metrica),
        "visualizacao": plano.visualizacao,
        "periodo": f"{plano.mes_inicio:02d}/{plano.ano}–{plano.mes_fim:02d}/{plano.ano}",
        "pontos": [ponto.model_dump() for ponto in pontos],
    }


def _response(registro: dict[str, Any], pontos: list[PontoDashboard]) -> DashboardResponse:
    plano = PlanoDashboard.model_validate(registro["plano"])
    return DashboardResponse(
        id=registro["id"], evento_id=registro["evento_id"], titulo=registro["titulo"],
        metrica=plano.metrica, unidade=_unidade(plano.metrica), agregacao=plano.agregacao,
        dimensao=plano.dimensao, visualizacao=plano.visualizacao, ano=plano.ano,
        mes_inicio=plano.mes_inicio, mes_fim=plano.mes_fim, publico=registro["publico"],
        criado_por=registro["criado_por"], pontos=pontos,
    )


def _unidade(metrica: str) -> str:
    return "BRL" if metrica == "faturamento_mes" else "nota" if metrica == "csat" else "numero"
