import { api } from '../../services/api';
import { ENV } from '../../config/env';
import { mockEmpresaListaResponse } from './mockData';
import type { EmpresaComIndicadores, EmpresaListaResponse, EmpresaQueryParams } from '../../types/empresa';

function filterMockData(params: EmpresaQueryParams): EmpresaListaResponse {
    let filtered = [...mockEmpresaListaResponse.data];
    const selectedClusters = params.clusters ?? (params.cluster != null ? [params.cluster] : []);

    // Search by name
    if (params.search) {
        const term = params.search.toLowerCase();
        filtered = filtered.filter((ej) => ej.nome.toLowerCase().includes(term));
    }

    // Filter by cluster
    if (selectedClusters.length > 0) {
        filtered = filtered.filter((ej) => ej.cluster != null && selectedClusters.includes(ej.cluster));
    }

    // Filter by ritmo
    if (params.ritmo) {
        filtered = filtered.filter((ej) => ej.ritmo === params.ritmo);
    }

    // Filter by at least one collaborative project sold
    if (params.fora_do_zero_colab) {
        filtered = filtered.filter((ej) => ej.projetos_colab_totais > 0);
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
        case 'csat': return ej.csat_medio ?? 0;
        case 'percentual_meta': return ej.percentual_meta ?? 0;
        case 'projetos': return ej.projetos_totais;
        default: return ej.faturamento_acumulado;
    }
}

export async function fetchEmpresas(
    params: EmpresaQueryParams = {}
): Promise<EmpresaListaResponse> {
    const selectedClusters = params.clusters ?? (params.cluster != null ? [params.cluster] : []);

    if (ENV.USE_MOCK) {
        await new Promise((resolve) => setTimeout(resolve, 400));
        return filterMockData(params);
    }

    const clusterParam = selectedClusters.length === 1 ? selectedClusters[0] : undefined;
    // Multicluster e ritmo só existem no cliente. A API deve devolver todo o
    // recorte antes desses filtros; aplicá-los em uma página de 20 omite EJs e
    // faz o total depender da ordenação.
    const filtroLocal = selectedClusters.length > 1 || Boolean(params.ritmo);
    const quantidade = filtroLocal ? Number.POSITIVE_INFINITY : (params.page_size ?? 20);

    const resposta = await buscarEmPaginas(
        {
            ...params,
            page: filtroLocal ? undefined : params.page,
            cluster: clusterParam,
            clusters: undefined,
            ritmo: undefined, // ritmo is not a backend param
            cluster_track: params.cluster_track,
        },
        quantidade,
    );

    if (selectedClusters.length > 1) {
        resposta.data = resposta.data.filter(
            (ej) => ej.cluster != null && selectedClusters.includes(ej.cluster),
        );
    }

    // Client-side ritmo filter (not supported by backend)
    if (params.ritmo) {
        resposta.data = resposta.data.filter((ej) => ej.ritmo === params.ritmo);
    }

    if (filtroLocal) {
        const total = resposta.data.length;
        const tamanho = params.page_size ?? 20;
        const pagina = params.page ?? 1;
        if (Number.isFinite(tamanho)) {
            resposta.data = resposta.data.slice((pagina - 1) * tamanho, pagina * tamanho);
        }
        resposta.meta = {
            page: pagina,
            page_size: Number.isFinite(tamanho) ? tamanho : Math.max(total, 1),
            total,
            total_pages: total === 0 ? 0 : (Number.isFinite(tamanho) ? Math.ceil(total / tamanho) : 1),
        };
    }

    return resposta;
}

/**
 * Todas as EJs que casam com os filtros — não só as 100 primeiras.
 *
 * Indicadores (Escalonado, Faturamento por Cidade), Comparação e Cluster Track
 * pediam `page_size: 100` e nunca liam `meta.total_pages`. Com a FEJEPE (43
 * EJs) isso nunca apareceu; com a FEJEMG (291), a tela mostrava 100 e dizia
 * "100 EJs encontradas" (divergência 9.17).
 */
export async function fetchTodasEmpresas(params: EmpresaQueryParams = {}): Promise<EmpresaListaResponse> {
    return fetchEmpresas({ ...params, page: undefined, page_size: Number.POSITIVE_INFINITY });
}

/** Teto de `page_size` em GET /empresas (`le=100` em app/routers/empresas.py). */
const PAGE_SIZE_MAXIMO_DA_API = 100;

/**
 * As `quantidade` primeiras EJs, em quantas páginas da API forem precisas.
 *
 * O "Carregar mais" do Dashboard somava 20 ao `page_size` a cada clique e,
 * no quinto (`page_size=120`), a API respondia 422 e a lista inteira sumia.
 * Aqui `page_size` da tela continua querendo dizer "quantas exibir"; quem
 * traduz isso em páginas de no máximo 100 é esta função.
 */
async function buscarEmPaginas(
    params: EmpresaQueryParams,
    quantidade: number,
): Promise<EmpresaListaResponse> {
    if (params.page != null || quantidade <= PAGE_SIZE_MAXIMO_DA_API) {
        const { data } = await api.get<EmpresaListaResponse>('/empresas', {
            params: { ...params, page_size: Math.min(quantidade, PAGE_SIZE_MAXIMO_DA_API) },
        });
        return data;
    }

    const empresas: EmpresaComIndicadores[] = [];
    let total = 0;
    for (let pagina = 1; ; pagina++) {
        const { data } = await api.get<EmpresaListaResponse>('/empresas', {
            params: { ...params, page: pagina, page_size: PAGE_SIZE_MAXIMO_DA_API },
        });
        empresas.push(...data.data);
        total = data.meta.total;
        if (pagina >= data.meta.total_pages || empresas.length >= quantidade || data.data.length === 0) {
            break;
        }
    }

    const exibidas = empresas.slice(0, quantidade);
    const tamanho = Number.isFinite(quantidade) ? quantidade : Math.max(exibidas.length, 1);
    return {
        data: exibidas,
        meta: {
            page: 1,
            page_size: tamanho,
            total,
            total_pages: Math.max(1, Math.ceil(total / tamanho)),
        },
    };
}
