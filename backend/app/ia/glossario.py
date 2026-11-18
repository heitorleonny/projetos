"""Glossário curado dos indicadores do MEJ, sem banco e sem modelo.

As regras são nacionais e iguais para todas as federações: o texto não varia por
tenant e nenhuma função aqui recebe cliente de banco. Fontes: docs/regras-de-negocio.md
(§4, §5 e §6.3) e backend/calculos.md. Limiares, faixas e pesos são lidos de
app/utils/constants.py no momento da montagem, nunca digitados no texto.
"""

from collections.abc import Callable

from app.models.ia import RespostaRede
from app.utils import constants


def _milhoes(valor: float) -> str:
    """Pontos de cluster em pt-BR: 12000000.0 → '12.000.000'."""
    return f"{valor:,.0f}".replace(",", ".")


def _decimal(valor: float) -> str:
    """Pesos em pt-BR com duas casas: 0.3 → '0,30'."""
    return f"{valor:.2f}".replace(".", ",")


def _inteiro(valor: float) -> str:
    return f"{valor:.0f}"


def _faixas_cluster() -> str:
    faixas = constants.CLUSTER_RANGES
    partes = [f"até {_milhoes(maximo)} pontos, cluster {cluster}" for _minimo, maximo, cluster in faixas[:-1]]
    ultimo_maximo = faixas[-2][1]
    partes.append(f"acima de {_milhoes(ultimo_maximo)}, cluster {faixas[-1][2]}")
    return "; ".join(partes)


def _pesos_sde() -> str:
    return "; ".join(f"C{indice} {_decimal(peso)}" for indice, peso in enumerate(constants.SDE_WEIGHTS, 1))


def _fora_do_zero() -> str:
    return (
        "Uma EJ está fora do zero quando o faturamento acumulado no ano, até o mês consultado, "
        "é maior que zero. O portal usa o acumulado informado no Portal BJ e não exige venda no "
        "próprio mês, por isso a medida é diferente do ritmo mensal. Para a federação, mostra quantas "
        "EJs já começaram a faturar no ano e quais ainda precisam de apoio para a primeira venda."
    )


def _ritmo() -> str:
    return (
        "O ritmo classifica as vendas de uma EJ em um único mês. Sem vendas: o faturamento do mês é zero. "
        "Ritmo mínimo: a EJ vendeu algo no mês. Ritmo significativo: faturou no mês pelo menos a meta "
        f"anual de faturamento dividida por {constants.MESES_ANO}; EJ sem meta cadastrada chega no máximo "
        "ao ritmo mínimo. Para a federação, mostra mês a mês quantas EJs vendem no passo da meta."
    )


def _cluster() -> str:
    return (
        f"O cluster posiciona a EJ em uma de {len(constants.CLUSTER_RANGES)} faixas de desempenho "
        "definidas nacionalmente pelo Movimento Empresa Júnior. A pontuação multiplica faturamento, CSAT, "
        "(1 + engajamento com o MEJ) e (1 + taxa de colaboração), e o resultado é multiplicado por "
        f"{constants.FATOR_ESCALA_PONTOS}. As faixas são: {_faixas_cluster()}. O cluster oficial do ano "
        "é o registrado pela Brasil Júnior; durante o ano, o portal também calcula estimativas, como o "
        "tracking de cluster. O projeto de impacto é obrigatório a partir do cluster "
        f"{constants.CLUSTER_EXIGE_PROJETO_IMPACTO}: sem ao menos um projeto de impacto, o cluster real da EJ "
        f"fica limitado ao {constants.CLUSTER_MAXIMO_SEM_PROJETO_IMPACTO}, mesmo que a pontuação aponte um cluster "
        "maior. Para a federação, o cluster orienta o acompanhamento e é a base do SDE."
    )


def _sde() -> str:
    return (
        "SDE é o Saldo de Evolução da Rede. Para cada cluster, ele subtrai as EJs que estão descendo das "
        f"que estão subindo e multiplica pelo peso do cluster oficial atual dessas EJs: {_pesos_sde()}. A referência é o "
        "cluster oficial do ano, comparado com o cluster calculado pelo portal em três cenários: índice "
        "de cluster com valores reais, índice com a meta de CSAT e tracking de cluster. Em todos os cenários "
        "vale o cluster real: EJ sem projeto de impacto não passa do cluster "
        f"{constants.CLUSTER_MAXIMO_SEM_PROJETO_IMPACTO}, então não sobe para o "
        f"{constants.CLUSTER_EXIGE_PROJETO_IMPACTO} ou o 5 e a que já está nesses clusters conta como descendo. "
        "Um SDE positivo "
        "indica que a rede, no conjunto, tende a subir de cluster; negativo, que tende a descer."
    )


