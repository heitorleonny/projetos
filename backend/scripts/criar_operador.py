"""Bootstrap administrativo fora da API, para uma conta NOVA e senha privada."""
from __future__ import annotations
import argparse
import getpass
import os
import sys
from urllib.parse import urlsplit
from uuid import UUID
import httpx
import psycopg


def criar(conexao, cliente, url, chave, email, nome, slug, senha):
    federacao = conexao.execute('SELECT id FROM public.federacao WHERE slug = %s', (slug,)).fetchone()
    if not federacao:
        raise ValueError('Federação não encontrada.')
    if conexao.execute('SELECT 1 FROM public.usuario WHERE lower(email) = lower(%s)', (email,)).fetchone():
        raise ValueError('Conta existente; este bootstrap só cria contas novas.')
    headers = {'apikey': chave, 'Authorization': f'Bearer {chave}'}
    resposta = cliente.post(f'{url}/auth/v1/admin/users', headers=headers,
        json={'email': email, 'password': senha, 'email_confirm': True})
    if resposta.status_code != 200:
        raise ValueError('Auth recusou a criação. Nenhuma conta existente foi alterada.')
    usuario_id = str(UUID(resposta.json()['id']))
    try:
        with conexao.transaction():
            # Prova que o Auth que criou o UUID usa este mesmo banco.
            if not conexao.execute('SELECT 1 FROM auth.users WHERE id = %s AND lower(email) = lower(%s)', (usuario_id, email)).fetchone():
                raise ValueError('Auth e banco não correspondem ao mesmo projeto.')
            conexao.execute("INSERT INTO public.usuario (federacao_id,nome,email,papel,auth_user_id,conta_principal) VALUES (%s,%s,%s,'plataforma',%s,false)",
                (federacao[0], nome, email, usuario_id))
    except Exception:
        removida = cliente.delete(f'{url}/auth/v1/admin/users/{usuario_id}', headers=headers)
        if removida.status_code not in (200, 204):
            raise ValueError('Vínculo falhou e compensação Auth falhou; operador deve remover a conta recém-criada no Dashboard.') from None
        raise ValueError('Vínculo falhou; a conta Auth recém-criada foi removida.') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email', required=True)
    parser.add_argument('--nome', required=True)
    parser.add_argument('--federacao', required=True, help='Slug existente, vínculo explícito do operador.')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--confirm-project', help='Hostname exato de SUPABASE_URL, obrigatório com --apply.')
    args = parser.parse_args()
    url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    host = urlsplit(url).hostname
    if not host or not os.environ.get('PORTAL_DATABASE_URL'):
        parser.error('Configure SUPABASE_URL e PORTAL_DATABASE_URL.')
    if args.apply and args.confirm_project != host:
        parser.error('Confirme hostname exato do projeto com --confirm-project.')
    try:
        with psycopg.connect(os.environ['PORTAL_DATABASE_URL'], autocommit=True, connect_timeout=10) as conexao:
            if not args.apply:
                conexao.execute('SET default_transaction_read_only = on')
                if not conexao.execute('SELECT 1 FROM public.federacao WHERE slug=%s', (args.federacao,)).fetchone():
                    raise ValueError('Federação não encontrada.')
                if conexao.execute('SELECT 1 FROM public.usuario WHERE lower(email)=lower(%s)', (args.email,)).fetchone():
                    raise ValueError('Conta já existente; use outra conta nova.')
                print('Revisão concluída. --apply cria Auth e vínculo plataforma; senha não recebida nem gravada.')
                return 0
            chave = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
            if not chave:
                raise ValueError('Configure SUPABASE_SERVICE_ROLE_KEY somente neste processo administrativo.')
            senha = os.environ.get('PORTAL_OPERATOR_PASSWORD') or getpass.getpass('Senha da nova conta: ')
            if len(senha) < 12 or senha.lower() in ('demo1234', 'password1234'):
                raise ValueError('Use senha nova com pelo menos 12 caracteres.')
            with httpx.Client(timeout=30) as cliente:
                criar(conexao, cliente, url, chave, args.email, args.nome, args.federacao, senha)
            print('Operador novo criado. Ative o access token hook e valide login/tenant antes de distribuir acesso.')
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (psycopg.Error, httpx.HTTPError, KeyError):
        print('Falha de conexão/bootstrap. Revise o destino; credenciais e respostas Auth não são exibidas.', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
