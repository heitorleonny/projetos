// Preferência de interface por conta e navegador; não concede permissões.
const memoria = new Set<string>();
const chave = (usuarioId: string) => `portal:onboarding:v1:${usuarioId}`;

export function onboardingVisto(usuarioId: string): boolean {
    const id = chave(usuarioId);
    if (memoria.has(id)) return true;
    try {
        return localStorage.getItem(id) === 'concluido' || sessionStorage.getItem(id) === 'adiado';
    } catch {
        return false;
    }
}

export function registrarOnboarding(usuarioId: string, concluir: boolean): void {
    const id = chave(usuarioId);
    memoria.add(id);
    // Navegadores que bloqueiam armazenamento ainda permitem explorar o portal.
    try {
        if (concluir) localStorage.setItem(id, 'concluido');
        else sessionStorage.setItem(id, 'adiado');
    } catch { /* A preferência fica em memória nesta sessão. */ }
}

export function destinoDoOnboarding(destino: unknown): string {
    if (typeof destino !== 'string' || !destino.startsWith('/') || destino.startsWith('//')) return '/dashboard';
    // Só devolvemos rotas internas; o guia e as telas de autenticação não são destinos.
    if (/^\/(onboarding|login|definir-senha)(?:[/?#]|$)/.test(destino) || destino.includes('\\')) return '/dashboard';
    return destino;
}
