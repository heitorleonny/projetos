import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchTodasEmpresas } from '../dashboard/dashboardService';
import { formatCurrency, formatPercent, formatSde, getClusterInfo } from '../../utils/formatters';
import EjLogo from '../../components/EjLogo';
import type { EmpresaComIndicadores } from '../../types/empresa';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';
import { ultimosAnosDecrescente } from '../../utils/anos';

const CLUSTERS = [1, 2, 3, 4, 5];

export default function ClusterTrackPage() {
    const [cluster, setCluster] = useState<number | undefined>(undefined);
    const [search, setSearch] = useState('');
    const { anoDefault } = useFederacaoBranding();
    const [ano, setAno] = useState(anoDefault);
    // Duas janelas: esta tela compara o ano corrente com o anterior.
    const anosDisponiveis = ultimosAnosDecrescente(anoDefault, 2);

    const { data, isLoading, isError } = useQuery({
        queryKey: ['cluster-track', cluster, search, ano],
        queryFn: () =>
            fetchTodasEmpresas({
                ano,
                cluster,
                search: search || undefined,
                ordem_por: 'faturamento',
                direcao: 'desc',
            }),
    });

    const empresas = data?.data ?? [];

    return (
        <div>
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                    <h1 className="text-2xl sm:text-3xl font-semibold text-neutral-50">
                        EJs por Cluster Track
                    </h1>
                </div>
                <p className="text-neutral-400 text-sm">
                    Listagem das EJs agrupadas pelo seu Cluster Track calculado, com todos os indicadores do Índice de Cluster.
                </p>
                <p className="text-neutral-500 text-xs mt-1">
                    O projeto de impacto é obrigatório nos clusters 4 e 5: o track pode apontar o Cluster 4 ou 5, mas o cluster real
                    só chega a eles, e só permanece neles, com projeto de impacto. Sem projeto, o cluster real fica no 3. Quando isso acontece, o cluster apontado aparece riscado
                    ao lado do cluster real.
                </p>
            </div>

            {/* Filters */}
            <div data-tour="cluster-filtros" className="glass-card rounded-2xl p-5 mb-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {/* Search */}
                    <div className="relative">
                        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Buscar EJ por nome..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-neutral-500
                                       focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                        />
                    </div>

                    {/* Cluster cadastral selector */}
                    <div className="flex gap-1.5">
                        <button
                            onClick={() => setCluster(undefined)}
                            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer border ${
                                cluster === undefined
                                    ? 'bg-primary-500/20 border-primary-500/40 text-primary-300'
                                    : 'bg-white/5 border-white/10 text-neutral-400 hover:text-white'
                            }`}
                        >
                            Todos
                        </button>
                        {CLUSTERS.map((c) => {
                            const info = getClusterInfo(c);
                            const isActive = cluster === c;
                            return (
                                <button
                                    key={c}
                                    onClick={() => setCluster(isActive ? undefined : c)}
                                    className="flex-1 py-2.5 rounded-lg text-sm font-bold transition-all cursor-pointer border"
                                    style={{
                                        color: isActive ? info.color : '#94a3b8',
                                        backgroundColor: isActive ? `${info.color}20` : 'rgba(255,255,255,0.03)',
                                        borderColor: isActive ? `${info.color}50` : 'rgba(255,255,255,0.1)',
                                    }}
                                >
                                    C{c}
                                </button>
                            );
                        })}
                    </div>

                    {/* Ano */}
                    <select
                        value={ano}
                        onChange={(e) => setAno(Number(e.target.value))}
                        className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white
                                   focus:outline-none focus:border-primary-500/50 transition-all cursor-pointer appearance-none"
                        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px' }}
                    >
                        {anosDisponiveis.map((a) => (
                            <option key={a} value={a} className="bg-neutral-800">{a}</option>
                        ))}
                    </select>
                </div>

                {data && (
                    <p className="text-xs text-neutral-400 mt-3">
                        {empresas.length} EJ{empresas.length !== 1 ? 's' : ''} encontrada{empresas.length !== 1 ? 's' : ''}
                        {cluster ? ` no Cluster ${cluster}` : ''}
                    </p>
                )}
            </div>

            {/* Loading */}
            {isLoading && (
                <div className="glass-card rounded-2xl p-12 flex items-center justify-center">
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-10 h-10 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
                        <p className="text-neutral-400 text-sm">Carregando…</p>
                    </div>
                </div>
            )}

            {/* Error */}
            {isError && (
                <div className="glass-card rounded-2xl p-10 text-center">
                    <p className="text-error">Erro ao carregar dados. Tente novamente.</p>
                </div>
            )}

            {/* Table */}
            {!isLoading && !isError && empresas.length > 0 && (
                <div className="glass-card rounded-2xl overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-white/5">
                                    <th className="text-left px-4 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold">EJ</th>
                                    <th className="text-center px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">Cluster<br/>Cad. / Track</th>
                                    <th className="text-right px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">Faturamento<br/><span className="text-neutral-600 normal-case">real / meta</span></th>
                                    <th className="text-right px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">Fat. Colab.<br/><span className="text-neutral-600 normal-case">real / taxa %</span></th>
                                    <th className="text-right px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">CSAT<br/><span className="text-neutral-600 normal-case">real / meta</span></th>
                                    <th className="text-right px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">Engaj. MEJ<br/><span className="text-neutral-600 normal-case">real / meta</span></th>
                                    <th className="text-center px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">Projeto de Impacto<br/><span className="text-neutral-600 normal-case">tem / meta</span></th>
                                    <th className="text-center px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">Índice Real<br/><span className="text-neutral-600 normal-case">cluster / pts</span></th>
                                    <th className="text-center px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">Track Índice<br/><span className="text-neutral-600 normal-case">cluster / pts</span></th>
                                    <th className="text-right px-3 py-3 text-[10px] text-neutral-400 uppercase tracking-wider font-semibold whitespace-nowrap">Falta (tracking)<br/><span className="text-neutral-600 normal-case">p/ próx. cluster</span></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/[0.04]">
                                {empresas.map((ej) => (
                                    <ClusterTrackRow key={ej.id} ej={ej} />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Empty */}
            {!isLoading && !isError && empresas.length === 0 && (
                <div className="glass-card rounded-2xl p-16 text-center">
                    <p className="text-neutral-400 text-sm">Nenhuma EJ encontrada para os filtros selecionados.</p>
                </div>
            )}
        </div>
    );
}

function ClusterTrackRow({ ej }: { ej: EmpresaComIndicadores }) {
    const cadastral = getClusterInfo(ej.cluster);
    const taxaColabReal = ej.taxa_colaboracao != null ? ej.taxa_colaboracao * 100 : null;

    return (
        <tr className="hover:bg-white/[0.02] transition-colors group">
            {/* EJ */}
            <td className="px-4 py-3">
                <Link to={`/empresas/${ej.id_ej}`} className="flex items-center gap-2.5 no-underline group/link">
                    <EjLogo
                        nome={ej.nome}
                        fotoUrl={ej.foto_url}
                        sizeClassName="w-8 h-8"
                        className="shrink-0 border border-white/10"
                        initialsClassName="text-xs"
                    />
                    <div className="min-w-0">
                        <p className="text-white font-medium text-sm truncate max-w-[160px] group-hover/link:text-primary-300 transition-colors">
                            {ej.nome}
                        </p>
                        <p className="text-neutral-400 text-[11px] truncate">{ej.cidade ?? 'Cidade não informada'}</p>
                    </div>
                </Link>
            </td>

            {/* Cluster Cadastral / Track */}
            <td className="px-3 py-3 text-center">
                <div className="flex flex-col items-center gap-1">
                    <ClusterBadge color={cadastral.color} label={ej.cluster ? `C${ej.cluster}` : '—'} />
                    <ClusterRealBadge apontado={ej.tracking_cluster_calculado ?? null} real={ej.tracking_cluster_efetivo ?? null} />
                </div>
            </td>

            {/* Faturamento: real / meta */}
            <td className="px-3 py-3 text-right">
                <p className="text-white font-medium tabular-nums text-sm">{formatCurrency(ej.faturamento_acumulado)}</p>
                <p className="text-neutral-400 tabular-nums text-[11px]">{ej.meta_faturamento != null ? formatCurrency(ej.meta_faturamento) : '—'}</p>
            </td>

            {/* Fat. Colab.: real / taxa real */}
            <td className="px-3 py-3 text-right">
                <p className="text-white font-medium tabular-nums text-sm">{ej.faturamento_colab_acumulado > 0 ? formatCurrency(ej.faturamento_colab_acumulado) : '—'}</p>
                <p className="text-neutral-400 tabular-nums text-[11px]">{taxaColabReal != null ? formatPercent(taxaColabReal) : '—'}</p>
            </td>

            {/* CSAT: real / meta */}
            <td className="px-3 py-3 text-right">
                <p className="text-white font-medium tabular-nums text-sm">{ej.csat_medio != null ? ej.csat_medio.toFixed(2) : '—'}</p>
                <p className="text-neutral-400 tabular-nums text-[11px]">{ej.meta_csat != null ? ej.meta_csat.toFixed(2) : '—'}</p>
            </td>

            {/* Engaj. MEJ: real / meta */}
            <td className="px-3 py-3 text-right">
                <p className="text-white font-medium tabular-nums text-sm">{ej.engajamento_mej != null ? formatPercent(ej.engajamento_mej * 100) : '—'}</p>
                <p className="text-neutral-400 tabular-nums text-[11px]">{ej.meta_engajamento_mej != null ? formatPercent(ej.meta_engajamento_mej) : '—'}</p>
            </td>

            {/* Projeto de impacto: tem / meta (vazio na planilha = nenhum projeto) */}
            <td className="px-3 py-3 text-center">
                {ej.tem_dados_no_ano === false ? (
                    <span className="text-neutral-600">—</span>
                ) : (
                    <>
                        <p className={`font-medium text-sm ${ej.tem_projeto_impacto ? 'text-green-400' : 'text-neutral-500'}`}>
                            {ej.tem_projeto_impacto ? 'Sim' : 'Não'}
                        </p>
                        <p className="text-neutral-400 tabular-nums text-[11px]">
                            {ej.meta_projetos_impacto != null ? `meta ${ej.meta_projetos_impacto}` : '—'}
                        </p>
                    </>
                )}
            </td>

            {/* Índice Real */}
            <td className="px-3 py-3 text-center">
                <div className="flex flex-col items-center gap-0.5">
                    <ClusterRealBadge apontado={ej.indice_cluster_calculado ?? null} real={ej.indice_cluster_efetivo ?? null} />
                    {ej.indice_cluster != null && (
                        <span className="text-[10px] text-neutral-400">{formatSde(ej.indice_cluster)}</span>
                    )}
                </div>
            </td>

            {/* Track Índice */}
            <td className="px-3 py-3 text-center">
                <div className="flex flex-col items-center gap-0.5">
                    <ClusterRealBadge apontado={ej.tracking_cluster_calculado ?? null} real={ej.tracking_cluster_efetivo ?? null} />
                    {ej.tracking_cluster != null && (
                        <span className="text-[10px] text-neutral-400">{formatSde(ej.tracking_cluster)}</span>
                    )}
                </div>
            </td>

            {/* Falta — Tracking */}
            <td className="px-3 py-3 text-right">
                <FaltaCell
                    valor={ej.faturamento_para_proximo_cluster}
                    trackingCluster={ej.tracking_cluster_calculado ?? null}
                    clusterReal={ej.tracking_cluster_efetivo ?? null}
                    exigeProjeto={ej.tem_dados_no_ano !== false && !ej.tem_projeto_impacto}
                />
            </td>

        </tr>
    );
}

function FaltaCell({ valor, trackingCluster, clusterReal, exigeProjeto }: {
    valor: number | null;
    trackingCluster: number | null;
    clusterReal: number | null;
    /** A EJ ainda não tem projeto de impacto (obrigatório no C4 e no C5). */
    exigeProjeto: boolean;
}) {
    // O track aponta C4/C5, mas o cluster real fica travado no C3 sem projeto.
    if (trackingCluster != null && clusterReal != null && clusterReal < trackingCluster) {
        return <span className="text-amber-300 text-xs font-medium">Falta projeto de impacto</span>;
    }
    if (trackingCluster === 5) {
        return <span className="text-green-400 text-xs font-medium">Cluster máx.</span>;
    }
    if (valor != null) {
        return (
            <div>
                <p className="text-primary-300 font-medium tabular-nums text-sm">{formatCurrency(valor)}</p>
                {trackingCluster != null && trackingCluster >= 3 && exigeProjeto && (
                    <p className="text-amber-300/80 text-[10px]">+ projeto de impacto</p>
                )}
            </div>
        );
    }
    return <span className="text-neutral-600">—</span>;
}

/**
 * Cluster que o índice/track aponta e o cluster real. Iguais: um badge só.
 * Diferentes (sem projeto de impacto o real não passa do C3): o apontado
 * aparece riscado ao lado do real.
 */
function ClusterRealBadge({ apontado, real }: { apontado: number | null; real: number | null }) {
    const infoApontado = getClusterInfo(apontado);
    if (apontado == null) return <ClusterBadge color={infoApontado.color} label="—" />;
    if (real == null || real === apontado) {
        return <ClusterBadge color={infoApontado.color} label={`C${apontado}`} />;
    }
    const infoReal = getClusterInfo(real);
    return (
        <span
            className="inline-flex items-center gap-1"
            title={`Aponta C${apontado}, mas sem projeto de impacto o cluster real é no máximo C${real}.`}
        >
            <span className="text-[11px] font-bold line-through opacity-50" style={{ color: infoApontado.color }}>
                C{apontado}
            </span>
            <ClusterBadge color={infoReal.color} label={`C${real}`} />
        </span>
    );
}

function ClusterBadge({ color, label }: { color: string; label: string }) {
    return (
        <span
            className="inline-block px-2 py-0.5 rounded-full text-[11px] font-bold border"
            style={{
                color,
                backgroundColor: `${color}15`,
                borderColor: `${color}30`,
            }}
        >
            {label}
        </span>
    );
}
