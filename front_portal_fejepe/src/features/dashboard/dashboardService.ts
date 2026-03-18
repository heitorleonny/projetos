import { api } from '../../services/api';
import { ENV } from '../../config/env';
import { mockEmpresaListaResponse } from './mockData';
import type { EmpresaComIndicadores, EmpresaListaResponse, EmpresaQueryParams } from '../../types/empresa';

function filterMockData(params: EmpresaQueryParams): EmpresaListaResponse {
    let filtered = [...mockEmpresaListaResponse.data];

    // Search by name
    if (params.search) {
        const term = params.search.toLowerCase();
        filtered = filtered.filter((ej) => ej.nome.toLowerCase().includes(term));
    }

    // Filter by cluster
    if (params.cluster) {
        filtered = filtered.filter((ej) => ej.cluster === params.cluster);
    }

    // Filter by comunidade
    if (params.comunidade) {
        filtered = filtered.filter((ej) => ej.comunidade === params.comunidade);
    }

    // Filter by ritmo
    if (params.ritmo) {
        filtered = filtered.filter((ej) => ej.ritmo === params.ritmo);
    }

    // Sort
    const sortKey = params.ordem_por ?? 'faturamento';
    const dir = params.direcao === 'asc' ? 1 : -1;

    filtered.sort((a, b) => {
        const valA = getSortValue(a, sortKey);
        const valB = getSortValue(b, sortKey);
        if (typeof valA === 'string' && typeof valB === 'string') {
            return valA.localeCompare(valB) * dir;
        }
        return ((valA as number) - (valB as number)) * dir;
    });

    return {
        data: filtered,
        meta: {
            page: 1,
            page_size: 20,
            total: filtered.length,
            total_pages: 1,
        },
    };
}

function getSortValue(ej: EmpresaComIndicadores, key: string): string | number {
    switch (key) {
        case 'nome': return ej.nome;
        case 'faturamento': return ej.faturamento_acumulado;
        case 'faturamento_colab': return ej.faturamento_colab_acumulado;
        case 'cluster': return ej.cluster ?? 0;
        case 'comunidade': return ej.comunidade ?? '';
        case 'csat': return ej.csat_medio ?? 0;
        case 'percentual_meta': return ej.percentual_meta ?? 0;
        case 'projetos': return ej.projetos_totais;
        default: return ej.faturamento_acumulado;
    }
}

export async function fetchEmpresas(
    params: EmpresaQueryParams = {}
): Promise<EmpresaListaResponse> {
    if (ENV.USE_MOCK) {
        await new Promise((resolve) => setTimeout(resolve, 400));
        return filterMockData(params);
    }

    const response = await api.get<EmpresaListaResponse>('/empresas', {
        params: {
            ...params,
            ritmo: undefined, // ritmo is not a backend param
        },
    });

    // Client-side ritmo filter (not supported by backend)
    if (params.ritmo) {
        response.data.data = response.data.data.filter((ej) => ej.ritmo === params.ritmo);
        response.data.meta.total = response.data.data.length;
    }

    return response.data;
}
