import type { Session } from '../services/auth';

// Isto identifica o cache local; autorização continua exclusivamente na API/RLS.
export function sessionScope(session: Session | null): string {
    if (!session) return 'anon';
    return JSON.stringify([session.user.id, session.user.app_metadata?.federacao_id ?? null, session.user.app_metadata?.papel ?? null]);
}

export function createSessionBoundary(clear: () => void) {
    let current: string | undefined;
    return (session: Session | null) => {
        const next = sessionScope(session);
        if (next !== current) clear();
        current = next;
        return next;
    };
}
