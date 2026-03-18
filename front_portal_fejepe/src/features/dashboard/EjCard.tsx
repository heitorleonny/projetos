import { Link } from 'react-router-dom';
import type { EmpresaComIndicadores } from '../../types/empresa';
import { formatCurrency, formatPercent, getClusterInfo, getRitmoLabel } from '../../utils/formatters';

interface EjCardProps {
    empresa: EmpresaComIndicadores;
}

export default function EjCard({ empresa }: EjCardProps) {
    const cluster = getClusterInfo(empresa.cluster);
    const ritmo = getRitmoLabel(empresa.ritmo);
    const percentMeta = empresa.percentual_meta ?? 0;

    return (
        <div className="glass-card rounded-2xl p-6 transition-all duration-300 flex flex-col gap-4 group">
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                    <h3 className="font-heading font-semibold text-base text-white truncate group-hover:text-primary-300 transition-colors">
                        {empresa.nome}
                    </h3>
                    <p className="text-sm text-neutral-500 truncate">
                        {empresa.comunidade ?? 'Sem comunidade'}
                    </p>
                </div>
                <span
                    className="shrink-0 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide whitespace-nowrap border"
                    style={{
                        color: cluster.color,
                        backgroundColor: `${cluster.color}15`,
                        borderColor: `${cluster.color}30`,
                    }}
                >
                    {cluster.label}
                </span>
            </div>

            {/* Divider */}
            <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

            {/* Indicators grid */}
            <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/[0.03] rounded-lg p-2.5">
                    <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-0.5">Faturamento</p>
                    <p className="text-sm font-semibold text-white">
                        {formatCurrency(empresa.faturamento_acumulado)}
                    </p>
                </div>
                <div className="bg-white/[0.03] rounded-lg p-2.5">
                    <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-0.5">Projetos</p>
                    <p className="text-sm font-semibold text-white">
                        {empresa.projetos_totais}
                    </p>
                </div>
                <div className="bg-white/[0.03] rounded-lg p-2.5">
                    <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-0.5">Ritmo</p>
                    <p className="text-xs font-semibold" style={{ color: ritmo.color }}>
                        {ritmo.label}
                    </p>
                </div>
            </div>

            {/* Progress bar — % Meta */}
            <div>
                <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] text-neutral-500 uppercase tracking-wider">Meta atingida</span>
                    <span className="text-xs font-bold text-white">
                        {formatPercent(empresa.percentual_meta)}
                    </span>
                </div>
                <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                    <div
                        className="h-full rounded-full transition-all duration-700 relative"
                        style={{
                            width: `${Math.min(percentMeta, 100)}%`,
                            background: percentMeta >= 80
                                ? 'linear-gradient(90deg, #16A34A, #22D3EE)'
                                : percentMeta >= 50
                                    ? 'linear-gradient(90deg, #F59E0B, #FBBF24)'
                                    : 'linear-gradient(90deg, #DC2626, #F87171)',
                            boxShadow: `0 0 8px ${percentMeta >= 80 ? '#16A34A' : percentMeta >= 50 ? '#F59E0B' : '#DC2626'}50`,
                        }}
                    />
                </div>
            </div>

            {/* CTA Button */}
            <Link
                to={`/empresas/${empresa.id_ej}`}
                className="mt-auto block text-center btn-glow text-white font-medium text-sm py-2.5 px-4 rounded-lg no-underline"
            >
                Visualizar dados
            </Link>
        </div>
    );
}
