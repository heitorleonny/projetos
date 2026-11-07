#!/usr/bin/env python3
"""Valida a configuração de deploy sem imprimir valores ou segredos."""
import argparse
import base64
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, unquote


def validar(arquivo: Path, modo: str) -> list[str]:
    # O manifesto histórico compose.aws.yml serve qualquer VPS com Docker.
    if modo == 'vps':
        modo = 'aws'
    valores = {}
    for linha in arquivo.read_text().splitlines():
        linha = linha.strip()
        if linha and not linha.startswith('#') and '=' in linha:
            chave, valor = linha.split('=', 1)
            valores[chave.strip()] = valor.strip().strip('\"\'')
    erros = []

    def exigir(chave):
        valor = valores.get(chave, '')
        if not valor or re.search(r'SUBSTITUIR|SEU-PROJETO|SUA-API|example\.com', valor, re.I):
            erros.append(f'{chave}: ausente ou exemplo ainda não substituído.')
        return valor

    def https(chave):
        valor = exigir(chave)
        try:
            url = urlsplit(valor)
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                erros.append(f'{chave}: exige URL HTTPS sem credenciais.')
        except ValueError:
            erros.append(f'{chave}: URL inválida.')
        return valor

    prefixo = 'VITE_' if modo == 'vercel' else ''
    https(prefixo + 'SUPABASE_URL')
    chave = prefixo + 'SUPABASE_ANON_KEY'
    valor = exigir(chave)
    if valor.startswith('sb_secret_'):
        erros.append(f'{chave}: chave secreta proibida no caminho público.')
    elif valor.count('.') == 2:
        try:
            parte = valor.split('.')[1]
            claims = json.loads(base64.urlsafe_b64decode(parte + '=' * (-len(parte) % 4)))
            if not isinstance(claims, dict) or claims.get('role') != 'anon':
                erros.append(f'{chave}: JWT exige papel anon.')
        except (ValueError, TypeError):
            erros.append(f'{chave}: JWT inválido.')
    elif not valor.startswith('sb_publishable_'):
        erros.append(f'{chave}: exige chave pública Supabase reconhecida.')

    if modo == 'vercel':
        api = https('VITE_API_BASE_URL')
        if not api.rstrip('/').endswith('/api/v1'):
            erros.append('VITE_API_BASE_URL: deve terminar em /api/v1.')
        if valores.get('VITE_USE_MOCK') != 'false':
            erros.append('VITE_USE_MOCK: deve ser false no beta.')
        for chave in valores:
            if chave.startswith('VITE_') and any(p in chave for p in ('SERVICE', 'SECRET', 'DSN', 'IA_API_KEY')):
                erros.append(f'{chave}: segredo não pode entrar no bundle.')
    elif modo == 'aws':
        dominio = exigir('PORTAL_DOMAIN')
        if not re.fullmatch(r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', dominio):
            erros.append('PORTAL_DOMAIN: use somente o domínio, sem esquema ou caminho.')
        if '@' not in exigir('ACME_EMAIL'):
            erros.append('ACME_EMAIL: endereço inválido.')
    if modo in ('aws', 'render'):
        if modo == 'render':
            for chave, esperado in [('DOCS_ENABLED', 'false'), ('TENANT_CLAIM_OBRIGATORIO', 'true')]:
                if valores.get(chave) != esperado:
                    erros.append(f'{chave}: deve ser {esperado} no beta.')
            origem = exigir('CORS_ORIGINS')
            origens = []
            for item in origem.split(','):
                try:
                    url = urlsplit(item.strip())
                    if (url.scheme != 'https' or not url.hostname or '*' in item
                            or url.username or url.password or url.path or url.query or url.fragment):
                        erros.append('CORS_ORIGINS: exige origens HTTPS exatas, sem caminho ou wildcard.')
                    else:
                        origens.append(item.strip())
                except ValueError:
                    erros.append('CORS_ORIGINS: origem inválida.')
            retorno = https('CONVITE_REDIRECT_URL')
            try:
                url = urlsplit(retorno)
                if url.path != '/definir-senha' or url.query or url.fragment or f'{url.scheme}://{url.netloc}' not in origens:
                    erros.append('CONVITE_REDIRECT_URL: exige /definir-senha em uma origem CORS permitida.')
            except ValueError:
                erros.append('CONVITE_REDIRECT_URL: retorno inválido.')
        if not exigir('SUPABASE_SERVICE_KEY'):
            erros.append('SUPABASE_SERVICE_KEY: necessária para habilitar convites no beta completo.')
        dsn = exigir('INGESTAO_DSN')
        try:
            url = urlsplit(dsn)
            # Pooler Supabase acrescenta .project-ref ao nome do login.
            login = unquote(url.username or '').split('.')[0].lower()
            if url.scheme not in ('postgres', 'postgresql') or login in ('', 'postgres', 'portal', 'service_role', 'supabase_admin'):
                erros.append('INGESTAO_DSN: exige login próprio sujeito a RLS.')
            if not url.password or not url.hostname or not re.search(r'(?:[?&])sslmode=(require|verify-ca|verify-full)(?:&|$)', dsn):
                erros.append('INGESTAO_DSN: exige credenciais e SSL.')
        except ValueError:
            erros.append('INGESTAO_DSN: conexão inválida.')
        if valores.get('IA_API_KEY') or valores.get('IA_MODELO'):
            exigir('IA_API_KEY')
            exigir('IA_MODELO')
        if valores.get('IA_BASE_URL'):
            https('IA_BASE_URL')
    return erros


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env', required=True, type=Path)
    parser.add_argument('--mode', required=True, choices=['aws', 'vps', 'vercel', 'render'])
    args = parser.parse_args()
    try:
        erros = validar(args.env, args.mode)
    except (OSError, UnicodeError):
        parser.exit(1, 'Não foi possível ler o arquivo de configuração.\n')
    for erro in erros:
        print(erro)
    if erros:
        parser.exit(1, 'Configuração ainda não está pronta. Nenhum valor foi exibido.\n')
    print('Configuração local válida. Credenciais e permissões remotas ainda exigem verificação.')
