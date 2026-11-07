import { useQuery } from '@tanstack/react-query';
import {
    fetchIndicadoresRede,
    fetchFaturamentoMensal,
    fetchRitmoMensal,
    fetchSdeCenarios,
    type IndicadoresParams,
} from './indicadoresService';
import { fetchTodasEmpresas } from '../dashboard/dashboardService';

export function useIndicadoresRede(params: IndicadoresParams) {
    return useQuery({
        queryKey: ['indicadores-rede', params],
        queryFn: () => fetchIndicadoresRede(params),
    });
}

export function useFaturamentoMensal(params: IndicadoresParams) {
    return useQuery({
        queryKey: ['faturamento-mensal', params.ano, params.cluster],
        queryFn: () => fetchFaturamentoMensal(params),
    });
}

export function useRitmoMensal(params: IndicadoresParams) {
    return useQuery({
        queryKey: ['ritmo-mensal', params.ano, params.cluster],
        queryFn: () => fetchRitmoMensal(params),
    });
}

export function useSdeCenarios(params: IndicadoresParams) {
    return useQuery({
        queryKey: ['sde-cenarios', params],
        queryFn: () => fetchSdeCenarios(params),
    });
}

export function useEmpresasRede(ano: number, cluster?: number) {
    return useQuery({
        queryKey: ['empresas-rede', ano, cluster],
        queryFn: () => fetchTodasEmpresas({
            ano,
            cluster,
            ordem_por: 'nome',
            direcao: 'asc',
        }),
    });
}

export function useEmpresasPorCidade(ano: number, cluster?: number) {
    return useQuery({
        queryKey: ['empresas-cidade', ano, cluster],
        queryFn: async () => {
            const res = await fetchTodasEmpresas({
                ano,
                cluster,
                ordem_por: 'faturamento',
                direcao: 'desc',
            });

            // Aggregate faturamento by cidade
            const porCidade: Record<string, number> = {};
            for (const ej of res.data) {
                const cidade = ej.cidade ?? 'Não informada';
                porCidade[cidade] = (porCidade[cidade] ?? 0) + ej.faturamento_acumulado;
            }

            return Object.entries(porCidade)
                .map(([cidade, faturamento]) => ({ cidade, faturamento }))
                .sort((a, b) => b.faturamento - a.faturamento);
        },
    });
}
