"""Variáveis que uma métrica personalizada pode usar, e como cada uma se agrega.

Catálogo FECHADO. A expressão só aceita estes nomes; a IA não cria variável nova.
As colunas foram conferidas em `backend/banco.md` e nas migrações 05, 16 e 26.

Agregação na janela de meses (sempre dentro de um único ano):

    soma    soma dos valores mensais registrados na janela; sem nenhum registro,
            a variável fica sem valor (não vira zero).
    ultimo  último valor registrado na janela (mês mais recente com valor).
            É o caso do CSAT: um valor único por EJ, não uma média de meses
            (decisão de Heitor em 12/11/2026).
    ano     valor anual da tabela `metas`.

`ausente_e_zero`: para `projetos_impacto`, NULL significa "nenhum projeto"
(comentário da migração 26), então a ausência vale 0.

Métricas personalizadas NÃO são indicadores oficiais do MEJ: nunca alteram
cluster, SDE, tracking ou qualquer fórmula de `calculo_service`.
"""

from dataclasses import dataclass
from typing import Literal

Agregacao = Literal["soma", "ultimo", "ano"]
Unidade = Literal["moeda", "numero"]


@dataclass(frozen=True)
class Variavel:
    nome: str
    rotulo: str
    descricao: str
    origem: Literal["monitoramento", "metas"]
    coluna: str
    agregacao: Agregacao
    unidade: Unidade
    ausente_e_zero: bool = False


VARIAVEIS: dict[str, Variavel] = {v.nome: v for v in (
    Variavel("faturamento", "Faturamento no período",
             "soma do faturamento mensal registrado nos meses do período",
             "monitoramento", "faturamento_mes", "soma", "moeda"),
    Variavel("faturamento_acumulado", "Faturamento acumulado no ano",
             "faturamento acumulado no ano, no último mês do período com registro",
             "monitoramento", "faturamento_acumulado", "ultimo", "moeda"),
    Variavel("faturamento_colab", "Faturamento colaborativo no período",
             "soma do faturamento colaborativo mensal nos meses do período",
             "monitoramento", "faturamento_colab_mes", "soma", "moeda"),
    Variavel("projetos_vendidos", "Projetos vendidos no período",
             "soma dos projetos vendidos nos meses do período",
             "monitoramento", "projetos_vendidos_mes", "soma", "numero"),
    Variavel("projetos_totais", "Projetos no ano",
             "total de projetos do ano, no último mês do período com registro",
             "monitoramento", "projetos_totais", "ultimo", "numero"),
    Variavel("csat", "CSAT",
             "último CSAT registrado até o fim do período (valor único da EJ)",
             "monitoramento", "csat", "ultimo", "numero"),
    Variavel("membros", "Membros",
             "número de membros no último mês do período com registro",
             "monitoramento", "numero_membros", "ultimo", "numero"),
    Variavel("projetos_impacto", "Projetos de impacto",
             "projetos de impacto realizados no ano até o fim do período (ausente = nenhum)",
             "monitoramento", "projetos_impacto", "ultimo", "numero", ausente_e_zero=True),
    Variavel("meta_faturamento", "Meta de faturamento",
             "meta anual de faturamento da EJ",
             "metas", "meta_faturamento", "ano", "moeda"),
    Variavel("meta_csat", "Meta de CSAT",
             "meta anual de CSAT da EJ",
             "metas", "meta_csat", "ano", "numero"),
    Variavel("meta_projetos_impacto", "Meta de projetos de impacto",
             "meta anual de projetos de impacto da EJ",
             "metas", "meta_projetos_impacto", "ano", "numero"),
)}


def colunas_de(origem: str, nomes: set[str]) -> list[str]:
    """Colunas da tabela `origem` que as variáveis usadas exigem, sem repetição."""
    return sorted({VARIAVEIS[n].coluna for n in nomes if VARIAVEIS[n].origem == origem})
