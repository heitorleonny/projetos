import { api } from '../../services/api';
import { ENV } from '../../config/env';
import { getMockEventoDetalhe, mockEventos } from './mockData';
import type { EventoDetalheResponse, EventoResumo } from '../../types/evento';

export async function fetchEventos(): Promise<EventoResumo[]> {
    if (ENV.USE_MOCK) {
        await new Promise((resolve) => setTimeout(resolve, 250));
        return mockEventos;
    }

    const response = await api.get<EventoResumo[]>('/eventos');
    return response.data;
}

export async function fetchEventoDetalhe(eventoId: string, ano = 2026, mes?: number): Promise<EventoDetalheResponse> {
    if (ENV.USE_MOCK) {
        await new Promise((resolve) => setTimeout(resolve, 250));
        return getMockEventoDetalhe(eventoId);
    }

    const response = await api.get<EventoDetalheResponse>(`/eventos/${eventoId}`, {
        params: mes !== undefined ? { ano, mes } : { ano },
    });

    return response.data;
}