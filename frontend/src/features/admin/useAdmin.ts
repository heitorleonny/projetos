import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/useAuth';
import {
    atualizarFederacao,
    atualizarUsuario,
    convidarUsuario,
    fetchCargas,
    fetchFederacoes,
    fetchSessao,
    fetchUsuarios,
    importarPlanilha,
    type Convite,
    type FederacaoAtualizacao,
    type PedidoImportacao,
    type UsuarioAtualizacao,
} from './adminService';

/**
 * Papel e federação segundo o BANCO (não o token). É o que decide se o link
 * do painel aparece; a API repete a checagem em cada endpoint.
 */
export function useSessaoAdmin() {
    const { user } = useAuth();
    return useQuery({
        queryKey: ['admin', 'sessao', user?.id],
        queryFn: fetchSessao,
        enabled: Boolean(user),
        staleTime: 5 * 60_000,
        retry: false,
    });
}

export function useFederacoesAdmin(habilitado = true) {
    return useQuery({ queryKey: ['admin', 'federacoes'], queryFn: fetchFederacoes, enabled: habilitado });
}

export function useAtualizarFederacao() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ id, dados }: { id: number; dados: FederacaoAtualizacao }) => atualizarFederacao(id, dados),
        onSuccess: async () => { await Promise.all([qc.invalidateQueries({ queryKey: ['admin', 'federacoes'] }), qc.invalidateQueries({ queryKey: ['master'] })]); },
    });
}

export function useUsuariosAdmin() {
    return useQuery({ queryKey: ['admin', 'usuarios'], queryFn: fetchUsuarios });
}

export function useAtualizarUsuario() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ id, dados }: { id: number; dados: UsuarioAtualizacao }) => atualizarUsuario(id, dados),
        onSuccess: async () => { await Promise.all([qc.invalidateQueries({ queryKey: ['admin', 'usuarios'] }), qc.invalidateQueries({ queryKey: ['master'] })]); },
    });
}

export function useConvidarUsuario() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (convite: Convite) => convidarUsuario(convite),
        onSuccess: async () => { await Promise.all([qc.invalidateQueries({ queryKey: ['admin', 'usuarios'] }), qc.invalidateQueries({ queryKey: ['master'] })]); },
    });
}

export function useCargas() {
    return useQuery({ queryKey: ['admin', 'cargas'], queryFn: fetchCargas });
}

export function useImportarPlanilha() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (pedido: PedidoImportacao) => importarPlanilha(pedido),
        onSettled: (_dados, _erro, pedido) => {
            // Carga gravada muda os números de todas as telas; a simulação, nenhum.
            qc.invalidateQueries({ queryKey: ['admin', 'cargas'] });
            if (!pedido.simular) {
                qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== 'admin' });
            }
        },
    });
}
