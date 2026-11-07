/** A imagem externa é carregada somente pelo navegador, nunca pela API. */
export function fotoUrlSegura(valor?: string | null): string | null {
    const texto = valor?.trim();
    if (!texto || texto.length > 2048 ||
        [...texto].some(caractere => caractere.charCodeAt(0) <= 32 || caractere === '\\')) return null;
    try {
        // Preserva arquivos servidos pelo próprio portal, sem URLs relativas à
        // rota, protocolo implícito ou travessia de diretórios (inclusive codificada).
        if (texto.startsWith('/')) {
            const caminho = decodeURIComponent(texto.split(/[?#]/, 1)[0]);
            if (!caminho.startsWith('//') && !caminho.includes('\\') &&
                !caminho.split('/').some(parte => parte === '..' || parte === '.') &&
                ![...caminho].some(caractere => caractere.charCodeAt(0) <= 32)) return texto;
            return null;
        }
        const url = new URL(texto);
        const host = url.hostname.toLowerCase().replace(/\.$/, '');
        // Fotos da origem devem ser HTTPS públicas. URLs locais, credenciais,
        // data: e javascript: não precisam ser carregadas para validar o campo.
        if (url.protocol !== 'https:' || url.username || url.password ||
            !host.includes('.') || host === 'localhost' || host.endsWith('.localhost') ||
            host.endsWith('.local') || host.endsWith('.internal') ||
            /^[\d.]+$/.test(host) || host.includes(':')) return null;
        return url.href;
    } catch {
        return null;
    }
}
