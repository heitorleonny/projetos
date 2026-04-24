import { useState, useRef, useCallback, useMemo } from 'react';
import html2canvas from 'html2canvas';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    LineChart, Line,
} from 'recharts';
import { useIndicadoresRede, useFaturamentoMensal, useRitmoMensal, useEmpresasRede, useSdeCenarios } from './useIndicadores';
import type { EjMovimento, SdeCenario } from './indicadoresService';
import { formatCurrency, getClusterInfo } from '../../utils/formatters';

const COMUNIDADES = ['CAPIBA', 'PRAIEIRA', 'TROPICANA', 'INCUBADORA DE APAIXONADOS', 'MANDACARU'];
const CLUSTERS = [1, 2, 3, 4, 5];
const MESES_ESCALONADO = [
    'JANEIRO', 'FEVEREIRO', 'MARCO', 'ABRIL', 'MAIO', 'JUNHO',
    'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO',
];

type EscalonadoStatus = 'azul' | 'verde' | 'amarelo' | 'vermelho' | 'cinza';

interface EscalonadoItem {
    id_ej: number;
    nome: string;
    status: EscalonadoStatus;
    mesPosicao: number;
}

const ESCALONADO_STATUS_STYLE: Record<EscalonadoStatus, { label: string; bg: string; text: string; border: string; countBg: string; countText?: string }> = {
    azul: {
        label: 'Azul',
        bg: '#2563EB',
        text: '#EFF6FF',
        border: '#1D4ED8',
        countBg: '#1D4ED825',
    },
    verde: {
        label: 'Verde',
        bg: '#16A34A',
        text: '#F0FDF4',
        border: '#15803D',
        countBg: '#15803D25',
    },
    amarelo: {
        label: 'Amarelo',
        bg: '#FACC15',
        text: '#1F2937',
        border: '#EAB308',
        countBg: '#FACC15',
        countText: '#111827',
    },
    vermelho: {
        label: 'Vermelho',
        bg: '#EF4444',
        text: '#FEF2F2',
        border: '#DC2626',
        countBg: '#DC262625',
    },
    cinza: {
        label: 'Zeradas',
        bg: '#6B7280',
        text: '#F9FAFB',
        border: '#4B5563',
        countBg: '#4B556325',
    },
};

function clampMes(value: number): number {
    if (value < 1) return 1;
    if (value > 12) return 12;
    return value;
}

const selectClass =
    'bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all cursor-pointer appearance-none';
const selectStyle = {
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 10px center',
    backgroundSize: '16px',
};

const ESCALONADO_BASE_OFFSET = 8;
const ESCALONADO_DEGRAU_OFFSET = 10;
const ESCALONADO_BADGE_HEIGHT = 30;
const ESCALONADO_BADGE_GAP = 4;
const ESCALONADO_ALTURA_MINIMA = 340;

function drawRoundedRect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    radius: number,
) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

function truncateCanvasText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
    if (ctx.measureText(text).width <= maxWidth) return text;

    const suffix = '...';
    let result = text;
    while (result.length > 0 && ctx.measureText(result + suffix).width > maxWidth) {
        result = result.slice(0, -1);
    }
    return result + suffix;
}

