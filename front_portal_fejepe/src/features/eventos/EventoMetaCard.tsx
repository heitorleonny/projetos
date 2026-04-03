import type { EventoMetaResultado } from '../../types/evento';
import { formatPercent, getClusterInfo } from '../../utils/formatters';

interface EventoMetaCardProps {
    meta: EventoMetaResultado;
    expanded: boolean;
    onToggle: () => void;
}

const META_THEME: Record<EventoMetaResultado['tipo'], { accent: string; glow: string }> = {
    fora_do_zero: { accent: '#0D6EFD', glow: '#0D6EFD22' },
    verde_abril: { accent: '#16A34A', glow: '#16A34A22' },
    colab_tracking: { accent: '#F59E0B', glow: '#F59E0B22' },
};

function formatCount(value: number): string {
    return new Intl.NumberFormat('pt-BR').format(value);
}

export default function EventoMetaCard({ meta, expanded, onToggle }: EventoMetaCardProps) {
    const theme = META_THEME[meta.tipo];
    const progress = meta.meta_contagem > 0
        ? Math.min(100, (meta.resultado_contagem / meta.meta_contagem) * 100)
        : 0;
    const statusText = meta.gap_contagem === 0 ? 'Meta batida' : `Faltam ${formatCount(meta.gap_contagem)} EJs`;
    const subgapText = meta.subgap_contagem == null || meta.subgap_contagem === 0
        ? 'Meta batida'
        : `Faltam ${formatCount(meta.subgap_contagem)} EJs`;

    return (
        <div className="glass-card rounded-2xl p-5 border border-white/10 h-full" style={{ boxShadow: `0 0 0 1px ${theme.glow} inset` }}>
            <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                    <div className="inline-flex items-center gap-2 mb-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: theme.accent }} />
                        <span className="text-[11px] uppercase tracking-[0.25em] text-neutral-400 font-semibold">
                            {meta.titulo}
                        </span>
                    </div>
                    <p className="text-sm text-neutral-300 leading-relaxed">{meta.descricao}</p>
                </div>
                <div className="text-right shrink-0">
                    <p className="text-xs text-neutral-500 uppercase tracking-wider">Meta</p>
                    <p className="text-xl font-bold text-white">{formatPercent(meta.meta_percentual)}</p>
                    <p className="text-xs text-neutral-500">{formatCount(meta.meta_contagem)} EJs</p>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="rounded-xl bg-white/5 border border-white/10 p-3">
                    <p className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Atual</p>
                    <p className="text-lg font-bold text-white">{formatPercent(meta.resultado_percentual)}</p>
                    <p className="text-xs text-neutral-400">{formatCount(meta.resultado_contagem)} EJs</p>
                </div>
                <div className="rounded-xl bg-white/5 border border-white/10 p-3">
                    <p className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Gap</p>
                    <p className="text-lg font-bold text-white">{formatPercent(meta.gap_percentual)}</p>
                    <p className="text-xs text-neutral-400">{statusText}</p>
                </div>
                <div className="rounded-xl bg-white/5 border border-white/10 p-3">
                    <p className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Cobertura</p>
                    <p className="text-lg font-bold text-white">{formatPercent(progress)}</p>
                    <p className="text-xs text-neutral-400">do objetivo</p>
                </div>
            </div>

            <div className="h-2 rounded-full bg-white/5 overflow-hidden mb-4">
                <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{ width: `${progress}%`, backgroundColor: theme.accent }}
                />
            </div>

            {meta.submeta_titulo && meta.submeta_contagem != null && meta.subresultado_contagem != null && (
                <div className="mb-4 rounded-xl border border-white/10 bg-white/5 p-3">
                    <div className="flex items-start justify-between gap-3">
                        <div>
                            <p className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Submeta</p>
                            <p className="text-sm text-white font-semibold">{meta.submeta_titulo}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm font-semibold text-white">{formatPercent(meta.submeta_percentual ?? 0)}</p>
                            <p className="text-xs text-neutral-400">{formatCount(meta.submeta_contagem)} EJs</p>
                        </div>
                    </div>
                    <p className="mt-2 text-xs text-neutral-400">
                        Atual: {formatCount(meta.subresultado_contagem)} EJs | Gap: {subgapText}
                    </p>
                </div>
            )}

            <button
                type="button"
                onClick={onToggle}
                className="w-full px-4 py-2.5 rounded-xl text-sm font-semibold border border-white/10 bg-white/5 text-white hover:bg-white/10 transition-all cursor-pointer"
            >
                {expanded ? 'Ocultar EJs' : 'Ver EJs contabilizadas'}
            </button>

            {expanded && (
                <div className="mt-4 space-y-2 max-h-72 overflow-auto pr-1">
                    {meta.participantes.length > 0 ? (
                        meta.participantes.map((participante) => {
                            const clusterInfo = getClusterInfo(participante.cluster);
                            return (
                                <div key={participante.id_ej} className="rounded-xl border border-white/10 bg-neutral-950/30 px-3 py-2.5 flex items-center justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-medium text-white">{participante.nome}</p>
                                        <p className="text-xs text-neutral-400">
                                            {participante.comunidade ?? 'Comunidade não informada'}
                                            {' '}• {formatPercent(participante.percentual_meta ?? 0)}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                        {participante.atende_cluster_1_2 && (
                                            <span className="text-[10px] px-2 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/20">
                                                Cluster 1/2
                                            </span>
                                        )}
                                        <span className="text-[10px] px-2 py-1 rounded-full border" style={{ backgroundColor: `${clusterInfo.color}15`, borderColor: `${clusterInfo.color}30`, color: clusterInfo.color }}>
                                            {clusterInfo.label}
                                        </span>
                                    </div>
                                </div>
                            );
                        })
                    ) : (
                        <div className="rounded-xl border border-dashed border-white/10 px-3 py-6 text-center text-sm text-neutral-500">
                            Nenhuma EJ entrou nesta meta ainda.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}