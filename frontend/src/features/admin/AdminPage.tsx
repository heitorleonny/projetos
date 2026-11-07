import { Navigate, useLocation, useSearchParams } from 'react-router-dom';
import FederacoesTab from './FederacoesTab';
import ImportacaoTab from './ImportacaoTab';
import UsuariosTab from './UsuariosTab';
import AparenciaTab from './AparenciaTab';
import { lerErro } from './adminService';
import { useFederacoesAdmin, useSessaoAdmin } from './useAdmin';
import { AvisoErro, Carregando } from './ui';

type Aba = 'importacao' | 'usuarios' | 'federacoes' | 'aparencia';

const ABAS: { id: Aba; rotulo: string; soPlataforma?: boolean }[] = [
    { id: 'importacao', rotulo: 'Importar planilha' },
    { id: 'usuarios', rotulo: 'Usuários' },
    { id: 'aparencia', rotulo: 'Aparência' },
    { id: 'federacoes', rotulo: 'Federações', soPlataforma: true },
];

/**
 * Painel administrativo. Quem entra e o que cada um alcança é decidido pela
 * API (e, abaixo dela, pela RLS); esta tela só esconde o que não se aplica.
 */
export default function AdminPage() {
    const sessao = useSessaoAdmin();
    const [params, setParams] = useSearchParams();
    const location = useLocation();
    const plataforma = Boolean(sessao.data?.eh_plataforma);
    const federacoes = useFederacoesAdmin(Boolean(sessao.data?.pode_administrar));

    if (sessao.isLoading) {
        return <div className="glass-card rounded-2xl p-6"><Carregando /></div>;
    }
    if (sessao.isError) {
        return <div className="glass-card rounded-2xl p-6"><AvisoErro erro={lerErro(sessao.error)} /></div>;
    }
    if (!sessao.data?.pode_administrar) {
        return <Navigate to="/dashboard" replace />;
    }

    const abas = ABAS.filter((a) => !a.soPlataforma || plataforma);
    const pedida = params.get('aba') as Aba | null;
    const aba: Aba = abas.some((a) => a.id === pedida) ? (pedida as Aba) : 'importacao';
    const listaFederacoes = federacoes.data ?? [];

    return (
        <div>
            <div className="mb-6">
                <h1 className="text-2xl font-semibold text-neutral-50">Administração</h1>
                <p className="mt-2 text-neutral-400 text-sm">
                    {plataforma
                        ? 'Operador da plataforma: todas as federações, seus usuários e as cargas de dados.'
                        : 'Usuários e dados da sua federação.'}
                </p>
            </div>

            <div role="tablist" className="flex flex-wrap gap-1 mb-6 border-b border-white/10">
                {abas.map((a) => (
                    <button
                        key={a.id}
                        role="tab"
                        type="button"
                        aria-selected={aba === a.id}
                        onClick={() => setParams(atuais => {
                            const proximos = new URLSearchParams(atuais);
                            proximos.set('aba', a.id);
                            return proximos;
                        }, { replace: true, state: location.state })}
                        className={`relative px-4 py-2.5 text-sm font-medium transition-colors cursor-pointer ${aba === a.id ? 'text-white' : 'text-white/50 hover:text-white'}`}
                    >
                        {a.rotulo}
                        {aba === a.id && <span className="absolute left-3 right-3 -bottom-px h-0.5 bg-primary-400 rounded-full" />}
                    </button>
                ))}
            </div>

            {federacoes.isError && <div className="mb-6"><AvisoErro erro={lerErro(federacoes.error)} /></div>}

            {aba === 'importacao' && <ImportacaoTab sessao={sessao.data} federacoes={listaFederacoes} />}
            {aba === 'usuarios' && <UsuariosTab sessao={sessao.data} federacoes={listaFederacoes} />}
            {aba === 'aparencia' && <AparenciaTab />}
            {aba === 'federacoes' && plataforma && (
                federacoes.isLoading ? <Carregando /> : <FederacoesTab federacoes={listaFederacoes} />
            )}
        </div>
    );
}
