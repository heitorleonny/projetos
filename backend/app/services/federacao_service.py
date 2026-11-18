"""
Leitura da federação de quem está logado.

Três telas precisam saber "de que federação é este usuário" além do id: o
branding depois do login, o campo "Federação" do perfil da EJ e o catálogo de
eventos. As três leem daqui, pela mesma consulta.

O `authenticated` só enxerga a PRÓPRIA linha de `federacao` (política
`federacao_select_proprio_tenant`, 07-rls-policies.sql). O `.eq("id", ...)`
é a segunda camada, pelo mesmo motivo de app/services/tenant.py.
"""

from app.database import Client

COLUNAS_BRANDING = "id, slug, nome, logo_url, cor_primaria, cor_secundaria, cor_acento, slogan"


def definir_paleta(sb: Client, dados: dict) -> dict | None:
    """RPC limitada por auth.uid e papel atual; não recebe id de federação."""
    linhas = sb.rpc("definir_paleta_da_federacao", {f"p_{chave}": valor for chave, valor in dados.items()}).execute().data or []
    return linhas[0] if linhas else None


# ── Logo enviada pela federação (migração 25) ────────────────

TAMANHO_MAXIMO_LOGO = 512 * 1024  # mesmo limite do CHECK em federacao_logo


def detectar_tipo_logo(dados: bytes) -> str | None:
    """Tipo pela assinatura do arquivo, nunca pelo nome ou Content-Type do cliente.

    Só PNG, JPEG e WebP: imagens sem script. SVG e qualquer outro formato → None.
    """
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if dados.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(dados) >= 12 and dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "image/webp"
    return None


def definir_logo(sb: Client, conteudo: bytes, tipo: str) -> dict | None:
    """RPC limitada por auth.uid e papel atual; não recebe id de federação."""
    linhas = sb.rpc("definir_logo_da_federacao", {"p_conteudo": conteudo, "p_tipo": tipo}).execute().data or []
    return linhas[0] if linhas else None


def remover_logo(sb: Client) -> dict | None:
    linhas = sb.rpc("remover_logo_da_federacao", {}).execute().data or []
    return linhas[0] if linhas else None


def buscar_logo_publica(sb: Client, slug: str) -> dict | None:
    """Arquivo da logo de uma federação ativa, por slug (leitura pública)."""
    linhas = sb.rpc("logo_da_federacao", {"p_slug": slug}).execute().data or []
    return linhas[0] if linhas else None


def buscar_federacao_do_usuario(sb: Client, federacao_id: int | None) -> dict | None:
    """
    A linha de `federacao` do usuário, ou None se não houver.

    `federacao_id=None` (token sem claim) cai só na RLS: devolve a única linha
    que a política deixa ver — ou nenhuma, e aí None.
    """
    consulta = sb.table("federacao").select(COLUNAS_BRANDING)
    if federacao_id is not None:
        consulta = consulta.eq("id", federacao_id)
    linhas = (consulta.limit(1).execute()).data or []
    return linhas[0] if linhas else None


def buscar_nome_da_federacao(sb: Client, federacao_id: int | None) -> str | None:
    """Nome de exibição da federação, para o perfil da EJ."""
    if federacao_id is None:
        return None
    linhas = (
        sb.table("federacao").select("nome").eq("id", federacao_id).limit(1).execute()
    ).data or []
    return linhas[0]["nome"] if linhas else None
