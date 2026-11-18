import axios from 'axios';
import { ENV } from '../config/env';
import { resolverLogoDaApi } from '../branding/logoUrl';

/**
 * Branding da federação — a única chamada que precisa funcionar deslogado.
 *
 * POR QUE NÃO USA O `api` DE services/api.ts
 *
 * Aquele cliente tem dois interceptors que estão certos para o resto da
 * aplicação e errados para esta chamada:
 *
 *   * o de request pede `supabase.auth.getSession()` antes de cada envio —
 *     aqui isso seria esperar por uma sessão que, na tela de login, não existe
 *     e não vai existir;
 *   * o de response trata 401 deslogando e redirecionando para /login — numa
 *     chamada que roda *dentro* do /login, isso é um laço.
 *
 * Então: cliente próprio, sem interceptor, sem token. É também o que o
 * endpoint espera (ver o cabeçalho de app/routers/federacao.py).
 */

export type FederacaoBranding = {
    slug: string;
    nome: string;
    logo_url: string | null;
    cor_primaria: string | null;
    cor_secundaria: string | null;
    cor_acento: string | null;
    /** Frase sob o título do Dashboard; nula esconde o subtítulo. */
    slogan: string | null;
    ano_default: number;
};

const clientePublico = axios.create({
    baseURL: ENV.API_BASE_URL,
    // O branding bloqueia o primeiro render. Sem timeout, uma API pendurada
    // deixaria o portal na tela de carregamento para sempre; com ele, cai no
    // fallback e a aplicação abre.
    timeout: 5000,
});

export function comLogoResolvido(branding: FederacaoBranding): FederacaoBranding {
    return { ...branding, logo_url: resolverLogoDaApi(branding.logo_url, ENV.API_BASE_URL) };
}

export async function buscarBranding(slug: string): Promise<FederacaoBranding> {
    const { data } = await clientePublico.get<FederacaoBranding>('/federacao/branding', {
        params: { slug },
    });
    return comLogoResolvido(data);
}

/**
 * Branding da federação de quem está logado — não a do deploy.
 *
 * `TENANT_SLUG` só decide a tela de login. Depois do login, quem manda é o
 * token: um usuário da FEJEMG, num deploy configurado com `fejepe`, via
 * "Portal FEJEPE" e os dados da FEJEMG (achado de 22/09/2026). O token vai
 * explícito, e não pelo interceptor de `api`, pelos motivos do topo deste
 * arquivo: um 401 aqui não pode deslogar ninguém — cai no branding do deploy.
 */
export async function buscarBrandingDoUsuario(token: string): Promise<FederacaoBranding> {
    const { data } = await clientePublico.get<FederacaoBranding>('/federacao/minha', {
        headers: { Authorization: `Bearer ${token}` },
    });
    return comLogoResolvido(data);
}

/**
 * O que mostrar quando a API não respondeu.
 *
 * Não é o branding "da FEJEPE": é o branding possível sem rede nenhuma. O nome
 * vem do slug que o próprio deploy declarou (TENANT_SLUG), em maiúsculas —
 * quem configurou `fejepe` vê FEJEPE, quem configurou `fejece` vê FEJECE. Sem
 * logo e sem cor, o portal cai nas iniciais e na paleta compilada.
 *
 * Isto é o que mantém `npm run dev` com VITE_USE_MOCK=true funcionando sem
 * backend no ar, como funcionava antes desta fase.
 */
export function brandingDeFallback(): FederacaoBranding {
    return {
        slug: ENV.TENANT_SLUG,
        nome: ENV.TENANT_SLUG.toUpperCase(),
        logo_url: null,
        cor_primaria: null,
        cor_secundaria: null,
        cor_acento: null,
        slogan: null,
        // Sem API não há `settings.ANO_DEFAULT`; o ano do calendário é o
        // palpite honesto. Vale só enquanto a API está fora — e, com a API
        // fora, não há dado de ano nenhum para exibir de qualquer forma.
        ano_default: new Date().getFullYear(),
    };
}
