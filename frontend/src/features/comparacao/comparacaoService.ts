import { fetchTodasEmpresas } from '../dashboard/dashboardService';
import type { EmpresaComIndicadores, EmpresaQueryParams } from '../../types/empresa';

export interface ComparacaoAno {
    ano: number;
    empresas: EmpresaComIndicadores[];
}

export async function fetchComparacaoAnos(
    anos: number[],
    mes?: number,
): Promise<ComparacaoAno[]> {
    const results = await Promise.all(
        anos.map(async (ano) => {
            const params: EmpresaQueryParams = {
                ano,
                mes,
                ordem_por: 'faturamento',
                direcao: 'desc',
            };
            const res = await fetchTodasEmpresas(params);
            // O cadastro da EJ existe em todos os anos, mas a exportação
            // disponível pode trazer fatos de apenas um. Sem fatos, zero seria
            // confundido com um resultado anual real na comparação/CSV.
            return { ano, empresas: res.data.filter((ej) => ej.tem_dados_no_ano !== false) };
        }),
    );
    return results;
}
