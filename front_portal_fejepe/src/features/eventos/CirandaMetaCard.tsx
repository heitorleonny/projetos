import type { EventoMetaResultado } from '../../types/evento';
import { formatCurrency, formatPercent, getClusterInfo } from '../../utils/formatters';

interface CirandaMetaCardProps {
    meta: EventoMetaResultado;
    expanded: boolean;
    onToggle: () => void;
}

const CIRANDA_THEME: Record<EventoMetaResultado['tipo'], { accent: string; bg: string; label: string }> = {
    faturamento_zero: { accent: '#F43F5E', bg: 'rgba(244,63,94,0.08)', label: 'Faturamento' },
    colab_zero:       { accent: '#F5C500', bg: 'rgba(245,197,0,0.08)',  label: 'Colab' },
    verde_mes:        { accent: '#10B981', bg: 'rgba(16,185,129,0.08)', label: 'Verde de Maio' },
    cluster_tracking: { accent: '#8B5CF6', bg: 'rgba(139,92,246,0.08)', label: 'Cluster' },
};

function formatCount(n: number) {
    return new Intl.NumberFormat('pt-BR').format(n);
}

export default function CirandaMetaCard({ meta, expanded, onToggle }: CirandaMetaCardProps) {
    const theme = CIRANDA_THEME[meta.tipo] ?? { accent: '#6B7280', bg: 'rgba(107,114,128,0.08)', label: meta.tipo };
    const progress = meta.meta_contagem > 0
        ? Math.min(100, (meta.resultado_contagem / meta.meta_contagem) * 100)
        : 0;
    const metaBatida = meta.gap_contagem === 0;

    return (
        <div
            className="rounded-2xl overflow-hidden flex flex-col"
            style={{ background: 'rgba(10,0,5,0.7)', border: `1px solid ${theme.accent}30` }}
        >
            {/* Header */}
            <div className="px-5 pt-5 pb-4" style={{ borderBottom: `1px solid ${theme.accent}20`, background: theme.bg }}>
                <div className="flex items-center gap-2 mb-2">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: theme.accent }} />
                    <span className="text-[10px] uppercase tracking-[0.25em] font-bold" style={{ color: theme.accent }}>
                        {theme.label}
                    </span>
                </div>
                <p className="text-sm font-semibold text-white leading-snug">{meta.titulo}</p>
                <p className="text-xs text-neutral-400 mt-0.5 leading-relaxed">{meta.descricao}</p>
            </div>

            {/* Hero metric */}
            <div className="px-5 py-5 flex-1">
                <div className="flex items-end gap-1.5 mb-1">
                    <span className="text-4xl font-black text-white leading-none tabular-nums">
                        {formatPercent(meta.resultado_percentual)}
                    </span>
                    <span className="text-lg font-semibold mb-0.5 leading-none" style={{ color: theme.accent }}>
                        / {formatPercent(meta.meta_percentual)}
                    </span>
                </div>
                <p className="text-xs text-neutral-500">
                    {formatCount(meta.resultado_contagem)} de {formatCount(meta.meta_contagem)} EJs
                </p>

                {/* Progress bar */}
                <div className="mt-4 h-1.5 rounded-full bg-white/5">
                    <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${progress}%`, backgroundColor: theme.accent }}
                    />
                </div>

                {/* Gap */}
                <p className="mt-2 text-xs" style={{ color: metaBatida ? '#10B981' : '#6b7280' }}>
                    {metaBatida
                        ? '✓ Meta atingida'
                        : `Faltam ${formatCount(meta.gap_contagem)} EJs (${formatPercent(meta.gap_percentual)})`}
                </p>
            </div>

            {/* Toggle */}
            <div className="px-5 pb-5">
                <button
                    type="button"
                    onClick={onToggle}
                    className="w-full px-4 py-2.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer"
                    style={{
                        borderColor: `${theme.accent}30`,
                        background: `${theme.accent}10`,
                        color: theme.accent,
                    }}
                >
                    {expanded ? 'Ocultar EJs' : `Ver ${formatCount(meta.resultado_contagem)} EJs contabilizadas`}
                </button>

                {expanded && (
                    <div className="mt-3 space-y-2 max-h-72 overflow-auto pr-1">
                        {meta.participantes.length > 0 ? (
                            meta.participantes.map((p) => {
                                const clusterInfo = getClusterInfo(p.cluster);
                                return (
                                    <div
                                        key={p.id_ej}
                                        className="rounded-xl px-3 py-2.5 flex items-center justify-between gap-3"
                                        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
                                    >
                                        <div className="min-w-0">
                                            <p className="text-sm font-medium text-white truncate">{p.nome}</p>
                                            <p className="text-xs text-neutral-400">
                                                {p.comunidade ?? '—'}
                                                {meta.tipo === 'faturamento_zero' && ` • ${formatCurrency(p.faturamento_acumulado)}`}
                                                {meta.tipo === 'colab_zero' && ` • ${formatCurrency(p.faturamento_colab_acumulado)}`}
                                                {meta.tipo === 'verde_mes' && p.percentual_meta != null && ` • ${formatPercent(p.percentual_meta)} da meta`}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-1.5 shrink-0">
                                            {meta.tipo === 'cluster_tracking' && p.tendencia_cluster && (
                                                <span
                                                    className="text-[10px] px-2 py-0.5 rounded-full border"
                                                    style={p.tendencia_cluster === 'sobe'
                                                        ? { background: 'rgba(139,92,246,0.15)', color: '#c4b5fd', borderColor: 'rgba(139,92,246,0.3)' }
                                                        : { background: 'rgba(255,255,255,0.06)', color: '#9ca3af', borderColor: 'rgba(255,255,255,0.1)' }}
                                                >
                                                    {p.tendencia_cluster === 'sobe' ? '↑ sobe' : '→ mantém'}
                                                </span>
                                            )}
                                            <span
                                                className="text-[10px] px-2 py-0.5 rounded-full border"
                                                style={{ backgroundColor: `${clusterInfo.color}15`, borderColor: `${clusterInfo.color}30`, color: clusterInfo.color }}
                                            >
                                                {clusterInfo.label}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })
                        ) : (
                            <div className="rounded-xl border border-dashed border-white/10 px-3 py-6 text-center text-xs text-neutral-500">
                                Nenhuma EJ entrou nesta meta ainda.
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
