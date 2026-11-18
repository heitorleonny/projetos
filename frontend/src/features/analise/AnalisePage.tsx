import { useState } from 'react';
import { Link } from 'react-router-dom';
import EjLogo from '../../components/EjLogo';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';
import { formatCurrency } from '../../utils/formatters';
import { useSessaoAdmin } from '../admin/useAdmin';
import { useAnalise, useBriefing, useRegenerarBriefing } from './useAnalise';
import type { Briefing, Comparativo, EjDestaque, Gravidade } from './analiseService';

const MESES = [
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
];
const LIMITE_LISTA = 10;

/** Percentual com vírgula decimal, como no resumo do mês (o formatPercent comum usa ponto). */
function percentualBR(valor: number | null | undefined): string {
    if (valor == null) return '—';
    return `${valor.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

/**
 * Análise do mês: resumo da federação, EJs em alerta e EJs em ascensão.
 *
 * Os motivos são regras descritivas calculadas no backend (o que já aconteceu
 * nos dados do mês). Não é previsão — ver docs/plano-analise-do-mes-2026-11-17.md.
 */
export default function AnalisePage() {
    const { nome, anoDefault } = useFederacaoBranding();
    const [mes, setMes] = useState<number | undefined>(undefined);
    const hoje = new Date();
    const { data, isLoading, isError } = useAnalise({ ano: anoDefault, mes });

    const mesRef = data?.mes ?? null;
    const mesAnt = data?.mes_anterior ?? null;

    return (
        <div>
            <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-semibold text-neutral-50">Análise do mês · {nome}</h1>
                    <p className="text-neutral-400 text-sm mt-1">
                        {mesRef ? `Referência: ${MESES[mesRef - 1]} de ${data?.ano}` : 'Resumo da federação, EJs em alerta e em ascensão.'}
                    </p>
                </div>
                <label className="flex flex-col gap-1 text-xs text-neutral-400">
                    Mês de referência
                    <select
                        value={mes ?? ''}
                        onChange={(e) => setMes(e.target.value ? Number(e.target.value) : undefined)}
                        className="glass-card rounded-lg px-3 py-2 text-sm text-white bg-transparent border border-neutral-700"
                    >
                        <option value="" className="bg-neutral-900">Último mês fechado</option>
                        {MESES.map((m, i) => (
                            <option key={m} value={i + 1} className="bg-neutral-900">
                                {m[0].toUpperCase() + m.slice(1)}
                                {anoDefault === hoje.getFullYear() && i + 1 === hoje.getMonth() + 1 ? ' (em andamento)' : ''}
                            </option>
                        ))}
                    </select>
                </label>
            </div>

            {isLoading && <p className="text-neutral-400">Carregando análise…</p>}
            {isError && <p className="text-red-400">Não foi possível carregar a análise do mês. Tente novamente.</p>}
            {data && mesRef === null && (
                <div className="glass-card rounded-xl p-6 text-neutral-300">Ainda não há monitoramento carregado para {data.ano}.</div>
            )}

            {data && mesRef !== null && (
                <>
                    {data.mes_parcial && (
                        <div role="status" className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                            {MESES[mesRef - 1][0].toUpperCase() + MESES[mesRef - 1].slice(1)} ainda está em andamento. As EJs continuam
                            reportando, então os alertas e as comparações deste mês são parciais.
                        </div>
                    )}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                        <CartaoComparativo
                            label="EJs fora do zero"
                            valor={data.resumo.fora_do_zero}
                            total={data.resumo.total_ejs}
                            mesAnt={mesAnt}
                            nota={`${data.resumo.total_ejs - data.resumo.fora_do_zero.atual} ainda sem venda no ano`}
                        />
                        <CartaoComparativo label="EJs no verde" valor={data.resumo.no_verde} total={data.resumo.total_ejs} mesAnt={mesAnt} />
                        <CartaoComparativo label="Ritmo significativo" valor={data.resumo.ritmo_significativo} total={data.resumo.total_ejs} mesAnt={mesAnt} />
                        <div className="glass-card rounded-xl p-4">
                            <p className="text-[10px] text-neutral-400 uppercase tracking-wider mb-0.5">Faturamento acumulado</p>
                            <p className="text-xl font-bold text-white">{formatCurrency(data.resumo.faturamento_acumulado.atual)}</p>
                            <p className="text-xs text-neutral-400 mt-1">
                                {data.resumo.percentual_meta_rede != null
                                    ? `${percentualBR(data.resumo.percentual_meta_rede)} da soma das metas`
                                    : 'Sem metas cadastradas'}
                            </p>
                        </div>
                    </div>

                    <ResumoDoMes ano={data.ano} mes={mesRef} fixo={data.briefing} />

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <ListaDestaques
                            titulo="EJs em alerta"
                            subtitulo="Precisam de atenção pelo que aconteceu nos dados do mês."
                            vazio="Nenhuma EJ em alerta neste mês."
                            tom="alerta"
                            itens={data.alertas}
                        />
                        <ListaDestaques
                            titulo="EJs em ascensão"
                            subtitulo="Foram bem neste mês."
                            vazio="Nenhuma EJ se destacou neste mês."
                            tom="ascensao"
                            itens={data.ascensao}
                        />
                    </div>
                </>
            )}
        </div>
    );
}

/**
 * Mostra o resumo fixo na hora e troca pelo texto da IA quando ele chega.
 * O texto da IA só chega se passou nas guardas do backend (números, nomes, vocabulário).
 */
function ResumoDoMes({ ano, mes, fixo }: { ano: number; mes: number; fixo: Briefing }) {
    const { data: sessao } = useSessaoAdmin();
    const { data: ia, isFetching } = useBriefing(ano, mes);
    const regenerar = useRegenerarBriefing(ano, mes);
    const briefing = ia ?? fixo;
    const redigindo = isFetching || regenerar.isPending;

    return (
        <section aria-labelledby="briefing-titulo" aria-busy={redigindo} className="glass-card rounded-xl p-5 mb-8">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <h2 id="briefing-titulo" className="text-sm font-semibold text-neutral-100">Resumo do mês</h2>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] uppercase tracking-wider text-neutral-500">
                        {redigindo ? 'Redigindo resumo…' : briefing.gerado_por_ia ? 'Redigido por IA a partir dos números da tela' : 'Resumo automático'}
                    </span>
                    {sessao?.pode_administrar && (
                        <button
                            type="button"
                            onClick={() => regenerar.mutate()}
                            disabled={redigindo}
                            className="text-xs text-accent-300 hover:text-white disabled:opacity-50 cursor-pointer"
                        >
                            Redigir de novo
                        </button>
                    )}
                </div>
            </div>
            <p className="text-neutral-300 text-sm leading-relaxed">{briefing.frases.join(' ')}</p>
        </section>
    );
}

function CartaoComparativo({ label, valor, total, mesAnt, nota }: {
    label: string; valor: Comparativo; total: number; mesAnt: number | null; nota?: string;
}) {
    const delta = valor.anterior != null ? valor.atual - valor.anterior : null;
    return (
        <div className="glass-card rounded-xl p-4">
            <p className="text-[10px] text-neutral-400 uppercase tracking-wider mb-0.5">{label}</p>
            <p className="text-xl font-bold text-white">
                {valor.atual} <span className="text-sm font-normal text-neutral-500">de {total}</span>
            </p>
            {delta != null && mesAnt != null && (
                <p className={`text-xs mt-1 ${delta > 0 ? 'text-green-400' : delta < 0 ? 'text-red-400' : 'text-neutral-400'}`}>
                    {delta === 0 ? `sem variação vs. ${MESES[mesAnt - 1]}` : `${delta > 0 ? '▲ +' : '▼ '}${delta} vs. ${MESES[mesAnt - 1]}`}
                </p>
            )}
            {nota && <p className="text-xs text-neutral-500 mt-0.5">{nota}</p>}
        </div>
    );
}

const ESTILO_GRAVIDADE: Record<Gravidade, string> = {
    alta: 'bg-red-500/15 text-red-300 border-red-500/30',
    media: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    baixa: 'bg-neutral-500/15 text-neutral-300 border-neutral-500/30',
};
const ROTULO_GRAVIDADE: Record<Gravidade, string> = { alta: 'Alta', media: 'Média', baixa: 'Baixa' };

function ListaDestaques({ titulo, subtitulo, vazio, tom, itens }: {
    titulo: string; subtitulo: string; vazio: string; tom: 'alerta' | 'ascensao'; itens: EjDestaque[];
}) {
    const [todas, setTodas] = useState(false);
    const visiveis = todas ? itens : itens.slice(0, LIMITE_LISTA);
    const corTitulo = tom === 'alerta' ? 'text-red-300' : 'text-green-300';
    const corMotivo = tom === 'alerta' ? 'border-red-500/30 bg-red-500/10 text-red-200' : 'border-green-500/30 bg-green-500/10 text-green-200';

    return (
        <section className="glass-card rounded-xl p-5" aria-label={titulo}>
            <div className="mb-4">
                <h2 className={`text-base font-semibold ${corTitulo}`}>
                    {titulo} <span className="text-neutral-500 font-normal">({itens.length})</span>
                </h2>
                <p className="text-xs text-neutral-400">{subtitulo}</p>
            </div>
            {itens.length === 0 ? (
                <p className="text-sm text-neutral-400">{vazio}</p>
            ) : (
                <ul className="flex flex-col gap-3">
                    {visiveis.map((ej) => (
                        <li key={ej.id_ej}>
                            <Link to={`/empresas/${ej.id_ej}`} className="flex gap-3 rounded-lg p-3 no-underline hover:bg-white/5 border border-white/5">
                                <EjLogo nome={ej.nome} fotoUrl={ej.foto_url} sizeClassName="w-10 h-10" />
                                <div className="min-w-0 flex-1">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="font-medium text-white truncate">{ej.nome}</span>
                                        {ej.gravidade && (
                                            <span className={`text-[10px] uppercase tracking-wider rounded border px-1.5 py-0.5 ${ESTILO_GRAVIDADE[ej.gravidade]}`}>
                                                {ROTULO_GRAVIDADE[ej.gravidade]}
                                            </span>
                                        )}
                                    </div>
                                    <ul className="mt-2 flex flex-wrap gap-1.5">
                                        {ej.motivos.map((m) => (
                                            <li key={m.codigo} className={`text-xs rounded-md border px-2 py-0.5 ${corMotivo}`}>{m.descricao}</li>
                                        ))}
                                    </ul>
                                    <p className="text-xs text-neutral-500 mt-2">
                                        Faturou {formatCurrency(ej.faturamento_mes)} no mês · {percentualBR(ej.percentual_meta)} da meta
                                    </p>
                                </div>
                            </Link>
                        </li>
                    ))}
                </ul>
            )}
            {itens.length > LIMITE_LISTA && (
                <button type="button" onClick={() => setTodas(!todas)} className="mt-4 text-sm text-accent-300 hover:text-white cursor-pointer">
                    {todas ? 'Mostrar menos' : `Ver todas (${itens.length})`}
                </button>
            )}
        </section>
    );
}
