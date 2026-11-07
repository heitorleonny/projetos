"""Empacota o código atual, inclusive arquivos novos, sem segredos/artefatos locais."""

import argparse
import base64
import json
import re
import subprocess
import tarfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SEGREDOS = re.compile(r"\b(?:sb_secret_[A-Za-z0-9_-]{16,}|sk-or-v1-[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b")
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]{10,}\b")
EXCLUIDOS = {".git", ".venv", "node_modules", "dist", "__pycache__", ".pytest_cache", "artifacts"}


def arquivos_codigo():
    resultado = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=RAIZ, capture_output=True, check=True,
    )
    arquivos = []
    for nome in sorted(set(resultado.stdout.decode().split("\0")) - {""}):
        relativo = Path(nome)
        caminho = RAIZ / relativo
        if not caminho.exists() or any(parte in EXCLUIDOS for parte in relativo.parts):
            continue
        if relativo.parts[:2] == ("supabase", "snippets"):
            continue  # consultas locais avulsas não são fonte do schema
        if relativo.parts[:2] == ("docs", "evidencias-nexo") or (relativo.parts[0] == "docs" and relativo.suffix == ".json"):
            continue  # relatórios brutos de avaliação podem conter linhas reais
        if relativo.name.startswith(".env") and not relativo.name.endswith(".example"):
            continue
        if relativo.suffix.lower() in {".xlsx", ".xls", ".csv", ".tsv", ".pem", ".key"}:
            continue
        if caminho.is_symlink():
            raise ValueError(f"Link simbólico precisa de revisão antes da entrega: {nome}")
        conteudo = caminho.read_bytes()
        if b"\x00" not in conteudo:
            texto = conteudo.decode("utf-8", errors="replace")
            if SEGREDOS.search(texto):
                raise ValueError(f"Possível credencial no arquivo: {nome}; valor omitido")
            for jwt in JWT.finditer(texto):
                payload = jwt.group(1)
                try:
                    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
                except (ValueError, UnicodeError):
                    continue
                if isinstance(claims, dict) and claims.get("role") == "service_role":
                    raise ValueError(f"Possível service key JWT no arquivo: {nome}; valor omitido")
        arquivos.append(relativo)
    return arquivos


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="verifica conteúdo sem gerar pacote")
    parser.add_argument("--saida", type=Path, default=RAIZ / "artifacts/portal-das-federacoes-src.tar.gz")
    args = parser.parse_args()
    arquivos = arquivos_codigo()
    obrigatorios = ["backend/app/main.py", "frontend/package.json", "infra/db/init/22-administracao-master.sql"]
    for nome in obrigatorios:
        if Path(nome) not in arquivos:
            raise ValueError(f"Código obrigatório ausente: {nome}")
    if not args.verificar:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(args.saida, "w:gz") as pacote:
            for relativo in arquivos:
                pacote.add(RAIZ / relativo, arcname=Path("portal-das-federacoes") / relativo, recursive=False)
        print(f"Pacote criado: {args.saida.resolve()}")
    print(f"Verificados {len(arquivos)} arquivos; conteúdo local e credenciais conhecidas excluídos.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from None
