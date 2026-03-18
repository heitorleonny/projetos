import { useQuery } from '@tanstack/react-query';
import { fetchEmpresas } from './dashboardService';
import type { EmpresaQueryParams } from '../../types/empresa';

export function useDashboard(params: EmpresaQueryParams = {}) {
    return useQuery({
        queryKey: ['empresas', params],
        queryFn: () => fetchEmpresas(params),
    });
}
