"""Compara indicadores agregados por GET; nunca imprime tokens ou valores reais.

Preparação de A5: executar exige URLs explícitas e JWTs próprios de leitura.
Comparação não explica divergências de fonte/período nem comprova isolamento.
"""

import argparse
import json
import math
import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SemRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # não encaminhar JWT para outro endereço


def validar_url(url):
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("URL deve conter apenas esquema, host e caminho da API")
    if not parsed.hostname or (parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    )):
        raise ValueError("Exigir HTTPS; HTTP só permitido em loopback")
    return url.rstrip("/")


def consultar(base, token, ano, mes, rota="indicadores"):
    if rota not in {"indicadores", "sde", "ritmo-mensal", "ranking"}:
        raise ValueError("Rota fora do catálogo")
    params = {"ano": ano, "mes": mes}
    if rota == "ranking":
        params.update({"criterio": "faturamento", "limit": 100})
    url = validar_url(base) + "/rede/" + rota + "?" + urlencode(params)
    request = Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    with build_opener(SemRedirect()).open(request, timeout=30) as response:
        payload = response.read(1_000_001)
    if len(payload) > 1_000_000:
        raise ValueError("Resposta excede limite de tamanho")
    dados = json.loads(payload)
    if rota == "ranking":
        if not isinstance(dados, list):
            raise ValueError("Ranking exige lista")
        # IDs/valores são comparados em memória; nunca gravados no relatório.
        return {"ordem_e_valores": [(d["posicao"], d["id_ej"], d["cluster"], d["valor"]) for d in dados]}
    if not isinstance(dados, dict) or dados.get("ano") != ano:
        raise ValueError("Resposta sem o período solicitado; comparação recusada")
    if rota in {"indicadores", "sde"} and dados.get("mes") != mes:
        raise ValueError("Resposta sem o mês solicitado")
    if rota == "sde":
        return {"total_ejs": dados["total_ejs"], "cenarios": [
            {"nome": c["nome"], "sde": c["sde"], **{grupo: sorted(
                (ej["id_ej"], ej["cluster_atual"], ej["cluster_calculado"]) for ej in c[grupo]
            ) for grupo in ("subindo", "mantendo", "descendo")}}
            for c in dados["cenarios"]]}
    if rota == "ritmo-mensal":
        return {"meses": [{k: m[k] for k in ("mes", "ejs_ritmo_minimo", "ejs_ritmo_significativo", "total_ejs")}
                           for m in dados["meses"]]}
    campos = {"ano", "mes", "faturamento_total", "faturamento_colab_total", "total_projetos",
              "media_csat", "total_ejs", "ejs_fora_do_zero", "ejs_ritmo_minimo",
              "ejs_ritmo_significativo", "sde", "crescimento_vs_ano_anterior", "distribuicao_clusters"}
    if set(dados) != campos or any(k not in {str(n) for n in range(1, 6)} for k in dados["distribuicao_clusters"]):
        raise ValueError("Contrato de indicadores incompatível")
    return dados


def comparar(a, b, tolerancia, caminho=""):
    resultados = []
    for chave in sorted(a.keys() | b.keys()):
        campo = f"{caminho}.{chave}" if caminho else chave
        if chave not in a or chave not in b:
            resultados.append({"metrica": campo, "status": "campo_ausente"})
            continue
        x, y = a[chave], b[chave]
        if isinstance(x, dict) and isinstance(y, dict):
            resultados.extend(comparar(x, y, tolerancia, campo))
            continue
        if type(x) in (int, float) and type(y) in (int, float):
            igual = math.isfinite(x) and math.isfinite(y) and math.isclose(x, y, rel_tol=0, abs_tol=tolerancia)
        else:
            igual = type(x) is type(y) and x == y
        resultados.append({"metrica": campo, "status": "igual" if igual else "divergente"})
    return resultados


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origem", required=True, help="URL da API terminada em /api/v1")
    parser.add_argument("--destino", required=True)
    parser.add_argument("--ano", required=True, type=int)
    parser.add_argument("--mes", required=True, type=int, choices=range(1, 13))
    parser.add_argument("--tolerancia", type=float, default=0.01, help="tolerância absoluta; relativa zero")
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.tolerancia) or args.tolerancia < 0:
        parser.error("tolerância deve ser finita e não negativa")
    tokens = [os.environ.get(nome) for nome in ("REGRESSAO_TOKEN_ORIGEM", "REGRESSAO_TOKEN_DESTINO")]
    if not all(tokens):
        parser.error("configure REGRESSAO_TOKEN_ORIGEM e REGRESSAO_TOKEN_DESTINO no ambiente")
    try:
        linhas = []
        for rota in ("indicadores", "sde", "ritmo-mensal", "ranking"):
            origem = consultar(args.origem, tokens[0], args.ano, args.mes, rota)
            destino = consultar(args.destino, tokens[1], args.ano, args.mes, rota)
            linhas.extend(comparar(origem, destino, args.tolerancia, rota))
    except Exception as exc:
        # bibliotecas podem incluir URL/conteúdo: somente o tipo é seguro aqui
        raise SystemExit(f"Comparação não executada: {type(exc).__name__}; detalhes privados omitidos") from None
    relatorio = {"ano": args.ano, "mes": args.mes, "tolerancia_absoluta": args.tolerancia,
                 "escopo": "indicadores, SDE, ritmo e ranking de faturamento top100; valores, URLs e identidades omitidos", "metricas": linhas}
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n")
    divergencias = sum(linha["status"] != "igual" for linha in linhas)
    print(f"Comparadas {len(linhas)} métricas; {divergencias} divergências. Valores privados omitidos.")
    return int(divergencias > 0)


if __name__ == "__main__":
    raise SystemExit(main())
