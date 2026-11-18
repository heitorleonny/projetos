import { api } from '../../services/api';

export type Gravidade = 'alta' | 'media' | 'baixa';

export interface MotivoDestaque {
    codigo: string;
    /** Motivo em linguagem de gestor, já pronto para exibir. */
    descricao: string;
}

export interface EjDestaque {
    id_ej: number;
    nome: string;
    foto_url: string | null;
    gravidade: Gravidade | null;
    motivos: MotivoDestaque[];
    faturamento_mes: number;
    percentual_meta: number | null;
}

export interface Comparativo {
    atual: number;
    anterior: number | null;
}

export interface ResumoAnalise {
    total_ejs: number;
    fora_do_zero: Comparativo;
    no_verde: Comparativo;
    ritmo_significativo: Comparativo;
    faturamento_acumulado: Comparativo;
    meta_faturamento_total: number | null;
    percentual_meta_rede: number | null;
}

export interface Briefing {
    frases: string[];
    gerado_por_ia: boolean;
    modelo: string | null;
}

export interface AnaliseMes {
    ano: number;
    mes: number | null;
    mes_anterior: number | null;
    /** O mês de referência ainda está em andamento (só quando pedido explicitamente). */
    mes_parcial: boolean;
    resumo: ResumoAnalise;
    alertas: EjDestaque[];
    ascensao: EjDestaque[];
    briefing: Briefing;
}

export interface AnaliseParams {
    ano: number;
    /** Sem mês, o backend usa o último mês com monitoramento carregado. */
    mes?: number;
}

export async function fetchAnalise(params: AnaliseParams): Promise<AnaliseMes> {
    const response = await api.get<AnaliseMes>('/analise', { params });
    return response.data;
}

/** Resumo redigido por IA; o backend devolve o resumo fixo se a IA falhar ou for recusada. */
export async function fetchBriefing(params: AnaliseParams): Promise<Briefing> {
    const response = await api.get<Briefing>('/analise/briefing', { params });
    return response.data;
}

export async function regenerarBriefing(params: AnaliseParams): Promise<Briefing> {
    const response = await api.post<Briefing>('/analise/briefing/regenerar', null, { params });
    return response.data;
}