export default function IndicadoresPage() {
    const [ano, setAno] = useState(2026);
    const [cluster, setCluster] = useState<number | undefined>();
    const [comunidade, setComunidade] = useState<string | undefined>();
    const [selectedCharts, setSelectedCharts] = useState<Set<string>>(new Set());

    const clusterRef = useRef<HTMLDivElement>(null);
    const ritmoRef = useRef<HTMLDivElement>(null);
    const linhaRef = useRef<HTMLDivElement>(null);
    const cidadeRef = useRef<HTMLDivElement>(null);
    const escalonadoRef = useRef<HTMLDivElement>(null);
    const escalonadoCaptureRef = useRef<HTMLDivElement>(null);

    const params = { ano, cluster, comunidade };
    const mesAtualCalendario = new Date().getMonth() + 1;

    const { data: indicadores, isLoading: loadingInd } = useIndicadoresRede(params);
    const { data: faturamentoMensal, isLoading: loadingFat } = useFaturamentoMensal(params);
    const { data: empresasRede, isLoading: loadingEjs } = useEmpresasRede(ano, cluster, comunidade);
    const { data: ritmoMensal, isLoading: loadingRitmo } = useRitmoMensal(params);
    const { data: sdeCenarios, isLoading: loadingSde } = useSdeCenarios(params);

    const empresasEscalonadas = useMemo(() => empresasRede?.data ?? [], [empresasRede?.data]);

    // ── Chart data ──

    const clusterData = indicadores
        ? Object.entries(indicadores.distribuicao_clusters)
            .map(([key, count]) => ({
                name: `Cluster ${key}`,
                value: count,
                color: getClusterInfo(Number(key)).color,
            }))
            .sort((a, b) => Number(a.name.split(' ')[1]) - Number(b.name.split(' ')[1]))
        : [];

    const cidadeChartData = useMemo(() => {
        const porCidade: Record<string, number> = {};
        for (const ej of empresasEscalonadas) {
            const cidade = ej.cidade ?? 'Nao informada';
            porCidade[cidade] = (porCidade[cidade] ?? 0) + ej.faturamento_acumulado;
        }

        return Object.entries(porCidade)
            .map(([cidade, faturamento]) => ({ cidade, faturamento }))
            .sort((a, b) => b.faturamento - a.faturamento)
            .slice(0, 10);
    }, [empresasEscalonadas]);

    const escalonadoData = useMemo(() => {
        const limiarVerde = (mesAtualCalendario / 12) * 100;
        const limiarAmarelo = (Math.max(0, mesAtualCalendario - 1) / 12) * 100;

        const grupos: Record<number, EscalonadoItem[]> = {
            0: [],
            1: [],
            2: [],
            3: [],
            4: [],
            5: [],
            6: [],
            7: [],
            8: [],
            9: [],
            10: [],
            11: [],
            12: [],
        };

        const contadores: Record<EscalonadoStatus, number> = {
            cinza: 0,
            vermelho: 0,
            amarelo: 0,
            verde: 0,
            azul: 0,
        };

        let semMetaCount = 0;

        for (const ej of empresasEscalonadas) {
            const faturamento = ej.faturamento_acumulado ?? 0;
            const percentual = ej.percentual_meta;

            let status: EscalonadoStatus;
            let mesPosicao = 0;

            if (faturamento <= 0) {
                status = 'cinza';
                mesPosicao = 0;
            } else {
                const mesEstimado = percentual == null
                    ? 1
                    : clampMes(Math.max(1, Math.floor((percentual / 100) * 12)));

                if (percentual != null && percentual >= 100) {
                    status = 'azul';
                    mesPosicao = 12;
                } else if (percentual != null && percentual >= limiarVerde) {
                    status = 'verde';
                    mesPosicao = mesEstimado;
                } else if (percentual != null && percentual >= limiarAmarelo) {
                    status = 'amarelo';
                    mesPosicao = mesEstimado;
                } else {
                    status = 'vermelho';
                    mesPosicao = mesEstimado;
                    if (percentual == null) semMetaCount += 1;
                }
            }

            grupos[mesPosicao].push({
                id_ej: ej.id_ej,
                nome: ej.nome,
                status,
                mesPosicao,
            });

            contadores[status] += 1;
        }

        for (const key of Object.keys(grupos)) {
            grupos[Number(key)].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
        }

        return {
            grupos,
            contadores,
            limiarVerde,
            limiarAmarelo,
            mesAtualCalendario,
            total: empresasEscalonadas.length,
            semMetaCount,
            houveTruncamento: (empresasRede?.meta.total ?? 0) > empresasEscalonadas.length,
            totalReal: empresasRede?.meta.total ?? empresasEscalonadas.length,
        };
    }, [empresasEscalonadas, empresasRede?.meta.total, mesAtualCalendario]);

    const faturamentoAcumuladoData = (faturamentoMensal ?? []).map((item) => ({
        mes: item.mes,
        label: item.label,
        faturamento_acumulado: item.faturamento,
    }));

    // ── Export ──

    const downloadCanvas = (canvas: HTMLCanvasElement, fileName: string) => {
        const link = document.createElement('a');
        link.download = fileName;
        link.href = canvas.toDataURL('image/png');
        link.click();
    };

    const buildEscalonadoCanvas = useCallback((): HTMLCanvasElement | null => {
        const colunas = [
            { mes: 0, label: 'ZERADAS' },
            ...MESES_ESCALONADO.map((label, index) => ({ mes: index + 1, label })),
        ];

        const maxItensColuna = Math.max(
            1,
            ...Object.values(escalonadoData.grupos).map((items) => items.length),
        );

        const alturaConteudo =
            maxItensColuna * ESCALONADO_BADGE_HEIGHT +
            Math.max(0, maxItensColuna - 1) * ESCALONADO_BADGE_GAP;

        const alturaEscada = 11 * ESCALONADO_DEGRAU_OFFSET;

        const exportAltura = Math.max(
            ESCALONADO_ALTURA_MINIMA,
            alturaConteudo + alturaEscada + ESCALONADO_BASE_OFFSET + 10,
        );

        const width = 1560;
        const headerHeight = 82;
        const footerHeight = 86;
        const monthChipHeight = 28;
        const graphTop = headerHeight;
        const graphBottomPadding = 12;
        const graphHeight = exportAltura;
        const chipsTop = graphTop + graphHeight + graphBottomPadding;
        const footerTop = chipsTop + monthChipHeight + 20;
        const height = footerTop + footerHeight;

        const canvas = document.createElement('canvas');
        canvas.width = width * 2;
        canvas.height = height * 2;

        const ctx = canvas.getContext('2d');
        if (!ctx) return null;

        ctx.scale(2, 2);
        ctx.fillStyle = '#0B1220';
        ctx.fillRect(0, 0, width, height);

        const colGap = 8;
        const paddingX = 24;
        const innerWidth = width - paddingX * 2;
        const colWidth = (innerWidth - (colunas.length - 1) * colGap) / colunas.length;

        ctx.fillStyle = '#F8FAFC';
        ctx.font = '700 24px sans-serif';
        ctx.fillText('ESCALONADO DE FATURAMENTO', paddingX, 36);

        ctx.fillStyle = '#94A3B8';
        ctx.font = '500 14px sans-serif';
        ctx.fillText(`Monitoramento da rede | Referencia: ${MESES_ESCALONADO[mesAtualCalendario - 1]}`, paddingX, 58);

        ctx.textAlign = 'right';
        ctx.fillText(
            `Verde >= ${escalonadoData.limiarVerde.toFixed(1)}% | Amarelo >= ${escalonadoData.limiarAmarelo.toFixed(1)}%`,
            width - paddingX,
            58,
        );
        ctx.textAlign = 'left';

        colunas.forEach((coluna, index) => {
            const x = paddingX + index * (colWidth + colGap);

            drawRoundedRect(ctx, x, graphTop, colWidth, graphHeight, 10);
            ctx.fillStyle = '#020617';
            ctx.fill();
            ctx.strokeStyle = 'rgba(148, 163, 184, 0.18)';
            ctx.lineWidth = 1;
            ctx.stroke();

            const items = escalonadoData.grupos[coluna.mes] ?? [];
            const degrau = coluna.mes === 0 ? 0 : (coluna.mes - 1) * ESCALONADO_DEGRAU_OFFSET;
            const deslocamentoVertical = ESCALONADO_BASE_OFFSET - degrau;
            const baseY = graphTop + graphHeight - 6 + deslocamentoVertical;

            items.forEach((item, itemIndex) => {
                const y = baseY - (itemIndex + 1) * (ESCALONADO_BADGE_HEIGHT + ESCALONADO_BADGE_GAP);
                const style = ESCALONADO_STATUS_STYLE[item.status];
                drawRoundedRect(ctx, x + 4, y, colWidth - 8, ESCALONADO_BADGE_HEIGHT, 6);
                ctx.fillStyle = style.bg;
                ctx.fill();
                ctx.strokeStyle = style.border;
                ctx.lineWidth = 1;
                ctx.stroke();

                ctx.fillStyle = style.text;
                ctx.font = '600 12px sans-serif';
                const label = truncateCanvasText(ctx, item.nome, colWidth - 16);
                ctx.fillText(label, x + 8, y + 19);
            });

            drawRoundedRect(ctx, x, chipsTop, colWidth, monthChipHeight, 6);
            ctx.fillStyle = '#1E3A8A';
            ctx.fill();
            ctx.strokeStyle = '#3B82F6';
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = '#E2E8F0';
            ctx.font = '700 11px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(coluna.label, x + colWidth / 2, chipsTop + 18);
            ctx.textAlign = 'left';
        });

        const counters: EscalonadoStatus[] = ['cinza', 'vermelho', 'amarelo', 'verde', 'azul'];
        const counterGap = 12;
        let cursorX = paddingX;
        const counterY = footerTop;

        counters.forEach((status) => {
            const style = ESCALONADO_STATUS_STYLE[status];
            const total = escalonadoData.contadores[status];
            const text = `${total} EJ${total !== 1 ? 's' : ''} ${style.label}`;

            ctx.font = '700 13px sans-serif';
            const textWidth = ctx.measureText(text).width;
            const boxWidth = textWidth + 24;

            drawRoundedRect(ctx, cursorX, counterY, boxWidth, 34, 17);
            ctx.fillStyle = style.countBg;
            ctx.fill();
            ctx.strokeStyle = style.border;
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = style.countText ?? style.text;
            ctx.fillText(text, cursorX + 12, counterY + 22);

            cursorX += boxWidth + counterGap;
        });

        return canvas;
    }, [escalonadoData.contadores, escalonadoData.grupos, escalonadoData.limiarAmarelo, escalonadoData.limiarVerde, mesAtualCalendario]);

    const exportEscalonado = useCallback(async () => {
        const target = escalonadoCaptureRef.current ?? escalonadoRef.current;
        if (!target) return;

        try {
            const canvas = await html2canvas(target, {
                backgroundColor: '#0F172A',
                scale: 2,
                useCORS: true,
                scrollX: 0,
                scrollY: -window.scrollY,
            });

            downloadCanvas(canvas, `grafico-escalonado-${ano}.png`);
        } catch {
            const fallbackCanvas = buildEscalonadoCanvas();
            if (fallbackCanvas) {
                downloadCanvas(fallbackCanvas, `grafico-escalonado-${ano}.png`);
                return;
            }
            alert('Nao foi possivel exportar o grafico escalonado. Tente novamente.');
        }
    }, [ano, buildEscalonadoCanvas]);

    const toggleChart = (id: string) => {
        setSelectedCharts((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const exportSelectedCharts = useCallback(async () => {
        const refs: Record<string, React.RefObject<HTMLDivElement | null>> = {
            escalonado: escalonadoRef,
            cluster: clusterRef,
            ritmo: ritmoRef,
            linha: linhaRef,
            cidade: cidadeRef,
        };

        const charts = selectedCharts.size > 0
            ? selectedCharts
            : new Set(['escalonado', 'cluster', 'ritmo', 'linha', 'cidade']);

        for (const chartId of charts) {
            const ref = refs[chartId];
            if (!ref?.current) continue;

            // Escalonado is an HTML layout; capture the whole card as PNG.
            if (chartId === 'escalonado') {
                await exportEscalonado();
                continue;
            }

            const svg = ref.current.querySelector('svg');
            if (!svg) continue;

            const svgData = new XMLSerializer().serializeToString(svg);
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            if (!ctx) continue;

            const img = new Image();
            const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
            const url = URL.createObjectURL(blob);

            await new Promise<void>((resolve) => {
                img.onload = () => {
                    canvas.width = img.width * 2;
                    canvas.height = img.height * 2;
                    ctx.scale(2, 2);
                    ctx.fillStyle = '#0F172A';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0);

                    downloadCanvas(canvas, `grafico-${chartId}-${ano}.png`);

                    URL.revokeObjectURL(url);
                    resolve();
                };
                img.src = url;
            });
        }
    }, [selectedCharts, ano, exportEscalonado]);

    const isLoading = loadingInd || loadingFat || loadingEjs || loadingRitmo;

    const chartIds = ['escalonado', 'cluster', 'ritmo', 'linha', 'cidade'];
    const chartLabels: Record<string, string> = {
        escalonado: 'Escalonado de Faturamento',
        cluster: 'Distribuição por Cluster',
        ritmo: 'Ritmo Mínimo e Ritmo Significativo',
        linha: 'Faturamento Acumulado',
        cidade: 'Faturamento por Cidade',
    };

    const escalonadoColunas = [
        { mes: 0, label: 'ZERADAS' },
        ...MESES_ESCALONADO.map((label, index) => ({ mes: index + 1, label })),
    ];

    const escalonadoAltura = useMemo(() => {
        const maxItensColuna = Math.max(
            1,
            ...Object.values(escalonadoData.grupos).map((items) => items.length),
        );

        const alturaConteudo =
            maxItensColuna * ESCALONADO_BADGE_HEIGHT +
            Math.max(0, maxItensColuna - 1) * ESCALONADO_BADGE_GAP;

        const alturaEscada = 11 * ESCALONADO_DEGRAU_OFFSET;

        return Math.max(
            ESCALONADO_ALTURA_MINIMA,
            alturaConteudo + alturaEscada + ESCALONADO_BASE_OFFSET + 10,
        );
    }, [escalonadoData.grupos]);

    return (
        <div>
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-1 h-8 rounded-full bg-gradient-to-b from-primary-400 to-primary-600" />
                    <h1 className="font-heading text-3xl font-bold text-gradient">
                        Indicadores da Rede
                    </h1>
                </div>
                <p className="text-neutral-400 ml-5 text-sm italic">
                    Visão analítica consolidada do desempenho da rede FEJEPE.
                </p>
            </div>

            {/* KPI Summary */}
            {indicadores && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    <KpiCard label="Faturamento Total" value={formatCurrency(indicadores.faturamento_total)} />
                    <KpiCard label="EJs na Rede" value={indicadores.total_ejs.toString()} />
                    <KpiCard label="EJs Fora do Zero" value={indicadores.ejs_fora_do_zero.toString()} />
                    <KpiCard
                        label="Crescimento"
                        value={
                            indicadores.crescimento_vs_ano_anterior != null
                                ? `${indicadores.crescimento_vs_ano_anterior > 0 ? '+' : ''}${indicadores.crescimento_vs_ano_anterior.toFixed(1)}%`
                                : '—'
                        }
                        color={
                            indicadores.crescimento_vs_ano_anterior != null
                                ? indicadores.crescimento_vs_ano_anterior >= 0 ? '#16A34A' : '#DC2626'
                                : undefined
                        }
                    />
                </div>
            )}

            {/* Filters */}
            <div className="glass-card rounded-2xl p-5 mb-8">
                <div className="flex flex-col sm:flex-row sm:items-end gap-4">
                    <div>
                        <label className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2 block">Ano</label>
                        <select value={ano} onChange={(e) => setAno(Number(e.target.value))} className={selectClass} style={selectStyle}>
                            {[2023, 2024, 2025, 2026].map((a) => (
                                <option key={a} value={a} className="bg-neutral-800">{a}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2 block">Cluster</label>
                        <select
                            value={cluster ?? ''}
                            onChange={(e) => setCluster(e.target.value ? Number(e.target.value) : undefined)}
                            className={selectClass}
                            style={selectStyle}
                        >
                            <option value="" className="bg-neutral-800">Todos</option>
                            {CLUSTERS.map((c) => (
                                <option key={c} value={c} className="bg-neutral-800">Cluster {c}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2 block">Comunidade</label>
                        <select
                            value={comunidade ?? ''}
                            onChange={(e) => setComunidade(e.target.value || undefined)}
                            className={selectClass}
                            style={selectStyle}
                        >
                            <option value="" className="bg-neutral-800">Todas</option>
                            {COMUNIDADES.map((c) => (
                                <option key={c} value={c} className="bg-neutral-800">{c}</option>
                            ))}
                        </select>
                    </div>

                    {/* Export */}
                    <div className="sm:ml-auto flex items-end gap-3">
                        <button
                            onClick={exportSelectedCharts}
                            disabled={isLoading}
                            className="btn-glow text-white font-medium text-sm py-2.5 px-5 rounded-lg cursor-pointer disabled:opacity-50 flex items-center gap-2"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                            Exportar {selectedCharts.size > 0 ? `(${selectedCharts.size})` : 'Todos'}
                        </button>
                    </div>
                </div>

                {/* Chart selection checkboxes */}
                <div className="flex flex-wrap gap-3 mt-4 pt-3 border-t border-white/5">
                    <span className="text-xs text-neutral-500 self-center">Selecionar gráficos:</span>
                    {chartIds.map((id) => (
                        <label key={id} className="flex items-center gap-2 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={selectedCharts.has(id)}
                                onChange={() => toggleChart(id)}
                                className="w-3.5 h-3.5 rounded border border-white/20 bg-white/5 accent-primary-500 cursor-pointer"
                            />
                            <span className="text-xs text-neutral-400 group-hover:text-white transition-colors">
                                {chartLabels[id]}
                            </span>
                        </label>
                    ))}
                </div>
            </div>

            {/* Loading */}
            {isLoading && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="glass-card rounded-2xl p-6 animate-pulse">
                            <div className="h-5 bg-white/10 rounded w-1/3 mb-6" />
                            <div className="h-52 bg-white/5 rounded-lg" />
                        </div>
                    ))}
                </div>
            )}

            {/* Charts */}
            {!isLoading && indicadores && (
                <>
                    <div ref={escalonadoRef} className="glass-card rounded-2xl p-6 mb-6">
                        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3 mb-5">
                            <div>
                                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                                    Escalonado de Faturamento
                                </h3>
                                <p className="text-xs text-neutral-400 mt-1">
                                    Monitoramento da rede | Referencia: {MESES_ESCALONADO[mesAtualCalendario - 1]}
                                </p>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="text-xs text-neutral-400">
                                    Verde {'>='} {escalonadoData.limiarVerde.toFixed(1)}% | Amarelo {'>='} {escalonadoData.limiarAmarelo.toFixed(1)}%
                                </div>
                                <button
                                    onClick={exportEscalonado}
                                    className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-primary-500/35 bg-primary-500/15 text-primary-100 hover:bg-primary-500/25 transition-colors cursor-pointer"
                                >
                                    Exportar Escalonado
                                </button>
                            </div>
                        </div>

                        {escalonadoData.total > 0 ? (
                            <>
                                <div ref={escalonadoCaptureRef} className="rounded-xl">
                                    <div className="overflow-x-auto pb-2">
                                        <div className="min-w-[1120px]">
                                            <div className="flex items-end gap-2">
                                                {escalonadoColunas.map((coluna) => {
                                                    const items = escalonadoData.grupos[coluna.mes] ?? [];
                                                    const degrau = coluna.mes === 0 ? 0 : (coluna.mes - 1) * ESCALONADO_DEGRAU_OFFSET;
                                                    const deslocamentoVertical = ESCALONADO_BASE_OFFSET - degrau;

                                                    return (
                                                        <div key={coluna.mes} className="flex-1 min-w-[78px]">
                                                            <div className="rounded-xl border border-white/10 bg-slate-950/35 p-1 pb-0.5 overflow-hidden" style={{ height: `${escalonadoAltura}px` }}>
                                                                <div
                                                                    className="h-full flex flex-col-reverse gap-1"
                                                                    style={{ transform: `translateY(${deslocamentoVertical}px)` }}
                                                                >
                                                                    {items.map((item) => {
                                                                        const style = ESCALONADO_STATUS_STYLE[item.status];
                                                                        return (
                                                                            <span
                                                                                key={`${coluna.mes}-${item.id_ej}`}
                                                                                className="block h-[30px] text-[10px] font-semibold leading-tight px-1.5 py-1 rounded whitespace-nowrap overflow-hidden text-ellipsis"
                                                                                style={{
                                                                                    backgroundColor: style.bg,
                                                                                    color: style.text,
                                                                                    border: `1px solid ${style.border}`,
                                                                                }}
                                                                                title={item.nome}
                                                                            >
                                                                                {item.nome}
                                                                            </span>
                                                                        );
                                                                    })}
                                                                </div>
                                                            </div>
                                                            <div className="mt-2 h-7 rounded-md bg-primary-500/20 border border-primary-500/30 flex items-center justify-center px-1">
                                                                <span className="text-[10px] font-bold tracking-wide text-primary-100 text-center leading-tight">
                                                                    {coluna.label}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="mt-4 flex flex-wrap gap-2">
                                        {(['cinza', 'vermelho', 'amarelo', 'verde', 'azul'] as EscalonadoStatus[]).map((status) => {
                                            const style = ESCALONADO_STATUS_STYLE[status];
                                            const total = escalonadoData.contadores[status];
                                            return (
                                                <div
                                                    key={status}
                                                    className="px-3 py-1.5 rounded-full border text-xs font-bold"
                                                    style={{
                                                        color: style.countText ?? style.text,
                                                        backgroundColor: style.countBg,
                                                        borderColor: style.border,
                                                    }}
                                                >
                                                    {total} EJ{total !== 1 ? 's' : ''} {style.label}
                                                </div>
                                            );
                                        })}
                                    </div>

                                    {(escalonadoData.houveTruncamento || escalonadoData.semMetaCount > 0) && (
                                        <div className="mt-3 space-y-1 text-xs">
                                            {escalonadoData.houveTruncamento && (
                                                <p className="text-amber-300">
                                                    Exibindo {escalonadoData.total} de {escalonadoData.totalReal} EJs (limite desta versão: 100 por filtro).
                                                </p>
                                            )}
                                            {escalonadoData.semMetaCount > 0 && (
                                                <p className="text-neutral-400">
                                                    {escalonadoData.semMetaCount} EJ{escalonadoData.semMetaCount !== 1 ? 's' : ''} sem meta definida foram posicionadas no início da escada.
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : (
                            <EmptyChart />
                        )}
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* 1. Distribuição por Cluster */}
                        <ChartCard title="Distribuição por Cluster" refProp={clusterRef}>
                            {clusterData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={280}>
                                    <PieChart>
                                        <Pie
                                            data={clusterData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={60}
                                            outerRadius={100}
                                            paddingAngle={3}
                                            dataKey="value"
                                            stroke="none"
                                        >
                                            {clusterData.map((entry, i) => (
                                                <Cell key={i} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1E293B', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', fontSize: '13px' }}
                                            formatter={(value, n) => [`${value} EJs`, n]}
                                        />
                                        <Legend
                                            verticalAlign="bottom"
                                            iconType="circle"
                                            iconSize={8}
                                            formatter={(value: string) => <span style={{ color: '#94A3B8', fontSize: '12px' }}>{value}</span>}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            ) : (
                                <EmptyChart />
                            )}
                        </ChartCard>

                        {/* 2. Ritmo Mínimo e Ritmo Significativo */}
                        <ChartCard title="Ritmo Mínimo e Ritmo Significativo" refProp={ritmoRef}>
                            {ritmoMensal && ritmoMensal.some((d) => d.rm_percent > 0 || d.rs_percent > 0) ? (
                                <ResponsiveContainer width="100%" height={280}>
                                    <BarChart data={ritmoMensal} margin={{ top: 20, right: 10, left: 10, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                        <XAxis
                                            dataKey="label"
                                            tick={{ fill: '#94A3B8', fontSize: 11 }}
                                            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                                        />
                                        <YAxis
                                            tick={{ fill: '#94A3B8', fontSize: 11 }}
                                            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                                            tickFormatter={(v) => `${v.toFixed(0)}%`}
                                        />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1E293B', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', fontSize: '13px' }}
                                            formatter={(value) => [`${Number(value).toFixed(2)}%`]}
                                        />
                                        <Legend
                                            verticalAlign="top"
                                            iconType="square"
                                            iconSize={10}
                                            formatter={(value: string) => <span style={{ color: '#94A3B8', fontSize: '12px' }}>{value}</span>}
                                        />
                                        <Bar dataKey="rm_percent" name="Ritmo Mínimo" fill="#3B82F6" radius={[3, 3, 0, 0]} barSize={16}
                                            label={{ position: 'top', fill: '#3B82F6', fontSize: 9, formatter: (v) => Number(v) > 0 ? `${Number(v).toFixed(2)}%` : '' }}
                                        />
                                        <Bar dataKey="rs_percent" name="Ritmo Significativo" fill="#EF4444" radius={[3, 3, 0, 0]} barSize={16}
                                            label={{ position: 'top', fill: '#EF4444', fontSize: 9, formatter: (v) => Number(v) > 0 ? `${Number(v).toFixed(2)}%` : '' }}
                                        />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <EmptyChart />
                            )}
                        </ChartCard>

                        {/* 3. Faturamento Acumulado */}
                        <ChartCard title="Faturamento Acumulado" refProp={linhaRef} wide>
                            {faturamentoAcumuladoData.length > 0 && faturamentoAcumuladoData.some((d) => d.faturamento_acumulado > 0) ? (
                                <ResponsiveContainer width="100%" height={300}>
                                    <LineChart data={faturamentoAcumuladoData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                        <XAxis dataKey="label" tick={{ fill: '#94A3B8', fontSize: 12 }} axisLine={{ stroke: 'rgba(255,255,255,0.1)' }} />
                                        <YAxis
                                            tick={{ fill: '#94A3B8', fontSize: 12 }}
                                            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                                            tickFormatter={(v) => {
                                                if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
                                                if (v >= 1e3) return `${(v / 1e3).toFixed(0)}k`;
                                                return v.toString();
                                            }}
                                        />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1E293B', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', fontSize: '13px' }}
                                            formatter={(value) => [formatCurrency(value as number), 'Faturamento Acumulado']}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="faturamento_acumulado"
                                            stroke="#0D6EFD"
                                            strokeWidth={2.5}
                                            dot={{ fill: '#0D6EFD', strokeWidth: 0, r: 4 }}
                                            activeDot={{ r: 6, strokeWidth: 0 }}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            ) : (
                                <EmptyChart />
                            )}
                        </ChartCard>

                        {/* 4. Faturamento por Cidade */}
                        <ChartCard title="Faturamento por Cidade (Top 10)" refProp={cidadeRef} wide>
                            {cidadeChartData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={300}>
                                    <BarChart data={cidadeChartData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                                        <XAxis
                                            type="number"
                                            tick={{ fill: '#94A3B8', fontSize: 12 }}
                                            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                                            tickFormatter={(v) => {
                                                if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
                                                if (v >= 1e3) return `${(v / 1e3).toFixed(0)}k`;
                                                return v.toString();
                                            }}
                                        />
                                        <YAxis
                                            type="category"
                                            dataKey="cidade"
                                            width={120}
                                            tick={{ fill: '#CBD5E1', fontSize: 12 }}
                                            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                                        />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1E293B', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', fontSize: '13px' }}
                                            formatter={(value) => [formatCurrency(value as number), 'Faturamento']}
                                        />
                                        <Bar dataKey="faturamento" fill="#0D6EFD" radius={[0, 6, 6, 0]} barSize={20} />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <EmptyChart />
                            )}
                        </ChartCard>
                    </div>

                    {/* ── SDE ── */}
                    <div className="glass-card rounded-2xl p-6">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h3 className="text-sm font-heading font-semibold text-white uppercase tracking-wider">
                                    SDE — Saldo de Desenvolvimento Estratégico
                                </h3>
                                <p className="text-xs text-neutral-500 mt-1">
                                    Compara o índice calculado de cada EJ com seu cluster oficial atual
                                    {sdeCenarios?.total_ejs != null && (
                                        <span className="ml-2 text-neutral-600">· {sdeCenarios.total_ejs} EJs processadas</span>
                                    )}
                                </p>
                            </div>
                        </div>

                        {loadingSde ? (
                            <div className="flex justify-center py-8">
                                <div className="w-8 h-8 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
                            </div>
                        ) : sdeCenarios?.cenarios && sdeCenarios.cenarios.length > 0 ? (
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                                {sdeCenarios.cenarios.map((cenario) => (
                                    <SdeCenarioCard key={cenario.nome} cenario={cenario} />
                                ))}
                            </div>
                        ) : (
                            <EmptyChart />
                        )}
                    </div>
                </>
            )}
        </div>
    );
}

/* ── Sub-components ── */

function KpiCard({ label, value, color }: { label: string; value: string; color?: string }) {
    return (
        <div className="glass-card rounded-xl p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider font-semibold mb-1">{label}</p>
            <p className="text-lg font-bold" style={{ color: color ?? '#fff' }}>{value}</p>
        </div>
    );
}

function ChartCard({
    title,
    children,
    refProp,
    wide,
}: {
    title: string;
    children: React.ReactNode;
    refProp: React.RefObject<HTMLDivElement | null>;
    wide?: boolean;
}) {
    return (
        <div
            ref={refProp}
            className={`glass-card rounded-2xl p-6 ${wide ? 'lg:col-span-1' : ''}`}
        >
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">{title}</h3>
            {children}
        </div>
    );
}

function EmptyChart() {
    return (
        <div className="flex items-center justify-center h-52 text-neutral-600 text-sm">
            Sem dados disponíveis
        </div>
    );
}

function SdeCenarioCard({ cenario }: { cenario: SdeCenario }) {
    const [expanded, setExpanded] = useState(false);

    const sdeColor = cenario.sde == null ? '#64748B'
        : cenario.sde > 0 ? '#16A34A'
        : cenario.sde < 0 ? '#DC2626'
        : '#F59E0B';

    const sdeLabel = cenario.sde == null ? '—'
        : cenario.sde > 0 ? `+${cenario.sde.toFixed(4)}`
        : cenario.sde.toFixed(4);

    return (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] flex flex-col overflow-hidden">
            {/* Header */}
            <div className="p-5 flex flex-col gap-3">
                <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">{cenario.nome}</p>
                    <p className="text-[10px] text-neutral-600 mt-0.5">{cenario.descricao}</p>
                </div>

                <p className="text-3xl font-bold tabular-nums" style={{ color: sdeColor }}>{sdeLabel}</p>

                {/* Contagens */}
                <div className="flex gap-3 text-xs">
                    <span className="flex items-center gap-1 text-green-400 font-semibold">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
                        </svg>
                        {cenario.subindo.length}
                    </span>
                    <span className="flex items-center gap-1 text-neutral-500 font-semibold">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
                        </svg>
                        {cenario.mantendo.length}
                    </span>
                    <span className="flex items-center gap-1 text-red-400 font-semibold">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                        {cenario.descendo.length}
                    </span>
                </div>
            </div>

            {/* Toggle expandir */}
            {(cenario.subindo.length > 0 || cenario.descendo.length > 0 || cenario.mantendo.length > 0) && (
                <>
                    <button
                        onClick={() => setExpanded((v) => !v)}
                        className="w-full flex items-center justify-center gap-1.5 py-2.5 border-t border-white/5 text-[11px] text-neutral-500 hover:text-neutral-300 hover:bg-white/[0.02] transition-colors"
                    >
                        {expanded ? 'Recolher' : `Ver todas as EJs (${cenario.subindo.length + cenario.mantendo.length + cenario.descendo.length})`}
                        <svg
                            className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`}
                            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>

                    {expanded && (
                        <div className="border-t border-white/5 divide-y divide-white/5 max-h-96 overflow-y-auto">
                            <EjMovimentoGroup label="Subindo" ejs={cenario.subindo} color="#16A34A" arrow="up" />
                            <EjMovimentoGroup label="Mantendo" ejs={cenario.mantendo} color="#94A3B8" arrow="right" />
                            <EjMovimentoGroup label="Descendo" ejs={cenario.descendo} color="#DC2626" arrow="down" />
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function EjMovimentoGroup({ label, ejs, color, arrow }: {
    label: string;
    ejs: EjMovimento[];
    color: string;
    arrow: 'up' | 'right' | 'down';
}) {
    if (ejs.length === 0) return null;

    const arrowPath = arrow === 'up'
        ? 'M5 15l7-7 7 7'
        : arrow === 'down'
        ? 'M19 9l-7 7-7-7'
        : 'M5 12h14';

    return (
        <div>
            <p className="px-4 py-2 text-[10px] uppercase tracking-widest font-semibold" style={{ color }}>
                {label} ({ejs.length})
            </p>
            {ejs.map((ej) => (
                <div key={ej.id_ej} className="flex items-center justify-between px-4 py-2 hover:bg-white/[0.02]">
                    <div className="flex items-center gap-2 min-w-0">
                        <svg className="w-3.5 h-3.5 shrink-0" style={{ color }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d={arrowPath} />
                        </svg>
                        <span className="text-xs text-neutral-300 truncate">{ej.nome}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0 ml-2">
                        <span className="text-[10px] text-neutral-600">C{ej.cluster_atual}</span>
                        <svg className="w-3 h-3 text-neutral-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                        </svg>
                        <span className="text-[10px] font-semibold" style={{ color }}>C{ej.cluster_calculado}</span>
                    </div>
                </div>
            ))}
        </div>
    );
}
