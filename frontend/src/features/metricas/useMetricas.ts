import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/useAuth';
import {
    arquivarMetrica, atualizarMetrica, criarMetrica, definirPainel, excluirMetrica, fetchCatalogo, fetchMetricas,
    fetchResultado, reordenarMetricas, restaurarMetrica, type MetricaEntrada,
} from './metricasService';

/* A chave inclui o usuário: trocar de conta nunca reaproveita dado de outra federação. */

export function useCatalogo() {
    const { user } = useAuth();
    return useQuery({ queryKey: ['metricas', user?.id, 'catalogo'], queryFn: fetchCatalogo, enabled: Boolean(user), staleTime: 5 * 60_000 });
}

export function useMetricas(arquivadas = false, habilitado = true) {
    const { user } = useAuth();
    return useQuery({
        queryKey: ['metricas', user?.id, 'lista', arquivadas],
        queryFn: () => fetchMetricas(arquivadas),
        enabled: Boolean(user) && habilitado,
    });
}

export function useResultado(id: number, versao: number) {
    const { user } = useAuth();
    return useQuery({
        queryKey: ['metricas', user?.id, 'resultado', id, versao],
        queryFn: () => fetchResultado(id),
        enabled: Boolean(user),
        staleTime: 60_000,
    });
}

function useInvalidar() {
    const qc = useQueryClient();
    return () => qc.invalidateQueries({ queryKey: ['metricas'] });
}

export function useSalvarMetrica() {
    const invalidar = useInvalidar();
    return useMutation({
        mutationFn: ({ id, dados }: { id?: number; dados: MetricaEntrada }) =>
            id === undefined ? criarMetrica(dados) : atualizarMetrica(id, dados),
        onSuccess: invalidar,
    });
}

export function useAcaoMetrica() {
    const invalidar = useInvalidar();
    return useMutation({
        mutationFn: async ({ id, acao }: { id: number; acao: 'tirar' | 'colocar' | 'arquivar' | 'restaurar' | 'excluir' }) => {
            if (acao === 'tirar' || acao === 'colocar') return definirPainel(id, acao === 'colocar');
            if (acao === 'arquivar') return arquivarMetrica(id);
            if (acao === 'restaurar') return restaurarMetrica(id);
            return excluirMetrica(id);
        },
        onSuccess: invalidar,
    });
}

export function useReordenar() {
    const invalidar = useInvalidar();
    return useMutation({ mutationFn: reordenarMetricas, onSuccess: invalidar });
}
