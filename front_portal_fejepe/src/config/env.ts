/**
 * Configuração da aplicação — runtime primeiro, build time como fallback.
 *
 * O PROBLEMA QUE ISTO RESOLVE
 *
 * O Vite congela `import.meta.env.VITE_*` dentro do bundle em build time. Com
 * o frontend servido por nginx como arquivo estático, isso significa uma
 * imagem Docker por ambiente e por federação: mudar a URL da API ou o tenant
 * exigia rebuildar.
 *
 * A saída é o padrão usual para SPA estática: o container escreve um
 * `env-config.js` no start (ver docker-entrypoint.sh), o `index.html` o
 * carrega antes do bundle, e ele publica `window.__ENV__`. Uma imagem, N
 * configurações.
 *
 * A ORDEM DE PRECEDÊNCIA, E POR QUE ELA É ESTA
 *
 *   1. `window.__ENV__`  — o que o container recebeu neste deploy
 *   2. `import.meta.env` — o que estava no `.env` quando o bundle foi gerado
 *
 * `npm run dev` não passa pelo entrypoint e não tem `window.__ENV__`: cai
 * direto no item 2 e continua funcionando sem nenhuma mudança de rotina.
 *
 * Valor vazio conta como ausente de propósito. O entrypoint escreve todas as
 * chaves, inclusive as que ninguém configurou; sem esta regra, uma variável
 * não preenchida no compose apagaria o default embutido na imagem.
 */

declare global {
    interface Window {
        __ENV__?: Record<string, string | undefined>;
    }
}

function deRuntime(chave: string): string | undefined {
    if (typeof window === 'undefined') return undefined;
    const valor = window.__ENV__?.[chave];
    return valor && valor.trim() !== '' ? valor.trim() : undefined;
}

function deBuild(valor: unknown): string | undefined {
    return typeof valor === 'string' && valor.trim() !== '' ? valor.trim() : undefined;
}

function ler(chave: string, valorDeBuild: unknown): string | undefined {
    return deRuntime(chave) ?? deBuild(valorDeBuild);
}

/**
 * Qual federação este deploy está servindo.
 *
 * PROVISÓRIO, E É IMPORTANTE QUE ESTEJA ESCRITO: a resolução do tenant é por
 * variável de ambiente, NÃO por domínio. Isso funciona para uma federação
 * declarada no deploy — uma instância, um tenant — e NÃO para N federações
 * simultâneas no mesmo servidor.
 *
 * A versão real disto (subdomínio por federação, DNS wildcard, certificado,
 * roteamento) é decisão de arquitetura de propagação do SaaS, e ficou fora
 * desta fase de propósito. O que esta fase entrega é o código deixar de
 * assumir uma federação específica; saber rotear várias é outro problema.
 *
 * O default mantém o comportamento de hoje para quem não configurar nada.
 */
const TENANT_SLUG_PADRAO = 'fejepe';

export const ENV = {
    API_BASE_URL: ler('API_BASE_URL', import.meta.env.VITE_API_BASE_URL) ?? '/api/v1',
    USE_MOCK: (ler('USE_MOCK', import.meta.env.VITE_USE_MOCK) ?? 'false') === 'true',
    SUPABASE_URL: ler('SUPABASE_URL', import.meta.env.VITE_SUPABASE_URL) ?? '',
    SUPABASE_ANON_KEY: ler('SUPABASE_ANON_KEY', import.meta.env.VITE_SUPABASE_ANON_KEY) ?? '',
    FEEDBACK_FORM_URL: ler('FEEDBACK_FORM_URL', import.meta.env.VITE_FEEDBACK_FORM_URL) ?? '',
    TENANT_SLUG: ler('TENANT_SLUG', import.meta.env.VITE_TENANT_SLUG) ?? TENANT_SLUG_PADRAO,
} as const;
