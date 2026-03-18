import { useState, useRef, useCallback } from 'react';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    LineChart, Line,
} from 'recharts';
import { useIndicadoresRede, useFaturamentoMensal, useEmpresasPorCidade, useRitmoMensal } from './useIndicadores';
import { formatCurrency, getClusterInfo } from '../../utils/formatters';

const COMUNIDADES = ['CAPIBA', 'PRAIEIRA', 'TROPICANA', 'INCUBADORA DE APAIXONADOS', 'MANDACARU'];
const CLUSTERS = [1, 2, 3, 4, 5];

const selectClass =
    'bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all cursor-pointer appearance-none';
const selectStyle = {
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 10px center',
    backgroundSize: '16px',
};

export default function IndicadoresPage() {
    const [ano, setAno] = useState(2026);
    const [cluster, setCluster] = useState<number | undefined>();
    const [comunidade, setComunidade] = useState<string | undefined>();
    const [selectedCharts, setSelectedCharts] = useState<Set<string>>(new Set());

    const clusterRef = useRef<HTMLDivElement>(null);
    const ritmoRef = useRef<HTMLDivElement>(null);
    const linhaRef = useRef<HTMLDivElement>(null);
    const cidadeRef = useRef<HTMLDivElement>(null);

    const params = { ano, cluster, comunidade };

    const { data: indicadores, isLoading: loadingInd } = useIndicadoresRede(params);
    const { data: faturamentoMensal, isLoading: loadingFat } = useFaturamentoMensal(params);
    const { data: cidadeData, isLoading: loadingCid } = useEmpresasPorCidade(ano, cluster, comunidade);
    const { data: ritmoMensal, isLoading: loadingRitmo } = useRitmoMensal(params);

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

    const cidadeChartData = (cidadeData ?? []).slice(0, 10);

    const faturamentoAcumuladoData = (faturamentoMensal ?? []).map((item) => ({
        mes: item.mes,
        label: item.label,
        faturamento_acumulado: item.faturamento,
    }));

    // ── Export ──

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
            cluster: clusterRef,
            ritmo: ritmoRef,
            linha: linhaRef,
            cidade: cidadeRef,
        };

        const charts = selectedCharts.size > 0 ? selectedCharts : new Set(['cluster', 'ritmo', 'linha', 'cidade']);

        for (const chartId of charts) {
            const ref = refs[chartId];
            if (!ref?.current) continue;

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

                    const link = document.createElement('a');
                    link.download = `grafico-${chartId}-${ano}.png`;
                    link.href = canvas.toDataURL('image/png');
                    link.click();

                    URL.revokeObjectURL(url);
                    resolve();
                };
                img.src = url;
            });
        }
    }, [selectedCharts, ano]);

    const isLoading = loadingInd || loadingFat || loadingCid || loadingRitmo;

    const chartIds = ['cluster', 'ritmo', 'linha', 'cidade'];
    const chartLabels: Record<string, string> = {
        cluster: 'Distribuição por Cluster',
        ritmo: 'Ritmo Mínimo e Ritmo Significativo',
        linha: 'Faturamento Acumulado',
        cidade: 'Faturamento por Cidade',
    };

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

            {/* Charts grid */}
            {!isLoading && indicadores && (
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
