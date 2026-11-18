"""Avaliação manual com custo do briefing do mês, sobre um retrato local dos dados.

Uso (a partir de backend/):

    python -m app.ia.avaliacao.briefing --dados <retrato.json> \\
        --federacoes 12 4 --meses 3 7 11 --saida ../docs/ia-avaliacao-briefing-<data>.json \\
        --textos <pasta fora do repositório>/textos.json

`--dados` é um JSON com as tabelas `empresa_junior`, `monitoramento`, `metas`,
`cluster_historico` e `federacao` (exportado do Postgres pelo dono do banco). As
regras e o redator são exatamente os da aplicação; só o acesso ao banco é trocado
por um cliente em memória. Isolamento e RLS não são o objeto desta avaliação (têm
suítes próprias).

O que vai para o arquivo versionado (`--saida`): por caso, federação anonimizada
(A, B…), mês, status das guardas, motivo de recusa, nº de frases, tokens e duração.
Frases, números e nomes reais vão só para `--textos`, que deve ficar fora do
repositório: servem à conferência manual de fidelidade.
"""

import argparse
import json
import string
from datetime import datetime
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.config import settings
from app.ia.briefing import RedatorCompativel, montar_fatos, validar_redacao
from app.ia.provedor import ProvedorIndisponivel
from app.services.analise_service import analisar_mes_com_nomes


class _Consulta:
    def __init__(self, linhas: list[dict]):
        self.linhas = linhas

    def select(self, *_a, **_k):
        return self

    def eq(self, coluna, valor):
        return _Consulta([l for l in self.linhas if l.get(coluna) == valor])

    def in_(self, coluna, valores):
        conjunto = set(valores)
        return _Consulta([l for l in self.linhas if l.get(coluna) in conjunto])

    def lte(self, coluna, valor):
        return _Consulta([l for l in self.linhas if l.get(coluna) is not None and l[coluna] <= valor])

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        return _Consulta(self.linhas[:n])

    def range(self, inicio, fim):
        fatia = _Consulta(self.linhas[inicio:fim + 1])
        fatia.total = len(self.linhas)
        return fatia

    def execute(self):
        return SimpleNamespace(data=self.linhas, count=getattr(self, "total", len(self.linhas)))


class ClienteEmMemoria:
    def __init__(self, tabelas: dict[str, list[dict]]):
        self.tabelas = tabelas

    def table(self, nome):
        return _Consulta(list(self.tabelas.get(nome) or []))

    def rpc(self, _nome):
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dados", type=Path, required=True)
    parser.add_argument("--federacoes", type=int, nargs="+", required=True)
    parser.add_argument("--meses", type=int, nargs="+", required=True)
    parser.add_argument("--ano", type=int, default=settings.ANO_DEFAULT)
    parser.add_argument("--modelo", default=settings.IA_MODELO)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--textos", type=Path, required=True)
    args = parser.parse_args()
    settings.IA_MODELO = args.modelo
    redator = RedatorCompativel()
    if not redator.configurado:
        parser.error("Configure IA_MODELO e IA_API_KEY.")

    sb = ClienteEmMemoria(json.loads(args.dados.read_text()))
    nomes_fed = {f["id"]: f["nome"] for f in sb.tabelas.get("federacao") or []}
    rotulos = {fid: string.ascii_uppercase[i] for i, fid in enumerate(args.federacoes)}

    resultados, textos = [], []
    for fid in args.federacoes:
        for mes in args.meses:
            analise, nomes = analisar_mes_com_nomes(sb, ano=args.ano, mes=mes, federacao_id=fid)
            fatos = montar_fatos(analise, nomes_fed.get(fid))
            item = {"federacao": rotulos[fid], "mes": mes, "ejs": analise.resumo.total_ejs}
            inicio = monotonic()
            try:
                redacao = redator.redigir(fatos)
                motivo = validar_redacao(redacao.frases, fatos, nomes)
                item.update(status="aceito" if motivo is None else "recusado", motivo=motivo,
                            frases=len(redacao.frases), tokens_entrada=redacao.tokens_entrada,
                            tokens_saida=redacao.tokens_saida, modelo=redacao.modelo)
                textos.append({"federacao": rotulos[fid], "mes": mes, "fatos": fatos,
                               "frases": redacao.frases, "motivo": motivo, "fixo": analise.briefing.frases})
            except ProvedorIndisponivel:
                # Não versionar o erro do fornecedor.
                item.update(status="indisponivel")
            item["duracao_ms"] = round((monotonic() - inicio) * 1000)
            resultados.append(item)
            print(item)

    aceitos = [r for r in resultados if r["status"] == "aceito"]
    resumo = {
        "casos": len(resultados),
        "aceitos": len(aceitos),
        "recusados": sum(r["status"] == "recusado" for r in resultados),
        "indisponiveis": sum(r["status"] == "indisponivel" for r in resultados),
        "motivos_de_recusa": {m: sum(r.get("motivo") == m for r in resultados)
                              for m in sorted({r["motivo"] for r in resultados if r.get("motivo")})},
        "tokens_entrada": sum(r.get("tokens_entrada", 0) for r in resultados),
        "tokens_saida": sum(r.get("tokens_saida", 0) for r in resultados),
    }
    instante = datetime.now(ZoneInfo("America/Recife"))
    args.saida.write_text(json.dumps({"data": instante.isoformat(), "modelo": args.modelo, "ano": args.ano,
                                      "resumo": resumo, "resultados": resultados},
                                     ensure_ascii=False, indent=2) + "\n")
    args.textos.write_text(json.dumps(textos, ensure_ascii=False, indent=2) + "\n")
    print(resumo)


if __name__ == "__main__":
    main()
