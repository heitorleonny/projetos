import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';
import { abasDoPortal } from '../../config/navigation';
import { useSessaoAdmin } from '../admin/useAdmin';
import { FormularioPaleta } from '../admin/AparenciaTab';
import { destinoDoOnboarding, registrarOnboarding } from './onboardingStorage';

const etapas = ['Conheça as abas', 'Suas cores', 'Tudo pronto'];
const botao = 'rounded-lg px-5 py-3 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary-400 cursor-pointer';

export default function OnboardingPage() {
    const location = useLocation();
    const estado = location.state as { etapa?: number; from?: unknown } | null;
    const [etapa, setEtapa] = useState(estado?.etapa === 1 ? 1 : 0);
    const titulo = useRef<HTMLHeadingElement>(null);
    const { user } = useAuth();
    const { nomeDoPortal, branding } = useFederacaoBranding();
    const sessao = useSessaoAdmin();
    const navigate = useNavigate();
    const destino = destinoDoOnboarding(estado?.from);
    const abas = abasDoPortal.filter(aba => aba.id !== 'admin' || sessao.data?.pode_administrar);

    useEffect(() => { titulo.current?.focus(); }, [etapa]);

    function sair(concluir: boolean, rota = destino) {
        if (!user) return;
        registrarOnboarding(user.id, concluir);
        navigate(rota, { replace: true });
    }
    function visitar(indice = 0) {
        if (!user) return;
        // A visita libera as telas nesta sessão, mas não conclui o onboarding.
        registrarOnboarding(user.id, false);
        navigate(`${abas[indice].to}?guia=${abas[indice].id}`, { replace: true, state: { from: destino } });
    }

    return <section className="mx-auto max-w-4xl pb-8" aria-labelledby="onboarding-titulo">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-medium text-primary-300">Primeiros passos</p>
            <button onClick={() => sair(false)} className={`${botao} text-neutral-300 hover:bg-white/5`}>Continuar depois</button>
        </div>
        <ol aria-label="Etapas do guia" className="mb-6 grid grid-cols-3 gap-2 sm:gap-4">
            {etapas.map((rotulo, indice) => <li key={rotulo}>
                <button onClick={() => setEtapa(indice)} aria-current={etapa === indice ? 'step' : undefined}
                    className={`w-full rounded-xl border p-3 text-left text-xs sm:text-sm focus-visible:outline-2 focus-visible:outline-primary-400 ${etapa === indice ? 'border-primary-400/50 bg-primary-500/10 text-white' : 'border-white/10 text-neutral-400 hover:bg-white/5'}`}>
                    <span className="mb-1 block font-semibold">{indice + 1}</span>{rotulo}
                </button>
            </li>)}
        </ol>
        <div className="glass-card rounded-2xl p-5 sm:p-8">
            <h1 ref={titulo} tabIndex={-1} id="onboarding-titulo" className="font-heading text-2xl sm:text-3xl font-bold text-white focus:outline-none">
                {etapa === 0 ? `Vamos conhecer o ${nomeDoPortal}?` : etapa === 1 ? 'Deixe o portal com a cara da sua rede' : 'Seu portal está pronto'}
            </h1>
            {etapa === 0 && <div className="mt-5 space-y-5">
                <p className="text-sm leading-relaxed text-neutral-300">Vamos abrir cada aba do portal com uma explicação curta. Você pode experimentar os filtros enquanto conhece as ferramentas e avançar no seu ritmo.</p>
                <button onClick={() => visitar()} className={`${botao} bg-primary-600 text-white hover:bg-primary-500`}>Começar visita guiada</button>
                <div className="grid gap-3 sm:grid-cols-2">
                    {abas.map((aba, indice) => <button key={aba.id} onClick={() => visitar(indice)} className="rounded-xl border border-white/10 bg-white/5 p-4 text-left hover:border-primary-400/50 focus-visible:outline-2 focus-visible:outline-primary-400">
                        <span className="text-xs text-primary-300">Aba {indice + 1} · {aba.grupo === 'analises' ? 'Menu Análises' : aba.grupo === 'conta' ? 'Menu Minha conta' : 'Navegação principal'}</span>
                        <h2 className="mt-1 font-semibold text-white">{aba.label}</h2>
                        <p className="mt-2 text-sm leading-relaxed text-neutral-300">{aba.descricao}</p>
                        <span className="mt-3 block text-sm font-medium text-primary-300">Conhecer esta aba →</span>
                    </button>)}
                </div>
                <p className="text-sm text-neutral-400">Os dados são da federação vinculada à sua conta. O Nexo, disponível pelo botão de conversa fora do guia, ajuda a consultar a rede em português.</p>
            </div>}
            {etapa === 1 && <div className="mt-5 space-y-4">
                <p className="text-sm leading-relaxed text-neutral-300">Esta etapa é opcional. Use o seletor de cores ou digite um código hexadecimal, como <code className="text-white">#2563EB</code>. A prévia permite experimentar antes de salvar.</p>
                {sessao.isPending ? <p role="status" className="text-sm text-neutral-400">Verificando suas permissões…</p>
                    : sessao.data?.pode_administrar ? <FormularioPaleta key={`${user?.id}:${branding.slug}`} />
                    : <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-neutral-300">
                        <p>A paleta é compartilhada pela federação e pode ser salva por um administrador. Você pode continuar com as cores atuais e pedir a ele uma alteração.</p>
                        {sessao.isError && <button onClick={() => void sessao.refetch()} className="mt-3 text-primary-300 underline">Tentar verificar permissões novamente</button>}
                    </div>}
                <button onClick={() => setEtapa(2)} className={`${botao} border border-white/10 text-neutral-300 hover:bg-white/5`}>Manter as cores atuais e continuar</button>
            </div>}
            {etapa === 2 && <div className="mt-5 space-y-4 text-sm leading-relaxed text-neutral-300">
                <p>Comece pela Visão geral: confira o período, encontre uma empresa júnior e abra seu perfil.</p>
                <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <p className="font-semibold text-white">Onde encontrar cada ferramenta</p>
                    <p className="mt-2">Visão geral, Indicadores e Eventos ficam na barra principal. Evolução de cluster, Comparação e Simulação estão em <strong className="text-white">Análises</strong>.</p>
                    <p className="mt-2">Em <strong className="text-white">Minha conta</strong>, você pode reabrir Primeiros passos{sessao.data?.pode_administrar ? ' e acessar Administração → Aparência para mudar as cores' : ''}.</p>
                </div>
                <p>Se faltarem dados, confira os filtros e o período; se necessário, peça ao administrador para verificar a importação.</p>
            </div>}
            <div className="mt-7 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-5">
                <button disabled={etapa === 0} onClick={() => setEtapa(etapa - 1)} className={`${botao} text-neutral-300 hover:bg-white/5 disabled:opacity-40 disabled:cursor-default`}>Voltar</button>
                <button onClick={() => etapa < etapas.length - 1 ? setEtapa(etapa + 1) : sair(true)} className={`${botao} bg-primary-600 text-white hover:bg-primary-500`}>
                    {etapa === 0 ? 'Ir para personalização' : etapa === 1 ? 'Continuar' : 'Concluir e explorar'}
                </button>
            </div>
        </div>
        <p className="mt-4 text-xs text-neutral-400">Você pode pular qualquer etapa. A conclusão fica salva para sua conta neste navegador.</p>
    </section>;
}
