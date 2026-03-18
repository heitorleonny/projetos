import { useState, useMemo } from 'react';
import { useComparacao } from './useComparacao';
import type { EmpresaComIndicadores } from '../../types/empresa';
import { formatCurrency, getClusterInfo } from '../../utils/formatters';

const ANOS_DISPONIVEIS = [2023, 2024, 2025, 2026];
const MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

type Indicador = 'faturamento' | 'faturamento_mes' | 'taxa_colab' | 'cluster' | 'percentual_meta' | 'projetos';

const INDICADORES: { key: Indicador; label: string; icon: string }[] = [
    { key: 'faturamento', label: 'Faturamento', icon: '💰' },
    { key: 'faturamento_mes', label: 'Fat. Mês', icon: '📅' },
    { key: 'taxa_colab', label: 'Taxa Colab', icon: '🤝' },
    { key: 'cluster', label: 'Cluster', icon: '🏷️' },
    { key: 'percentual_meta', label: '% Meta', icon: '🎯' },
    { key: 'projetos', label: 'Projetos', icon: '📊' },
];

const selectClass =
    'w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all cursor-pointer appearance-none';
const selectStyle = {
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 10px center',
    backgroundSize: '16px',
};

interface EjRow {
    id_ej: number;
    nome: string;
    comunidade: string | null;
    foto_url: string | null;
    porAno: Record<number, EmpresaComIndicadores | undefined>;
}

