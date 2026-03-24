import { fetchEmpresas } from '../dashboard/dashboardService';
import type { EmpresaComIndicadores, EmpresaQueryParams } from '../../types/empresa';

export interface ComparacaoAno {
    ano: number;
    empresas: EmpresaComIndicadores[];
}

export async function fetchComparacaoAnos(
    anos: number[],
    mes?: number,
    comunidade?: string,
): Promise<ComparacaoAno[]> {
    const results = await Promise.all(
        anos.map(async (ano) => {
            const params: EmpresaQueryParams = {
                ano,
                mes,
                comunidade,
                page_size: 100,
                ordem_por: 'faturamento',
                direcao: 'desc',
            };
            const res = await fetchEmpresas(params);
            return { ano, empresas: res.data };
        }),
    );
    return results;
}
