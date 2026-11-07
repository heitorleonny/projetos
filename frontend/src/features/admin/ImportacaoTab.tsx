import { useMemo, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';
import { ultimosAnosDecrescente } from '../../utils/anos';
import { lerErro, type Carga, type ErroApi, type Federacao, type ResultadoImportacao, type Sessao } from './adminService';
import { useCargas, useImportarPlanilha } from './useAdmin';
import {
    AvisoErro, AvisoOk, Cartao, Carregando, Selo, botaoPrimario, botaoSecundario,
    inputClass, labelClass, selectClass,
} from './ui';
import { dataHora, numero } from './formatacao';

const NACIONAL = '';

/**
 * Importação da planilha do Portal BJ em dois passos: SIMULAR (a carga roda
 * inteira no banco e é desfeita, então as contagens são as reais) e GRAVAR.
 * Gravar só fica disponível para o mesmo arquivo, ano e escopo que acabaram
 * de ser simulados.
 */
export default function ImportacaoTab({ sessao, federacoes }: { sessao: Sessao; federacoes: Federacao[] }) {
    const { anoDefault } = useFederacaoBranding();
    const [arquivo, setArquivo] = useState<File | null>(null);
    const [ano, setAno] = useState(anoDefault);
    const [slug, setSlug] = useState(() => federacoes.find(f => f.id === sessao.federacao_id)?.slug ?? '__propria__');
    const [simulado, setSimulado] = useState<ResultadoImportacao | null>(null);
    const [gravado, setGravado] = useState<ResultadoImportacao | null>(null);
    const [erro, setErro] = useState<ErroApi | null>(null);
    const campoArquivo = useRef<HTMLInputElement>(null);

    const importar = useImportarPlanilha();
    const cargas = useCargas();

    const nomePorId = useMemo(() => new Map(federacoes.map((f) => [f.id, f.nome])), [federacoes]);
    const propria = federacoes.find((f) => f.id === sessao.federacao_id);

    const limparResultado = () => {
        setSimulado(null);
        setGravado(null);
        setErro(null);
    };

    const enviar = (simular: boolean) => {
        if (!arquivo) return;
        setErro(null);
        importar.mutate(
            { arquivo, ano, simular, federacaoSlug: sessao.eh_plataforma ? (slug === '__propria__' ? propria?.slug : slug || undefined) : undefined },
            {
                onSuccess: (resultado) => {
                    if (simular) {
                        setSimulado(resultado);
                    } else {
                        setGravado(resultado);
                        setSimulado(null);
                        setArquivo(null);
                        if (campoArquivo.current) campoArquivo.current.value = '';
                    }
                },
                onError: (e) => setErro(lerErro(e)),
            },
        );
    };

    const onSimular = (e: FormEvent) => {
        e.preventDefault();
        setGravado(null);
        enviar(true);
    };

    const escopoTexto = sessao.eh_plataforma
        ? (slug ? federacoes.find((f) => f.slug === slug)?.nome ?? slug : 'todas as federações')
        : (propria?.nome ?? 'sua federação');

    return (
        <>
            <Cartao
                titulo="Atualizar dados por planilha"
                descricao="Use apenas a exportação de monitoramento acumulado do Portal BJ (.xlsx, aba EMPRESAS_JUNIORES). Um arquivo por ano alimenta cadastro, metas, indicadores e comparação. Uma exportação mais recente corrige os meses anteriores sem duplicar dados."
            >
                <form onSubmit={onSimular} className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1.5fr_auto] gap-4 items-end">
                    <div>
                        <label htmlFor="arquivo" className={labelClass}>Arquivo</label>
                        <input
                            id="arquivo"
                            ref={campoArquivo}
                            type="file"
                            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            onChange={(e) => { setArquivo(e.target.files?.[0] ?? null); limparResultado(); }}
                            className={`${inputClass} file:mr-3 file:rounded-md file:border-0 file:bg-primary-600 file:px-3 file:py-1 file:text-white file:text-xs cursor-pointer`}
                            required
                        />
                    </div>
                    <div>
                        <label htmlFor="ano" className={labelClass}>Ano</label>
                        <select id="ano" value={ano} onChange={(e) => { setAno(Number(e.target.value)); limparResultado(); }} className={`${selectClass} w-full`}>
                            {ultimosAnosDecrescente(anoDefault, 4).map((a) => <option key={a} value={a}>{a}</option>)}
                        </select>
                    </div>
                    <div>
                        <label htmlFor="escopo" className={labelClass}>Federação</label>
                        {sessao.eh_plataforma ? (
                            <select id="escopo" value={slug} onChange={(e) => { setSlug(e.target.value); limparResultado(); }} className={`${selectClass} w-full`}>
                                <option value="__propria__">Minha federação</option><option value={NACIONAL}>Todas — somente administrador master</option>
                                {federacoes.map((f) => <option key={f.id} value={f.slug}>{f.nome}</option>)}
                            </select>
                        ) : (
                            <div className={`${inputClass} text-neutral-300`}>{propria?.nome ?? 'Sua federação'}</div>
                        )}
                    </div>
                    <button type="submit" disabled={!arquivo || importar.isPending} className={botaoSecundario}>
                        {importar.isPending && importar.variables?.simular ? 'Simulando…' : '1. Simular'}
                    </button>
                </form>

                {sessao.eh_plataforma && <p className="mt-3 rounded-lg border border-amber-500/30 p-3 text-sm text-amber-200">Sua conta é administrador master. Apenas esse papel pode importar para outras federações ou executar uma carga nacional.</p>}
                {!sessao.eh_plataforma && (
                    <p className="text-xs text-neutral-500 mt-3">
                        Pode enviar a exportação nacional: só as linhas de {propria?.nome ?? 'sua federação'} são aplicadas, as outras são ignoradas.
                    </p>
                )}
                <p className="text-xs text-neutral-500 mt-3">
                    Para comparar anos, envie o acumulado de cada ano. Sem a série de um ano, a comparação deixa seus valores em branco.
                </p>

                <div className="mt-5 space-y-4">
                    <AvisoErro erro={erro} />

                    {simulado && (
                        <ResumoRelatorio resultado={simulado} titulo={`Simulação — ${escopoTexto}, ${ano}. Nada foi gravado.`}>
                            <div className="flex flex-wrap items-center gap-3 pt-2">
                                <button type="button" disabled={importar.isPending} onClick={() => enviar(false)} className={botaoPrimario}>
                                    {importar.isPending && !importar.variables?.simular ? 'Gravando…' : '2. Gravar estes dados'}
                                </button>
                                <span className="text-xs text-neutral-500">Tudo ou nada: se o banco recusar qualquer linha, nada é gravado.</span>
                            </div>
                        </ResumoRelatorio>
                    )}

                    {gravado && (
                        <>
                            <AvisoOk>
                                Carga #{gravado.relatorio.carga_id} gravada
                                {gravado.relatorio.reenvio_de ? ` (mesmo arquivo da carga #${gravado.relatorio.reenvio_de})` : ''}.
                                As telas do portal já mostram os dados novos.
                            </AvisoOk>
                            <ResumoRelatorio resultado={gravado} titulo="O que foi gravado" />
                        </>
                    )}
                </div>
            </Cartao>

            <Cartao titulo="Cargas anteriores" descricao="As 50 mais recentes, inclusive as que falharam.">
                {cargas.isLoading ? <Carregando /> : cargas.isError ? (
                    <AvisoErro erro={lerErro(cargas.error)} />
                ) : (cargas.data ?? []).length === 0 ? (
                    <p className="text-sm text-neutral-400">Nenhuma carga registrada ainda.</p>
                ) : (
                    <TabelaCargas cargas={cargas.data ?? []} nomePorId={nomePorId} />
                )}
            </Cartao>
        </>
    );
}

