"""
Contrato de entrada da planilha de monitoramento do Portal BJ — nível EJ.

ESCRITO CONTRA ESTA EXPORTAÇÃO (quando o contrato quebrar, compare com ela):

    monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx
    aba EMPRESAS_JUNIORES, exportada em 21/09/2026
    13.563 linhas × 98 colunas — 1.507 EJs × 9 meses, 27 federações

POR QUE ESTE ARQUIVO EXISTE ANTES DE QUALQUER CÓDIGO DE CARGA

O Portal BJ está fora do nosso controle. Se a origem renomear uma coluna, isso
tem de aparecer como erro de validação na hora da carga, nomeando o que faltou
("faltam as colunas: META_DE_CSAT, CLUSTER_2026") — nunca como `KeyError` solto
no meio da transformação, nem como importação parcial, nem como gráfico errado
três semanas depois.

O QUE ESTÁ DECLARADO AQUI

Só as colunas que a carga usa (o arquivo traz 98; as outras vão para a staging
em jsonb, sem contrato). Para cada uma: nome exato, tipo e se aceita célula
vazia. "Aceita vazio" é sobre a CÉLULA, não sobre a coluna: toda coluna daqui é
obrigatória no cabeçalho.

Só quatro colunas recusam vazio — as que formam a chave ou são NOT NULL no
banco (ID, MES, FEDERACAO, EMPRESA_JUNIOR). Nas outras, vazio vira NULL, que é
ausência de dado. Recusar o arquivo inteiro por um faturamento vazio seria
trocar um buraco num mês de uma EJ por nenhuma carga para 1.507 EJs.

Os comentários "N vazios em 21/09" registram o que a exportação de referência
trazia. Não são regra: são a linha de base para perceber mudança na origem.

AS COLUNAS DE CLUSTER DEPENDEM DO ANO

A exportação de 2026 traz CLUSTER_2025 e CLUSTER_2026: o ano da carga e o
anterior. O contrato exige esse par a partir de `--ano`, em vez de fixar
"2025/2026" no código. Com `--ano 2026` o resultado é exatamente o par da
exportação de referência. Um `--ano` errado derruba a carga aqui, pelo par que
falta, em vez de gravar o cluster no ano errado.

Colunas que NUNCA entram no banco, nem na staging: E_MAIL, SITE, FACEBOOK. É
dado de contato sem uso no portal, que não precisa existir aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

ABA_PADRAO = "EMPRESAS_JUNIORES"

# Descartadas na leitura, antes de qualquer outra etapa: não chegam à staging.
COLUNAS_DESCARTADAS: tuple[str, ...] = ("E_MAIL", "SITE", "FACEBOOK")


class Tipo(str, Enum):
    INTEIRO = "inteiro"
    DECIMAL = "decimal"
    TEXTO = "texto"


@dataclass(frozen=True)
class Coluna:
    nome: str
    tipo: Tipo
    aceita_vazio: bool = True
    # Valores admitidos, quando o domínio é fechado. `None` = qualquer valor do tipo.
    dominio: frozenset | None = None


def _c(nome: str, tipo: Tipo, *, aceita_vazio: bool = True, dominio=None) -> Coluna:
    return Coluna(nome, tipo, aceita_vazio, frozenset(dominio) if dominio is not None else None)


I, D, T = Tipo.INTEIRO, Tipo.DECIMAL, Tipo.TEXTO

IDENTIFICACAO: tuple[Coluna, ...] = (
    _c("ID", I, aceita_vazio=False),              # id_ej do Portal BJ
    _c("EMPRESA_JUNIOR", T, aceita_vazio=False),
    _c("CNPJ", T),                                # com máscara: 10.279.902/0001-62
    _c("FEDERACAO", T, aceita_vazio=False),       # nome, não id: roteia a linha para o tenant
    _c("NUCLEOS", T),                             # 6.390 vazios em 21/09 — nem toda EJ tem núcleo
    _c("E_FEDERADA", T),                          # "Sim" nas 13.563 linhas em 21/09
    _c("ANO_DE_FEDERACAO", I),
    _c("ESTADO", T),                              # 522 vazios em 21/09
    _c("CIDADE", T),                              # 522 vazios em 21/09
    _c("UNIVERSIDADE", T),                        # 171 vazios em 21/09
    _c("CURSOS", T),                              # 171 vazios em 21/09; lista separada por vírgula
    _c("MEMBROS", I),                             # igual em todos os meses da EJ: é foto, não série
)

METAS: tuple[Coluna, ...] = (
    _c("META_DE_REVENUE", D),                     # R$ por ano
    _c("META_DE_IMPACT_PROJECTS", I),             # 0 ou 1 em 21/09
    _c("META_DE_MEJ_ENGAGED_MEMBERS", D),         # percentual 0–100 (50 a 75 em 21/09) — ver 9.1
    _c("META_DE_COLLABORATIVE_RATE", D),          # percentual; 4 EJs acima de 100 em 21/09 (máx. 25.000)
    _c("META_DE_LENGTH_OF_STAY", D),              # sem coluna em `metas`: só na staging
    _c("META_DE_CSAT", D),                        # 3,5 a 5,0 em 21/09
    _c("META_DE_DI_POLITICS", I, dominio={0, 1}), # vira booleano em `metas.meta_pdi`
)

FATO_MENSAL: tuple[Coluna, ...] = (
    _c("MES", I, aceita_vazio=False, dominio=range(1, 13)),
    _c("FATURAMENTO", D),                         # nenhum vazio em 21/09; 1 linha negativa (−350)
    _c("FATURAMENTO_ACUMULADO", D),               # 5.509 vazios em 21/09: vazio ⇔ soma corrida ≤ 0
    _c("FATURAMENTO_COLABORATIVO", D),
    _c("FATURAMENTO_COLABORATIVO_ACUMULADO", D),  # 5.509 vazios em 21/09, nas mesmas linhas
    _c("CONTRATOS", I),
    _c("NUMERO_DE_CONTRATOS_QUE_REALIZOU_ACAO_COLABORATIVA", I),
    _c("SOLUCOES", I),                            # valor do MÊS, não total: só na staging
    _c("CSAT", D),                                # 0 a 5; 0 com coleta 0 = "sem coleta" (9.8)
    _c("PORCENTAGEM_DE_COLETA_CSAT", D),          # 0 a 100
    _c("QUANTIDADE_DE_MEMBROS_ENGAJADOS_COM_MEJ", I),
)

# Faixas oficiais são 1–5 (app/utils/constants.py). O 0 vem da origem para EJ
# sem cluster naquele ano — em 21/09, 75 das 82 EJs com CLUSTER_2025 = 0 foram
# federadas em 2025 ou 2026. Qualquer outro valor é mudança na origem.
DOMINIO_CLUSTER = range(0, 6)


def colunas_de_cluster(ano: int) -> tuple[Coluna, Coluna]:
    """O par de colunas de cluster que a exportação de `ano` traz: ano anterior e ano."""
    return (
        _c(f"CLUSTER_{ano - 1}", I, dominio=DOMINIO_CLUSTER),
        _c(f"CLUSTER_{ano}", I, dominio=DOMINIO_CLUSTER),
    )


def colunas_obrigatorias(ano: int) -> tuple[Coluna, ...]:
    """Todas as colunas que o cabeçalho precisa ter para uma carga de `ano`."""
    return IDENTIFICACAO + colunas_de_cluster(ano) + METAS + FATO_MENSAL


class ErroContrato(ValueError):
    """
    A planilha não cumpre o contrato. A mensagem nomeia cada problema.

    `problemas` guarda a lista, uma frase por problema, para quem quiser
    exibir de outro jeito (a porta HTTP, por exemplo).
    """

    def __init__(self, problemas: list[str]):
        self.problemas = list(problemas)
        super().__init__("A planilha não cumpre o contrato de entrada:\n  - " + "\n  - ".join(self.problemas))


def verificar_cabecalho(presentes: list[str], ano: int) -> None:
    """
    Levanta `ErroContrato` se faltar coluna obrigatória. Colunas a mais são aceitas.

    A comparação é exata (maiúsculas, sem trim): "CSAT " não é "CSAT". Se a
    origem mudar a grafia, é mudança de contrato e precisa de decisão, não de
    tolerância silenciosa.
    """
    conjunto = set(presentes)
    faltando = [c.nome for c in colunas_obrigatorias(ano) if c.nome not in conjunto]
    if faltando:
        problema = "faltam as colunas: " + ", ".join(faltando)
        clusters = {c.nome for c in colunas_de_cluster(ano)}
        if clusters & set(faltando):
            problema += (
                f" (as colunas de cluster exigidas dependem de --ano={ano}; "
                "confira se o ano informado é o da exportação)"
            )
        raise ErroContrato([problema])
