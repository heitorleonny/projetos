import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';

type LocationState = {
    from?: string;
};

const SHOW_WELCOME_AFTER_LOGIN_KEY = 'portal-fejepe-show-welcome-after-login';

export default function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, signInWithPassword, loading } = useAuth();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const redirectTo = useMemo(() => {
        const state = location.state as LocationState | null;
        if (state?.from && state.from.startsWith('/')) return state.from;
        return '/dashboard';
    }, [location.state]);

    if (!loading && user) {
        return <Navigate to={redirectTo} replace />;
    }

    const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError(null);
        setSubmitting(true);

        const authError = await signInWithPassword(email.trim(), password);
        setSubmitting(false);

        if (authError) {
            setError('Nao foi possivel entrar. Verifique email e senha.');
            return;
        }

        sessionStorage.setItem(SHOW_WELCOME_AFTER_LOGIN_KEY, '1');
        navigate(redirectTo, { replace: true });
    };

    return (
        <div className="min-h-screen bg-[#060C1A] bg-grid-pattern flex items-center justify-center px-4">
            <div className="w-full max-w-md glass-card rounded-2xl p-8">
                <div className="mb-6">
                    <h1 className="font-heading text-2xl text-white font-bold">Entrar no Portal FEJEPE</h1>
                    <p className="text-sm text-neutral-400 mt-1">Acesso restrito para usuarios pre-cadastrados.</p>
                </div>

                <form onSubmit={onSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="email" className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2 block">
                            Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            autoComplete="email"
                            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                            placeholder="voce@exemplo.com"
                        />
                    </div>

                    <div>
                        <label htmlFor="password" className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2 block">
                            Senha
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            autoComplete="current-password"
                            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                            placeholder="Sua senha"
                        />
                    </div>

                    {error && (
                        <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={submitting}
                        className="btn-glow w-full text-white font-medium text-sm py-2.5 px-5 rounded-lg cursor-pointer disabled:opacity-50"
                    >
                        {submitting ? 'Entrando...' : 'Entrar'}
                    </button>
                </form>
            </div>
        </div>
    );
}
