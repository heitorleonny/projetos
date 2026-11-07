"""
Schemas Pydantic do painel administrativo (`/api/v1/admin`).

Os corpos de atualização têm todos os campos opcionais e só o que vier é
gravado (`model_dump(exclude_unset=True)`): o painel manda o que mudou, não a
linha inteira.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Papel = Literal["membro", "admin", "plataforma"]
StatusFederacao = Literal["ativa", "inativa", "piloto"]


# ── Sessão ───────────────────────────────────────────────────


class Sessao(BaseModel):
    """Quem está usando o painel, segundo a tabela `usuario` — não o token."""

    usuario_id: int | None = Field(description="`usuario.id`; nulo quando a conta não tem vínculo.")
    nome: str | None = None
    papel: Papel | None = Field(description="Papel no banco; nulo quando a conta não tem vínculo ativo.")
    federacao_id: int | None = None
    pode_administrar: bool = Field(description="Verdadeiro para `admin` e `plataforma`: mostra o painel.")
    eh_plataforma: bool = Field(description="Verdadeiro só para o operador: mostra a aba de federações e o escopo nacional.")


# ── Federações ───────────────────────────────────────────────


class Federacao(BaseModel):
    id: int
    slug: str
    nome: str
    uf: str
    status: StatusFederacao
    logo_url: str | None = None
    cor_primaria: str | None = None
    slogan: str | None = None


class FederacaoAtualizacao(BaseModel):
    """O que o operador pode mudar. `id`, `slug` e `uf` não são editáveis (ver 13 e 15)."""

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    status: StatusFederacao | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    cor_primaria: str | None = Field(
        default=None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="#RRGGBB. O banco tem o mesmo CHECK (09).",
    )
    slogan: str | None = Field(default=None, max_length=200, description="Subtítulo do Dashboard (14).")


# ── Usuários ─────────────────────────────────────────────────


class Usuario(BaseModel):
    convite_url: str | None = None
    id: int
    federacao_id: int
    federacao_nome: str
    nome: str
    email: str
    papel: Papel
    ativo: bool
    conta_principal: bool
    vinculado: bool = Field(description="Já existe conta de acesso ligada a esta linha.")
    ultimo_login: datetime | None = Field(description="`auth.users.last_sign_in_at`. Nulo: nunca entrou.")
    criado_em: datetime


class UsuarioAtualizacao(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    papel: Papel | None = None
    ativo: bool | None = None
    federacao_id: int | None = Field(default=None, description="Só o operador move usuário de federação.")


class Convite(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    # Formato mínimo, e não `EmailStr`: o validador dele recusa domínios
    # reservados (`.local`, `.test`), que são os da demo. Quem decide se o
    # endereço é entregável é o Supabase Auth, ao mandar o convite.
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    papel: Papel = "membro"
    federacao_id: int | None = Field(
        default=None,
        description="Obrigatório para o operador. Para o admin, é sempre a própria federação.",
    )


# ── Importações ──────────────────────────────────────────────


class Carga(BaseModel):
    """Uma linha de `ingestao_carga`, sem o resumo completo."""

    id: int
    arquivo_nome: str
    ano: int
    exportado_em: str | None = None
    carregado_em: datetime
    carregado_por: int | None = None
    origem: str
    escopo: str
    federacao_id: int | None = None
    status: str
    linhas_lidas: int | None = None
    linhas_aplicadas: int | None = None
    linhas_ignoradas: int | None = None
    mensagem_erro: str | None = None
    reenvio_de: int | None = None


class ResultadoImportacao(BaseModel):
    """
    O relatório de `app.ingestao.importacao.importar`, mais o texto que a CLI
    imprime. `simulacao=True`: nada foi gravado, as contagens são as reais.
    """

    relatorio: dict
    texto: str


class FederacaoMaster(BaseModel):
    id: int
    nome: str
    uf: str
    status: StatusFederacao
    plano_id: int | None
    usuarios_total: int
    usuarios_ativos: int
    administradores: int
    usuarios_sem_vinculo: int


class PlanoDados(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    limite_usuarios: int | None = Field(default=None, ge=0, le=1000000)
    limite_creditos_ia_mes: int | None = Field(default=None, ge=0, le=1000000)
    preco_mensal: float | None = Field(default=None, ge=0, le=1000000, allow_inf_nan=False)


class Plano(PlanoDados):
    id: int


class VinculoPlano(BaseModel):
    plano_id: int | None = Field(ge=1)
