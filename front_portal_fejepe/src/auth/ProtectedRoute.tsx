import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './useAuth';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div className="min-h-screen bg-[#060C1A] bg-grid-pattern flex items-center justify-center">
                <div className="text-sm text-neutral-300">Verificando sessao...</div>
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace state={{ from: location.pathname }} />;
    }

    return <>{children}</>;
}
