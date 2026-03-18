import { useState } from 'react';
import { useDashboard } from './useDashboard';
import EjCard from './EjCard';
import DashboardFilters from './DashboardFilters';
import ExportModal from './ExportModal';
import type { EmpresaQueryParams } from '../../types/empresa';

export default function DashboardPage() {
    const [filters, setFilters] = useState<EmpresaQueryParams>({
        ano: 2026,
        mes: new Date().getMonth() + 1,
        ordem_por: 'faturamento',
        direcao: 'desc',
    });

    const { data, isLoading, isError, error } = useDashboard(filters);
    const [showExport, setShowExport] = useState(false);

    return (
        <div>
            {/* Page Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-1 h-8 rounded-full bg-gradient-to-b from-primary-400 to-primary-600" />
                    <h1 className="font-heading text-3xl font-bold text-gradient">
                        Dashboard FEJEPE
                    </h1>
                </div>
                <p className="text-neutral-400 ml-5 text-sm italic">
                    RNN 7 - Acreditamos e trabalhamos por uma federação de impacto.
                </p>
            </div>

            {/* Summary bar */}
            {data && (
                <div className="grid grid-cols-3 gap-4 mb-8">
                    <SummaryCard
                        label="Total de EJs"
                        value={data.meta.total.toString()}
                        icon={
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
                            </svg>
                        }
                    />
                    <SummaryCard
                        label="Faturamento Total"
                        value={`R$ ${(
                            data.data.reduce((sum, ej) => sum + ej.faturamento_acumulado, 0) / 1000
                        ).toFixed(0)}k`}
                        icon={
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        }
                    />
                    <SummaryCard
                        label="Projetos"
                        value={data.data.reduce((sum, ej) => sum + ej.projetos_totais, 0).toString()}
                        icon={
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" />
                            </svg>
                        }
                    />
                </div>
            )}

            {/* Filters */}
            <DashboardFilters filters={filters} onChange={setFilters} />

            {/* Export button */}
            {data && data.data.length > 0 && (
                <div className="flex justify-end mb-4 -mt-4">
                    <button
                        onClick={() => setShowExport(true)}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl glass-card text-sm font-medium text-primary-400 hover:text-white hover:bg-primary-500/20 border border-primary-500/20 hover:border-primary-500/40 transition-all cursor-pointer"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                        </svg>
                        Exportar CSV
                    </button>
                </div>
            )}

            {/* Loading State */}
            {isLoading && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <div
                            key={i}
                            className="glass-card rounded-2xl p-6 animate-pulse"
                        >
                            <div className="h-5 bg-white/10 rounded w-3/4 mb-3" />
                            <div className="h-4 bg-white/5 rounded w-1/2 mb-6" />
                            <div className="h-px bg-white/5 mb-4" />
                            <div className="grid grid-cols-2 gap-3">
                                <div className="h-14 bg-white/5 rounded-lg" />
                                <div className="h-14 bg-white/5 rounded-lg" />
                                <div className="h-14 bg-white/5 rounded-lg" />
                                <div className="h-14 bg-white/5 rounded-lg" />
                            </div>
                            <div className="h-1.5 bg-white/5 rounded-full mt-4" />
                            <div className="h-10 bg-white/5 rounded-lg mt-4" />
                        </div>
                    ))}
                </div>
            )}

            {/* Error State */}
            {isError && (
                <div className="text-center py-16 glass-card rounded-2xl">
                    <div className="text-error text-4xl mb-3">⚠</div>
                    <h3 className="font-heading font-semibold text-lg text-white mb-1">
                        Erro ao carregar dados
                    </h3>
                    <p className="text-neutral-500 text-sm">
                        {(error as Error)?.message ?? 'Tente novamente mais tarde.'}
                    </p>
                </div>
            )}

            {/* EJ Cards Grid */}
            {data && data.data.length > 0 && (
                <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {data.data.map((empresa) => (
                            <EjCard key={empresa.id} empresa={empresa} />
                        ))}
                    </div>

                    {/* Load More */}
                    {data.meta.page < data.meta.total_pages && (
                        <div className="flex flex-col items-center mt-10 gap-2">
                            <p className="text-neutral-500 text-xs">
                                Exibindo {data.data.length} de {data.meta.total} EJs
                            </p>
                            <button
                                onClick={() =>
                                    setFilters((prev) => ({
                                        ...prev,
                                        page_size: (prev.page_size ?? 20) + 20,
                                    }))
                                }
                                className="px-6 py-2.5 rounded-xl glass-card text-sm font-medium text-primary-400 hover:text-white hover:bg-primary-500/20 border border-primary-500/20 hover:border-primary-500/40 transition-all cursor-pointer"
                            >
                                Carregar mais
                            </button>
                        </div>
                    )}
                </>
            )}

            {/* Export Modal */}
            {showExport && data && (
                <ExportModal
                    empresas={data.data}
                    onClose={() => setShowExport(false)}
                />
            )}

            {/* Empty State */}
            {data && data.data.length === 0 && (
                <div className="text-center py-16 glass-card rounded-2xl">
                    <div className="text-neutral-600 text-5xl mb-4">
                        <svg className="w-16 h-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={0.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                        </svg>
                    </div>
                    <h3 className="font-heading font-semibold text-lg text-white mb-1">
                        Nenhuma EJ encontrada
                    </h3>
                    <p className="text-neutral-500 text-sm">
                        Ajuste os filtros para encontrar Empresas Juniores.
                    </p>
                </div>
            )}
        </div>
    );
}

/* ── Summary Card (inline component) ── */

function SummaryCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
    return (
        <div className="glass-card rounded-xl p-4 flex items-start gap-3">
            <div className="p-2 rounded-lg bg-primary-500/10 text-primary-400 shrink-0">
                {icon}
            </div>
            <div>
                <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-0.5">{label}</p>
                <p className="text-xl font-bold text-white">{value}</p>
            </div>
        </div>
    );
}