def _taxa_colaboracao() -> str:
    return (
        "A taxa de colaboração é a parte do faturamento acumulado que veio de projetos colaborativos. "
        "É calculada como faturamento colaborativo acumulado dividido pelo faturamento acumulado, e fica "
        "sem valor enquanto a EJ não faturou. Entra na pontuação de cluster como (1 + taxa). Para a "
        "federação, mostra o quanto as EJs da rede trabalham em conjunto."
    )


def _faturamento_colaborativo() -> str:
    return (
        "O faturamento colaborativo é o valor vendido em projetos colaborativos. O portal usa o acumulado "
        "informado pelo Portal BJ no último mês do recorte e, no gráfico mensal, o valor de cada mês. "
        "É a base da taxa de colaboração, que aumenta a pontuação de cluster. Para a federação, indica o "
        "volume de negócios gerado pela cooperação."
    )


def _csat() -> str:
    return (
        "O CSAT mede a satisfação dos clientes da EJ. O portal calcula a média simples das notas "
        "registradas no período e ignora os meses sem coleta; uma nota zero registrada conta como nota. "
        "O CSAT multiplica o faturamento na pontuação de cluster. Para a federação, sinaliza a qualidade "
        "das entregas, e não só o volume vendido."
    )


def _engajamento() -> str:
    return (
        "O engajamento com o MEJ indica que fração dos membros da EJ participou de eventos do movimento. "
        "O valor real usa o melhor mês do ano: membros engajados nesse mês divididos pelo número de membros "
        "do último mês do recorte. A meta de engajamento é cadastrada em percentual e convertida em fração "
        "antes do cálculo. Entra na pontuação de cluster como (1 + engajamento). Para a federação, mostra a "
        "conexão das EJs com o movimento além das vendas."
    )


def _tracking_cluster() -> str:
    return (
        "O tracking de cluster estima em que cluster a EJ termina o ano se mantiver o ritmo de faturamento "
        "e cumprir as metas de qualidade. O faturamento acumulado é anualizado (dividido pelo mês atual da "
        f"EJ e multiplicado por {constants.MESES_ANO}) e entra na fórmula de pontos com a meta de CSAT, a "
        "meta de engajamento e a taxa de colaboração real. Sem meta de CSAT ou sem faturamento, o perfil "
        "da EJ não mostra o tracking. O tracking apenas aponta o cluster: o cluster real só chega ao "
        f"{constants.CLUSTER_EXIGE_PROJETO_IMPACTO} ou ao 5, e só permanece neles, se a EJ tiver projeto de "
        f"impacto; sem ele fica no {constants.CLUSTER_MAXIMO_SEM_PROJETO_IMPACTO}. Para a federação, antecipa quais EJs "
        "tendem a subir ou cair de cluster."
    )


def _projecao_anual() -> str:
    return (
        "A projeção anual estima quanto a EJ fatura no ano se a tendência dos meses informados continuar. "
        "O portal ajusta uma reta (regressão linear simples) ao faturamento de cada mês e soma os valores "
        f"da reta nos {constants.MESES_ANO} meses, sem ficar abaixo de zero. Precisa de pelo menos dois "
        "meses de dados. É uma tendência, não uma previsão garantida; ajuda a federação a comparar o rumo "
        "da EJ com a meta anual."
    )


def _ritmo_necessario() -> str:
    return (
        "O ritmo necessário é quanto a EJ precisa faturar por mês, até dezembro, para bater a meta anual "
        "de faturamento. É a diferença entre a meta e o faturamento acumulado, dividida pelos meses "
        f"restantes ({constants.MESES_ANO} menos os meses já informados). Se a meta já foi batida, o "
        "valor é zero; sem meta cadastrada, não é calculado. Para a federação, transforma a meta anual "
        "em um alvo mensal concreto."
    )


def _meta_atingida() -> str:
    atingida = _inteiro(constants.LIMIAR_META_ATINGIDA)
    parcial = _inteiro(constants.LIMIAR_META_PARCIAL)
    return (
        "O percentual da meta atingida compara o faturamento acumulado no ano com a meta anual de "
        "faturamento: acumulado dividido pela meta, em percentual. A comparação é com a meta do ano "
        "inteiro, não com a parcela proporcional ao mês; EJ sem meta cadastrada fica sem percentual. "
        f"No Lamps, as EJs são agrupadas em: {atingida}% ou mais, de {parcial}% a menos de {atingida}%, "
        f"abaixo de {parcial}% e sem meta cadastrada. Para a federação, mostra quanto da meta anual a "
        "rede já cumpriu."
    )


