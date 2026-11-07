import { Fragment, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Session, User } from '../services/auth';
import { authClient } from '../services/auth';
import { queryClient } from '../services/queryClient';
import { AuthContext } from './authContextStore';
import type { AuthContextValue } from './authContextStore';
import { createSessionBoundary, sessionScope } from './sessionScope';

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        let receivedAuthEvent = false;
        const boundary = createSessionBoundary(() => queryClient.clear());
        const applySession = (nextSession: Session | null) => {
            if (!active) return;
            // clear destrói também queries em voo antes de montar a nova conta.
            boundary(nextSession);
            setSession(nextSession);
            setUser(nextSession?.user ?? null);
            setLoading(false);
        };

        authClient.auth.getSession().then(({ data }) => {
            if (!receivedAuthEvent) applySession(data.session ?? null);
        }).catch(() => {
            if (active) setLoading(false);
        });

        const {
            data: { subscription },
        } = authClient.auth.onAuthStateChange((_event, nextSession) => {
            receivedAuthEvent = true;
            applySession(nextSession ?? null);
        });

        return () => {
            active = false;
            subscription.unsubscribe();
        };
    }, []);

    const value = useMemo<AuthContextValue>(
        () => ({
            user,
            session,
            loading,
            signInWithPassword: async (email: string, password: string) => {
                const { error } = await authClient.auth.signInWithPassword({ email, password });
                if (error) return error.message;
                return null;
            },
            signOut: async () => {
                await authClient.auth.signOut();
                queryClient.clear();
            },
        }),
        [user, session, loading],
    );

    return <AuthContext.Provider value={value}>
        <Fragment key={sessionScope(session)}>{children}</Fragment>
    </AuthContext.Provider>;
}
