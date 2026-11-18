import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useSessaoAdmin } from '../admin/useAdmin';
import { destinoDoOnboarding } from './onboardingStorage';
import { indiceDoParametro, passosVisiveis, posicionarCartao, recorteDoAlvo } from './passosDoTour';
import type { Retangulo, Tamanho } from './passosDoTour';

const ESPERA_MAXIMA_MS = 4000;

function reduzMovimento() {
    return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

function primeiroVisivel(alvos: string[]): HTMLElement | null {
    for (const alvo of alvos) {
        for (const elemento of document.querySelectorAll<HTMLElement>(`[data-tour="${alvo}"]`)) {
            const caixa = elemento.getBoundingClientRect();
            if (caixa.width > 0 && caixa.height > 0) return elemento;
        }
    }
    return null;
}

function janelaAtual(): Tamanho {
    return { width: window.innerWidth, height: window.innerHeight };
}

/**
 * Tour guiado: `?tour=N` na URL mantém o passo ao recarregar. Cada passo abre a
 * tela do roteiro, escurece o resto e destaca o elemento marcado com `data-tour`.
 * Setas do teclado avançam e voltam; Esc encerra. Nada aqui altera dados.
 */
export default function TourGuiado() {
    const [params] = useSearchParams();
    const location = useLocation();
    const navigate = useNavigate();
    const { data: sessao } = useSessaoAdmin();
    const passos = useMemo(() => passosVisiveis(Boolean(sessao?.pode_administrar)), [sessao?.pode_administrar]);
    const indice = indiceDoParametro(params.get('tour'), passos.length);
    const passo = indice === null ? null : passos[indice];
    const retorno = destinoDoOnboarding((location.state as { from?: unknown } | null)?.from);

    // Resultado da busca do alvo, marcado com o passo a que pertence: ao trocar
    // de passo, o resultado antigo deixa de valer sem precisar ser apagado.
    const chave = passo ? `${indice}:${passo.rota}` : '';
    const [busca, setBusca] = useState<{ chave: string; elemento: HTMLElement | null } | null>(null);
    const elemento = busca?.chave === chave ? busca.elemento : null;
    const procurando = busca?.chave !== chave;
    const [medida, setMedida] = useState<{ elemento: HTMLElement; caixa: Retangulo | null } | null>(null);
    const alvo = medida && medida.elemento === elemento ? medida.caixa : null;
    const [janela, setJanela] = useState<Tamanho>(() => typeof window === 'undefined' ? { width: 1280, height: 800 } : janelaAtual());
    const [cartao, setCartao] = useState<Tamanho>({ width: 360, height: 240 });
    const refTitulo = useRef<HTMLHeadingElement>(null);
    const observadorCartao = useRef<ResizeObserver | null>(null);
    const refCartao = useCallback((no: HTMLDivElement | null) => {
        observadorCartao.current?.disconnect();
        if (!no || typeof ResizeObserver === 'undefined') return;
        observadorCartao.current = new ResizeObserver(([entrada]) => {
            const { width, height } = entrada.target.getBoundingClientRect();
            setCartao(atual => Math.abs(atual.width - width) > 1 || Math.abs(atual.height - height) > 1 ? { width, height } : atual);
        });
        observadorCartao.current.observe(no);
    }, []);

    const ir = useCallback((proximo: number) => {
        navigate(`${passos[proximo].rota}?tour=${proximo}`, { replace: true, state: { from: retorno } });
    }, [navigate, passos, retorno]);
    const encerrar = useCallback(() => {
        navigate('/onboarding', { replace: true, state: { etapa: 1, from: retorno } });
    }, [navigate, retorno]);
    const avancar = useCallback(() => {
        if (indice === null) return;
        if (indice < passos.length - 1) ir(indice + 1); else encerrar();
    }, [indice, passos.length, ir, encerrar]);
    const voltar = useCallback(() => { if (indice) ir(indice - 1); }, [indice, ir]);

    // Abre a tela do passo e procura o alvo enquanto a página carrega.
    useEffect(() => {
        if (!passo) return;
        if (location.pathname !== passo.rota) {
            navigate(`${passo.rota}?tour=${indice}`, { replace: true, state: { from: retorno } });
            return;
        }
        // A tela pode estar carregando dados: tenta a cada 50 ms, por até 4 s.
        const inicio = Date.now();
        let espera = 0;
        const procurar = () => {
            const encontrado = primeiroVisivel(passo.alvos);
            if (encontrado) {
                encontrado.scrollIntoView({ block: 'center', inline: 'nearest', behavior: reduzMovimento() ? 'auto' : 'smooth' });
                setBusca({ chave, elemento: encontrado });
            } else if (Date.now() - inicio > ESPERA_MAXIMA_MS) {
                setBusca({ chave, elemento: null }); // segue sem destaque: o cartão fica centralizado
            } else {
                espera = window.setTimeout(procurar, 50);
            }
        };
        espera = window.setTimeout(procurar, 0);
        return () => window.clearTimeout(espera);
    }, [passo, indice, chave, location.pathname, navigate, retorno]);

    // Acompanha rolagem, redimensionamento e mudanças de tamanho do alvo.
    useEffect(() => {
        if (!elemento) return;
        const medir = () => {
            setJanela(janelaAtual());
            const caixa = elemento.getBoundingClientRect();
            const visivel = elemento.isConnected && caixa.width > 0 && caixa.height > 0;
            setMedida({ elemento, caixa: visivel ? { top: caixa.top, left: caixa.left, width: caixa.width, height: caixa.height } : null });
        };
        // A rolagem suave até o alvo leva alguns quadros; mede de novo ao terminar.
        const inicial = window.setTimeout(medir, 0);
        const aposRolagem = window.setTimeout(medir, 450);
        window.addEventListener('resize', medir);
        window.addEventListener('scroll', medir, true);
        const observador = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(medir) : null;
        observador?.observe(elemento);
        return () => {
            window.clearTimeout(inicial);
            window.clearTimeout(aposRolagem);
            window.removeEventListener('resize', medir);
            window.removeEventListener('scroll', medir, true);
            observador?.disconnect();
        };
    }, [elemento]);

    // Sem alvo, o cartão centralizado ainda acompanha o tamanho da janela.
    useEffect(() => {
        const aoRedimensionar = () => setJanela(janelaAtual());
        window.addEventListener('resize', aoRedimensionar);
        return () => window.removeEventListener('resize', aoRedimensionar);
    }, []);

    useEffect(() => { if (passo && !procurando) refTitulo.current?.focus({ preventScroll: true }); }, [passo, procurando]);

    useEffect(() => {
        if (!passo) return;
        function teclas(evento: KeyboardEvent) {
            if (evento.key === 'ArrowRight') { evento.preventDefault(); avancar(); }
            else if (evento.key === 'ArrowLeft') { evento.preventDefault(); voltar(); }
            else if (evento.key === 'Escape') { evento.preventDefault(); encerrar(); }
        }
        window.addEventListener('keydown', teclas);
        return () => window.removeEventListener('keydown', teclas);
    }, [passo, avancar, voltar, encerrar]);

    if (!passo || indice === null) return null;

    const recorte = alvo ? recorteDoAlvo(alvo, janela) : null;
    // Pronto quando o alvo foi medido, ou quando a busca terminou sem alvo.
    const pronto = !procurando && (elemento === null || alvo !== null);
    const posicao = posicionarCartao(pronto ? recorte : null, janela, cartao);
    const ultimo = indice === passos.length - 1;
    const largura = Math.min(380, janela.width - 32);

    return createPortal(<div className="fixed inset-0 z-[80]" data-tour-ativo="">
        {/* Bloqueia cliques no portal durante o tour; sem alvo, escurece tudo. */}
        <div className={`absolute inset-0 ${recorte ? '' : 'bg-slate-950/75'}`} aria-hidden="true" />
        {recorte && <div aria-hidden="true"
            className="pointer-events-none absolute rounded-xl ring-2 ring-primary-400 transition-all duration-300 ease-out motion-reduce:transition-none"
            style={{ ...recorte, boxShadow: '0 0 0 9999px rgba(2, 6, 23, 0.75)' }} />}
        <div ref={refCartao} role="dialog" aria-modal="true" aria-labelledby="tour-titulo" aria-describedby="tour-texto"
            className={`absolute rounded-2xl border border-white/10 bg-neutral-900 p-5 text-white shadow-2xl transition-[top,left,opacity] duration-300 ease-out motion-reduce:transition-none ${pronto ? 'opacity-100' : 'opacity-0'}`}
            style={{ top: posicao.top, left: posicao.left, width: largura }}>
            <p className="text-xs font-semibold text-primary-300">Passo {indice + 1} de {passos.length}</p>
            <h2 ref={refTitulo} tabIndex={-1} id="tour-titulo" className="mt-1 text-lg font-semibold focus:outline-none">{passo.titulo}</h2>
            <p id="tour-texto" className="mt-2 text-sm leading-relaxed text-neutral-300">{passo.texto}</p>
            <div className="mt-4 flex gap-1.5" aria-hidden="true">
                {passos.map((p, i) => <span key={p.id} className={`h-1.5 rounded-full transition-all motion-reduce:transition-none ${i === indice ? 'w-5 bg-primary-400' : i < indice ? 'w-1.5 bg-primary-400/60' : 'w-1.5 bg-white/20'}`} />)}
            </div>
            <div className="mt-4 flex items-center justify-between gap-2">
                <button type="button" onClick={encerrar} className="rounded-lg px-2 py-2 text-sm text-neutral-400 hover:text-white">Pular tour</button>
                <div className="flex items-center gap-2">
                    <button type="button" onClick={voltar} disabled={indice === 0} aria-label="Passo anterior"
                        className="flex h-10 w-10 items-center justify-center rounded-full border border-white/15 text-lg hover:bg-white/10 disabled:opacity-30">←</button>
                    <button type="button" onClick={avancar} aria-label={ultimo ? 'Concluir o tour' : 'Próximo passo'}
                        className={`flex h-10 items-center justify-center rounded-full bg-primary-600 text-lg font-semibold text-white hover:bg-primary-500 ${ultimo ? 'px-4 text-sm' : 'w-10'}`}>{ultimo ? 'Personalizar' : '→'}</button>
                </div>
            </div>
        </div>
    </div>, document.body);
}
