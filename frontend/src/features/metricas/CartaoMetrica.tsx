import { useRef } from 'react';
import { lerErro } from '../admin/adminService';
import { AvisoErro, Carregando, Selo } from '../admin/ui';
import ResultadoView from './ResultadoMetrica';
import type { Metrica } from './metricasService';
import { useAcaoMetrica, useResultado } from './useMetricas';

interface Props {
    metrica: Metrica;
    podeEditar: boolean;
    editar: (metrica: Metrica) => void;
    mover?: (direcao: -1 | 1) => void;
    primeira?: boolean;
    ultima?: boolean;
}

const botaoMenu = 'w-full rounded-lg px-3 py-2 text-left text-sm text-neutral-200 hover:bg-white/5 disabled:opacity-40';

export default function CartaoMetrica({ metrica, podeEditar, editar, mover, primeira, ultima }: Props) {
    const resultado = useResultado(metrica.id, metrica.versao);
    const acao = useAcaoMetrica();
    const menu = useRef<HTMLDetailsElement>(null);
    const fecharMenu = () => { if (menu.current) menu.current.open = false; };

    function executar(tipo: 'tirar' | 'arquivar', confirmacao?: string) {
        fecharMenu();
        if (confirmacao && !window.confirm(confirmacao)) return;
        acao.mutate({ id: metrica.id, acao: tipo });
    }

    return (
        <article className="glass-card flex min-w-0 flex-col rounded-2xl p-5" aria-labelledby={`metrica-${metrica.id}`}>
            <header className="mb-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <h2 id={`metrica-${metrica.id}`} className="font-heading text-base font-semibold text-white break-words">{metrica.nome}</h2>
                    {metrica.descricao && <p className="mt-1 text-sm text-neutral-400 break-words">{metrica.descricao}</p>}
                    <div className="mt-2 flex flex-wrap gap-1.5">
                        <Selo tom="cinza" titulo="Criada pela federação. Não é indicador oficial do MEJ.">Personalizada</Selo>
                        {metrica.definicao.cluster !== null && <Selo tom="azul">Cluster {metrica.definicao.cluster}</Selo>}
                    </div>
                </div>
                {podeEditar && (
                    <details ref={menu} className="relative shrink-0">
                        <summary aria-label={`Ações da métrica ${metrica.nome}`} className="cursor-pointer list-none rounded-lg border border-white/10 px-2.5 py-1.5 text-sm text-neutral-300 hover:bg-white/5">⋯</summary>
                        <div className="absolute right-0 z-20 mt-2 w-52 rounded-xl border border-neutral-700 bg-neutral-900 p-2 shadow-xl">
                            <button className={botaoMenu} onClick={() => { fecharMenu(); editar(metrica); }}>Editar</button>
                            {mover && <button className={botaoMenu} disabled={primeira} onClick={() => { fecharMenu(); mover(-1); }}>Mover para antes</button>}
                            {mover && <button className={botaoMenu} disabled={ultima} onClick={() => { fecharMenu(); mover(1); }}>Mover para depois</button>}
                            <button className={botaoMenu} disabled={acao.isPending} onClick={() => executar('tirar')}>Tirar do painel</button>
                            <button className={`${botaoMenu} text-red-300`} disabled={acao.isPending}
                                onClick={() => executar('arquivar', `Arquivar "${metrica.nome}"? Ela sai do painel e pode ser restaurada depois.`)}>
                                Arquivar
                            </button>
                        </div>
                    </details>
                )}
            </header>
            {acao.isError && <div className="mb-3"><AvisoErro erro={lerErro(acao.error)} /></div>}
            {resultado.isLoading && <Carregando linhas={3} />}
            {resultado.isError && <AvisoErro erro={lerErro(resultado.error)} />}
            {resultado.data && <ResultadoView resultado={resultado.data} visual={metrica.visual} />}
        </article>
    );
}
