"""Executa o portal contra a demo local sem copiar chaves para arquivos ou logs."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote, urlsplit


RAIZ = Path(__file__).resolve().parents[1]


def status_demo() -> dict:
    resultado = subprocess.run(
        ["supabase", "status", "-o", "json"], cwd=RAIZ,
        capture_output=True, text=True,
    )
    if resultado.returncode:
        raise RuntimeError("Demo indisponível. Execute `make demo` com o Docker aberto.")
    return json.loads(resultado.stdout)


def preparar() -> None:
    # A saída da CLI inclui chaves. Guardá-la em memória evita publicá-las no log.
    resultado = subprocess.run(["supabase", "start"], cwd=RAIZ, capture_output=True, text=True)
    if resultado.returncode:
        raise RuntimeError("Não foi possível iniciar a demo. Verifique Docker, portas 544xx e `supabase status`.")
    status = status_demo()
    import psycopg

    with psycopg.connect(status["DB_URL"], connect_timeout=5) as conexao:
        existe = conexao.execute("SELECT to_regclass('public.empresa_junior') IS NOT NULL").fetchone()[0]
        if existe:
            # Não se reaplicam migrações históricas sobre um banco já populado.
            # O comando não tenta adivinhar nem corrigir uma migração parcial.
            atual = conexao.execute("""
                SELECT to_regprocedure('public.admin_listar_usuarios()') IS NOT NULL
                   AND EXISTS (SELECT 1 FROM information_schema.columns
                                WHERE table_schema='public' AND table_name='federacao'
                                  AND column_name='slogan')
                   AND EXISTS (SELECT 1 FROM information_schema.column_privileges
                                WHERE table_schema='public' AND table_name='federacao'
                                  AND column_name='slogan' AND grantee='authenticated'
                                  AND privilege_type='UPDATE')
                   AND EXISTS (SELECT 1 FROM information_schema.columns
                                WHERE table_schema='public' AND table_name='monitoramento'
                                  AND column_name='projetos_colab_mes')
                   AND to_regclass('public.dashboard_evento_ia') IS NOT NULL
                   AND to_regprocedure('public.master_resumo_federacoes()') IS NOT NULL
                   AND NOT has_function_privilege('anon','public.reservar_consulta_ia()','EXECUTE')
            """).fetchone()[0]
            if not atual:
                raise RuntimeError("Demo com schema antigo ou parcial. Aplique as migrações pendentes em infra/db/init sem apagar os dados; `make demo-reset` apaga os volumes.")
    if not existe:
        subprocess.run(["make", "demo-schema"], cwd=RAIZ, check=True)
    print("Demo disponível; dados existentes preservados. Studio: http://localhost:54423")
    print("Inicie o portal em dois terminais: make demo-backend / make demo-frontend")


def esquema() -> None:
    """Banco novo da CLI recebe o executor canônico, sem reaplicar schema legado."""
    status = status_demo()
    import psycopg

    with psycopg.connect(status["DB_URL"], connect_timeout=5) as conexao:
        destino = conexao.execute("SELECT current_database()").fetchone()[0]
    ambiente = os.environ.copy()
    ambiente["PORTAL_DATABASE_URL"] = status["DB_URL"]
    subprocess.run(
        [sys.executable, "-m", "scripts.migrar_banco", "--apply", "--confirm-database", destino],
        cwd=RAIZ / "backend", env=ambiente, check=True,
    )


def executar(servico: str) -> None:
    status = status_demo()
    ambiente = os.environ.copy()
    if servico in ("backend", "verificar"):
        porta_db = urlsplit(status["DB_URL"]).port or 54422
        senha_ingestao = quote(ambiente.get("INGESTAO_SENHA", "app_ingestao"), safe="")
        ambiente.update({
            "SUPABASE_URL": status["API_URL"],
            "SUPABASE_ANON_KEY": status["ANON_KEY"],
            "SUPABASE_SERVICE_KEY": status["SERVICE_ROLE_KEY"],
            "SUPABASE_KEY": "",
            "INGESTAO_DSN": f"postgresql://app_ingestao:{senha_ingestao}@127.0.0.1:{porta_db}/postgres",
            "CONVITE_REDIRECT_URL": "http://localhost:5173/definir-senha",
            "CORS_ORIGINS": "http://127.0.0.1:5173,http://localhost:5173,http://localhost:8080",
            "DOCS_ENABLED": "true",
            "TENANT_CLAIM_OBRIGATORIO": "true",
            "ANO_DEFAULT": ambiente.get("ANO_DEFAULT", "2026"),
        })
        diretorio = RAIZ / "backend"
        comando = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
        if servico == "verificar":
            comando = [sys.executable, "-m", "scripts.verificar_demo"]
    else:
        ambiente.update({
            "VITE_API_BASE_URL": "http://127.0.0.1:8000/api/v1",
            "VITE_SUPABASE_URL": status["API_URL"],
            "VITE_SUPABASE_ANON_KEY": status["ANON_KEY"],
            "VITE_USE_MOCK": "false",
            "VITE_TENANT_SLUG": ambiente.get("TENANT_SLUG", "fejepe"),
        })
        # As chaves de servidor não precisam ser herdadas pelo processo do Vite.
        for nome in ("SUPABASE_SERVICE_KEY", "INGESTAO_DSN", "SUPABASE_KEY"):
            ambiente.pop(nome, None)
        diretorio = RAIZ / "frontend"
        comando = ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"]
    os.chdir(diretorio)
    os.execvpe(comando[0], comando, ambiente)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["preparar", "esquema", "backend", "frontend", "verificar"])
    args = parser.parse_args()
    try:
        if args.acao == "preparar":
            preparar()
        elif args.acao == "esquema":
            esquema()
        else:
            executar(args.acao)
    except (RuntimeError, FileNotFoundError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"Demo: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
