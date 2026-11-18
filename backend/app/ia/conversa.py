"""Esclarecimentos e identificação declarativa; autoridade permanece no JWT."""

import re
import unicodedata
from app.models.ia import Esclarecimento, OpcaoEsclarecimento, PlanoConsulta, RespostaRede


def normalizar(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold()) if not unicodedata.combining(c)).strip()


def aliases_da_federacao(federacao: dict | None) -> set[str]:
    return {normalizar(str(federacao[chave])) for chave in ('nome', 'slug')
            if federacao and federacao.get(chave)}


def normalizar_referencia_propria(pergunta: str, federacao: dict | None) -> str:
    # Somente aliases obtidos pelo backend com JWT; nenhum alias vem do corpo.
    aliases = aliases_da_federacao(federacao)
    if not aliases:
        return pergunta
    padrao = r'(?<!\w)(?:' + '|'.join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r')(?!\w)'
    # Mapear cada caractere normalizado ao original conserva nomes/acentos da EJ.
    caracteres, indices = [], []
    for indice, caractere in enumerate(pergunta):
        for normalizado in normalizar(caractere):
            caracteres.append(normalizado)
            indices.append(indice)
        if caractere.isspace():
            caracteres.append(caractere)
            indices.append(indice)
    texto = ''.join(caracteres)
    intervalos = []
    for correspondencia in re.finditer(padrao, texto, flags=re.I):
        inicio = indices[correspondencia.start()]
        fim = indices[correspondencia.end() - 1] + 1
        while fim < len(pergunta) and unicodedata.combining(pergunta[fim]):
            fim += 1
        intervalos.append((inicio, fim))
    for inicio, fim in reversed(intervalos):
        pergunta = pergunta[:inicio] + 'minha federação' + pergunta[fim:]
    return pergunta


def referencia_externa(pergunta: str) -> bool:
    texto = normalizar(pergunta)
    # Siglas nacionais, mais referências explicitamente fora da própria rede.
    return bool(re.search(r'\b(?:feje[a-z]+|fej[a-z]{2,}|unijr(?:[- ]?[a-z]{2})?|riojunior|concentro)\b', texto)
                or re.search(r'\b(?:outra[s]?|todas as|todas|demais) federa(?:cao|coes)\b', texto))


