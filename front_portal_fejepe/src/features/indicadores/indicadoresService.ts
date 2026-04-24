import { api } from '../../services/api';

export interface IndicadoresRede {
    ano: number;
    mes: number | null;
    faturamento_total: number;
    faturamento_colab_total: number;
    total_projetos: number;
    media_csat: number | null;
    total_ejs: number;
    ejs_fora_do_zero: number;
    ejs_ritmo_minimo: number;
    ejs_ritmo_significativo: number;
    sde: number | null;
    crescimento_vs_ano_anterior: number | null;
    distribuicao_clusters: Record<string, number>;
    participacao_comunidades: Record<string, number>;
}

export interface IndicadoresParams {
    ano: number;
    mes?: number;
    cluster?: number;
    comunidade?: string;
}

export async function fetchIndicadoresRede(params: IndicadoresParams): Promise<IndicadoresRede> {
    const response = await api.get<IndicadoresRede>('/rede/indicadores', { params });
    return response.data;
}

export interface FaturamentoMesData {
    mes: number;
    label: string;
    faturamento: number;
}

const MESES_LABELS = [
    'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
];

export async function fetchFaturamentoMensal(params: IndicadoresParams): Promise<FaturamentoMesData[]> {
    const hoje = new Date();
    const anoAtual = hoje.getFullYear();
    const mesAtual = hoje.getMonth() + 1;

    if (params.ano > anoAtual) {
        return [];
    }

    const limiteMes = params.ano === anoAtual ? mesAtual : 12;

    // Fetch indicadores for each month in parallel
    const promises = Array.from({ length: limiteMes }, (_, i) => {
        const mes = i + 1;
        return fetchIndicadoresRede({ ...params, mes })
            .then((data) => ({
                mes,
                label: MESES_LABELS[i],
                faturamento: data.faturamento_total,
            }))
            .catch(() => ({
                mes,
                label: MESES_LABELS[i],
                faturamento: 0,
            }));
    });

    const data = await Promise.all(promises);
    return data.sort((a, b) => a.mes - b.mes);
}

/* ── Ritmo mensal ── */

export interface RitmoMesItem {
    mes: number;
    ejs_ritmo_minimo: number;
    ejs_ritmo_significativo: number;
    total_ejs: number;
}

interface RitmoMensalResponse {
    ano: number;
    meses: RitmoMesItem[];
}

export interface RitmoMesData {
    mes: number;
    label: string;
    rm_percent: number;
    rs_percent: number;
}

/* ── SDE ── */

export interface EjMovimento {
    id_ej: number;
    nome: string;
    cluster_atual: number | null;
    cluster_calculado: number | null;
    foto_url: string | null;
}

export interface SdeCenario {
    nome: string;
    descricao: string;
    sde: number | null;
    subindo: EjMovimento[];
    mantendo: EjMovimento[];
    descendo: EjMovimento[];
}

export interface SdeResponse {
    ano: number;
    mes: number | null;
    total_ejs: number;
    cenarios: SdeCenario[];
}

export async function fetchSdeCenarios(params: IndicadoresParams): Promise<SdeResponse> {
    const response = await api.get<SdeResponse>('/rede/sde', { params });
    return response.data;
}

export async function fetchRitmoMensal(params: IndicadoresParams): Promise<RitmoMesData[]> {
    const response = await api.get<RitmoMensalResponse>('/rede/ritmo-mensal', { params });
    const { meses } = response.data;

    return meses.map((item) => {
        const total = item.total_ejs || 1;
        return {
            mes: item.mes,
            label: MESES_LABELS[item.mes - 1],
            rm_percent: ((item.ejs_ritmo_minimo + item.ejs_ritmo_significativo) / total) * 100,
            rs_percent: (item.ejs_ritmo_significativo / total) * 100,
        };
    });
}
