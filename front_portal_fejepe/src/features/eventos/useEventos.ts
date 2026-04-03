import { useQuery } from '@tanstack/react-query';
import { fetchEventoDetalhe, fetchEventos } from './eventosService';

export function useEventos() {
    return useQuery({
        queryKey: ['eventos'],
        queryFn: fetchEventos,
        placeholderData: (previousData) => previousData,
    });
}

export function useEventoDetalhe(eventoId: string | null | undefined, ano = 2026, mes = 4) {
    return useQuery({
        queryKey: ['evento-detalhe', eventoId, ano, mes],
        queryFn: () => fetchEventoDetalhe(eventoId as string, ano, mes),
        enabled: Boolean(eventoId),
        placeholderData: (previousData) => previousData,
    });
}