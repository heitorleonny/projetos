import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell
} from 'recharts';
import { useEmpresaPerfil } from './useEmpresaPerfil';
import { formatCurrency, formatPercent, getClusterInfo, getRitmoLabel } from '../../utils/formatters';
import type { FaturamentoMensal, MetaVsRealizado } from '../../types/empresa';
import EjLogo from '../../components/EjLogo';

const MONTH_LABELS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

export default function EmpresaPage() {
    const { idEj } = useParams<{ idEj: string }>();
    const [ano, setAno] = useState(2026);

    const { data, isLoading, isError } = useEmpresaPerfil(Number(idEj) || 0, ano);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
                    <p className="text-neutral-400 text-sm">Carregando perfil da EJ…</p>
                </div>
            </div>
        );
    }

    if (isError || !data) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="glass-card rounded-2xl p-10 text-center max-w-md">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-error/10 flex items-center justify-center">
                        <svg className="w-8 h-8 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-heading font-bold text-white mb-2">EJ não encontrada</h2>
                    <p className="text-neutral-400 text-sm mb-6">Não foi possível carregar os dados desta Empresa Júnior.</p>
                    <Link to="/dashboard" className="btn-glow text-white font-medium text-sm py-2.5 px-6 rounded-lg no-underline">
                        Voltar ao Dashboard
                    </Link>
                </div>
            </div>
        );
    }

    const { empresa, indicadores, serie_mensal, metas, projecao_anual, ritmo_necessario, crescimento_mensal, crescimento_anual } = data;
    const cluster = getClusterInfo(indicadores.cluster);
    const ritmo = getRitmoLabel(indicadores.ritmo);
    const percentMeta = indicadores.percentual_meta ?? 0;

    return (
        <div className="space-y-8">
            {/* Back navigation */}
            <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 text-sm text-neutral-400 hover:text-primary-400 transition-colors no-underline group"
            >
                <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
                Voltar ao Dashboard
            </Link>

            {/* ── Header Card ── */}
            <div className="glass-card rounded-2xl p-8">
                <div className="flex flex-col md:flex-row gap-8 items-start">
                    {/* Photo */}
                    <div className="shrink-0">
                        <EjLogo
                            nome={empresa.nome}
                            fotoUrl={empresa.foto_url}
                            sizeClassName="w-28 h-28"
                            className="border-2 border-white/10"
                            initialsClassName="text-3xl text-primary-400"
                        />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-3 mb-3">
                            <h1 className="text-2xl md:text-3xl font-heading font-bold text-white">
                                {empresa.nome}
                            </h1>
                            <span
                                className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide border"
                                style={{
                                    color: cluster.color,
                                    backgroundColor: `${cluster.color}15`,
                                    borderColor: `${cluster.color}30`,
                                }}
                            >
                                {cluster.label}
                            </span>
                            <span
                                className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide border"
                                style={{
                                    color: ritmo.color,
                                    backgroundColor: `${ritmo.color}15`,
                                    borderColor: `${ritmo.color}30`,
                                }}
                            >
                                {ritmo.label}
                            </span>
                        </div>

                        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-neutral-400">
                            {empresa.comunidade && (
                                <span className="flex items-center gap-1.5">
                                    <svg className="w-4 h-4 text-primary-500/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                    </svg>
                                    Comunidade {empresa.comunidade}
                                </span>
                            )}
                            {empresa.universidade && (
                                <span className="flex items-center gap-1.5">
                                    <svg className="w-4 h-4 text-primary-500/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 14l9-5-9-5-9 5 9 5z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                                    </svg>
                                    {empresa.universidade}
                                </span>
                            )}
                            {empresa.cidade && empresa.estado && (
                                <span className="flex items-center gap-1.5">
                                    <svg className="w-4 h-4 text-primary-500/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
                                    </svg>
                                    {empresa.cidade}/{empresa.estado}
                                </span>
                            )}
                            {empresa.cnpj && (
                                <span className="flex items-center gap-1.5 font-mono text-xs text-neutral-500">
                                    CNPJ: {empresa.cnpj}
                                </span>
                            )}
                        </div>

                        {empresa.curso && (
                            <p className="mt-2 text-xs text-neutral-500 leading-relaxed line-clamp-2">
                                <span className="text-neutral-600">Cursos:</span> {empresa.curso}
                            </p>
                        )}
                    </div>

                    {/* Year selector */}
                    <div className="shrink-0">
                        <label className="block text-[10px] text-neutral-500 uppercase tracking-wider mb-1.5 font-semibold">
                            Ano de referência
                        </label>
                        <select
                            value={ano}
                            onChange={(e) => setAno(Number(e.target.value))}
                            className="bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white
                                       focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all
                                       cursor-pointer appearance-none min-w-[100px]"
                            style={{
                                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
                                backgroundRepeat: 'no-repeat',
                                backgroundPosition: 'right 10px center',
                                backgroundSize: '16px',
                            }}
                        >
                            {[2026, 2025, 2024, 2023].map((y) => (
                                <option key={y} value={y} className="bg-neutral-800">{y}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* ── KPI Cards ── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard
                    label="Faturamento"
                    value={formatCurrency(indicadores.faturamento_acumulado)}
                    icon={<path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />}
                />
                <KpiCard
                    label="Projetos"
                    value={String(indicadores.projetos_totais)}
                    icon={<path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />}
                />
                <KpiCard
                    label="CSAT Médio"
                    value={indicadores.csat_medio != null ? indicadores.csat_medio.toFixed(2) : '—'}
                    icon={<path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />}
                />
                <KpiCard
                    label="Meta Atingida"
                    value={formatPercent(indicadores.percentual_meta)}
                    icon={<path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />}
                    accent={percentMeta >= 80 ? '#16A34A' : percentMeta >= 50 ? '#F59E0B' : '#DC2626'}
                />
            </div>

            {/* ── Progress Bar (Meta) ── */}
            <div className="glass-card rounded-2xl p-6">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-heading font-semibold text-white uppercase tracking-wider">Progresso da Meta de Faturamento</h3>
                    <span className="text-xs font-bold text-white">{formatPercent(indicadores.percentual_meta)}</span>
                </div>
                <div className="w-full bg-white/5 rounded-full h-3 overflow-hidden">
                    <div
                        className="h-full rounded-full transition-all duration-1000 relative"
                        style={{
                            width: `${Math.min(percentMeta, 100)}%`,
                            background: percentMeta >= 80
                                ? 'linear-gradient(90deg, #16A34A, #22D3EE)'
                                : percentMeta >= 50
                                    ? 'linear-gradient(90deg, #F59E0B, #FBBF24)'
                                    : 'linear-gradient(90deg, #DC2626, #F87171)',
                            boxShadow: `0 0 12px ${percentMeta >= 80 ? '#16A34A' : percentMeta >= 50 ? '#F59E0B' : '#DC2626'}60`,
                        }}
                    />
                </div>
                {metas?.meta_faturamento != null && (
                    <div className="flex items-center justify-between mt-2 text-xs text-neutral-500">
                        <span>Realizado: {formatCurrency(metas.faturamento_acumulado)}</span>
                        <span>Meta: {formatCurrency(metas.meta_faturamento)}</span>
                    </div>
                )}
            </div>

            {/* ── Série Mensal (mini chart) ── */}
            {serie_mensal.length > 0 && (
                <div className="glass-card rounded-2xl p-6">
                    <h3 className="text-sm font-heading font-semibold text-white uppercase tracking-wider mb-5">
                        Faturamento Mensal — {ano}
                    </h3>
                    <FaturamentoChart data={serie_mensal} />
                </div>
            )}

            {/* ── Metas vs Realizado + Projeção ── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Metas */}
                {metas && (
                    <div className="glass-card rounded-2xl p-6">
                        <h3 className="text-sm font-heading font-semibold text-white uppercase tracking-wider mb-5">
                            Metas vs Realizado
                        </h3>
                        <MetaTable metas={metas} />
                    </div>
                )}

                {/* Projeção & Crescimento */}
                <div className="glass-card rounded-2xl p-6">
                    <h3 className="text-sm font-heading font-semibold text-white uppercase tracking-wider mb-5">
                        Projeção & Crescimento
                    </h3>
                    <div className="space-y-4">
                        <ProjecaoItem
                            label="Projeção Anual"
                            value={projecao_anual != null ? formatCurrency(projecao_anual) : '—'}
                        />
                        <ProjecaoItem
                            label="Ritmo Necessário (mensal)"
                            value={ritmo_necessario != null ? formatCurrency(ritmo_necessario) : '—'}
                        />
                        <ProjecaoItem
                            label="Crescimento Mensal"
                            value={crescimento_mensal != null ? `${crescimento_mensal.toFixed(1)}%` : '—'}
                            accent={crescimento_mensal != null ? (crescimento_mensal >= 0 ? '#16A34A' : '#DC2626') : undefined}
                        />
                        <ProjecaoItem
                            label="Crescimento Anual"
                            value={crescimento_anual != null ? `${crescimento_anual.toFixed(1)}%` : '—'}
                            accent={crescimento_anual != null ? (crescimento_anual >= 0 ? '#16A34A' : '#DC2626') : undefined}
                        />
                    </div>
                </div>
            </div>

            {/* ── Info Cadastral ── */}
            <div className="glass-card rounded-2xl p-6">
                <h3 className="text-sm font-heading font-semibold text-white uppercase tracking-wider mb-5">
                    Informações Cadastrais
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    <InfoItem label="Status" value={empresa.status} />
                    <InfoItem label="Federação" value={empresa.federacao} />
                    <InfoItem label="Ano de Federação" value={empresa.ano_federacao?.toString()} />
                    <InfoItem label="Universidade" value={empresa.universidade} />
                    <InfoItem label="Cidade/UF" value={empresa.cidade && empresa.estado ? `${empresa.cidade}/${empresa.estado}` : null} />
                    <InfoItem label="CNPJ" value={empresa.cnpj} mono />
                    <InfoItem label="Taxa de Colaboração" value={indicadores.taxa_colaboracao != null ? `${indicadores.taxa_colaboracao.toFixed(1)}%` : null} />
                </div>
            </div>
        </div>
    );
}

/* ── Sub-components ── */

function KpiCard({ label, value, icon, accent }: {
    label: string;
    value: string;
    icon: React.ReactNode;
    accent?: string;
}) {
    return (
        <div className="glass-card rounded-xl p-5 flex items-start gap-4">
            <div
                className="p-2.5 rounded-lg shrink-0"
                style={{ backgroundColor: `${accent ?? '#3B82F6'}15` }}
            >
                <svg className="w-5 h-5" style={{ color: accent ?? '#3B82F6' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    {icon}
                </svg>
            </div>
            <div className="min-w-0">
                <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 font-semibold">{label}</p>
                <p className="text-lg font-bold text-white truncate" style={accent ? { color: accent } : undefined}>{value}</p>
            </div>
        </div>
    );
}

function FaturamentoChart({ data }: { data: FaturamentoMensal[] }) {
    const chartData = data.map((d) => ({
        ...d,
        nome: MONTH_LABELS[d.mes - 1],
    }));

    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                    <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#3B82F6" stopOpacity={1} />
                        <stop offset="100%" stopColor="#0D6EFD" stopOpacity={0.7} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                    dataKey="nome"
                    tick={{ fill: '#64748B', fontSize: 11 }}
                    axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                    tickLine={false}
                />
                <YAxis
                    tick={{ fill: '#64748B', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: number) =>
                        v >= 1000 ? `R$${(v / 1000).toFixed(0)}k` : `R$${v}`
                    }
                    width={65}
                />
                <Tooltip
                    content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0].payload as FaturamentoMensal & { nome: string };
                        return (
                            <div className="bg-neutral-900/95 border border-white/10 rounded-xl px-4 py-3 shadow-xl backdrop-blur-sm">
                                <p className="text-xs font-semibold text-white mb-1.5">{d.nome}</p>
                                <p className="text-sm text-primary-300 font-bold">{formatCurrency(d.faturamento)}</p>
                                {d.faturamento_colab > 0 && (
                                    <p className="text-xs text-neutral-400 mt-1">Colab: {formatCurrency(d.faturamento_colab)}</p>
                                )}
                                {d.projetos_vendidos > 0 && (
                                    <p className="text-xs text-neutral-400">{d.projetos_vendidos} projeto{d.projetos_vendidos > 1 ? 's' : ''}</p>
                                )}
                                {d.csat != null && d.csat > 0 && (
                                    <p className="text-xs text-neutral-400">CSAT: {d.csat.toFixed(1)}</p>
                                )}
                            </div>
                        );
                    }}
                    cursor={{ fill: 'rgba(59,130,246,0.08)' }}
                />
                <Bar dataKey="faturamento" radius={[6, 6, 0, 0]} maxBarSize={48}>
                    {chartData.map((d, i) => (
                        <Cell
                            key={i}
                            fill={d.faturamento > 0 ? 'url(#barGradient)' : 'rgba(255,255,255,0.04)'}
                            style={d.faturamento > 0 ? { filter: 'drop-shadow(0 0 6px rgba(59,130,246,0.3))' } : undefined}
                        />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}

function MetaTable({ metas }: { metas: MetaVsRealizado }) {
    const rows = [
        { label: 'Faturamento', meta: metas.meta_faturamento != null ? formatCurrency(metas.meta_faturamento) : '—', real: formatCurrency(metas.faturamento_acumulado), pct: metas.percentual_meta },
        { label: 'CSAT', meta: metas.meta_csat?.toFixed(1) ?? '—', real: metas.csat_medio?.toFixed(2) ?? '—', pct: null },
        { label: 'Taxa Colaboração', meta: metas.meta_taxa_colaboracao != null ? `${metas.meta_taxa_colaboracao}%` : '—', real: metas.taxa_colaboracao != null ? `${metas.taxa_colaboracao.toFixed(1)}%` : '—', pct: null },
        { label: 'Engajamento MEJ', meta: metas.meta_engajamento_mej != null ? `${metas.meta_engajamento_mej}%` : '—', real: '—', pct: null },
    ];

    return (
        <div className="space-y-3">
            {/* Header */}
            <div className="grid grid-cols-4 gap-2 text-[10px] uppercase tracking-wider text-neutral-500 font-semibold pb-2 border-b border-white/5">
                <span>Indicador</span>
                <span className="text-right">Meta</span>
                <span className="text-right">Realizado</span>
                <span className="text-right">%</span>
            </div>
            {rows.map((r) => (
                <div key={r.label} className="grid grid-cols-4 gap-2 text-sm">
                    <span className="text-neutral-400">{r.label}</span>
                    <span className="text-right text-neutral-500">{r.meta}</span>
                    <span className="text-right text-white font-medium">{r.real}</span>
                    <span className="text-right font-bold" style={{
                        color: r.pct != null
                            ? r.pct >= 80 ? '#16A34A' : r.pct >= 50 ? '#F59E0B' : '#DC2626'
                            : '#64748B'
                    }}>
                        {r.pct != null ? `${r.pct.toFixed(1)}%` : '—'}
                    </span>
                </div>
            ))}
        </div>
    );
}

function ProjecaoItem({ label, value, accent }: { label: string; value: string; accent?: string }) {
    return (
        <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
            <span className="text-sm text-neutral-400">{label}</span>
            <span className="text-sm font-bold" style={{ color: accent ?? '#FFFFFF' }}>{value}</span>
        </div>
    );
}

function InfoItem({ label, value, mono }: { label: string; value: string | null | undefined; mono?: boolean }) {
    return (
        <div className="bg-white/[0.03] rounded-lg p-3">
            <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1 font-semibold">{label}</p>
            <p className={`text-sm text-white ${mono ? 'font-mono' : 'font-medium'}`}>
                {value ?? '—'}
            </p>
        </div>
    );
}
