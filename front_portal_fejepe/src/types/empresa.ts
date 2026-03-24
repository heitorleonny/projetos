// ── Enums ──

export type Ritmo = 'sem_vendas' | 'minimo' | 'significativo';

export type TendenciaCluster = 'sobe' | 'mantem' | 'desce';

export type OrdemEmpresa =
    | 'nome'
    | 'faturamento'
    | 'faturamento_colab'
    | 'cluster'
    | 'comunidade'
    | 'csat'
    | 'percentual_meta'
    | 'projetos';

export type Direcao = 'asc' | 'desc';

// ── Response Types ──

export interface EmpresaComIndicadores {
    id: number;
    id_ej: number;
    nome: string;
    cluster: number | null;
    comunidade: string | null;
    status: string | null;
    foto_url: string | null;
    cidade: string | null;
    universidade: string | null;
    faturamento_acumulado: number;
    faturamento_colab_acumulado: number;
    faturamento_mes: number;
    projetos_totais: number;
    csat_medio: number | null;
    percentual_meta: number | null;
    ritmo: Ritmo;
    taxa_colaboracao: number | null;
    pontos_cluster: number | null;
    cluster_calculado: number | null;
    tendencia_cluster: TendenciaCluster | null;
}

export interface PaginacaoMeta {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
}

export interface EmpresaListaResponse {
    data: EmpresaComIndicadores[];
    meta: PaginacaoMeta;
}

// ── Query Params ──

export interface EmpresaQueryParams {
    ano?: number;
    mes?: number;
    cluster?: number;
    clusters?: number[];
    comunidade?: string;
    status?: string;
    search?: string;
    cidade?: string;
    universidade?: string;
    ritmo?: Ritmo;
    ordem_por?: OrdemEmpresa;
    direcao?: Direcao;
    page?: number;
    page_size?: number;
}

// ── EJ Full Profile (individual page) ──

export interface EmpresaJunior {
    id: number;
    id_ej: number;
    nome: string;
    cnpj: string | null;
    ano_federacao: number | null;
    federacao: string | null;
    cluster: number | null;
    comunidade: string | null;
    estado: string | null;
    cidade: string | null;
    universidade: string | null;
    curso: string | null;
    status: string | null;
    created_at: string | null;
    updated_at: string | null;
    foto_url: string | null;
}

export interface FaturamentoMensal {
    mes: number;
    faturamento: number;
    faturamento_colab: number;
    projetos_vendidos: number;
    csat: number | null;
}

export interface MetaVsRealizado {
    meta_faturamento: number | null;
    faturamento_acumulado: number;
    percentual_meta: number;
    meta_csat: number | null;
    csat_medio: number | null;
    meta_taxa_colaboracao: number | null;
    taxa_colaboracao: number | null;
    meta_projetos_impacto: number | null;
    meta_engajamento_mej: number | null;
}

export interface EmpresaPerfilCompleto {
    empresa: EmpresaJunior;
    indicadores: EmpresaComIndicadores;
    serie_mensal: FaturamentoMensal[];
    metas: MetaVsRealizado | null;
    projecao_anual: number | null;
    ritmo_necessario: number | null;
    crescimento_mensal: number | null;
    crescimento_anual: number | null;
}
