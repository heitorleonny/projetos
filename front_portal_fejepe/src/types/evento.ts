export type EventoMetaTipo = 'faturamento_zero' | 'colab_zero' | 'verde_mes' | 'cluster_tracking';

export interface EventoResumo {
    id_evento: string;
    nome: string;
    descricao: string | null;
    ativo: boolean;
    ano: number;
    mes_referencia: number;
}

export interface EventoMetaParticipante {
    id_ej: number;
    nome: string;
    comunidade: string | null;
    cluster: number | null;
    status: string | null;
    faturamento_acumulado: number;
    faturamento_colab_acumulado: number;
    percentual_meta: number | null;
    projetos_colab_totais: number;
    atende_cluster_1_2: boolean;
    tendencia_cluster?: 'sobe' | 'mantem' | 'desce' | null;
}

export interface EventoMetaResultado {
    tipo: EventoMetaTipo;
    titulo: string;
    descricao: string;
    meta_percentual: number;
    meta_contagem: number;
    resultado_percentual: number;
    resultado_contagem: number;
    gap_percentual: number;
    gap_contagem: number;
    submeta_titulo: string | null;
    submeta_percentual: number | null;
    submeta_contagem: number | null;
    subresultado_contagem: number | null;
    subgap_contagem: number | null;
    participantes: EventoMetaParticipante[];
}

export interface EventoDetalheResponse {
    evento: EventoResumo;
    total_ejs: number;
    metas: EventoMetaResultado[];
}