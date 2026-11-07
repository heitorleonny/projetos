import { api } from '../../services/api';

export type Conceito = 'fora_do_zero' | 'ritmo' | 'cluster' | 'sde' | 'taxa_colaboracao' | 'faturamento_colaborativo'
    | 'csat' | 'engajamento' | 'tracking_cluster' | 'projecao_anual' | 'ritmo_necessario' | 'meta_atingida';

export interface ContextoConsulta {
    ferramenta: 'fora_do_zero' | 'indicadores_rede' | 'ranking' | 'sde' | 'ritmo_mensal' | 'explicar' | 'esclarecer' | 'recusar';
    ano: number | null;
    mes: number | null;
    criterio: 'faturamento' | 'csat' | 'projetos' | 'colab' | null;
    limite: number | null;
    cluster?: number | null;
    busca?: string | null;
    esclarecimento?: 'metrica_ranking' | 'periodo' | 'escopo' | null;
    federacao_mencionada?: string | null;
    conceito?: Conceito | null;
    ordem?: 'desc' | 'asc' | null;
}

export interface RespostaRede {
    status: 'respondida' | 'fora_do_catalogo' | 'sem_dados' | 'esclarecimento';
    resposta: string;
    fonte: string | null;
    ano: number | null;
    mes: number | null;
    total: number;
    linhas: { id_ej: number | null; nome: string; valor: number | null; unidade?: 'moeda' | 'numero' | null }[];
    unidade: 'moeda' | 'numero';
    modelo: string | null;
    contexto?: ContextoConsulta | null;
    sugestoes?: string[];
    esclarecimento?: { pergunta: string; opcoes: { rotulo: string; pergunta: string }[] } | null;
    /** Série mensal preenchida pelo backend (perfil de EJ). */
    serie?: { mes: number; valor: number }[] | null;
}

export async function perguntarRede(pergunta: string, signal: AbortSignal, contexto?: ContextoConsulta | null): Promise<RespostaRede> {
    const { data } = await api.post<RespostaRede>('/ia/perguntar', { pergunta, ...(contexto ? { contexto } : {}) }, { signal, timeout: 60000 });
    return data;
}
