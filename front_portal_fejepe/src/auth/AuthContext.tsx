import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '../services/supabase';
import { queryClient } from '../services/queryClient';
import { AuthContext } from './authContextStore';
import type { AuthContextValue } from './authContextStore';

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;

        supabase.auth.getSession().then(({ data }) => {
            if (!active) return;
            setSession(data.session ?? null);
            setUser(data.session?.user ?? null);
            setLoading(false);
        });

        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, nextSession) => {
            setSession(nextSession ?? null);
            setUser(nextSession?.user ?? null);
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
                const { error } = await supabase.auth.signInWithPassword({ email, password });
                if (error) return error.message;
                return null;
            },
            signOut: async () => {
                await supabase.auth.signOut();
                queryClient.clear();
            },
        }),
        [user, session, loading],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
