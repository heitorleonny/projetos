"""Bootstrap explícito de conta; somente CLI com credencial de proprietário."""
import argparse
import getpass
import os
import uuid
import psycopg
from app.auth_native import hash_senha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--email',required=True)
    p.add_argument('--nome',required=True)
    p.add_argument('--federacao',type=int,required=True)
    args=p.parse_args()
    senha=os.environ.get('PORTAL_BOOTSTRAP_PASSWORD') or getpass.getpass('Senha (mínimo 12 caracteres): ')
    codificada=hash_senha(senha)
    dsn=os.environ.get('PORTAL_DATABASE_URL')
    kwargs={} if dsn else dict(host='postgres',dbname=os.environ['POSTGRES_DB'],user=os.environ['POSTGRES_USER'],password=os.environ['POSTGRES_PASSWORD'])
    with psycopg.connect(dsn or '',**kwargs) as conn:
        identidade=uuid.uuid4()
        conn.execute('INSERT INTO auth.users(id,email,password_hash) VALUES(%s,%s,%s)',(identidade,args.email.strip().lower(),codificada))
        conn.execute("INSERT INTO public.usuario(nome,email,papel,federacao_id,auth_user_id) VALUES(%s,%s,'plataforma',%s,%s)",(args.nome,args.email.strip().lower(),args.federacao,identidade))
    print('Operador criado. Nenhuma senha ou token foi exibido.')

if __name__=='__main__':
    try: main()
    except (psycopg.Error,KeyError): raise SystemExit('Bootstrap recusado: confira banco, federação e e-mail único. Valores omitidos.') from None
