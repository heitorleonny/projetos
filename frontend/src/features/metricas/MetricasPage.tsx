import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { lerErro } from '../admin/adminService';
import { AvisoErro, botaoPrimario, botaoSecundario, Carregando, inputClass } from '../admin/ui';
import CartaoMetrica from './CartaoMetrica';
import ConstrutorMetrica from './ConstrutorMetrica';
import ResultadoView from './ResultadoMetrica';
import { definicaoPadrao, interpretar, type Catalogo, type Metrica, type MetricaEntrada, type PropostaMetrica } from './metricasService';
import { useAcaoMetrica, useCatalogo, useMetricas, useReordenar, useSalvarMetrica } from './useMetricas';

type Edicao = { inicial: MetricaEntrada; id?: number } | null;

const EXEMPLOS = [
    'Top 10 EJs que mais faturaram em outubro e novembro',
    'Crie a métrica Impacto comercial: faturamento vezes CSAT vezes projetos vendidos',
    'Faturamento total da rede por mês no segundo semestre',
];

function paraEntrada(m: Metrica): MetricaEntrada {
    return { nome: m.nome, descricao: m.descricao, visual: m.visual, no_painel: m.no_painel, definicao: m.definicao };
}

function TextoLivre({ catalogo, abrir }: { catalogo: Catalogo; abrir: (inicial: MetricaEntrada) => void }) {
    const [texto, setTexto] = useState('');
    const pedido = useMutation({ mutationFn: interpretar });
    const salvar = useSalvarMetrica();
    const proposta: PropostaMetrica | undefined = pedido.data;

    function enviar(valor = texto) {
        const limpo = valor.trim();
        if (limpo.length < 3) return;
        setTexto(limpo);
        salvar.reset();
        pedido.mutate(limpo);
    }

    return (
        <section data-tour="metricas-criar" className="glass-card mb-6 rounded-2xl p-5" aria-labelledby="texto-livre-titulo">
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 id="texto-livre-titulo" className="font-heading text-lg font-semibold text-white">Criar métrica</h2>
                    <p className="mt-1 text-sm text-neutral-400">Descreva em português o que quer acompanhar ou monte a fórmula no construtor. Nada é salvo sem a sua confirmação.</p>
                </div>
                <button type="button" className={botaoSecundario} onClick={() => abrir({ nome: '', descricao: null, visual: 'ranking', no_painel: true, definicao: definicaoPadrao(catalogo.ano) })}>
                    Abrir construtor
                </button>
            </div>
            <form onSubmit={e => { e.preventDefault(); enviar(); }} className="flex flex-col gap-2 sm:flex-row">
                <label htmlFor="texto-livre" className="sr-only">Pedido em texto livre</label>
                <input id="texto-livre" className={inputClass} value={texto} maxLength={500} onChange={e => setTexto(e.target.value)}
                    disabled={!catalogo.texto_livre_disponivel || pedido.isPending}
                    placeholder={catalogo.texto_livre_disponivel ? 'Ex.: top 10 EJs que mais faturaram em outubro e novembro' : 'Texto livre indisponível no servidor'} />
                <button className={`${botaoPrimario} shrink-0`} disabled={!catalogo.texto_livre_disponivel || pedido.isPending || texto.trim().length < 3}>
                    {pedido.isPending ? 'Interpretando…' : 'Interpretar'}
                </button>
            </form>
            {!catalogo.texto_livre_disponivel && (
                <p className="mt-2 text-xs text-neutral-500">O provedor de IA não está configurado no servidor. O construtor funciona normalmente.</p>
            )}
            {catalogo.texto_livre_disponivel && !proposta && !pedido.isError && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                    {EXEMPLOS.map(ex => (
                        <button key={ex} type="button" onClick={() => enviar(ex)}
                            className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-neutral-300 hover:bg-white/10">{ex}</button>
                    ))}
                </div>
            )}
            {pedido.isError && <div className="mt-3"><AvisoErro erro={lerErro(pedido.error)} /></div>}

            {proposta && proposta.status !== 'pronta' && (
                <div role="status" className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
                    <p>{proposta.mensagem}</p>
                    {proposta.opcoes.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                            {proposta.opcoes.map(op => (
                                <button key={op.texto} type="button" onClick={() => enviar(op.texto)}
                                    className="rounded-lg border border-amber-500/30 px-3 py-1.5 text-xs hover:bg-amber-500/10">{op.rotulo}</button>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {proposta?.status === 'pronta' && proposta.metrica && (
                <div role="status" className="mt-4 rounded-xl border border-primary-500/30 bg-primary-500/5 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-primary-300">Entendi assim · confira antes de salvar</p>
                    <h3 className="mt-2 font-heading text-base font-semibold text-white">{proposta.metrica.nome}</h3>
                    <p className="mt-1 text-sm text-neutral-300">{proposta.formula_legivel}</p>
                    {proposta.resultado && <div className="mt-4"><ResultadoView resultado={proposta.resultado} visual={proposta.metrica.visual} /></div>}
                    {salvar.isError && <div className="mt-3"><AvisoErro erro={lerErro(salvar.error)} /></div>}
                    <div className="mt-4 flex flex-wrap gap-2">
                        <button type="button" className={botaoPrimario} disabled={salvar.isPending}
                            onClick={async () => {
                                try { await salvar.mutateAsync({ dados: proposta.metrica! }); pedido.reset(); setTexto(''); }
                                catch { /* erro mostrado acima */ }
                            }}>
                            {salvar.isPending ? 'Salvando…' : 'Salvar no painel'}
                        </button>
                        <button type="button" className={botaoSecundario} onClick={() => { abrir(proposta.metrica!); pedido.reset(); }}>Ajustar no construtor</button>
                        <button type="button" className={botaoSecundario} onClick={() => pedido.reset()}>Descartar</button>
                    </div>
                    {proposta.modelo && <p className="mt-3 text-xs text-neutral-500">Interpretado por {proposta.modelo}. Os números vêm do portal, não do modelo.</p>}
                </div>
            )}
        </section>
    );
}

function Gerenciar({ foraDoPainel, editar }: { foraDoPainel: Metrica[]; editar: (m: Metrica) => void }) {
    const [verArquivadas, setVerArquivadas] = useState(false);
    const arquivadas = useMetricas(true, verArquivadas);
    const acao = useAcaoMetrica();
    const linha = 'flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 px-4 py-3';
    const pequeno = 'rounded-lg border border-white/10 px-3 py-1.5 text-xs text-neutral-200 hover:bg-white/5 disabled:opacity-40';

    return (
        <section className="mt-8 space-y-6" aria-label="Gerenciar métricas">
            {acao.isError && <AvisoErro erro={lerErro(acao.error)} />}
            <div>
                <h2 className="mb-3 font-heading text-base font-semibold text-white">Fora do painel ({foraDoPainel.length})</h2>
                {foraDoPainel.length === 0
                    ? <p className="text-sm text-neutral-500">Todas as métricas ativas estão no painel.</p>
                    : <ul className="space-y-2">{foraDoPainel.map(m => (
                        <li key={m.id} className={linha}>
                            <div className="min-w-0"><p className="truncate text-sm font-medium text-white">{m.nome}</p><p className="truncate text-xs text-neutral-400">{m.formula_legivel}</p></div>
                            <div className="flex flex-wrap gap-1.5">
                                <button className={pequeno} disabled={acao.isPending} onClick={() => acao.mutate({ id: m.id, acao: 'colocar' })}>Colocar no painel</button>
                                <button className={pequeno} onClick={() => editar(m)}>Editar</button>
                                <button className={`${pequeno} text-red-300`} disabled={acao.isPending}
                                    onClick={() => window.confirm(`Arquivar "${m.nome}"?`) && acao.mutate({ id: m.id, acao: 'arquivar' })}>Arquivar</button>
                            </div>
                        </li>))}
                    </ul>}
            </div>
            <details onToggle={e => setVerArquivadas((e.target as HTMLDetailsElement).open)}>
                <summary className="cursor-pointer font-heading text-base font-semibold text-white">Arquivadas</summary>
                <div className="mt-3">
                    {arquivadas.isLoading && <Carregando linhas={2} />}
                    {arquivadas.isError && <AvisoErro erro={lerErro(arquivadas.error)} />}
                    {arquivadas.data?.length === 0 && <p className="text-sm text-neutral-500">Nenhuma métrica arquivada.</p>}
                    <ul className="space-y-2">{arquivadas.data?.map(m => (
                        <li key={m.id} className={linha}>
                            <div className="min-w-0"><p className="truncate text-sm font-medium text-white">{m.nome}</p><p className="truncate text-xs text-neutral-400">{m.formula_legivel}</p></div>
                            <div className="flex flex-wrap gap-1.5">
                                <button className={pequeno} disabled={acao.isPending} onClick={() => acao.mutate({ id: m.id, acao: 'restaurar' })}>Restaurar</button>
                                <button className={`${pequeno} text-red-300`} disabled={acao.isPending}
                                    onClick={() => window.confirm(`Excluir "${m.nome}" de vez? Isso não pode ser desfeito.`) && acao.mutate({ id: m.id, acao: 'excluir' })}>
                                    Excluir de vez
                                </button>
                            </div>
                        </li>))}
                    </ul>
                </div>
            </details>
        </section>
    );
}

export default function MetricasPage() {
    const catalogo = useCatalogo();
    const metricas = useMetricas();
    const reordenar = useReordenar();
    const [edicao, setEdicao] = useState<Edicao>(null);

    if (catalogo.isLoading || metricas.isLoading) return <div className="glass-card rounded-2xl p-6"><Carregando /></div>;
    if (catalogo.isError) return <div className="glass-card rounded-2xl p-6"><AvisoErro erro={lerErro(catalogo.error)} /></div>;
    if (metricas.isError) return <div className="glass-card rounded-2xl p-6"><AvisoErro erro={lerErro(metricas.error)} /></div>;
    const cat = catalogo.data!;
    const ativas = metricas.data ?? [];
    const noPainel = ativas.filter(m => m.no_painel);
    const fora = ativas.filter(m => !m.no_painel);

    function mover(indice: number, direcao: -1 | 1) {
        const ids = noPainel.map(m => m.id);
        const alvo = indice + direcao;
        [ids[indice], ids[alvo]] = [ids[alvo], ids[indice]];
        reordenar.mutate([...ids, ...fora.map(m => m.id)]);
    }

    return (
        <div>
            <div className="mb-6">
                <h1 className="font-heading text-2xl font-semibold text-neutral-50">Métricas</h1>
                <p className="mt-2 text-sm text-neutral-400">
                    Métricas criadas pela sua federação para acompanhar {cat.ano}. São personalizadas: não substituem os indicadores oficiais do MEJ.
                    {!cat.pode_editar && ' Só administradores da federação criam ou alteram métricas.'}
                </p>
            </div>

            {cat.pode_editar && <TextoLivre catalogo={cat} abrir={inicial => setEdicao({ inicial })} />}
            {reordenar.isError && <div className="mb-4"><AvisoErro erro={lerErro(reordenar.error)} /></div>}

            <div data-tour="metricas-painel">
                {noPainel.length === 0 ? (
                    <div className="glass-card rounded-2xl p-8 text-center">
                        <p className="font-heading text-base font-semibold text-white">Nenhuma métrica no painel ainda</p>
                        <p className="mt-2 text-sm text-neutral-400">
                            {cat.pode_editar ? 'Descreva uma métrica acima ou abra o construtor para criar a primeira.' : 'Quando um administrador criar métricas, elas aparecem aqui.'}
                        </p>
                    </div>
                ) : (
                    <div className="grid gap-6 lg:grid-cols-2">
                        {noPainel.map((m, i) => (
                            <CartaoMetrica key={m.id} metrica={m} podeEditar={cat.pode_editar}
                                editar={metrica => setEdicao({ inicial: paraEntrada(metrica), id: metrica.id })}
                                mover={reordenar.isPending ? undefined : direcao => mover(i, direcao)} primeira={i === 0} ultima={i === noPainel.length - 1} />
                        ))}
                    </div>
                )}
            </div>

            {cat.pode_editar && <Gerenciar foraDoPainel={fora} editar={m => setEdicao({ inicial: paraEntrada(m), id: m.id })} />}

            {edicao && <ConstrutorMetrica key={edicao.id ?? 'nova'} catalogo={cat} inicial={edicao.inicial} id={edicao.id} fechar={() => setEdicao(null)} />}
        </div>
    );
}
