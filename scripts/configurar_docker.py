"""Gera configuração privada para o Compose PostgreSQL, sem sobrescrever arquivos."""
from pathlib import Path
import secrets

RAIZ = Path(__file__).resolve().parents[1]

def main():
    destino = RAIZ / '.env.docker'
    valores = {
        'POSTGRES_DB': 'portal',
        'POSTGRES_USER': 'portal_owner',
        'POSTGRES_PASSWORD': secrets.token_hex(32),
        'APP_DB_PASSWORD': secrets.token_hex(32),
        'AUTH_DB_PASSWORD': secrets.token_hex(32),
        'INGESTAO_DB_PASSWORD': secrets.token_hex(32),
        'FRONTEND_PORT': '8080',
        'TENANT_SLUG': 'fejepe',
    }
    try:
        with destino.open('x') as arquivo:
            destino.chmod(0o600)
            arquivo.write('# Gerado localmente. Não versionar ou compartilhar.\n')
            arquivo.writelines(f'{chave}={valor}\n' for chave, valor in valores.items())
    except FileExistsError:
        raise SystemExit('.env.docker já existe; preservado. Use-o com --env-file .env.docker.') from None
    print('Criado .env.docker (permissão 600). Nenhuma senha foi exibida.')

if __name__ == '__main__':
    main()
