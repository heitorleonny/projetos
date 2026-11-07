import type { RespostaRede } from './assistenteService';

/**
 * Visualização da consulta: só reorganiza valores que o backend já calculou e
 * devolveu. Nenhuma fórmula, nenhuma chamada ao modelo, nada é persistido.
 */
export type TipoGrafico = 'barras_horizontais' | 'barras' | 'linha';

export interface PontoGrafico {
    rotulo: string;
    valor: number;
}

export interface Grafico {
    tipo: TipoGrafico;
    titulo: string;
    unidade: 'moeda' | 'numero';
    pontos: PontoGrafico[];
}

export const LIMITE_RANKING_GRAFICO = 10;

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

type RespostaGrafico = Pick<RespostaRede, 'fonte' | 'linhas' | 'unidade'> & Partial<Pick<RespostaRede, 'serie'>>;

function pontosDasLinhas(resposta: RespostaGrafico): PontoGrafico[] {
    return resposta.linhas
        .filter(linha => typeof linha.valor === 'number' && Number.isFinite(linha.valor))
        .map(linha => ({ rotulo: linha.nome, valor: linha.valor as number }));
}

/**
 * Indicadores da rede (unidades misturadas) e EJs fora do zero (listas longas)
 * continuam em cartões e tabela: devolvem null.
 */
export function graficoDaResposta(resposta: RespostaGrafico): Grafico | null {
    let grafico: Grafico | null = null;
    switch (resposta.fonte) {
        case 'rede_service.gerar_ranking':
            grafico = { tipo: 'barras_horizontais', titulo: 'Ranking das EJs', unidade: resposta.unidade,
                pontos: pontosDasLinhas(resposta).slice(0, LIMITE_RANKING_GRAFICO) };
            break;
        case 'rede_service.calcular_ritmo_mensal':
            grafico = { tipo: 'barras', titulo: 'EJs por ritmo no mês', unidade: 'numero', pontos: pontosDasLinhas(resposta) };
            break;
        case 'rede_service.calcular_sde_cenarios':
            grafico = { tipo: 'barras', titulo: 'SDE por cenário', unidade: 'numero', pontos: pontosDasLinhas(resposta) };
            break;
        case 'calculo_service.calcular_percentual_meta':
            // Só a distribuição por faixa; a lista de EJs de uma faixa fica na tabela.
            if (resposta.linhas.every(linha => linha.id_ej === null)) {
                grafico = { tipo: 'barras', titulo: 'EJs por faixa da meta de faturamento', unidade: 'numero', pontos: pontosDasLinhas(resposta) };
            }
            break;
        case 'empresa_service.buscar_empresa':
            grafico = { tipo: 'linha', titulo: 'Faturamento por mês', unidade: 'moeda',
                pontos: (resposta.serie ?? []).map(ponto => ({ rotulo: MESES[ponto.mes - 1] ?? String(ponto.mes), valor: ponto.valor })) };
            break;
        default:
            return null;
    }
    return grafico && grafico.pontos.length > 0 ? grafico : null;
}

export function rotuloDoMes(mes: number): string {
    return MESES[mes - 1] ?? String(mes);
}
