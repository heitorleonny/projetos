"""
Importa a planilha de monitoramento do Portal BJ (nível EJ) no banco.

    cd backend
    python -m scripts.importar_planilha \\
        --arquivo ~/Documents/TCC/dados/monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx \\
        --ano 2026 \\
        (--todas-federacoes | --federacao fejepe) \\
        [--dry-run]

Ou, da raiz do repositório: `make importar ARQUIVO=... ANO=2026 ESCOPO=--todas-federacoes`.

O escopo é obrigatório e não tem default: `--todas-federacoes` importa as 27
federações; `--federacao <slug>` importa só a fatia daquela federação e conta o
resto como ignorado. `--dry-run` roda a carga inteira e desfaz a transação no
fim — as contagens são as reais, e nada fica gravado. Rode com ele primeiro.

CONEXÃO: `--dsn`, ou a variável INGESTAO_DSN, ou o papel `app_ingestao` do
laboratório (localhost:55432). A carga se recusa a rodar com papel que ignora
Row Level Security — superusuário, BYPASSRLS, dono das tabelas —, que é o
equivalente local da service key.

Saída: 0 sucesso; 1 carga rejeitada ou recusada pelo banco; 2 uso errado ou
banco inacessível.
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg
from psycopg.conninfo import conninfo_to_dict

from app.ingestao.carga import ErroCarga, ErroPapel
from app.ingestao.contrato import ABA_PADRAO, ErroContrato
from app.ingestao.importacao import ErroEscopo, Escopo, como_texto, importar


def _dsn_padrao() -> str:
    # Credencial do laboratório, pública e versionada de propósito (ver
    # infra/db/init/10-ingestao-staging.sql). Porta 55432, não 5432: ver infra/db/README.md.
    porta = os.getenv("POSTGRES_PORT", "55432")
    return os.getenv("INGESTAO_DSN", f"postgresql://app_ingestao:app_ingestao@localhost:{porta}/portal_lab")


def _destino(dsn: str) -> str:
    """Para onde a carga vai, sem a senha."""
    partes = conninfo_to_dict(dsn)
    return f"{partes.get('user', '?')}@{partes.get('host', 'localhost')}:{partes.get('port', '5432')}/{partes.get('dbname', '?')}"


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.importar_planilha",
        description="Importa a planilha de monitoramento do Portal BJ (nível EJ).",
    )
    parser.add_argument("--arquivo", required=True, help="caminho do .xlsx exportado do Portal BJ")
    parser.add_argument("--ano", type=int, required=True, help="ano de referência da exportação (a planilha não traz)")
    escopo = parser.add_mutually_exclusive_group(required=True)
    escopo.add_argument("--todas-federacoes", action="store_true", help="importa as 27 federações (escopo nacional)")
    escopo.add_argument("--federacao", metavar="SLUG", help="importa só a fatia desta federação (ex.: fejepe)")
    parser.add_argument("--dry-run", action="store_true", help="valida, transforma e relata o que faria, sem gravar nada")
    parser.add_argument("--aba", default=ABA_PADRAO, help=f"aba da planilha (padrão: {ABA_PADRAO})")
    parser.add_argument("--dsn", default=None, help="conexão Postgres (padrão: INGESTAO_DSN ou o app_ingestao do lab)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    escopo = Escopo.nacional() if args.todas_federacoes else Escopo.federacao(args.federacao)
    dsn = args.dsn or _dsn_padrao()
    print(f"Destino: {_destino(dsn)}{'  [SIMULAÇÃO]' if args.dry_run else ''}", flush=True)

    try:
        with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conexao:
            relatorio = importar(conexao, args.arquivo, ano=args.ano, escopo=escopo, simular=args.dry_run, aba=args.aba)
    except psycopg.OperationalError as exc:
        print(f"Não consegui conectar em {_destino(dsn)}. O laboratório está no ar (`make lab`)?\n{exc}", file=sys.stderr)
        return 2
    except (ErroEscopo, ErroPapel) as exc:
        print(f"Carga não iniciada: {exc}", file=sys.stderr)
        return 2
    except ErroContrato as exc:
        registrada = getattr(exc, "carga_id", None)
        sufixo = f"\nRegistrada como carga #{registrada} (status 'rejeitada')." if registrada else ""
        print(f"CARGA REJEITADA — nada foi gravado.\n{exc}{sufixo}", file=sys.stderr)
        return 1
    except ErroCarga as exc:
        sufixo = (
            f"\nRegistrada como carga #{exc.carga_id} (status '{exc.status}'), com a staging das linhas para diagnóstico."
            if exc.carga_id else ""
        )
        titulo = "CARGA REJEITADA" if exc.status == "rejeitada" else "CARGA RECUSADA PELO BANCO"
        print(f"{titulo} — {exc}{sufixo}", file=sys.stderr)
        return 1

    print(como_texto(relatorio))
    return 0


if __name__ == "__main__":
    sys.exit(main())
