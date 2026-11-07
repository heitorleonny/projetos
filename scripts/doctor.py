"""Diagnóstico local; não lê nem imprime arquivos .env ou credenciais."""

from pathlib import Path
import shutil
import subprocess
import sys

RAIZ = Path(__file__).resolve().parents[1]


def main() -> int:
    falhas = []
    for nome in ("docker", "node", "npm"):
        presente = shutil.which(nome) is not None
        print(f"{'OK' if presente else 'FALTA'}: {nome}")
        if not presente:
            falhas.append(nome)
    for caminho in (".venv/bin/python", "frontend/node_modules"):
        presente = (RAIZ / caminho).exists()
        print(f"{'OK' if presente else 'FALTA'}: {caminho}")
        if not presente:
            falhas.append(caminho)
    if shutil.which("docker"):
        resultado = subprocess.run(["docker", "info"], capture_output=True)
        print("OK: Docker iniciado" if resultado.returncode == 0 else "FALTA: iniciar Docker Desktop")
        if resultado.returncode:
            falhas.append("Docker iniciado")
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=RAIZ, capture_output=True, text=True)
    print(f"Branch atual: {branch.stdout.strip()}")
    print("Dependências: make setup | Testes completos: make check | Docker: make docker-config && make up")
    return bool(falhas)


if __name__ == "__main__":
    sys.exit(main())
