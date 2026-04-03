import { mockEmpresaListaResponse } from '../dashboard/mockData';
import type {
    EventoDetalheResponse,
    EventoMetaParticipante,
    EventoMetaResultado,
    EventoMetaTipo,
    EventoResumo,
} from '../../types/evento';
import type { EmpresaComIndicadores } from '../../types/empresa';

type EventoMetaDef = {
    tipo: EventoMetaTipo;
    titulo: string;
    descricao: string;
    meta_percentual: number;
    submeta_titulo?: string;
    submeta_percentual?: number;
};

const EVENTOS_MOCK: EventoResumo[] = [
    {
        id_evento: 'encontro-das-instancias',
        nome: 'Encontro das Instancias',
        descricao: 'Monitoramento das metas operacionais do encontro de abril.',
        ativo: true,
        ano: 2026,
        mes_referencia: 4,
    },
    {
        id_evento: 'proximo-evento-fejepe',
        nome: 'Próximo Evento FEJEPE',
        descricao: 'Configuração base para a próxima edição do monitoramento.',
        ativo: false,
        ano: 2026,
        mes_referencia: 4,
    },
];

const EVENTOS_META: Record<string, EventoMetaDef[]> = {
    'encontro-das-instancias': [
        {
            tipo: 'fora_do_zero',
            titulo: 'EJs fora do zero',
            descricao: 'EJs com faturamento acumulado maior que zero.',
            meta_percentual: 70,
        },
        {
            tipo: 'verde_abril',
            titulo: 'Verde de Abril',
            descricao: 'EJs que bateram a meta de faturamento acumulado até abril.',
            meta_percentual: 35,
            submeta_titulo: 'Cluster 1 ou 2 dentro do Verde',
            submeta_percentual: 15,
        },
        {
            tipo: 'colab_tracking',
            titulo: 'Tracking de colab',
            descricao: 'EJs com pelo menos um projeto colaborativo vendido.',
            meta_percentual: 15,
        },
    ],
    'proximo-evento-fejepe': [
        {
            tipo: 'fora_do_zero',
            titulo: 'EJs fora do zero',
            descricao: 'EJs com faturamento acumulado maior que zero.',
            meta_percentual: 60,
        },
        {
            tipo: 'verde_abril',
            titulo: 'Verde do período',
            descricao: 'EJs que bateram a meta do recorte escolhido.',
            meta_percentual: 30,
            submeta_titulo: 'Cluster 1 ou 2 dentro do Verde',
            submeta_percentual: 15,
        },
        {
            tipo: 'colab_tracking',
            titulo: 'Tracking de colab',
            descricao: 'EJs com pelo menos um projeto colaborativo vendido.',
            meta_percentual: 10,
        },
    ],
};

function isActiveEj(ej: EmpresaComIndicadores) {
    const status = (ej.status ?? '').trim().toLowerCase();
    return !status || !['inativa', 'inativo', 'desativada', 'desativado'].includes(status);
}

function toParticipant(ej: EmpresaComIndicadores): EventoMetaParticipante {
    return {
        id_ej: ej.id_ej,
        nome: ej.nome,
        comunidade: ej.comunidade,
        cluster: ej.cluster,
        status: ej.status,
        faturamento_acumulado: ej.faturamento_acumulado,
        percentual_meta: ej.percentual_meta,
        projetos_colab_totais: ej.projetos_colab_totais,
        atende_cluster_1_2: ej.cluster === 1 || ej.cluster === 2,
    };
}

function filterParticipants(tipo: EventoMetaTipo, empresas: EmpresaComIndicadores[], mesRef: number) {
    if (tipo === 'fora_do_zero') {
        return empresas.filter((empresa) => empresa.faturamento_acumulado > 0);
    }

    if (tipo === 'verde_abril') {
        const limiarPercentual = (mesRef / 12) * 100;
        return empresas.filter(
            (empresa) => empresa.percentual_meta != null && empresa.percentual_meta >= limiarPercentual,
        );
    }

    return empresas.filter((empresa) => empresa.projetos_colab_totais > 0);
}

function buildMeta(
    metaDef: EventoMetaDef,
    empresas: EmpresaComIndicadores[],
    totalEjs: number,
    mesRef: number,
): EventoMetaResultado {
    const metaContagem = totalEjs > 0 ? Math.ceil((metaDef.meta_percentual / 100) * totalEjs) : 0;
    const participantes = filterParticipants(metaDef.tipo, empresas, mesRef);
    const resultadoContagem = participantes.length;
    const resultadoPercentual = totalEjs > 0 ? Number(((resultadoContagem / totalEjs) * 100).toFixed(1)) : 0;
    const gapContagem = Math.max(metaContagem - resultadoContagem, 0);
    const gapPercentual = Math.max(Number((metaDef.meta_percentual - resultadoPercentual).toFixed(1)), 0);

    const submetaContagem = metaDef.tipo === 'verde_abril' && metaContagem > 0
        ? Math.ceil((metaDef.submeta_percentual ?? 0) / 100 * metaContagem)
        : null;
    const subresultadoContagem = metaDef.tipo === 'verde_abril'
        ? participantes.filter((ej) => ej.cluster === 1 || ej.cluster === 2).length
        : null;
    const subgapContagem = submetaContagem != null && subresultadoContagem != null
        ? Math.max(submetaContagem - subresultadoContagem, 0)
        : null;

    return {
        tipo: metaDef.tipo,
        titulo: metaDef.titulo,
        descricao: metaDef.descricao,
        meta_percentual: metaDef.meta_percentual,
        meta_contagem: metaContagem,
        resultado_percentual: resultadoPercentual,
        resultado_contagem: resultadoContagem,
        gap_percentual: gapPercentual,
        gap_contagem: gapContagem,
        submeta_titulo: metaDef.submeta_titulo ?? null,
        submeta_percentual: metaDef.submeta_percentual ?? null,
        submeta_contagem: submetaContagem,
        subresultado_contagem: subresultadoContagem,
        subgap_contagem: subgapContagem,
        participantes: participantes.map(toParticipant).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    };
}

export const mockEventos = EVENTOS_MOCK;

export function getMockEventoDetalhe(eventoId: string): EventoDetalheResponse {
    const evento = EVENTOS_MOCK.find((item) => item.id_evento === eventoId) ?? EVENTOS_MOCK[0];
    const metas = EVENTOS_META[evento.id_evento] ?? EVENTOS_META['encontro-das-instancias'];
    const empresas = mockEmpresaListaResponse.data.filter(isActiveEj);

    return {
        evento,
        total_ejs: empresas.length,
        metas: metas.map((meta) => buildMeta(meta, empresas, empresas.length, evento.mes_referencia)),
    };
}