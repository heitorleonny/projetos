import type { ReactNode } from 'react';
import type { ErroApi } from './adminService';

/* Peças visuais repetidas nas três abas do painel, no estilo das outras telas. */

export const inputClass =
    'w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder:text-neutral-500 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all disabled:opacity-50';

export const selectClass =
    'bg-neutral-900 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';

export const labelClass = 'text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2 block';

export const botaoPrimario =
    'btn-glow text-white font-medium text-sm py-2.5 px-5 rounded-lg cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';

export const botaoSecundario =
    'bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-medium py-2.5 px-5 rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';

export function Cartao({ titulo, descricao, acao, children }: {
    titulo: string;
    descricao?: string;
    acao?: ReactNode;
    children: ReactNode;
}) {
    return (
        <section className="glass-card rounded-2xl p-6 mb-6">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
                <div>
                    <h2 className="font-heading text-lg font-semibold text-white">{titulo}</h2>
                    {descricao && <p className="text-sm text-neutral-400 mt-1">{descricao}</p>}
                </div>
                {acao}
            </div>
            {children}
        </section>
    );
}

export function AvisoErro({ erro }: { erro: ErroApi | null }) {
    if (!erro) return null;
    return (
        <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
            <p>{erro.mensagem}</p>
            {erro.problemas.length > 0 && (
                <ul className="list-disc ml-5 mt-1 space-y-0.5">
                    {erro.problemas.map((p) => <li key={p}>{p}</li>)}
                </ul>
            )}
        </div>
    );
}

export function AvisoOk({ children }: { children: ReactNode }) {
    return (
        <div className="text-sm text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">
            {children}
        </div>
    );
}

type Tom = 'verde' | 'amarelo' | 'vermelho' | 'azul' | 'cinza';

const TONS: Record<Tom, string> = {
    verde: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    amarelo: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    vermelho: 'bg-red-500/10 text-red-300 border-red-500/30',
    azul: 'bg-primary-500/10 text-primary-300 border-primary-500/30',
    cinza: 'bg-white/5 text-neutral-400 border-white/10',
};

export function Selo({ tom, children, titulo }: { tom: Tom; children: ReactNode; titulo?: string }) {
    return (
        <span title={titulo} className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium whitespace-nowrap ${TONS[tom]}`}>
            {children}
        </span>
    );
}

export function Carregando({ linhas = 4 }: { linhas?: number }) {
    return (
        <div className="space-y-2 animate-pulse">
            {Array.from({ length: linhas }, (_, i) => <div key={i} className="h-10 bg-white/5 rounded-lg" />)}
        </div>
    );
}
