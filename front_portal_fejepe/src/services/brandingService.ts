import axios from 'axios';
import { ENV } from '../config/env';

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
    ano_default: number;
};

const clientePublico = axios.create({
    baseURL: ENV.API_BASE_URL,
    // O branding bloqueia o primeiro render. Sem timeout, uma API pendurada
    // deixaria o portal na tela de carregamento para sempre; com ele, cai no
    // fallback e a aplicação abre.
    timeout: 5000,
});

export async function buscarBranding(slug: string): Promise<FederacaoBranding> {
    const { data } = await clientePublico.get<FederacaoBranding>('/federacao/branding', {
        params: { slug },
    });
    return data;
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
        // Sem API não há `settings.ANO_DEFAULT`; o ano do calendário é o
        // palpite honesto. Vale só enquanto a API está fora — e, com a API
        // fora, não há dado de ano nenhum para exibir de qualquer forma.
        ano_default: new Date().getFullYear(),
    };
}
