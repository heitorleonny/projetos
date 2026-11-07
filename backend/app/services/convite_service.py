"""Convite local de uso único; não envia e-mail automaticamente."""
import secrets
import uuid
from app.config import settings
from app.auth_native import operacao,hash_token

class ErroConvite(RuntimeError): pass
class ConviteIndisponivel(RuntimeError): pass

def convidar(sb, *, nome, email, papel, federacao_id):
    if not sb.token: raise ErroConvite('Sessão obrigatória.')
    token=secrets.token_urlsafe(48)
    usuario_id=operacao('portal_convidar',hash_token(sb.token),uuid.uuid4(),hash_token(token),nome,email.strip().lower(),papel,federacao_id)
    base=settings.CONVITE_REDIRECT_URL or 'http://localhost:8080/definir-senha'
    sb.convite_url=base+'#convite='+token
    return usuario_id
