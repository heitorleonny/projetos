import type { EmpresaQueryParams, OrdemEmpresa, Ritmo } from '../../types/empresa';

interface DashboardFiltersProps {
    filters: EmpresaQueryParams;
    onChange: (filters: EmpresaQueryParams) => void;
}

const comunidades = ['CAPIBA', 'PRAIEIRA', 'TROPICANA', 'INCUBADORA DE APAIXONADOS', 'MANDACARU'];
const clusters = [1, 2, 3, 4, 5];
const meses = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];
const ordenacoes: { value: OrdemEmpresa; label: string }[] = [
    { value: 'nome', label: 'Nome' },
    { value: 'faturamento', label: 'Faturamento' },
    { value: 'cluster', label: 'Cluster' },
    { value: 'projetos', label: 'Projetos' },
    { value: 'percentual_meta', label: '% Meta' },
];
const ritmos: { value: Ritmo; label: string }[] = [
    { value: 'significativo', label: 'Significativo' },
    { value: 'minimo', label: 'Mínimo' },
    { value: 'sem_vendas', label: 'Sem Vendas' },
];

export default function DashboardFilters({ filters, onChange }: DashboardFiltersProps) {
    const update = (partial: Partial<EmpresaQueryParams>) => {
        onChange({ ...filters, ...partial });
    };

    const activeCount = [
        filters.cluster,
        filters.comunidade,
        filters.search,
        filters.cidade,
        filters.universidade,
        filters.mes,
        filters.ritmo,
    ].filter(Boolean).length;

    return (
        <div className="glass-card rounded-2xl p-5 mb-8">
            <div className="flex items-center gap-3 mb-4">
                <svg className="w-4 h-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                </svg>
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                    Filtros
                </h3>
                {activeCount > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-primary-500/20 text-primary-300 border border-primary-500/30">
                        {activeCount} ativo{activeCount > 1 ? 's' : ''}
                    </span>
                )}
                {activeCount > 0 && (
                    <button
                        onClick={() => onChange({ ano: filters.ano, ordem_por: filters.ordem_por, direcao: filters.direcao })}
                        className="ml-auto text-xs text-neutral-500 hover:text-primary-400 transition-colors cursor-pointer"
                    >
                        Limpar filtros
                    </button>
                )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
                {/* Search */}
                <div className="relative">
                    <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <input
                        type="text"
                        placeholder="Buscar EJ por nome..."
                        value={filters.search ?? ''}
                        onChange={(e) => update({ search: e.target.value || undefined })}
                        className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-neutral-500 
                                   focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                    />
                </div>

                {/* Cidade */}
                <input
                    type="text"
                    placeholder="Cidade..."
                    value={filters.cidade ?? ''}
                    onChange={(e) => update({ cidade: e.target.value || undefined })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-neutral-500
                               focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                />

                {/* Universidade */}
                <input
                    type="text"
                    placeholder="Universidade..."
                    value={filters.universidade ?? ''}
                    onChange={(e) => update({ universidade: e.target.value || undefined })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-neutral-500
                               focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                />

                {/* Cluster */}
                <select
                    value={filters.cluster ?? ''}
                    onChange={(e) => update({ cluster: e.target.value ? Number(e.target.value) : undefined })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white
                               focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all 
                               cursor-pointer appearance-none"
                    style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px' }}
                >
                    <option value="" className="bg-neutral-800">Todos os Clusters</option>
                    {clusters.map((c) => (
                        <option key={c} value={c} className="bg-neutral-800">Cluster {c}</option>
                    ))}
                </select>

            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* Mês */}
                <select
                    value={filters.mes ?? ''}
                    onChange={(e) => update({ mes: e.target.value ? Number(e.target.value) : undefined })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white
                               focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all
                               cursor-pointer appearance-none"
                    style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px' }}
                >
                    <option value="" className="bg-neutral-800">Acumulado (todos os meses)</option>
                    {meses.map((label, i) => (
                        <option key={i + 1} value={i + 1} className="bg-neutral-800">{label}</option>
                    ))}
                </select>

                {/* Comunidade */}
                <select
                    value={filters.comunidade ?? ''}
                    onChange={(e) => update({ comunidade: e.target.value || undefined })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white
                               focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all
                               cursor-pointer appearance-none"
                    style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px' }}
                >
                    <option value="" className="bg-neutral-800">Todas as Comunidades</option>
                    {comunidades.map((c) => (
                        <option key={c} value={c} className="bg-neutral-800">{c}</option>
                    ))}
                </select>

                {/* Ritmo */}
                <select
                    value={filters.ritmo ?? ''}
                    onChange={(e) => update({ ritmo: (e.target.value || undefined) as Ritmo | undefined })}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white
                               focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all
                               cursor-pointer appearance-none"
                    style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px' }}
                >
                    <option value="" className="bg-neutral-800">Todos os Ritmos</option>
                    {ritmos.map((r) => (
                        <option key={r.value} value={r.value} className="bg-neutral-800">{r.label}</option>
                    ))}
                </select>

                {/* Ordenação */}
                <div className="flex gap-2">
                    <select
                        value={filters.ordem_por ?? 'faturamento'}
                        onChange={(e) => update({ ordem_por: e.target.value as OrdemEmpresa })}
                        className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white
                                   focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all
                                   cursor-pointer appearance-none"
                        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px' }}
                    >
                        {ordenacoes.map((o) => (
                            <option key={o.value} value={o.value} className="bg-neutral-800">{o.label}</option>
                        ))}
                    </select>
                    <button
                        onClick={() => update({ direcao: filters.direcao === 'asc' ? 'desc' : 'asc' })}
                        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-neutral-400 hover:text-white hover:border-primary-500/30 transition-all cursor-pointer"
                        title={filters.direcao === 'asc' ? 'Crescente' : 'Decrescente'}
                    >
                        <svg className={`w-4 h-4 transition-transform ${filters.direcao === 'asc' ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
