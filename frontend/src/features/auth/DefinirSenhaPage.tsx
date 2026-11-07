import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';
import { authClient } from '../../services/auth';

const TAMANHO_MINIMO = 12;

/**
 * Destino do link do e-mail de convite (CONVITE_REDIRECT_URL no backend).
 *
 * O link traz a sessão no fragmento da URL; o cliente do Supabase a lê sozinho
 * ao carregar (`detectSessionInUrl`). Aqui a pessoa só escolhe a senha — sem
 * ela, o convite vale uma vez e o próximo acesso não tem como entrar.
 */
export default function DefinirSenhaPage() {
    const navigate = useNavigate();
    const convite = new URLSearchParams(location.hash.slice(1)).get('convite');
    const { user, loading } = useAuth();
    const { nomeDoPortal } = useFederacaoBranding();
    const [senha, setSenha] = useState('');
    const [confirmacao, setConfirmacao] = useState('');
    const [enviando, setEnviando] = useState(false);
    const [erro, setErro] = useState<string | null>(null);

    const campo =
        'w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all';

    const onSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (enviando || loading || (!user && !convite)) return;
        setErro(null);
        if (senha.length < TAMANHO_MINIMO) {
            setErro(`A senha precisa de pelo menos ${TAMANHO_MINIMO} caracteres.`);
            return;
        }
        if (senha !== confirmacao) {
            setErro('As duas senhas não são iguais.');
            return;
        }
        setEnviando(true);
        try {
            const { error } = await authClient.auth.updateUser({ password: senha });
            if (error) {
                setErro('Não foi possível salvar a senha. Tente novamente; se o convite expirou, peça um novo ao administrador.');
                return;
            }
            navigate('/login', { replace: true });
        } catch {
            setErro('Não foi possível conectar. Verifique sua conexão e tente novamente.');
        } finally {
            setEnviando(false);
        }
    };

    return (
        <div className="min-h-screen bg-neutral-950 bg-grid-pattern flex items-center justify-center px-4">
            <div className="w-full max-w-md glass-card rounded-2xl p-8">
                {loading ? (
                    <p className="text-sm text-neutral-300">Verificando o convite…</p>
                ) : !user && !convite ? (
                    <>
                        <h1 className="font-heading text-2xl text-white font-bold mb-2">Link inválido ou expirado</h1>
                        <p className="text-sm text-neutral-400 mb-6">
                            O link do convite vale uma vez e por tempo limitado. Peça um novo ao administrador da sua federação.
                        </p>
                        <Link to="/login" className="text-primary-300 hover:text-white text-sm">Ir para o login</Link>
                    </>
                ) : (
                    <>
                        <div className="mb-6">
                            <h1 className="font-heading text-2xl text-white font-bold">Bem-vindo ao {nomeDoPortal}</h1>
                            <p className="text-sm text-neutral-400 mt-1">
                                Defina a senha de <span className="text-white">{user?.email || 'sua conta'}</span> para os próximos acessos.
                            </p>
                        </div>
                        <p id="senha-ajuda" className="mb-4 text-sm text-neutral-400">Use pelo menos {TAMANHO_MINIMO} caracteres.</p>
                        <form onSubmit={onSubmit} className="space-y-4">
                            <div>
                                <label htmlFor="senha" className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2 block">Nova senha</label>
                                <input id="senha" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={TAMANHO_MINIMO} aria-describedby="senha-ajuda" autoComplete="new-password" className={campo} />
                            </div>
                            <div>
                                <label htmlFor="confirmacao" className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2 block">Repita a senha</label>
                                <input id="confirmacao" type="password" value={confirmacao} onChange={(e) => setConfirmacao(e.target.value)} required minLength={TAMANHO_MINIMO} aria-describedby="senha-ajuda" autoComplete="new-password" className={campo} />
                            </div>
                            {erro && (
                                <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{erro}</div>
                            )}
                            <button type="submit" disabled={enviando} className="btn-glow w-full text-white font-medium text-sm py-2.5 px-5 rounded-lg cursor-pointer disabled:opacity-50">
                                {enviando ? 'Salvando…' : 'Salvar senha e ir ao login'}
                            </button>
                        </form>
                    </>
                )}
            </div>
        </div>
    );
}
