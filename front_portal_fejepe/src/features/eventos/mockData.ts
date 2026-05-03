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
        id_evento: 'ciranda-mej-26',
        nome: "CirandaMEJ'26: O Que Ecoa Entre Nós?",
        descricao: "Monitoramento das metas do CirandaMEJ'26 — evento de fevereiro a maio de 2026.",
        ativo: true,
        ano: 2026,
        mes_referencia: 5,
    },
];

const EVENTOS_META: Record<string, EventoMetaDef[]> = {
    'ciranda-mej-26': [
        {
            tipo: 'faturamento_zero',
            titulo: 'Fora do zero de faturamento',
            descricao: 'EJs com faturamento acumulado maior que zero.',
            meta_percentual: 72,
        },
        {
            tipo: 'colab_zero',
            titulo: 'Fora do zero de colab',
            descricao: 'EJs com faturamento colaborativo acumulado maior que zero.',
            meta_percentual: 34,
        },
        {
            tipo: 'verde_mes',
            titulo: 'No verde de maio',
            descricao: 'EJs que bateram a meta de faturamento acumulado até maio.',
            meta_percentual: 30,
        },
        {
            tipo: 'cluster_tracking',
            titulo: 'Se mantendo ou subindo de cluster',
            descricao: 'EJs com tendência de cluster estável ou crescente.',
            meta_percentual: 67,
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
        faturamento_colab_acumulado: ej.faturamento_colab_acumulado,
        percentual_meta: ej.percentual_meta,
        projetos_colab_totais: ej.projetos_colab_totais,
        atende_cluster_1_2: ej.cluster === 1 || ej.cluster === 2,
        tendencia_cluster: ej.tendencia_cluster ?? null,
    };
}

function filterParticipants(tipo: EventoMetaTipo, empresas: EmpresaComIndicadores[], mesRef: number) {
    if (tipo === 'faturamento_zero') {
        return empresas.filter((empresa) => empresa.faturamento_acumulado > 0);
    }

    if (tipo === 'colab_zero') {
        return empresas.filter((empresa) => empresa.faturamento_colab_acumulado > 0);
    }

    if (tipo === 'verde_mes') {
        const limiarPercentual = (mesRef / 12) * 100;
        return empresas.filter(
            (empresa) => empresa.percentual_meta != null && empresa.percentual_meta >= limiarPercentual,
        );
    }

    if (tipo === 'cluster_tracking') {
        return empresas.filter((empresa) => empresa.tendencia_cluster === 'sobe' || empresa.tendencia_cluster === 'mantem');
    }

    return [];
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

    const submetaContagem = metaDef.tipo === 'verde_mes' && metaContagem > 0
        ? Math.ceil((metaDef.submeta_percentual ?? 0) / 100 * metaContagem)
        : null;
    const subresultadoContagem = metaDef.tipo === 'verde_mes'
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
    const metas = EVENTOS_META[evento.id_evento] ?? EVENTOS_META['ciranda-mej-26'];
    const empresas = mockEmpresaListaResponse.data.filter(isActiveEj);

    return {
        evento,
        total_ejs: empresas.length,
        metas: metas.map((meta) => buildMeta(meta, empresas, empresas.length, evento.mes_referencia)),
    };
}