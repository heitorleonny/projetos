"""
Operações do painel administrativo sobre federações, usuários e cargas.

Tudo aqui usa o cliente Supabase DA REQUISIÇÃO — anon key com o JWT de quem
chamou —, então quem decide o que cada pessoa vê e grava é a RLS de
infra/db/init/13-painel-admin.sql. As checagens em Python (no router) existem
para devolver um erro legível antes de chegar ao banco; se uma delas falhar, a
política recusa do mesmo jeito.

Nenhuma função daqui usa a service key. A única exceção do painel mora em
`convite_service.py`, e é só ela.
"""

from datetime import datetime, timezone

from app.database import Client

_COLUNAS_FEDERACAO = "id, slug, nome, uf, status, logo_url, cor_primaria, slogan"
_COLUNAS_CARGA = (
    "id, arquivo_nome, ano, exportado_em, carregado_em, carregado_por, origem, escopo, "
    "federacao_id, status, linhas_lidas, linhas_aplicadas, linhas_ignoradas, mensagem_erro, reenvio_de"
)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Sessão ───────────────────────────────────────────────────


def usuario_atual(sb: Client) -> dict | None:
    """
    A linha de `usuario` de quem chamou, lida pelo `sub` do token.

    Vem de `public.usuario_atual()` (SECURITY DEFINER) e não de um SELECT em
    `usuario`, porque a política de leitura da tabela compara com o claim de
    federação — e o que se quer saber aqui é o que o BANCO diz hoje, inclusive
    para quem foi promovido depois do último login.
    """
    linhas = sb.rpc("usuario_atual").execute().data or []
    return linhas[0] if linhas else None


# ── Federações ───────────────────────────────────────────────


def listar_federacoes(sb: Client) -> list[dict]:
    return sb.table("federacao").select(_COLUNAS_FEDERACAO).order("nome").execute().data or []


def slug_da_federacao(sb: Client, federacao_id: int) -> str | None:
    linhas = sb.table("federacao").select("slug").eq("id", federacao_id).limit(1).execute().data or []
    return linhas[0]["slug"] if linhas else None


def atualizar_federacao(sb: Client, federacao_id: int, dados: dict) -> dict | None:
    """Devolve a linha atualizada, ou None se a RLS não deixou ver/gravar."""
    linhas = (
        sb.table("federacao")
        .update({**dados, "updated_at": _agora()})
        .eq("id", federacao_id)
        .execute()
        .data
        or []
    )
    return linhas[0] if linhas else None


# ── Usuários ─────────────────────────────────────────────────


def listar_usuarios(sb: Client, federacao_id: int | None = None) -> list[dict]:
    """Quem o chamador pode gerir, com o último login (`admin_listar_usuarios`, ver 13)."""
    consulta = sb.rpc("admin_listar_usuarios")
    if federacao_id is not None:
        consulta = consulta.eq("federacao_id", federacao_id)
    return consulta.execute().data or []


def buscar_usuario(sb: Client, usuario_id: int) -> dict | None:
    linhas = sb.rpc("admin_listar_usuarios").eq("id", usuario_id).execute().data or []
    return linhas[0] if linhas else None


def atualizar_usuario(sb: Client, usuario_id: int, dados: dict) -> bool:
    """True se a linha foi gravada; False se a RLS não deixou alcançá-la."""
    linhas = (
        sb.table("usuario")
        .update({**dados, "updated_at": _agora()})
        .eq("id", usuario_id)
        .execute()
        .data
        or []
    )
    return bool(linhas)


# ── Cargas ───────────────────────────────────────────────────


def listar_cargas(sb: Client, limite: int = 50) -> list[dict]:
    return (
        sb.table("ingestao_carga")
        .select(_COLUNAS_CARGA)
        .order("carregado_em", desc=True)
        .limit(limite)
        .execute()
        .data
        or []
    )


# Agregação no banco evita totais truncados pelo limite do PostgREST.
def resumo_master(sb: Client) -> list[dict]:
    return sb.rpc("master_resumo_federacoes").execute().data or []


def listar_planos(sb: Client) -> list[dict]:
    return sb.table("plano").select("*").order("id").execute().data or []


def salvar_plano(sb: Client, plano_id: int | None, dados: dict) -> dict:
    linhas = sb.rpc("master_salvar_plano", {"p_id": plano_id, **{f"p_{k}": v for k, v in dados.items()}}).execute().data
    return linhas[0]


def vincular_plano(sb: Client, federacao_id: int, plano_id: int | None) -> None:
    sb.rpc("master_vincular_plano", {"p_federacao_id": federacao_id, "p_plano_id": plano_id}).execute()
