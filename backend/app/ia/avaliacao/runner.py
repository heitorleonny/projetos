"""Avaliação manual com custo: IA_EVAL_TOKEN é um JWT de usuário da demo."""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from time import monotonic
from zoneinfo import ZoneInfo
from types import SimpleNamespace

from fastapi.security import HTTPAuthorizationCredentials

from app.config import settings
from app.dependencies import get_current_user, get_federacao_id, get_supabase
from app.ia.fabrica import criar_provedor
from app.ia.assistente import preparar_pergunta, perguntar
from app.ia.conversa import busca_com_intencao_de_nome, normalizar, normalizar_referencia_propria, referencia_externa
from app.services.federacao_service import buscar_federacao_do_usuario
from app.ia.ferramentas import executar_consulta
from app.models.ia import PlanoConsulta
from app.services.leitura import ler_todas
from app.services.tenant import filtrar_por_tenant


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", default=settings.IA_MODELO)
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args()
    if not args.modelo or not settings.IA_API_KEY.get_secret_value() or not os.environ.get("IA_EVAL_TOKEN"):
        parser.error("Configure IA_MODELO, IA_API_KEY e IA_EVAL_TOKEN (JWT de usuário da demo).")
    credenciais = HTTPAuthorizationCredentials(scheme="Bearer", credentials=os.environ["IA_EVAL_TOKEN"])
    sb = get_supabase(credenciais)
    user = get_current_user(credenciais, sb)
    tenant = get_federacao_id(user, credenciais)
    if tenant is None:
        parser.error("JWT sem federação: avaliação recusada.")
    settings.IA_MODELO = args.modelo
    provedor = criar_provedor()
    permitidos = {e["id_ej"] for e in ler_todas(sb, "empresa_junior", "id_ej", lambda q: filtrar_por_tenant(q, tenant))}
    federacao = buscar_federacao_do_usuario(sb, tenant)
    ej_exemplo = escolher_ej_exemplo(sb, tenant)
    casos = [substituir_ej(caso, ej_exemplo) for caso in json.loads(Path(__file__).with_name("perguntas.json").read_text())]
    resultados = []
    for caso in casos:
        inicio = monotonic()
        item = {"id": caso["id"], "adversarial": caso.get("adversarial", False)}
        esperado = PlanoConsulta.model_validate(caso["esperado"])
        try:
            contexto = PlanoConsulta.model_validate(caso["contexto"]) if caso.get("contexto") else None
            pergunta_original = caso["pergunta"].replace("{minha_federacao}", (federacao or {}).get("slug", "minha federação"))
            pergunta = normalizar_referencia_propria(pergunta_original, federacao) if caso.get("normalizar_propria") else pergunta_original
            interpretacao = provedor.interpretar(preparar_pergunta(pergunta, contexto), settings.ANO_DEFAULT)
            plano = interpretacao.plano
            resposta = executar_consulta(sb, plano, federacao_id=tenant, ano_padrao=settings.ANO_DEFAULT)
            # Gabarito de valores calculado pelo mesmo catálogo de services,
            # usando o plano-ouro, nunca por uma resposta escrita à mão.
            gabarito = executar_consulta(sb, esperado, federacao_id=tenant, ano_padrao=settings.ANO_DEFAULT)
            # Reaproveita a interpretação já obtida: sem segunda chamada/custo do modelo.
            # Complementa interpretação+catálogo com guardas e esclarecimentos do fluxo.
            fluxo = perguntar(sb, SimpleNamespace(interpretar=lambda *_args: interpretacao), pergunta_original,
                              federacao_id=tenant, usuario_id=str(user.id), ano_padrao=settings.ANO_DEFAULT,
                              contexto=contexto, federacao=federacao)
            item.update(
                fluxo_status_correto=fluxo.status == gabarito.status,
                fluxo_valores_corretos=fluxo.linhas == gabarito.linhas,
                fluxo_isolamento=all(l.id_ej in permitidos for l in fluxo.linhas if l.id_ej is not None),
                ferramenta_correta=plano.ferramenta == esperado.ferramenta,
                parametros_corretos=normalizar_plano(plano) == normalizar_plano(esperado),
                conceito_correto=plano.conceito == esperado.conceito if esperado.ferramenta == "explicar" else None,
                ordem_correta=(plano.ordem or "desc") == (esperado.ordem or "desc") if esperado.ferramenta == "ranking" else None,
                faixa_correta=plano.faixa == esperado.faixa if esperado.ferramenta == "metas" else None,
                resposta_correta=resposta.model_dump() == gabarito.model_dump(),
                recusa_correta=resposta.status == "fora_do_catalogo" if esperado.ferramenta == "recusar" else None,
                isolamento=all(l.id_ej in permitidos for l in resposta.linhas if l.id_ej is not None),
                status=resposta.status, tokens_entrada=interpretacao.tokens_entrada, tokens_saida=interpretacao.tokens_saida,
            )
        except Exception:
            # Não versionar erro de fornecedor, token, nomes ou valores reais.
            item.update(erro="Falha de interpretação ou consulta.")
        item["duracao_ms"] = round((monotonic() - inicio) * 1000)
        resultados.append(item)
        print(f"Caso {caso['id']}: {'erro' if 'erro' in item else item['status']}", flush=True)
    resumo = {"casos": len(casos), "erros": sum("erro" in r for r in resultados)}
    for metrica in ("ferramenta_correta", "parametros_corretos", "resposta_correta", "isolamento", "fluxo_status_correto", "fluxo_valores_corretos", "fluxo_isolamento"):
        resumo[metrica] = sum(r.get(metrica) is True for r in resultados) / len(casos)
    for metrica, ferramenta in (("conceito_correto", "explicar"), ("ordem_correta", "ranking"), ("faixa_correta", "metas")):
        aplicaveis = [r for r, c in zip(resultados, casos) if c["esperado"]["ferramenta"] == ferramenta]
        resumo[metrica] = sum(r.get(metrica) is True for r in aplicaveis) / len(aplicaveis) if aplicaveis else None
    recusas = [r for r, c in zip(resultados, casos) if c["esperado"]["ferramenta"] == "recusar"]
    resumo["recusa_correta"] = sum(r.get("recusa_correta") is True for r in recusas) / len(recusas)
    resumo["tokens_entrada"] = sum(r.get("tokens_entrada", 0) for r in resultados)
    resumo["tokens_saida"] = sum(r.get("tokens_saida", 0) for r in resultados)
    instante = datetime.now(ZoneInfo("America/Recife"))
    destino = args.saida or Path(__file__).resolve().parents[4] / "docs" / f"ia-avaliacao-{instante:%Y-%m-%d-%H%M%S}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"data": instante.isoformat(), "modelo": args.modelo, "resumo": resumo,
                                  "limites": "Interpretação do modelo e catálogo são métricas distintas do fluxo com guardas backend; fluxo reaproveita a mesma interpretação, sem segunda chamada. Não valida HTTP/autenticação da rota. Não mede carga. Isolamento por IDs complementa os testes de agregados com RLS real. Custo monetário não estimado; consultar tarifa do provedor.",
                                  "resultados": resultados}, ensure_ascii=False, indent=2) + "\n")
    print(f"Relatório salvo em {destino}; {resumo['erros']} erros em {len(casos)} casos.")
    if resumo["erros"] or any(resumo[m] is not None and resumo[m] < 1 for m in (
            "ferramenta_correta", "parametros_corretos", "resposta_correta", "isolamento", "recusa_correta",
            "fluxo_status_correto", "fluxo_valores_corretos", "fluxo_isolamento",
            "conceito_correto", "ordem_correta", "faixa_correta")):
        raise SystemExit(1)


