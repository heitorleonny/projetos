"""Gera configuração privada para o Compose PostgreSQL, sem sobrescrever arquivos.

Local (padrão):  python3 scripts/configurar_docker.py
Produção (VPS):  python3 scripts/configurar_docker.py --producao \\
                     --dominio federacoes.portalfejepe.cloud \\
                     --destino /opt/portal-federacoes/.env.prod

Em produção o domínio entra no link de convite e no CORS; IA_* ficam vazias
(Nexo e resumo por IA desligados até o operador decidir o provedor).
"""
import argparse
import re
import secrets
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOMINIO = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def valores_base() -> dict[str, str]:
    return {
        'POSTGRES_DB': 'portal',
        'POSTGRES_USER': 'portal_owner',
        'POSTGRES_PASSWORD': secrets.token_hex(32),
        'APP_DB_PASSWORD': secrets.token_hex(32),
        'AUTH_DB_PASSWORD': secrets.token_hex(32),
        'INGESTAO_DB_PASSWORD': secrets.token_hex(32),
        'FRONTEND_PORT': '8080',
        'TENANT_SLUG': 'fejepe',
    }


def valores_producao(dominio: str) -> dict[str, str]:
    dominio = dominio.strip().lower()
    if not DOMINIO.match(dominio):
        raise SystemExit('Domínio inválido: use só o nome, sem protocolo nem barra (ex.: portal.exemplo.org).')
    return valores_base() | {
        'PORTAL_DOMAIN': dominio,
        'CONVITE_REDIRECT_URL': f'https://{dominio}/definir-senha',
        'CORS_ORIGINS': f'https://{dominio}',
        'DOCS_ENABLED': 'false',
        'IA_PROVEDOR': 'openrouter',
        'IA_MODELO': '',
        'IA_API_KEY': '',
        'IA_BASE_URL': '',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--producao', action='store_true', help='gera o arquivo de produção da VPS')
    parser.add_argument('--dominio', help='domínio público (obrigatório com --producao)')
    parser.add_argument('--destino', type=Path, help='arquivo a criar (padrão: .env.docker na raiz)')
    args = parser.parse_args()

    if args.producao:
        if not args.dominio or not args.destino:
            parser.error('--producao exige --dominio e --destino.')
        valores = valores_producao(args.dominio)
    else:
        valores = valores_base()
    destino = args.destino or (RAIZ / '.env.docker')

    try:
        with destino.open('x') as arquivo:
            destino.chmod(0o600)
            arquivo.write('# Gerado localmente. Não versionar ou compartilhar.\n')
            arquivo.writelines(f'{chave}={valor}\n' for chave, valor in valores.items())
    except FileExistsError:
        raise SystemExit(f'{destino.name} já existe; preservado. Use-o com --env-file.') from None
    print(f'Criado {destino} (permissão 600). Nenhuma senha foi exibida.')


if __name__ == '__main__':
    main()
