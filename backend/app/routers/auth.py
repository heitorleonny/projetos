from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from app import auth_native as auth
from app.dependencies import _bearer_scheme

router=APIRouter(prefix='/api/v1/auth',tags=['Autenticação'])
class Login(BaseModel):
    email: str = Field(min_length=3,max_length=254)
    password: str = Field(min_length=1,max_length=256)
class Senha(BaseModel):
    password: str = Field(min_length=12,max_length=256)
    convite: str | None = Field(default=None,max_length=256)

@router.post('/login')
def login(body: Login, response: Response):
    response.headers['Cache-Control']='no-store'
    return auth.entrar(body.email,body.password)

@router.get('/me')
def me(response: Response, cred=Depends(_bearer_scheme)):
    response.headers['Cache-Control']='no-store'
    return auth.publico(auth.autenticar(cred.credentials if cred else ''))

@router.post('/logout',status_code=204)
def logout(cred=Depends(_bearer_scheme)):
    if cred: auth.operacao('portal_sair',auth.hash_token(cred.credentials))

@router.post('/senha',status_code=204)
def senha(body: Senha, cred=Depends(_bearer_scheme)):
    token=body.convite or (cred.credentials if cred else '')
    if not token or not auth.operacao('portal_senha',auth.hash_token(token),auth.hash_senha(body.password),bool(body.convite)):
        raise HTTPException(401,'Sessão ou convite inválido/expirado.')
