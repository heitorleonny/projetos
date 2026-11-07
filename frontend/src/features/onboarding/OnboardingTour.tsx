import { useEffect, useRef } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { abasDoPortal } from '../../config/navigation';
import { useSessaoAdmin } from '../admin/useAdmin';
import { destinoDoOnboarding } from './onboardingStorage';

export default function OnboardingTour() {
    const [params] = useSearchParams();
    const location = useLocation();
    const navigate = useNavigate();
    const { data: sessao } = useSessaoAdmin();
    const titulo = useRef<HTMLHeadingElement>(null);
    const abas = abasDoPortal.filter(aba => aba.id !== 'admin' || sessao?.pode_administrar);
    const indice = abas.findIndex(aba => aba.id === params.get('guia') && aba.to === location.pathname);
    const aba = abas[indice];
    const retorno = destinoDoOnboarding((location.state as { from?: unknown } | null)?.from);
    useEffect(() => { if (aba) titulo.current?.focus(); }, [aba]);
    if (!aba) return null;

    function ir(proximo: number) {
        navigate(`${abas[proximo].to}?guia=${abas[proximo].id}`, { replace: true, state: { from: retorno } });
    }
    function voltarAoGuia() {
        navigate('/onboarding', { replace: true, state: { etapa: 1, from: retorno } });
    }
    return <aside aria-labelledby="tour-titulo" className="fixed inset-x-0 bottom-0 z-[60] max-h-[50dvh] overflow-y-auto border-t border-primary-400/30 bg-neutral-900 shadow-2xl">
        <div className="mx-auto max-w-[1280px] px-4 py-4 sm:px-6">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <p className="mb-1 text-xs font-semibold text-primary-300">Conhecendo o portal · Aba {indice + 1} de {abas.length}</p>
                    <h2 ref={titulo} tabIndex={-1} id="tour-titulo" className="text-lg font-semibold text-white focus:outline-none">{aba.label}</h2>
                </div>
                <button onClick={voltarAoGuia} className="rounded-lg px-3 py-2 text-sm text-neutral-300 hover:bg-white/5">Encerrar visita</button>
            </div>
            <p className="mt-2 text-sm text-neutral-300">{aba.descricao}</p>
            <p className="mt-1 text-sm text-primary-300">{aba.acao}</p>
            <div className="mt-3 flex items-center justify-between gap-3">
                <button disabled={indice === 0} onClick={() => ir(indice - 1)} className="rounded-lg border border-white/10 px-4 py-2 text-sm text-white disabled:opacity-40">Aba anterior</button>
                <button onClick={() => indice < abas.length - 1 ? ir(indice + 1) : voltarAoGuia()} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-500">{indice < abas.length - 1 ? `Próxima: ${abas[indice + 1].label}` : 'Escolher minhas cores'}</button>
            </div>
        </div>
    </aside>;
}