def normalizar_plano(plano: PlanoConsulta) -> PlanoConsulta:
    """`ordem` nula e "desc" são o mesmo pedido (maiores valores)."""
    return plano.model_copy(update={"ordem": None}) if plano.ordem == "desc" else plano


def escolher_ej_exemplo(sb, tenant: int) -> str:
    """EJ do próprio tenant para as perguntas de perfil, escolhida na hora.

    O nome real não é versionado no corpus nem gravado no relatório: só entra na
    pergunta enviada ao modelo, como faria um usuário. Exige nome que não esteja
    contido em outro (resolução única) e que passe pelas guardas de pergunta.
    """
    empresas = sorted(ler_todas(sb, "empresa_junior", "id_ej,nome", lambda q: filtrar_por_tenant(q, tenant)),
                      key=lambda e: e["id_ej"])
    nomes = [normalizar(e["nome"] or "") for e in empresas]
    plano = PlanoConsulta(ferramenta="perfil_ej", ano=None, mes=None, criterio=None, limite=None)
    for empresa, nome in zip(empresas, nomes):
        pergunta = f"Como está a {empresa['nome']}?"
        if (len(nome) >= 2 and sum(nome in outro for outro in nomes) == 1 and not referencia_externa(pergunta)
                and busca_com_intencao_de_nome(pergunta, plano.model_copy(update={"busca": empresa["nome"].strip()}), None)):
            return empresa["nome"].strip()
    raise SystemExit("Nenhuma EJ do tenant serve de exemplo para as perguntas de perfil.")


def substituir_ej(caso: dict, ej_exemplo: str) -> dict:
    texto = json.dumps(caso, ensure_ascii=False).replace("{EJ EXEMPLO}", ej_exemplo.replace('"', '\\"'))
    return json.loads(texto)


if __name__ == "__main__":
    main()
