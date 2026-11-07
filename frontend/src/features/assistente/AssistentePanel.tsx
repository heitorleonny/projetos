import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { createPortal } from 'react-dom';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';
import NexoMascot from '../../components/NexoMascot';
import { useAssistente } from './useAssistente';
import ResultadoConsulta from './ResultadoConsulta';

const exemplos = [
    { titulo: 'Quem já saiu do zero?', pergunta: 'Quais EJs estão fora do zero no último mês disponível?', detalhe: 'Acompanhe o faturamento das EJs' },
    { titulo: 'Como está nossa rede?', pergunta: 'Quais são os indicadores da rede?', detalhe: 'Veja os principais indicadores' },
    { titulo: 'Quais EJs lideram?', pergunta: 'Top 10 EJs por faturamento', detalhe: 'Explore o ranking de faturamento' },
];

export default function AssistentePanel({ aberto, fechar }: { aberto: boolean; fechar: () => void }) {
    const [pergunta, setPergunta] = useState('');
    const { mensagens, enviando, enviar, interromper, limpar } = useAssistente();
    const { nome, anoDefault } = useFederacaoBranding();
    const painel = useRef<HTMLDialogElement>(null);
    const titulo = useRef<HTMLHeadingElement>(null);
    const campo = useRef<HTMLTextAreaElement>(null);
    const fim = useRef<HTMLDivElement>(null);
    const ultima = mensagens.at(-1);
    const contextoAtivo = [...mensagens].reverse().find(mensagem => mensagem.resposta?.contexto)?.resposta?.contexto;

    useEffect(() => {
        const dialogo = painel.current;
        if (aberto && !dialogo?.open) { dialogo?.showModal(); titulo.current?.focus(); }
        if (!aberto && dialogo?.open) dialogo.close();
    }, [aberto]);
    useEffect(() => { if (aberto) fim.current?.scrollIntoView({ block: 'nearest' }); }, [mensagens, enviando, aberto]);

    function perguntar(texto: string) {
        if (texto.trim().length < 3 || enviando) return;
        void enviar(texto.trim());
        setPergunta('');
    }
    function submeter(evento: FormEvent) { evento.preventDefault(); perguntar(pergunta); }

    return createPortal(
        <dialog ref={painel} id="assistente-rede" aria-labelledby="assistente-titulo"
            onCancel={evento => { evento.preventDefault(); fechar(); }}
            onClick={evento => {
                if (evento.target !== painel.current) return;
                const area = painel.current.getBoundingClientRect();
                if (evento.clientX < area.left || evento.clientX > area.right || evento.clientY < area.top || evento.clientY > area.bottom) fechar();
            }}
            className="fixed inset-auto bottom-0 right-0 m-0 h-[92dvh] max-h-[850px] w-full max-w-none overflow-hidden rounded-t-2xl border border-neutral-700 bg-neutral-900 p-0 text-white shadow-2xl backdrop:bg-black/60 sm:bottom-5 sm:right-5 sm:h-[min(780px,calc(100dvh-2.5rem))] sm:w-[520px] sm:rounded-2xl">
            <div className="flex h-full flex-col">
                <header className="flex shrink-0 items-center gap-3 border-b border-neutral-700/70 bg-neutral-800/50 px-5 py-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-primary-400/30 bg-primary-500/15"><NexoMascot size={40} className="text-primary-300" /></div>
                    <div className="min-w-0 flex-1">
                        <h2 ref={titulo} tabIndex={-1} id="assistente-titulo" className="text-base font-semibold outline-none">Nexo</h2>
                        <p className="mt-0.5 truncate text-xs text-neutral-400">Pergunte à sua rede · {nome}</p>
                    </div>
                    <button type="button" onClick={() => { limpar(); setPergunta(''); }} disabled={mensagens.length === 0 && !pergunta} className="rounded-lg px-2 py-2 text-xs text-neutral-300 hover:bg-neutral-700 disabled:opacity-30" title="Apagar esta conversa">Limpar</button>
                    <button type="button" onClick={fechar} aria-label="Fechar Nexo" className="rounded-lg px-3 py-2 text-xl text-neutral-300 hover:bg-neutral-700">×</button>
                </header>
                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5">
                    {mensagens.length === 0 && <div className="space-y-6">
                        <div className="pb-1 pt-1">
                            <NexoMascot size={48} className="mb-3 text-primary-300" />
                            <h3 className="text-xl font-semibold text-white">Consultar dados da rede</h3>
                            <p className="mt-3 text-sm leading-relaxed text-neutral-400">Consulte EJs, faturamento, indicadores e rankings de {nome}. Escolha um exemplo ou escreva uma pergunta com mês, ano e cluster.</p>
                        </div>
                        <div className="space-y-2">
                            {exemplos.map(exemplo => <button type="button" key={exemplo.titulo} onClick={() => perguntar(exemplo.pergunta)} className="group flex w-full items-center justify-between gap-3 rounded-xl border border-neutral-700 bg-neutral-800/40 p-4 text-left transition hover:border-primary-400/50 hover:bg-primary-500/10">
                                <span><span className="block text-sm font-medium text-neutral-100">{exemplo.titulo}</span><span className="mt-1 block text-xs text-neutral-400">{exemplo.detalhe}</span></span><span aria-hidden="true" className="text-primary-200">↗</span>
                            </button>)}
                        </div>
                        <p className="text-xs leading-relaxed text-neutral-500">Para um período específico, inclua mês e ano. Exemplo: “faturamento em setembro de {anoDefault}”. Depois, você pode continuar com “e em agosto?”.</p>
                    </div>}
                    <div role="log" aria-label="Conversa com Nexo" aria-live="polite" aria-relevant="additions text" className="space-y-6">
                        {mensagens.map(mensagem => <article key={mensagem.id} className="space-y-3">
                            <div className="ml-8 rounded-2xl rounded-tr-sm border border-primary-400/20 bg-primary-500/15 px-4 py-3"><p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-primary-200">Você</p><p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-neutral-100">{mensagem.pergunta}</p></div>
                            {(mensagem.resposta || mensagem.erro || mensagem.interrompida) && <div className="rounded-2xl rounded-tl-sm border border-neutral-700/60 bg-neutral-800/20 p-4">
                                <p className="mb-3 text-[10px] font-medium uppercase tracking-wider text-primary-200">Nexo</p>
                                {mensagem.resposta && <ResultadoConsulta resposta={mensagem.resposta} fechar={fechar} escolher={perguntar} enviando={enviando} />}
                                {mensagem.erro && <p className="text-sm leading-relaxed text-red-200">{mensagem.erro}</p>}
                                {mensagem.interrompida && <p className="text-sm text-neutral-400">Consulta interrompida.</p>}
                                {(mensagem.erro || mensagem.interrompida) && <button type="button" disabled={enviando} onClick={() => void enviar(mensagem.pergunta, mensagem.id)} className="mt-3 rounded-lg border border-neutral-600 px-3 py-2 text-xs text-neutral-200 hover:bg-neutral-700 disabled:opacity-40">Tentar novamente</button>}
                            </div>}
                        </article>)}
                    </div>
                    {enviando && <div role="status" className="mt-4 flex items-center gap-3 text-sm text-neutral-300"><span className="h-4 w-4 rounded-full border-2 border-primary-300 border-t-transparent motion-safe:animate-spin" aria-hidden="true" />Consultando os dados da rede…</div>}
                    {!enviando && ultima?.resposta?.sugestoes && <div className="mt-4 flex flex-wrap gap-2">{ultima.resposta.sugestoes.slice(0, 3).map(sugestao => <button type="button" key={sugestao} onClick={() => perguntar(sugestao)} className="rounded-full border border-primary-400/30 px-3 py-2 text-xs text-primary-200 hover:bg-primary-500/10">{sugestao}</button>)}</div>}
                    <div ref={fim} />
                </div>
                <footer className="shrink-0 border-t border-neutral-700/70 bg-neutral-900 px-5 pb-4 pt-3">
                    {contextoAtivo && <div className="mb-2 flex flex-wrap gap-1 text-[10px] text-neutral-400" aria-label="Contexto para perguntas de continuação">
                        <span>Continuação:</span>{contextoAtivo.mes && <span>{String(contextoAtivo.mes).padStart(2, '0')}/{contextoAtivo.ano}</span>}
                        {contextoAtivo.cluster && <span>· cluster {contextoAtivo.cluster}</span>}{contextoAtivo.busca && <span>· nome {contextoAtivo.busca}</span>}
                        <span>· uma nova pergunta pode mudar os filtros</span>
                    </div>}
                    <form onSubmit={submeter} className="rounded-xl border border-neutral-600 bg-neutral-800/50 p-2 focus-within:border-primary-300">
                        <label htmlFor="pergunta-rede" className="sr-only">Pergunta aos dados da rede</label>
                        <textarea ref={campo} id="pergunta-rede" value={pergunta} onChange={evento => setPergunta(evento.target.value)} maxLength={1000} rows={2} placeholder="Pergunte sobre sua rede…" onKeyDown={evento => { if (evento.key === 'Enter' && !evento.shiftKey && !evento.nativeEvent.isComposing) { evento.preventDefault(); perguntar(pergunta); } }} className="block w-full resize-none bg-transparent px-2 py-1 text-sm leading-relaxed text-neutral-100 outline-none placeholder:text-neutral-500" />
                        <div className="flex items-center justify-between px-1 pt-1"><span className="text-[10px] text-neutral-500">Enter envia · Shift + Enter quebra linha</span>{enviando ? <button type="button" onClick={interromper} className="rounded-lg border border-neutral-500 px-3 py-2 text-xs text-neutral-200">Interromper</button> : <button type="submit" disabled={pergunta.trim().length < 3} className="rounded-lg bg-primary-600 px-4 py-2 text-xs font-semibold text-white hover:bg-primary-500 disabled:opacity-40">Enviar ↑</button>}</div>
                    </form>
                    <p className="mt-2 text-center text-[10px] leading-relaxed text-neutral-500">IA pode interpretar errado. Confira a fonte e o período. Sua pergunta é enviada ao provedor de IA.</p>
                </footer>
            </div>
        </dialog>, document.body,
    );
}
