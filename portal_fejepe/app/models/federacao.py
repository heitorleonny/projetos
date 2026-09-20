"""
Schemas Pydantic da tabela `federacao`.

Só o que é público. O resto da linha (id, uf, status, timestamps) não sai por
aqui — ver a nota de RLS em infra/db/init/09-federacao-branding.sql.
"""

from pydantic import BaseModel, Field


class FederacaoBranding(BaseModel):
    """
    Identidade visual da federação, mais os defaults que o frontend precisa
    saber para não os escrever no próprio código.

    `ano_default` não é branding, e mesmo assim viaja junto: é a mesma pergunta
    ("que federação é esta e como ela se apresenta?") feita no mesmo momento —
    antes do primeiro render, sem token. Um endpoint a mais para devolver um
    inteiro custaria mais do que resolve.
    """

    slug: str = Field(description="Identificador da federação em URL/configuração.")
    nome: str = Field(description="Nome de exibição, usado no título e no cabeçalho.")
    logo_url: str | None = Field(
        default=None,
        description="Caminho ou URL do logo. Nulo quando a federação ainda não tem um.",
    )
    cor_primaria: str | None = Field(
        default=None,
        description="Cor da marca em #RRGGBB. Nula mantém a paleta compilada no frontend.",
    )
    ano_default: int = Field(
        description="Ano de referência da plataforma (settings.ANO_DEFAULT).",
    )