export default function ComparacaoPage() {
    const [anosSelecionados, setAnosSelecionados] = useState<number[]>([2024, 2026]);
    const [mesSelecionado, setMesSelecionado] = useState<number | undefined>(undefined);
    const [indicador, setIndicador] = useState<Indicador>('faturamento');
    const [busca, setBusca] = useState('');

    const { data, isLoading, isError, error } = useComparacao(anosSelecionados, mesSelecionado);

    const toggleAno = (ano: number) => {
        setAnosSelecionados((prev) => {
            if (prev.includes(ano)) {
                if (prev.length <= 1) return prev;
                return prev.filter((a) => a !== ano);
            }
            return [...prev, ano].sort();
        });
    };

    const rows = useMemo<EjRow[]>(() => {
        if (!data) return [];

        const map = new Map<number, EjRow>();

        for (const { ano, empresas } of data) {
            for (const ej of empresas) {
                if (!map.has(ej.id_ej)) {
                    map.set(ej.id_ej, {
                        id_ej: ej.id_ej,
                        nome: ej.nome,
                        comunidade: ej.comunidade,
                        foto_url: ej.foto_url,
                        porAno: {},
                    });
                }
                const row = map.get(ej.id_ej)!;
                row.porAno[ano] = ej;
                if (ano === Math.max(...anosSelecionados)) {
                    row.nome = ej.nome;
                    row.comunidade = ej.comunidade;
                    row.foto_url = ej.foto_url;
                }
            }
        }

        let result = Array.from(map.values());

        if (busca.trim()) {
            const term = busca.trim().toLowerCase();
            result = result.filter(
                (r) =>
                    r.nome.toLowerCase().includes(term) ||
                    (r.comunidade ?? '').toLowerCase().includes(term),
            );
        }

        return result.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
    }, [data, anosSelecionados, busca]);

    const formatTaxaColab = (value: number | null | undefined): string => {
        if (value == null) return '—';
        return `${(value * 100).toFixed(1)}%`;
    };

    const getValor = (ej: EmpresaComIndicadores | undefined): number | null => {
        if (!ej) return null;
        switch (indicador) {
            case 'faturamento': return ej.faturamento_acumulado;
            case 'faturamento_mes': return ej.faturamento_mes;
            case 'taxa_colab': return ej.taxa_colaboracao;
            case 'cluster': return ej.cluster;
            case 'percentual_meta': return ej.percentual_meta;
            case 'projetos': return ej.projetos_totais;
        }
    };

    const formatValor = (value: number | null): string => {
        if (value == null) return '—';
        switch (indicador) {
            case 'faturamento':
            case 'faturamento_mes':
                return formatCurrency(value);
            case 'taxa_colab':
                return formatTaxaColab(value);
            case 'percentual_meta':
                return `${value.toFixed(1)}%`;
            case 'cluster':
            case 'projetos':
                return value.toString();
        }
    };

    // Summary per year
    const summaryPerAno = useMemo(() => {
        if (!data) return {};
        const result: Record<number, { total: number; fatTotal: number; projTotal: number; mediaPercMeta: number }> = {};
        for (const { ano, empresas } of data) {
            const metaVals = empresas.map((e) => e.percentual_meta).filter((v): v is number => v != null);
            result[ano] = {
                total: empresas.length,
                fatTotal: empresas.reduce((s, e) => s + e.faturamento_acumulado, 0),
                projTotal: empresas.reduce((s, e) => s + e.projetos_totais, 0),
                mediaPercMeta: metaVals.length > 0 ? metaVals.reduce((a, b) => a + b, 0) / metaVals.length : 0,
            };
        }
        return result;
    }, [data]);

    // Find max value across all rows for bar visualization
    const maxValor = useMemo(() => {
        let max = 0;
        for (const row of rows) {
            for (const ano of anosSelecionados) {
                const val = getValor(row.porAno[ano]);
                if (val != null && val > max) max = val;
            }
        }
        return max || 1;
    }, [rows, anosSelecionados, indicador]);

    const anoColors: Record<number, string> = {
        2023: '#8B5CF6',
        2024: '#F59E0B',
        2025: '#0D6EFD',
        2026: '#16A34A',
    };

    return (
        <div>
            {/* Page Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-1 h-8 rounded-full bg-gradient-to-b from-primary-400 to-primary-600" />
                    <h1 className="font-heading text-3xl font-bold text-gradient">
                        Comparação por Ano
                    </h1>
                </div>
                <p className="text-neutral-400 ml-5 text-sm italic">
                    Compare os indicadores das EJs ao longo dos anos.
                </p>
            </div>

            {/* Summary cards per year — richer design */}
            {data && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    {anosSelecionados.map((ano) => {
                        const s = summaryPerAno[ano];
                        const color = anoColors[ano] ?? '#0D6EFD';
                        return (
                            <div
                                key={ano}
                                className="glass-card rounded-2xl p-5 relative overflow-hidden group"
                            >
                                {/* Accent bar */}
                                <div
                                    className="absolute top-0 left-0 w-full h-1 rounded-t-2xl"
                                    style={{ background: `linear-gradient(90deg, ${color}, ${color}40)` }}
                                />
                                <div className="flex items-center justify-between mb-3">
                                    <span
                                        className="text-2xl font-bold font-heading"
                                        style={{ color }}
                                    >
                                        {ano}
                                    </span>
                                    <span className="text-[11px] text-neutral-500 bg-white/5 px-2 py-0.5 rounded-full">
                                        {s?.total ?? 0} EJs
                                    </span>
                                </div>
                                <p className="text-lg font-bold text-white mb-1">{formatCurrency(s?.fatTotal ?? 0)}</p>
                                <div className="flex items-center gap-3 text-[11px] text-neutral-500">
                                    <span>{s?.projTotal ?? 0} projetos</span>
                                    <span className="w-px h-3 bg-white/10" />
                                    <span>{s?.mediaPercMeta?.toFixed(0) ?? 0}% meta média</span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Filters */}
            <div className="glass-card rounded-2xl p-5 mb-8">
                <div className="flex flex-col gap-5">
                    {/* Row 1: Years + Indicator selector */}
                    <div className="flex flex-col sm:flex-row sm:items-end gap-5">
                        {/* Year toggle chips */}
                        <div className="flex-1">
                            <label className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2.5 block">
                                Selecionar Anos
                            </label>
                            <div className="flex flex-wrap gap-2">
                                {ANOS_DISPONIVEIS.map((ano) => {
                                    const active = anosSelecionados.includes(ano);
                                    const color = anoColors[ano] ?? '#0D6EFD';
                                    return (
                                        <button
                                            key={ano}
                                            onClick={() => toggleAno(ano)}
                                            className={`relative px-5 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer border
                                                ${active
                                                    ? 'text-white border-transparent shadow-lg'
                                                    : 'bg-white/5 text-neutral-500 border-white/10 hover:bg-white/10 hover:text-neutral-300'
                                                }`}
                                            style={active ? {
                                                backgroundColor: `${color}20`,
                                                borderColor: `${color}50`,
                                                color,
                                                boxShadow: `0 0 20px ${color}15`,
                                            } : undefined}
                                        >
                                            {active && (
                                                <span
                                                    className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-neutral-900"
                                                    style={{ backgroundColor: color }}
                                                />
                                            )}
                                            {ano}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Month dropdown */}
                        <div className="sm:w-44">
                            <label className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2.5 block">
                                Mês
                            </label>
                            <select
                                value={mesSelecionado ?? ''}
                                onChange={(e) =>
                                    setMesSelecionado(e.target.value ? Number(e.target.value) : undefined)
                                }
                                className={selectClass}
                                style={selectStyle}
                            >
                                <option value="" className="bg-neutral-800">
                                    Acumulado (todos)
                                </option>
                                {MESES.map((label, i) => (
                                    <option key={i + 1} value={i + 1} className="bg-neutral-800">
                                        {label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Row 2: Indicator pills */}
                    <div>
                        <label className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2.5 block">
                            Indicador
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {INDICADORES.map((ind) => {
                                const active = indicador === ind.key;
                                return (
                                    <button
                                        key={ind.key}
                                        onClick={() => setIndicador(ind.key)}
                                        className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer border
                                            ${active
                                                ? 'bg-primary-500/15 text-primary-300 border-primary-500/30 shadow-sm'
                                                : 'bg-white/[0.03] text-neutral-500 border-white/5 hover:bg-white/[0.06] hover:text-neutral-300'
                                            }`}
                                    >
                                        <span className="text-xs">{ind.icon}</span>
                                        {ind.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Row 3: Search */}
                    <div className="relative">
                        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Buscar EJ por nome ou comunidade..."
                            value={busca}
                            onChange={(e) => setBusca(e.target.value)}
                            className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-neutral-500
                                       focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                        />
                    </div>
                </div>
            </div>

            {/* Loading */}
            {isLoading && (
                <div className="space-y-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="glass-card rounded-2xl p-5 animate-pulse">
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 bg-white/10 rounded-full shrink-0" />
                                <div className="flex-1">
                                    <div className="h-4 bg-white/10 rounded w-1/3 mb-2" />
                                    <div className="h-3 bg-white/5 rounded w-1/5" />
                                </div>
                                <div className="flex gap-3">
                                    {anosSelecionados.map((ano) => (
                                        <div key={ano} className="h-6 bg-white/5 rounded w-20" />
                                    ))}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Error */}
            {isError && (
                <div className="text-center py-16 glass-card rounded-2xl">
                    <div className="text-4xl mb-3">⚠️</div>
                    <h3 className="font-heading font-semibold text-lg text-white mb-1">
                        Erro ao carregar dados
                    </h3>
                    <p className="text-neutral-500 text-sm">
                        {(error as Error)?.message ?? 'Tente novamente mais tarde.'}
                    </p>
                </div>
            )}

            {/* Comparison — Card-based list */}
            {data && rows.length > 0 && (
                <div>
                    {/* Legend */}
                    <div className="flex items-center gap-4 mb-4 px-1">
                        {anosSelecionados.map((ano) => (
                            <div key={ano} className="flex items-center gap-1.5">
                                <span
                                    className="w-3 h-3 rounded-sm"
                                    style={{ backgroundColor: anoColors[ano] ?? '#0D6EFD' }}
                                />
                                <span className="text-xs font-semibold text-neutral-400">{ano}</span>
                            </div>
                        ))}
                        <span className="ml-auto text-xs text-neutral-600">
                            {rows.length} EJ{rows.length !== 1 ? 's' : ''}
                            {mesSelecionado ? ` · ${MESES[mesSelecionado - 1]}` : ' · Acumulado'}
                        </span>
                    </div>

                    <div className="space-y-3">
                        {rows.map((row) => {
                            const valores = anosSelecionados.map((ano) => getValor(row.porAno[ano]));

                            let variacao: number | null = null;
                            if (anosSelecionados.length >= 2) {
                                const primeiro = valores[0];
                                const ultimo = valores[valores.length - 1];
                                if (primeiro != null && ultimo != null && primeiro !== 0) {
                                    variacao = ((ultimo - primeiro) / Math.abs(primeiro)) * 100;
                                }
                            }

                            return (
                                <div
                                    key={row.id_ej}
                                    className="glass-card rounded-2xl p-4 sm:p-5 transition-all hover:bg-white/[0.03] group"
                                >
                                    {/* Top: EJ info + variation badge */}
                                    <div className="flex items-center gap-3 mb-4">
                                        {/* Avatar */}
                                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500/30 to-primary-700/30 flex items-center justify-center shrink-0 border border-white/10 overflow-hidden">
                                            {row.foto_url ? (
                                                <img src={row.foto_url} alt={row.nome} className="w-full h-full object-cover" />
                                            ) : (
                                                <span className="text-sm font-bold text-primary-300">
                                                    {row.nome.charAt(0).toUpperCase()}
                                                </span>
                                            )}
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <h3 className="font-semibold text-sm text-white truncate group-hover:text-primary-300 transition-colors">
                                                {row.nome}
                                            </h3>
                                            <p className="text-[11px] text-neutral-500 truncate">
                                                {row.comunidade ?? '—'}
                                            </p>
                                        </div>
                                        {/* Variation badge */}
                                        {variacao != null && (
                                            <span
                                                className="shrink-0 inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-lg"
                                                style={{
                                                    color: variacao > 0 ? '#16A34A' : variacao < 0 ? '#DC2626' : '#94A3B8',
                                                    backgroundColor: variacao > 0 ? '#16A34A12' : variacao < 0 ? '#DC262612' : '#94A3B812',
                                                    border: `1px solid ${variacao > 0 ? '#16A34A25' : variacao < 0 ? '#DC262625' : '#94A3B825'}`,
                                                }}
                                            >
                                                {variacao > 0 ? '▲' : variacao < 0 ? '▼' : '—'}
                                                {Math.abs(variacao).toFixed(1)}%
                                            </span>
                                        )}
                                    </div>

                                    {/* Year bars */}
                                    <div className="space-y-2">
                                        {anosSelecionados.map((ano, idx) => {
                                            const val = valores[idx];
                                            const color = anoColors[ano] ?? '#0D6EFD';
                                            const barWidth = val != null && indicador !== 'cluster'
                                                ? Math.max((Math.abs(val) / maxValor) * 100, 2)
                                                : 0;

                                            return (
                                                <div key={ano} className="flex items-center gap-3">
                                                    <span className="text-[11px] font-bold w-10 text-right shrink-0" style={{ color }}>
                                                        {ano}
                                                    </span>
                                                    {indicador === 'cluster' && val != null ? (
                                                        <div className="flex-1 flex items-center">
                                                            <ClusterBadge cluster={val} />
                                                        </div>
                                                    ) : (
                                                        <div className="flex-1 flex items-center gap-3">
                                                            <div className="flex-1 h-6 bg-white/[0.04] rounded-lg overflow-hidden relative">
                                                                <div
                                                                    className="h-full rounded-lg transition-all duration-500 ease-out"
                                                                    style={{
                                                                        width: `${barWidth}%`,
                                                                        background: `linear-gradient(90deg, ${color}90, ${color}50)`,
                                                                    }}
                                                                />
                                                            </div>
                                                            <span className="text-sm font-semibold text-white tabular-nums w-24 text-right shrink-0">
                                                                {formatValor(val)}
                                                            </span>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Empty */}
            {data && rows.length === 0 && (
                <div className="text-center py-16 glass-card rounded-2xl">
                    <div className="text-neutral-600 text-5xl mb-4">
                        <svg className="w-16 h-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={0.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                        </svg>
                    </div>
                    <h3 className="font-heading font-semibold text-lg text-white mb-1">
                        Nenhuma EJ encontrada
                    </h3>
                    <p className="text-neutral-500 text-sm">
                        {busca ? 'Nenhuma EJ corresponde à busca.' : 'Nenhum dado disponível para os anos selecionados.'}
                    </p>
                </div>
            )}
        </div>
    );
}

/* ── Sub-components ── */

function ClusterBadge({ cluster }: { cluster: number }) {
    const info = getClusterInfo(cluster);
    return (
        <span
            className="inline-block px-3 py-1 rounded-lg text-[11px] font-bold border"
            style={{
                color: info.color,
                backgroundColor: `${info.color}15`,
                borderColor: `${info.color}30`,
            }}
        >
            {info.label}
        </span>
    );
}