function ResumoRelatorio({ resultado, titulo, children }: {
    resultado: ResultadoImportacao;
    titulo: string;
    children?: ReactNode;
}) {
    const r = resultado.relatorio;
    const meses = r.meses.length > 1 ? `${r.meses[0]} a ${r.meses[r.meses.length - 1]}` : String(r.meses[0] ?? '—');
    const indicadores = [
        { rotulo: 'Linhas aplicadas', valor: numero(r.linhas_aplicadas), extra: `de ${numero(r.linhas_lidas)} lidas` },
        { rotulo: 'EJs', valor: numero(r.ejs), extra: `${r.federacoes.length} federação(ões)` },
        { rotulo: 'Meses', valor: meses, extra: r.exportado_em ? `exportado em ${r.exportado_em.split('-').reverse().join('/')}` : 'data não identificada' },
        { rotulo: 'Ignoradas', valor: numero(r.linhas_ignoradas), extra: 'fora do recorte' },
    ];

    return (
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-4">
            <p className="text-sm font-medium text-white">{titulo}</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {indicadores.map((i) => (
                    <div key={i.rotulo} className="rounded-lg bg-white/5 px-3 py-2">
                        <div className="text-[11px] uppercase tracking-wider text-neutral-500">{i.rotulo}</div>
                        <div className="text-lg font-heading font-semibold text-white tabular-nums">{i.valor}</div>
                        <div className="text-xs text-neutral-500">{i.extra}</div>
                    </div>
                ))}
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-left text-xs uppercase tracking-wider text-neutral-500">
                            <th className="py-2 pr-4 font-medium">Tabela</th>
                            <th className="py-2 pr-4 font-medium text-right">Novas</th>
                            <th className="py-2 pr-4 font-medium text-right">Atualizadas</th>
                            <th className="py-2 pr-4 font-medium text-right">Sem mudança</th>
                        </tr>
                    </thead>
                    <tbody className="tabular-nums">
                        {Object.entries(r.tabelas).map(([nome, c]) => (
                            <tr key={nome} className="border-t border-white/5">
                                <td className="py-2 pr-4 text-neutral-300 font-mono text-xs">{nome}</td>
                                <td className="py-2 pr-4 text-right text-white">{numero(c.novas)}</td>
                                <td className="py-2 pr-4 text-right text-white">{numero(c.atualizadas)}</td>
                                <td className="py-2 pr-4 text-right text-neutral-400">{numero(c.inalteradas)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {(r.avisos.length > 0 || r.nucleos_criados.length > 0) && (
                <div className="text-sm text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
                    <p className="font-medium mb-1">Avisos</p>
                    <ul className="list-disc ml-5 space-y-0.5">
                        {r.nucleos_criados.map((n) => <li key={n}>Núcleo criado sem ID do Portal BJ: {n}</li>)}
                        {r.avisos.map((a) => <li key={a}>{a}</li>)}
                    </ul>
                </div>
            )}

            <details className="text-xs">
                <summary className="cursor-pointer text-neutral-400 hover:text-white">Relatório completo (o mesmo da linha de comando)</summary>
                <pre className="mt-2 max-h-80 overflow-auto rounded-lg bg-black/40 p-3 text-neutral-300 whitespace-pre-wrap">{resultado.texto}</pre>
            </details>

            {children}
        </div>
    );
}

const STATUS_CARGA: Record<Carga['status'], { tom: 'verde' | 'amarelo' | 'vermelho'; rotulo: string }> = {
    sucesso: { tom: 'verde', rotulo: 'Sucesso' },
    rejeitada: { tom: 'amarelo', rotulo: 'Rejeitada' },
    erro: { tom: 'vermelho', rotulo: 'Erro' },
};

function TabelaCargas({ cargas, nomePorId }: { cargas: Carga[]; nomePorId: Map<number, string> }) {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="text-left text-xs uppercase tracking-wider text-neutral-500">
                        <th className="py-2 pr-4 font-medium">#</th>
                        <th className="py-2 pr-4 font-medium">Quando</th>
                        <th className="py-2 pr-4 font-medium">Arquivo</th>
                        <th className="py-2 pr-4 font-medium">Escopo</th>
                        <th className="py-2 pr-4 font-medium">Origem</th>
                        <th className="py-2 pr-4 font-medium text-right">Aplicadas</th>
                        <th className="py-2 pr-4 font-medium">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {cargas.map((c) => (
                        <tr key={c.id} className="border-t border-white/5 align-top">
                            <td className="py-2 pr-4 text-neutral-500 tabular-nums">{c.id}</td>
                            <td className="py-2 pr-4 text-neutral-300 whitespace-nowrap">{dataHora(c.carregado_em)}</td>
                            <td className="py-2 pr-4 text-neutral-300 max-w-[260px] truncate" title={c.arquivo_nome}>
                                {c.arquivo_nome}
                                <span className="text-neutral-500"> · {c.ano}</span>
                            </td>
                            <td className="py-2 pr-4 text-neutral-300">
                                {c.escopo === 'nacional' ? 'Nacional' : nomePorId.get(c.federacao_id ?? -1) ?? `Federação ${c.federacao_id}`}
                            </td>
                            <td className="py-2 pr-4 text-neutral-400">{c.origem === 'upload' ? 'Painel' : 'Linha de comando'}</td>
                            <td className="py-2 pr-4 text-right text-white tabular-nums">{numero(c.linhas_aplicadas)}</td>
                            <td className="py-2 pr-4">
                                <Selo tom={STATUS_CARGA[c.status].tom} titulo={c.mensagem_erro ?? undefined}>
                                    {STATUS_CARGA[c.status].rotulo}
                                </Selo>
                                {c.reenvio_de && <span className="ml-2 text-xs text-neutral-500">reenvio de #{c.reenvio_de}</span>}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
