/**
 * Logo enviada pelo portal: o banco guarda o caminho da API (`/api/v1/federacao/logo?...`).
 * Com a API em outro endereço (ex.: `npm run dev` com VITE_API_BASE_URL absoluta),
 * o caminho é reescrito para esse endereço. URLs externas passam sem mudança.
 */
export function resolverLogoDaApi(logoUrl: string | null, apiBase: string): string | null {
    if (!logoUrl || !logoUrl.startsWith('/api/v1/')) return logoUrl;
    return apiBase.replace(/\/+$/, '') + logoUrl.slice('/api/v1'.length);
}

/** Só a logo enviada pelo portal pode ser removida pelo admin; a externa é da plataforma. */
export function logoFoiEnviada(logoUrl: string | null): boolean {
    return Boolean(logoUrl && /\/federacao\/logo\?/.test(logoUrl));
}
