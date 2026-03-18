/**
 * Formata um número como moeda brasileira (BRL).
 */
export function formatCurrency(value: number): string {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
}

/**
 * Formata um número como porcentagem.
 * A API retorna valores já em forma de porcentagem (ex: 72.5 = 72.5%).
 */
export function formatPercent(value: number | null | undefined): string {
    if (value == null) return '—';
    return `${value.toFixed(1)}%`;
}

/**
 * Formata o Saldo de Evolução (SDE / pontos_cluster) de forma legível.
 */
export function formatSde(value: number): string {
    if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(0)}k`;
    return value.toFixed(0);
}

/**
 * Retorna o label e a cor CSS para um cluster.
 */
export function getClusterInfo(cluster: number | null): {
    label: string;
    color: string;
    bg: string;
} {
    switch (cluster) {
        case 1:
            return { label: 'Cluster 1', color: '#DC2626', bg: '#FEE2E2' };
        case 2:
            return { label: 'Cluster 2', color: '#F59E0B', bg: '#FEF3C7' };
        case 3:
            return { label: 'Cluster 3', color: '#0D6EFD', bg: '#DBEAFE' };
        case 4:
            return { label: 'Cluster 4', color: '#7C3AED', bg: '#EDE9FE' };
        case 5:
            return { label: 'Cluster 5', color: '#16A34A', bg: '#DCFCE7' };
        default:
            return { label: 'N/A', color: '#64748B', bg: '#F1F5F9' };
    }
}

/**
 * Retorna o label e ícone para a tendência de cluster.
 */
export function getTendenciaInfo(tendencia: string | null): {
    label: string;
    icon: string;
    color: string;
} {
    switch (tendencia) {
        case 'sobe':
            return { label: 'Subindo', icon: '▲', color: '#16A34A' };
        case 'desce':
            return { label: 'Descendo', icon: '▼', color: '#DC2626' };
        case 'mantem':
            return { label: 'Mantém', icon: '►', color: '#F59E0B' };
        default:
            return { label: '—', icon: '', color: '#64748B' };
    }
}

/**
 * Retorna o label em português para o ritmo.
 */
export function getRitmoLabel(ritmo: string): {
    label: string;
    color: string;
} {
    switch (ritmo) {
        case 'significativo':
            return { label: 'Ritmo Significativo', color: '#16A34A' };
        case 'minimo':
            return { label: 'Ritmo Mínimo', color: '#F59E0B' };
        case 'sem_vendas':
        default:
            return { label: 'Sem Vendas', color: '#DC2626' };
    }
}
