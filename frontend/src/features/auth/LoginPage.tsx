import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';

type LocationState = {
    from?: string;
};


export default function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, signInWithPassword, loading } = useAuth();
    const { nomeDoPortal } = useFederacaoBranding();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const redirectTo = useMemo(() => {
        const state = location.state as LocationState | null;
        if (state?.from && state.from.startsWith('/') && !state.from.startsWith('//') && !state.from.includes('\\')) return state.from;
        return '/analise';
    }, [location.state]);

    if (!loading && user) {
        return <Navigate to={redirectTo} replace />;
    }

    const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (submitting || loading) return;
        setError(null);
        setSubmitting(true);
        try {
            const authError = await signInWithPassword(email.trim(), password);
            if (authError) {
                setError('Não foi possível entrar. Verifique e-mail e senha.');
                return;
            }
            navigate(redirectTo, { replace: true });
        } catch {
            setError('Não foi possível conectar. Verifique sua conexão e tente novamente.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            <div className="w-full max-w-md glass-card rounded-2xl p-8">
                <div className="mb-6">
                    <h1 className="font-heading text-2xl text-white font-bold">Entrar no {nomeDoPortal}</h1>
                    <p className="text-sm text-neutral-400 mt-1">Acompanhe os resultados da sua federação. No primeiro acesso, use o convite enviado por e-mail.</p>
                </div>

                <form onSubmit={onSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="email" className="text-sm text-neutral-300 font-medium mb-2 block">
                            E-mail
                        </label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            autoComplete="email"
                            className="w-full bg-neutral-800 border border-neutral-600 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                            placeholder="voce@exemplo.com"
                        />
                    </div>

                    <div>
                        <label htmlFor="password" className="text-sm text-neutral-300 font-medium mb-2 block">
                            Senha
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            autoComplete="current-password"
                            className="w-full bg-neutral-800 border border-neutral-600 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                            placeholder="Sua senha"
                        />
                    </div>

                    {error && (
                        <div role="alert" className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={submitting || loading}
                        className="btn-glow w-full text-white font-medium text-sm py-2.5 px-5 rounded-lg cursor-pointer disabled:opacity-50"
                    >
                        {submitting ? 'Entrando...' : 'Entrar'}
                    </button>
                </form>
            </div>
        </div>
    );
}