def filtros_do_esclarecimento(pergunta: str, contexto: PlanoConsulta | None, ano_padrao: int) -> PlanoConsulta:
    plano = contexto or PlanoConsulta(ferramenta='ranking', ano=None, mes=None, criterio=None, limite=None)
    texto = normalizar(pergunta)
    alteracoes = {}
    cluster = re.search(r'\bcluster\s+([1-5])\b', texto)
    ano = re.search(r'\b(20\d{2}|2100)\b', texto)
    numerico = re.search(r'\b(0?[1-9]|1[0-2])/(20\d{2}|2100)\b', texto)
    nomes = ['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    if cluster:
        alteracoes['cluster'] = int(cluster.group(1))
    if ano:
        alteracoes['ano'] = int(ano.group(1))
    if numerico:
        alteracoes.update(mes=int(numerico.group(1)), ano=int(numerico.group(2)))
    else:
        for mes, nome in enumerate(nomes, 1):
            if re.search(r'\b' + nome + r'\b', texto):
                alteracoes['mes'] = mes
                alteracoes.setdefault('ano', plano.ano or ano_padrao)
    return plano.model_copy(update=alteracoes)



def sufixo_filtros(plano: PlanoConsulta | None) -> str:
    if plano is None:
        return ''
    recorte = f' do cluster {plano.cluster}' if plano.cluster is not None else ''
    if plano.mes and plano.ano:
        recorte += f' em {plano.mes:02d}/{plano.ano}'
    elif plano.ano:
        recorte += f' em {plano.ano}'
    return recorte


def esclarecer(motivo: str | None, contexto: PlanoConsulta | None) -> RespostaRede:
    filtros = sufixo_filtros(contexto)
    if motivo == 'metrica_ranking':
        pergunta = 'Qual indicador você quer usar para comparar as EJs?'
        opcoes = [OpcaoEsclarecimento(rotulo=rotulo, pergunta=f'Top 10 EJs por {criterio}{filtros}')
                  for rotulo, criterio in [('Maior faturamento', 'faturamento'), ('Maior CSAT', 'CSAT'),
                                          ('Mais projetos', 'projetos'), ('Maior colaboração', 'colab')]]
    elif motivo == 'ej':
        # Sem nome não há opções: listar EJs aqui seria uma consulta nova.
        pergunta = 'Qual EJ você quer consultar? Escreva parte do nome, por exemplo: como está a EJ chamada …?'
        opcoes = []
    else:
        pergunta = 'O que você quer consultar sobre sua rede?'
        opcoes = [OpcaoEsclarecimento(rotulo='Indicadores da rede', pergunta=f'Quais são os indicadores da rede{filtros}?'),
                  OpcaoEsclarecimento(rotulo='EJs fora do zero', pergunta=f'Quais EJs estão fora do zero{filtros}?')]
    return RespostaRede(status='esclarecimento', resposta=pergunta, contexto=contexto,
                        esclarecimento=Esclarecimento(pergunta=pergunta, opcoes=opcoes))


def ranking_ambiguo(pergunta: str) -> bool:
    texto = normalizar(pergunta)
    ambiguo = re.search(r'\b(?:melhores|piores|melhor desempenho|melhor performance)\b', texto)
    metrica = re.search(r'\b(?:faturamento|csat|projetos|colab|colaborativo|colaboracao)\b', texto)
    if not ambiguo or metrica:
        return False
    # Só antecipamos pedidos simples com filtros suportados. Qualquer requisito
    # restante vai ao intérprete, evitando descartar cidade/universidade etc.
    cluster = re.search(r'\bcluster\s+(\d+)\b', texto)
    if cluster and int(cluster.group(1)) not in range(1, 6):
        return False
    restante = re.sub(r'\b(?:0?[1-9]|1[0-2])/(?:20\d{2}|2100)\b', '', texto)
    restante = re.sub(r'\b(?:20\d{2}|2100|[1-5])\b', '', restante)
    palavras = {'quais', 'qual', 'sao', 'as', 'os', 'a', 'o', 'ejs', 'ej', 'empresas', 'juniores',
                'melhores', 'piores', 'melhor', 'desempenho', 'performance', 'ranking', 'da', 'de',
                'do', 'das', 'dos', 'no', 'na', 'em', 'por', 'minha', 'rede', 'federacao', 'cluster',
                'janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto',
                'setembro', 'outubro', 'novembro', 'dezembro'}
    return all(palavra in palavras for palavra in re.findall(r'\w+', restante))


# "EJ de Recife", "EJs em Olinda", "empresa júnior da UFRPE": forma de localidade.
_EJ_COM_LOCALIDADE = re.compile(
    r'\b(?:ej|ejs|empresa junior|empresas juniores)\s+(?:de|do|da|dos|das|em|no|na|nos|nas)\s+\w')


def nome_literal_de_ej(texto_normalizado: str, busca: str) -> bool:
    """Só para `perfil_ej`: o trecho precisa aparecer como palavra(s) na pergunta.

    Sem marcador explícito ("nome", "chamada"), qualquer "EJ de/em/da …" na pergunta
    é tratado como localidade e recusado, mesmo que exista EJ com esse nome.
    """
    if _EJ_COM_LOCALIDADE.search(texto_normalizado):
        return False
    return bool(re.search(r'(?<!\w)' + re.escape(normalizar(busca)) + r'(?!\w)', texto_normalizado))


def busca_com_intencao_de_nome(pergunta: str, plano: PlanoConsulta, contexto: PlanoConsulta | None) -> bool:
    """Busca só pode representar nome pedido literalmente ou seguimento limitado.

    Uma palavra de cidade/universidade não vira nome de EJ por decisão do modelo.
    O plano contextual não autoriza uma busca diferente da anterior.
    """
    if not plano.busca:
        return True
    texto = normalizar(pergunta)
    if re.search(r'\b(?:cidade|municipio|universidade|localizad[ao]s?|sediad[ao]s?)\b', texto):
        return False
    marcador = re.search(r'\b(?:nome|contendo|chamada[s]?|chamado[s]?|denominada[s]?|denominado[s]?)\b', texto)
    if marcador and normalizar(plano.busca) in texto[marcador.end():]:
        return True
    if plano.ferramenta == 'perfil_ej' and nome_literal_de_ej(texto, plano.busca):
        return True
    if not contexto or not contexto.busca or normalizar(contexto.busca) != normalizar(plano.busca):
        return False
    mes = r'(?:janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|(?:0?[1-9]|1[0-2])/(?:20\d{2}|2100))'
    seguimento = r'(?:e|agora) (?:em ' + mes + r'(?: de (?:20\d{2}|2100))?(?: no cluster [1-5])?|no cluster [1-5])\??'
    return bool(re.fullmatch(seguimento, texto))


# Termos aceitos pela guarda local do glossário (texto já normalizado).
_TERMOS_CONCEITO = {
    'fora do zero': 'fora_do_zero', 'estar fora do zero': 'fora_do_zero', 'ej fora do zero': 'fora_do_zero',
    'ritmo': 'ritmo', 'ritmo mensal': 'ritmo', 'ritmo minimo': 'ritmo', 'ritmo significativo': 'ritmo',
    'cluster': 'cluster', 'clusters': 'cluster', 'cluster oficial': 'cluster',
    'pontuacao de cluster': 'cluster', 'pontos de cluster': 'cluster',
    'sde': 'sde', 'saldo de evolucao': 'sde', 'saldo de evolucao da rede': 'sde',
    'taxa de colaboracao': 'taxa_colaboracao', 'taxa colab': 'taxa_colaboracao', 'taxa de colab': 'taxa_colaboracao',
    'faturamento colaborativo': 'faturamento_colaborativo', 'faturamento colab': 'faturamento_colaborativo',
    'csat': 'csat', 'satisfacao do cliente': 'csat',
    'engajamento': 'engajamento', 'engajamento mej': 'engajamento', 'engajamento com o mej': 'engajamento',
    'engajamento no mej': 'engajamento',
    'tracking': 'tracking_cluster', 'tracking de cluster': 'tracking_cluster', 'tracking do cluster': 'tracking_cluster',
    'cluster track': 'tracking_cluster',
    'projecao anual': 'projecao_anual', 'projecao de faturamento': 'projecao_anual',
    'ritmo necessario': 'ritmo_necessario',
    'meta atingida': 'meta_atingida', '% da meta': 'meta_atingida', 'percentual da meta': 'meta_atingida',
    'porcentagem da meta': 'meta_atingida', 'atingimento da meta': 'meta_atingida',
    'projeto de impacto': 'projeto_impacto', 'projetos de impacto': 'projeto_impacto',
    'formula adaptativa': 'formula_adaptativa', 'formula adaptativa de cluster': 'formula_adaptativa',
    'cluster adaptativo': 'formula_adaptativa',
}
_PERGUNTA_CONCEITO = re.compile(
    r'(?:o que (?:e|sao|significa|quer dizer|seria)|como (?:e|sao) calculad[oa]s?|como se calcula|como calcula'
    r'|como funciona|qual (?:e )?a (?:definicao|formula) d[aoe]|explique|explica|me explica|me explique|defina'
    r'|significado d[aoe])\s+(?:(?:o|a|os|as|um|uma)\s+)?(?:(?:indicador|conceito|metrica)\s+(?:d[aoe]\s+)?)?'
    r'(?P<termo>' + '|'.join(re.escape(t) for t in sorted(_TERMOS_CONCEITO, key=len, reverse=True)) + r')\s*[?.!]*'
)


def conceito_local(pergunta: str) -> str | None:
    """Pergunta de definição inteira → conceito do glossário; o resto vai ao intérprete.

    Só casa a pergunta completa: "o que é SDE?" responde aqui, "qual o SDE da rede?"
    (pedido de dado) não casa e segue o fluxo normal.
    """
    correspondencia = _PERGUNTA_CONCEITO.fullmatch(re.sub(r'\s+', ' ', normalizar(pergunta)))
    return _TERMOS_CONCEITO[correspondencia.group('termo')] if correspondencia else None
