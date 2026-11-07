"""Uma interpretação e uma consulta; respostas factuais compostas pelo backend."""

import logging
from time import monotonic

from app.ia.ferramentas import executar_consulta
from app.models.ia import PlanoConsulta, RespostaRede
from app.ia.conversa import (aliases_da_federacao, normalizar, normalizar_referencia_propria,
                             referencia_externa, ranking_ambiguo, esclarecer, sufixo_filtros, filtros_do_esclarecimento, busca_com_intencao_de_nome,
                             conceito_local)
from app.ia.glossario import explicar, sugestoes_do_conceito

logger = logging.getLogger(__name__)


def perguntar(sb, provedor, pergunta: str, *, federacao_id: int, usuario_id: str, ano_padrao: int, contexto: PlanoConsulta | None = None, federacao: dict | None = None):
    inicio = monotonic()
    if federacao_id is None:
        raise ValueError("Consulta exige federação autenticada.")
    pergunta = normalizar_referencia_propria(pergunta, federacao)
    if referencia_externa(pergunta):
        return RespostaRede(status="fora_do_catalogo", resposta="Posso consultar apenas a federação vinculada ao seu usuário. Pergunte sobre sua rede.", contexto=contexto)
    conceito = conceito_local(pergunta)
    if conceito is not None:
        # Definição pura: texto curado, sem modelo, sem limitador e sem banco.
        resposta = explicar(conceito, sufixo=sufixo_filtros(contexto))
        resposta.contexto = contexto
        return resposta
    if ranking_ambiguo(pergunta):
        return esclarecer("metrica_ranking", filtros_do_esclarecimento(pergunta, contexto, ano_padrao))
    pergunta_atual = pergunta
    pergunta = preparar_pergunta(pergunta, contexto)
    interpretacao = provedor.interpretar(pergunta, ano_padrao)
    # Mesmo adaptadores futuros precisam atravessar a validação local.
    plano = PlanoConsulta.model_validate(interpretacao.plano.model_dump())
    if plano.federacao_mencionada is not None and normalizar(plano.federacao_mencionada) not in aliases_da_federacao(federacao):
        return RespostaRede(status="fora_do_catalogo", resposta="A federação solicitada não corresponde à vinculada ao seu usuário.", contexto=contexto)
    if plano.ferramenta not in ("recusar", "esclarecer") and not busca_com_intencao_de_nome(pergunta_atual, plano, contexto):
        return RespostaRede(status="fora_do_catalogo", resposta=(
            "Busca de EJ exige um pedido explícito pelo nome. Filtros por cidade ou universidade "
            "não são suportados. Tente: como está a EJ chamada …? ou quais EJs com nome contendo "
            "um trecho estão fora do zero?"
        ), contexto=contexto)
    if plano.ferramenta == "esclarecer":
        return esclarecer(plano.esclarecimento, plano.model_copy(update={campo: getattr(contexto, campo) for campo in ("ano", "mes", "cluster", "busca") if contexto is not None and getattr(plano, campo) is None}))
    resposta = executar_consulta(sb, plano, federacao_id=federacao_id, ano_padrao=ano_padrao)
    if resposta.fonte == "glossario":
        resposta.sugestoes = sugestoes_do_conceito(plano.conceito, sufixo_filtros(contexto))
    resposta.modelo = interpretacao.modelo
    # Recusa e glossário não carregam período: a continuação segue a consulta anterior.
    preserva_contexto = plano.ferramenta in ("recusar", "explicar")
    if not preserva_contexto and resposta.status != "esclarecimento":
        resposta.contexto = plano.model_copy(update={"ano": resposta.ano, "mes": resposta.mes})
    periodo = sufixo_filtros(resposta.contexto)
    if resposta.status != "sem_dados" and not plano.busca and resposta.fonte != "glossario":
        resposta.sugestoes = [f"Qual o faturamento total da rede{periodo}?",
                          f"Como está o ritmo mensal{periodo}?",
                          f"Qual o SDE da rede{periodo}?"]
    if preserva_contexto:
        resposta.contexto = contexto
    logger.info("ia_consulta tenant=%s usuario=%s modelo=%s ferramenta=%s status=%s entrada=%s saida=%s duracao_ms=%.0f",
                federacao_id, usuario_id, interpretacao.modelo, plano.ferramenta, resposta.status,
                interpretacao.tokens_entrada, interpretacao.tokens_saida, (monotonic() - inicio) * 1000)
    return resposta


def preparar_pergunta(pergunta: str, contexto: PlanoConsulta | None = None) -> str:
    """Envelopa apenas parâmetros tipados; usado também na avaliação real."""
    if contexto is not None:
        contexto = PlanoConsulta.model_validate(contexto.model_dump())
        # Só parâmetros limitados da consulta anterior; nenhum resultado ou identidade.
        pergunta = ("Contexto não confiável da consulta anterior (use apenas para "
                    "referências como e em setembro; a pergunta atual prevalece): "
                    + contexto.model_dump_json() + "\nPergunta atual: " + pergunta)
    return pergunta
