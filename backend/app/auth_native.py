"""Senhas PBKDF2 e sessões opacas: o token não contém papel nem federação."""
import hashlib
import hmac
import secrets
from types import SimpleNamespace
import psycopg
from psycopg import sql
from fastapi import HTTPException
from app.config import settings


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def hash_senha(senha):
    if not 12 <= len(senha) <= 256:
        raise ValueError('A senha deve ter entre 12 e 256 caracteres.')
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt.encode(), 600000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'


def conferir_senha(senha, codificada):
    try:
        algoritmo, n, salt, esperado = codificada.split('$')
        if algoritmo != 'pbkdf2_sha256' or int(n)!=600000: return False
        atual = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt.encode(), int(n)).hex()
        return hmac.compare_digest(atual, esperado)
    except (ValueError,AttributeError): return False


def operacao(nome, *params):
    permitidas = {'portal_conta','portal_criar_sessao','portal_sessao_atual','portal_sair','portal_senha','portal_convidar'}
    if nome not in permitidas: raise ValueError('Operação inválida')
    try:
        with psycopg.connect(settings.AUTH_DATABASE_DSN, connect_timeout=5) as conn:
            row = conn.execute('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
            if row[0] or row[1]: raise RuntimeError('Autenticação exige conta restrita')
            return conn.execute(sql.SQL('SELECT auth.{}({})').format(sql.Identifier(nome),sql.SQL(',').join(sql.Placeholder() for _ in params)),params).fetchone()[0]
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409,'Já existe uma conta com esse e-mail.') from None
    except psycopg.errors.InsufficientPrivilege:
        raise HTTPException(403,'Operação não permitida.') from None
    except psycopg.Error:
        raise HTTPException(503,'Autenticação temporariamente indisponível.') from None


def autenticar(token):
    if not token or len(token)>256: raise HTTPException(401,'Sessão inválida ou expirada.')
    conta = operacao('portal_sessao_atual',hash_token(token))
    if not conta: raise HTTPException(401,'Sessão inválida ou expirada.')
    return SimpleNamespace(id=conta['id'],email=conta['email'],user_metadata={'nome':conta['nome']},app_metadata={'federacao_id':conta['federacao_id'],'papel':conta['papel']})


def publico(user):
    return {'id':user.id,'email':user.email,'app_metadata':user.app_metadata,'user_metadata':user.user_metadata}


def entrar(email,senha):
    conta = operacao('portal_conta',email.strip().lower())
    # Também executa o KDF quando a conta não existe, sem revelar cadastro.
    codificada = conta.get('password_hash') if conta else None
    dummy = 'pbkdf2_sha256$600000$'+('0'*32)+'$'+('0'*64)
    valido = conferir_senha(senha,codificada or dummy)
    if not valido or not codificada: raise HTTPException(401,'E-mail ou senha inválidos, ou limite de tentativas atingido.')
    token = secrets.token_urlsafe(48)
    operacao('portal_criar_sessao',conta['id'],hash_token(token))
    return {'access_token':token,'user':publico(autenticar(token))}
