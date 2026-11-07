import { Link } from 'react-router-dom';
import type { EmpresaComIndicadores } from '../../types/empresa';
import { formatCurrency, formatPercent, getClusterInfo, getRitmoLabel } from '../../utils/formatters';
import EjLogo from '../../components/EjLogo';

interface EjCardProps {
    empresa: EmpresaComIndicadores;
}

export default function EjCard({ empresa }: EjCardProps) {
    const cluster = getClusterInfo(empresa.cluster);
    const ritmo = getRitmoLabel(empresa.ritmo);
    const percentMeta = empresa.percentual_meta ?? 0;

    return (
        <div className="glass-card rounded-xl p-5 flex flex-col gap-4 group">
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1 flex items-center gap-3">
                    <EjLogo
                        nome={empresa.nome}
                        fotoUrl={empresa.foto_url}
                        sizeClassName="w-11 h-11"
                        className="shrink-0 border border-white/10"
                        initialsClassName="text-base"
                    />
                    <div className="min-w-0 flex-1">
                        <h3 className="font-semibold text-base text-white truncate">
                            {empresa.nome}
                        </h3>
                        <p className="text-sm text-neutral-400 truncate">
                            {empresa.cidade ?? 'Cidade não informada'}
                        </p>
                    </div>
                </div>
                <span
                    className="shrink-0 px-2 py-1 rounded-md text-xs font-medium whitespace-nowrap border"
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
            <div className="h-px bg-neutral-700" />

            {/* Indicators grid */}
            <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg py-1">
                    <p className="text-xs text-neutral-400 mb-0.5">Faturamento</p>
                    <p className="text-sm font-semibold text-white">
                        {formatCurrency(empresa.faturamento_acumulado)}
                    </p>
                </div>
                <div className="rounded-lg py-1">
                    <p className="text-xs text-neutral-400 mb-0.5">Projetos</p>
                    <p className="text-sm font-semibold text-white">
                        {empresa.projetos_totais}
                    </p>
                </div>
                <div className="rounded-lg py-1">
                    <p className="text-xs text-neutral-400 mb-0.5">Ritmo</p>
                    <p className="text-xs font-semibold" style={{ color: ritmo.color }}>
                        {ritmo.label}
                    </p>
                </div>
                <div className="rounded-lg py-1">
                    <p className="text-xs text-neutral-400 mb-0.5">Proj. Colab.</p>
                    <p className="text-sm font-semibold text-white">
                        {empresa.projetos_colab_totais ?? 0}
                    </p>
                </div>
            </div>

            {/* Progress bar — % Meta */}
            <div>
                <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs text-neutral-400">Meta atingida</span>
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
                                ? 'var(--color-success)'
                                : percentMeta >= 50
                                    ? 'var(--color-warning)'
                                    : 'var(--color-error)',
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
