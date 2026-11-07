import { NavLink, useLocation } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/useAuth';
import { ENV } from '../config/env';
import { abasDoPortal } from '../config/navigation';
import { useFederacaoBranding } from '../branding/useFederacaoBranding';
import { useSessaoAdmin } from '../features/admin/useAdmin';

const principais = abasDoPortal.filter(aba => aba.grupo === 'principal');
const analises = abasDoPortal.filter(aba => aba.grupo === 'analises');
const estiloLink = ({ isActive }: { isActive: boolean }) => `block rounded-lg px-3 py-2 text-sm font-medium no-underline ${isActive ? 'text-accent-300 bg-secondary-500/20' : 'text-neutral-300 hover:text-white hover:bg-white/5'}`;

export default function Navbar() {
    const { user, signOut } = useAuth();
    const { branding, nome, nomeDoPortal } = useFederacaoBranding();
    const { data: sessao } = useSessaoAdmin();
    const location = useLocation();
    const nav = useRef<HTMLElement>(null);
    const feedback = useRef<HTMLDialogElement>(null);
    const [saindo, setSaindo] = useState(false);
    const [erro, setErro] = useState('');

    useEffect(() => {
        nav.current?.querySelectorAll('details').forEach(menu => { menu.open = false; });
    }, [location]);
    useEffect(() => {
        function fechar(evento: PointerEvent) {
            nav.current?.querySelectorAll('details[open]').forEach(menu => {
                if (!menu.contains(evento.target as Node)) (menu as HTMLDetailsElement).open = false;
            });
        }
        document.addEventListener('pointerdown', fechar);
        return () => document.removeEventListener('pointerdown', fechar);
    }, []);
    function escape(evento: React.KeyboardEvent) {
        if (evento.key !== 'Escape') return;
        nav.current?.querySelectorAll('details[open]').forEach(menu => {
            (menu as HTMLDetailsElement).open = false;
            menu.querySelector('summary')?.focus();
        });
    }
    async function sair() {
        if (saindo) return;
        setSaindo(true); setErro('');
        try { await signOut(); }
        catch { setErro('Não foi possível sair. Tente novamente.'); }
        finally { setSaindo(false); }
    }
    function sugestao() {
        nav.current?.querySelectorAll('details').forEach(menu => { menu.open = false; });
        feedback.current?.showModal();
    }

    return <>
        <nav ref={nav} onKeyDown={escape} aria-label="Navegação principal" className="fixed inset-x-0 top-0 z-50 glass-nav h-16">
            <div className="mx-auto flex h-full max-w-[1280px] items-center justify-between gap-3 px-4 sm:px-6">
                <NavLink to="/dashboard" className="flex min-w-0 items-center gap-3 no-underline">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary-500">
                        {branding.logo_url ? <img src={branding.logo_url} alt={`Logo ${nome}`} className="h-6 w-6 object-contain" /> : <span className="font-heading text-sm font-bold">{nome.charAt(0).toUpperCase()}</span>}
                    </div>
                    <span className="hidden sm:block min-w-0">
                        <span className="block truncate font-heading text-base font-semibold text-white">{nomeDoPortal}</span>
                        <span className="block text-xs text-neutral-400">Gestão da rede</span>
                    </span>
                </NavLink>
                <div className="hidden lg:flex items-center gap-1">
                    {principais.map(aba => <NavLink key={aba.id} to={aba.to} className={estiloLink}>{aba.label}</NavLink>)}
                    <details className="relative">
                        <summary className={`cursor-pointer list-none rounded-lg px-3 py-2 text-sm font-medium ${analises.some(aba => aba.to === location.pathname) ? 'bg-secondary-500/20 text-accent-300' : 'text-neutral-300 hover:bg-white/5'}`}>Análises <span aria-hidden="true">⌄</span></summary>
                        <div className="absolute right-0 mt-2 w-60 rounded-xl border border-neutral-700 bg-neutral-900 p-2 shadow-xl">
                            {analises.map(aba => <NavLink key={aba.id} to={aba.to} className={estiloLink}>{aba.label}</NavLink>)}
                        </div>
                    </details>
                </div>
                <div className="flex items-center gap-2">
                    <details className="lg:hidden">
                        <summary aria-label="Abrir navegação" className="cursor-pointer list-none rounded-lg px-3 py-2 text-sm text-neutral-300 hover:bg-white/5">Abas <span aria-hidden="true">⌄</span></summary>
                        <div className="absolute inset-x-0 top-16 max-h-[calc(100dvh-5rem)] overflow-y-auto border-b border-neutral-700 bg-neutral-900 p-4 shadow-xl">
                            {principais.map(aba => <NavLink key={aba.id} to={aba.to} className={estiloLink}>{aba.label}</NavLink>)}
                            <p className="mt-3 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">Análises</p>
                            {analises.map(aba => <NavLink key={aba.id} to={aba.to} className={estiloLink}>{aba.label}</NavLink>)}
                        </div>
                    </details>
                    <details className="relative">
                        <summary className="cursor-pointer list-none rounded-lg border border-white/10 px-3 py-2 text-sm text-white hover:bg-white/5">Minha conta <span aria-hidden="true">⌄</span></summary>
                        <div className="absolute right-0 mt-2 w-64 max-w-[calc(100vw-2rem)] rounded-xl border border-neutral-700 bg-neutral-900 p-2 shadow-xl">
                            <p className="break-all border-b border-white/10 px-3 py-2 text-xs text-neutral-400">{user?.email}</p>
                            {sessao?.eh_plataforma && <NavLink to="/admin/master" className={estiloLink}>Administração master</NavLink>}
                            {sessao?.pode_administrar && <NavLink to="/admin" className={estiloLink}>Administração</NavLink>}
                            <NavLink to="/onboarding" className={estiloLink}>Primeiros passos</NavLink>
                            <button onClick={sugestao} className="w-full rounded-lg px-3 py-2 text-left text-sm text-neutral-300 hover:bg-white/5">Enviar sugestão</button>
                            <button disabled={saindo} onClick={() => void sair()} className="w-full rounded-lg border-t border-white/10 px-3 py-2 text-left text-sm text-neutral-300 hover:bg-white/5 disabled:opacity-40">{saindo ? 'Saindo…' : 'Sair'}</button>
                            {erro && <p role="alert" className="px-3 py-2 text-xs text-red-300">{erro}</p>}
                        </div>
                    </details>
                </div>
            </div>
        </nav>
        <dialog ref={feedback} aria-labelledby="feedback-titulo" className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-neutral-700 bg-neutral-900 p-6 text-white shadow-2xl backdrop:bg-black/60">
            <h2 id="feedback-titulo" className="mb-2 text-lg font-semibold">Ajude a melhorar o portal</h2>
            {ENV.FEEDBACK_FORM_URL ? <>
                <p className="mb-5 text-sm text-neutral-300">Registre um bug ou sugira uma melhoria no formulário.</p>
                <a href={ENV.FEEDBACK_FORM_URL} target="_blank" rel="noopener noreferrer" className="block rounded-lg bg-primary-600 px-4 py-3 text-center text-sm font-semibold">Ir para o formulário</a>
            </> : <p className="mb-5 text-sm text-neutral-400">O formulário ainda não está disponível. Fale com o administrador da sua federação.</p>}
            <form method="dialog"><button className="mt-3 w-full rounded-lg bg-white/5 px-4 py-3 text-sm hover:bg-white/10">Fechar</button></form>
        </dialog>
    </>;
}
