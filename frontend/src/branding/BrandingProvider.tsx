import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { ENV } from '../config/env';
import { brandingDeFallback, buscarBranding, buscarBrandingDoUsuario } from '../services/brandingService';
import { authClient } from '../services/auth';
import type { FederacaoBranding } from '../services/brandingService';
import { BrandingContext } from './brandingContextStore';
import type { BrandingContextValue } from './brandingContextStore';
import { aplicarPaleta, aplicarFavicon } from './tema';
import FullPageSpinner from '../components/FullPageSpinner';

/**
 * Carrega o branding da federação antes do primeiro render da aplicação.
 *
 * POR QUE BLOQUEIA O RENDER
 *
 * Nome, logo e cor aparecem na primeira tela, inclusive na de login. Renderizar
 * antes de saber quais são significa mostrar um nome, trocar por outro meio
 * segundo depois e repintar a interface inteira — o usuário vê a aplicação se
 * corrigindo. Uma tela de carregamento curta é melhor do que isso.
 *
 * O bloqueio é limitado: o cliente HTTP tem timeout (services/brandingService.ts)
 * e, se a API não responder, a aplicação abre com o fallback local. Não existe
 * caminho em que o portal fique preso aqui.
 *
 * DE QUAL FEDERAÇÃO
 *
 * Sem sessão (tela de login), a do deploy: `TENANT_SLUG`. Com sessão, a do
 * usuário: `/federacao/minha`, pelo token. Até 29/09/2026 era sempre a do
 * deploy, e um usuário da FEJEMG via "Portal FEJEPE" sobre os dados da FEJEMG.
 * Entrar e sair recarregam o branding, sem voltar para a tela de carregamento.
 *
 * POR QUE NÃO PASSA PELO REACT QUERY
 *
 * O queryClient e o interceptor de auth são infraestrutura da aplicação
 * logada. Esta chamada acontece antes disso tudo, e só se repete quando a
 * sessão muda.
 */
export function BrandingProvider({ children }: { children: ReactNode }) {
    const [branding, setBranding] = useState<FederacaoBranding | null>(null);
    const [usandoFallback, setUsandoFallback] = useState(false);

    useEffect(() => {
        let ativo = true;
        // Entrar e sair em sequência disparam duas cargas; só a última vale,
        // mesmo que a primeira responda depois.
        let ultimaCarga = 0;

        const carregar = async (token: string | undefined) => {
            const esta = ++ultimaCarga;
            const vigente = () => ativo && esta === ultimaCarga;

            if (token) {
                try {
                    const doUsuario = await buscarBrandingDoUsuario(token);
                    if (!vigente()) return;
                    setBranding(doUsuario);
                    setUsandoFallback(false);
                    return;
                } catch (erro) {
                    // Cai no branding do deploy: melhor a marca errada por um
                    // instante do que a tela presa no carregamento.
                    console.warn('[branding] federação do usuário indisponível; usando a do deploy.', erro);
                }
            }

            try {
                const doDeploy = await buscarBranding(ENV.TENANT_SLUG);
                if (!vigente()) return;
                setBranding(doDeploy);
                setUsandoFallback(false);
            } catch (erro) {
                if (!vigente()) return;
                // Não é fatal: a aplicação abre com o que dá para saber sem a
                // API. O aviso fica no console porque, em produção, branding
                // faltando costuma significar API fora — e isso o usuário vai
                // descobrir na tela seguinte de qualquer forma.
                console.warn('[branding] não foi possível carregar; usando fallback local.', erro);
                setBranding(brandingDeFallback());
                setUsandoFallback(true);
            }
        };

        authClient.auth
            .getSession()
            .then(({ data }) => carregar(data.session?.access_token))
            .catch(() => carregar(undefined));

        const {
            data: { subscription },
        } = authClient.auth.onAuthStateChange((evento, sessao) => {
            // INITIAL_SESSION fica de fora: é a mesma sessão do getSession acima.
            if (evento === 'SIGNED_IN' || evento === 'SIGNED_OUT') {
                void carregar(sessao?.access_token);
            }
        });

        // Recarrega a paleta compartilhada quando outro admin a altera.
        // Apenas metadados de branding; nunca reconsulta dados estratégicos.
        const atualizar = () => { void authClient.auth.getSession().then(({ data }) => carregar(data.session?.access_token)); };
        const aoFocar = () => { if (document.visibilityState === 'visible') atualizar(); };
        const intervalo = window.setInterval(atualizar, 60_000);
        window.addEventListener('focus', aoFocar);
        document.addEventListener('visibilitychange', aoFocar);

        return () => {
            ativo = false;
            subscription.unsubscribe();
            window.clearInterval(intervalo);
            window.removeEventListener('focus', aoFocar);
            document.removeEventListener('visibilitychange', aoFocar);
        };
    }, []);

    // useLayoutEffect, e não useEffect: roda depois da montagem do DOM e ANTES
    // do navegador pintar. É o que evita o frame em que o conteúdo já apareceu
    // mas ainda está com a paleta e o título antigos.
    useLayoutEffect(() => {
        if (!branding) return;

        document.title = `Portal ${branding.nome}`;
        aplicarFavicon(branding.logo_url);
        aplicarPaleta(branding);
    }, [branding]);

    const valor = useMemo<BrandingContextValue | null>(() => {
        if (!branding) return null;
        return {
            branding,
            nome: branding.nome,
            nomeDoPortal: `Portal ${branding.nome}`,
            anoDefault: branding.ano_default,
            usandoFallback,
            // Uma gravação iniciada antes da troca de federação não pode
            // repintar a sessão nova quando a resposta antiga chegar.
            atualizarBranding: (nova, slugEsperado) => setBranding(atual => atual?.slug === slugEsperado ? nova : atual),
        };
    }, [branding, usandoFallback]);

    if (!valor) {
        return <FullPageSpinner />;
    }

    return <BrandingContext.Provider value={valor}>{children}</BrandingContext.Provider>;
}
