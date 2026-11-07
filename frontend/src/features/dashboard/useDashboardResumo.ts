import { useQuery } from '@tanstack/react-query';
import type { EmpresaQueryParams } from '../../types/empresa';
import { fetchTodasEmpresas } from './dashboardService';

/** Totais do recorte completo, independentes do botão "Carregar mais". */
export function useDashboardResumo(params: EmpresaQueryParams) {
    const filtros = { ...params, page: undefined, page_size: undefined };
    return useQuery({
        queryKey: ['empresas-resumo', filtros],
        queryFn: async () => {
            const { data } = await fetchTodasEmpresas(filtros);
            return {
                total: data.length,
                faturamento: data.reduce((soma, ej) => soma + ej.faturamento_acumulado, 0),
                projetos: data.reduce((soma, ej) => soma + ej.projetos_totais, 0),
                empresas: data,
            };
        },
        staleTime: 30_000,
    });
}
