import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchAnalise, fetchBriefing, regenerarBriefing, type AnaliseParams } from './analiseService';

export function useAnalise(params: AnaliseParams) {
    return useQuery({
        queryKey: ['analise-mes', params.ano, params.mes ?? 'ultimo'],
        queryFn: () => fetchAnalise(params),
        staleTime: 60_000,
    });
}

/** Só busca depois que a análise resolveu o mês, para os dois falarem do mesmo período. */
export function useBriefing(ano: number, mes: number | null) {
    return useQuery({
        queryKey: ['analise-briefing', ano, mes],
        queryFn: () => fetchBriefing({ ano, mes: mes ?? undefined }),
        enabled: mes != null,
        staleTime: 10 * 60_000,
        retry: false,
    });
}

export function useRegenerarBriefing(ano: number, mes: number | null) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () => regenerarBriefing({ ano, mes: mes ?? undefined }),
        onSuccess: (briefing) => queryClient.setQueryData(['analise-briefing', ano, mes], briefing),
    });
}
