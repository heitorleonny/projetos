export function variacaoComparacao(indicador: string, primeiro: number | null, ultimo: number | null): number | null {
    if (primeiro == null || ultimo == null) return null;
    if (indicador === 'cluster' || indicador === 'percentual_meta') return ultimo - primeiro;
    if (indicador === 'taxa_colab') return (ultimo - primeiro) * 100;
    return primeiro !== 0 ? ((ultimo - primeiro) / Math.abs(primeiro)) * 100 : null;
}
