import { ENV } from '../config/env';
export type User = { id: string; email: string; app_metadata: { federacao_id: number; papel: string }; user_metadata: { nome: string } };
export type Session = { access_token: string; user: User };
type Evento = 'SIGNED_IN' | 'SIGNED_OUT' | 'TOKEN_REFRESHED';
const chave = 'portal.sessao.v1';
const ouvintes = new Set<(evento: Evento, sessao: Session | null) => void>();
let atual: Session | null = null;
try { atual = JSON.parse(localStorage.getItem(chave) || 'null'); } catch { /* armazenamento indisponível */ }
function aplicar(sessao: Session | null, persistir = true) {
    atual = sessao;
    if (persistir) { try { if (sessao) localStorage.setItem(chave, JSON.stringify(sessao)); else localStorage.removeItem(chave); } catch { /* sessão somente em memória */ } }
    ouvintes.forEach(fn => fn(sessao ? 'SIGNED_IN' : 'SIGNED_OUT', sessao));
}
window.addEventListener('storage', e => {
    if (e.key === chave || e.key === null) {
        try { aplicar(JSON.parse(e.newValue || 'null'), false); } catch { aplicar(null, false); }
    }
});
async function requisitar(caminho: string, body?: unknown, token = atual?.access_token) {
    const r = await fetch(`${ENV.API_BASE_URL}/auth/${caminho}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store',
    });
    if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(typeof d.detail === 'string' ? d.detail : 'Não foi possível autenticar.'); }
    return r.status === 204 ? null : r.json();
}
export const authClient = { auth: {
    async getSession() {
        const antes = atual;
        if (antes) {
            try {
                const user: User = await requisitar('me', undefined, antes.access_token);
                if (atual === antes) {
                    const proxima = { ...antes, user };
                    if (JSON.stringify(user) !== JSON.stringify(antes.user)) aplicar(proxima);
                    else atual = proxima;
                }
            } catch { if (atual === antes) aplicar(null); }
        }
        return { data: { session: atual } };
    },
    onAuthStateChange(fn: (evento: Evento, sessao: Session | null) => void) {
        ouvintes.add(fn);
        return { data: { subscription: { unsubscribe: () => ouvintes.delete(fn) } } };
    },
    async signInWithPassword(body: { email: string; password: string }) {
        try { const session: Session = await requisitar('login', body, ''); aplicar(session); return { error: null }; }
        catch (e) { return { error: { message: e instanceof Error ? e.message : 'Falha no login.' } }; }
    },
    async signOut() {
        const token = atual?.access_token;
        aplicar(null);
        if (token) await requisitar('logout', {}, token);
    },
    async updateUser(body: { password: string }) {
        try {
            const convite = new URLSearchParams(location.hash.slice(1)).get('convite');
            await requisitar('senha', { ...body, convite });
            history.replaceState(null, '', location.pathname);
            aplicar(null);
            return { error: null };
        } catch (e) { return { error: { message: e instanceof Error ? e.message : 'Falha ao salvar senha.' } }; }
    },
} };