def _projeto_impacto() -> str:
    return (
        f"O projeto de impacto é obrigatório a partir do cluster {constants.CLUSTER_EXIGE_PROJETO_IMPACTO}, "
        f"ou seja, nos clusters {constants.CLUSTER_EXIGE_PROJETO_IMPACTO} e 5. O tracking pode apontar subida "
        "para esses clusters, mas o cluster real só chega a eles, e só permanece neles, se a EJ tiver ao menos "
        f"um projeto de impacto. Sem projeto, o cluster real fica limitado ao {constants.CLUSTER_MAXIMO_SEM_PROJETO_IMPACTO}, "
        f"e do cluster {constants.CLUSTER_MAXIMO_SEM_PROJETO_IMPACTO} para baixo a regra não muda nada. "
        "A EJ conta como tendo projeto quando o maior valor informado no ano é pelo menos um; campo vazio "
        "significa nenhum projeto. Para a federação, mostra quais EJs só sustentam o cluster alto se registrarem esse projeto."
    )


def _formula_adaptativa() -> str:
    return (
        "A fórmula adaptativa estima o cluster de fim de ano usando metas no lugar do que ainda não foi medido, "
        "e troca por valores reais conforme o ano avança. O faturamento é sempre anualizado e a taxa de "
        "colaboração é sempre a real. No primeiro trimestre, CSAT e engajamento vêm das metas. No segundo "
        "trimestre, o CSAT continua sendo a meta e o engajamento usa a meta se o real alcançou um quarto dela; "
        "senão, usa o real dividido por um quarto. Do segundo semestre em diante, CSAT e engajamento são os reais. "
        "Sem faturamento ou sem o CSAT da fase, não há estimativa."
    )


# Título exibido e consultas de dados que levam do conceito ao portal.
VERBETES: dict[str, tuple[str, Callable[[], str], tuple[str, ...]]] = {
    "fora_do_zero": ("Fora do zero", _fora_do_zero, ("Quais EJs estão fora do zero{sufixo}?",)),
    "ritmo": ("Ritmo mensal", _ritmo, ("Como está o ritmo mensal{sufixo}?",)),
    "cluster": ("Cluster", _cluster, ("Quais são os indicadores da rede{sufixo}?", "O que é tracking de cluster?")),
    "sde": ("SDE — Saldo de Evolução da Rede", _sde, ("Qual o SDE da rede{sufixo}?",)),
    "taxa_colaboracao": ("Taxa de colaboração", _taxa_colaboracao, ("Top 10 EJs por faturamento colaborativo{sufixo}",)),
    "faturamento_colaborativo": ("Faturamento colaborativo", _faturamento_colaborativo, ("Top 10 EJs por faturamento colaborativo{sufixo}",)),
    "csat": ("CSAT", _csat, ("Top 10 EJs por CSAT{sufixo}",)),
    "engajamento": ("Engajamento com o MEJ", _engajamento, ("O que é cluster?", "Qual o SDE da rede{sufixo}?")),
    "tracking_cluster": ("Tracking de cluster", _tracking_cluster, ("Qual o SDE da rede{sufixo}?",)),
    "projecao_anual": ("Projeção anual", _projecao_anual, ("O que é ritmo necessário?", "Top 10 EJs por faturamento{sufixo}")),
    "ritmo_necessario": ("Ritmo necessário", _ritmo_necessario, ("O que significa meta atingida?", "Quantas EJs atingiram a meta de faturamento{sufixo}?")),
    "meta_atingida": ("Meta atingida", _meta_atingida, ("Quantas EJs atingiram a meta de faturamento{sufixo}?",)),
    "projeto_impacto": ("Projeto de impacto", _projeto_impacto, ("O que é cluster?", "Quais EJs estão no cluster 4?")),
    "formula_adaptativa": ("Fórmula adaptativa de cluster", _formula_adaptativa, ("O que é tracking de cluster?", "O que é cluster?")),
}


def texto_do_conceito(conceito: str) -> str:
    return VERBETES[conceito][1]()


def sugestoes_do_conceito(conceito: str, sufixo: str = "") -> list[str]:
    """Uma ou duas perguntas do catálogo que levam do conceito ao dado."""
    return [modelo.format(sufixo=sufixo) for modelo in VERBETES[conceito][2]][:2]


def explicar(conceito: str, *, sufixo: str = "") -> RespostaRede:
    """Resposta determinística; `sufixo` só repete filtros já validados."""
    titulo, texto, _sugestoes = VERBETES[conceito]
    return RespostaRede(status="respondida", resposta=f"{titulo}\n\n{texto()}", fonte="glossario",
                        sugestoes=sugestoes_do_conceito(conceito, sufixo))


def recusar_conceito() -> RespostaRede:
    return RespostaRede(status="fora_do_catalogo", resposta=(
        "Posso explicar: " + ", ".join(titulo for titulo, _texto, _sug in VERBETES.values()) + "."
    ))
