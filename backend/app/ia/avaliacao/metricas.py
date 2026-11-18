"""Avaliação MANUAL, com rede e custo, da interpretação de métricas em texto livre.

Compara o plano devolvido pelo modelo real com o gabarito de `metricas_casos.json`.
Não lê banco nem precisa de token de usuário: avalia só a interpretação. O
cálculo é determinístico e já coberto por tests/test_metricas.py.

    cd backend
    IA_PROVEDOR=openrouter IA_API_KEY=... IA_MODELO=... python -m app.ia.avaliacao.metricas --saida ../docs/evidencias-metricas/avaliacao.json

Não roda no pytest (AGENTS: "Não testar modelo pago no pytest").
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from time import monotonic
from zoneinfo import ZoneInfo

from app.config import settings
from app.ia.metricas_interprete import InterpreteCompativel
from app.metricas.expressao import ErroExpressao, analisar, formatar


def _normalizar_expressao(texto):
    try:
        return formatar(analisar(texto)) if texto else None
    except ErroExpressao:
        return f"INVÁLIDA: {texto}"


def comparar(plano: dict, esperado: dict) -> list[str]:
    erros = []
    for campo, valor in esperado.items():
        obtido = plano.get(campo)
        if campo == "expressao":
            obtido, valor = _normalizar_expressao(obtido), _normalizar_expressao(valor)
        elif isinstance(valor, str) and isinstance(obtido, str):
            obtido, valor = obtido.strip().casefold(), valor.strip().casefold()
        if obtido != valor:
            erros.append(f"{campo}: esperado {valor!r}, obtido {obtido!r}")
    return erros


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", default=settings.IA_MODELO)
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args()
    settings.IA_MODELO = args.modelo
    interprete = InterpreteCompativel()
    if not interprete.configurado:
        parser.error("Configure IA_PROVEDOR, IA_API_KEY e IA_MODELO (ou --modelo).")
    casos = json.loads(Path(__file__).with_name("metricas_casos.json").read_text())
    resultados = []
    for caso in casos:
        inicio = monotonic()
        item = {"id": caso["id"], "adversarial": caso.get("adversarial", False)}
        try:
            interpretacao = interprete.interpretar(caso["texto"], settings.ANO_DEFAULT)
            plano = interpretacao.plano.model_dump()
            erros = comparar(plano, caso["esperado"])
            item.update(acertou=not erros, erros=erros, plano=plano, modelo=interpretacao.modelo,
                        tokens_entrada=interpretacao.tokens_entrada, tokens_saida=interpretacao.tokens_saida)
        except Exception as exc:  # noqa: BLE001 — falha do provedor conta como erro do caso
            item.update(acertou=False, erros=[f"falha: {type(exc).__name__}: {exc}"])
        item["duracao_ms"] = round((monotonic() - inicio) * 1000)
        resultados.append(item)
        print(f"{'OK ' if item['acertou'] else 'ERR'} {caso['id']}" + ("" if item["acertou"] else f"  {item['erros']}"))
    acertos = sum(r["acertou"] for r in resultados)
    adversariais = [r for r in resultados if r["adversarial"]]
    resumo = {
        "executado_em": datetime.now(ZoneInfo("America/Recife")).isoformat(),
        "modelo": args.modelo, "ano": settings.ANO_DEFAULT, "casos": len(resultados), "acertos": acertos,
        "adversariais": len(adversariais), "adversariais_recusados": sum(r["acertou"] for r in adversariais),
        "resultados": resultados,
    }
    print(f"\n{acertos}/{len(resultados)} casos; adversariais recusados {resumo['adversariais_recusados']}/{len(adversariais)}.")
    print("Lembrete: mesmo um plano errado passa pelo parser e pela prévia; o admin confere antes de salvar.")
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
