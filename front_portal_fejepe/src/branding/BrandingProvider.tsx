import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { ENV } from '../config/env';
import { brandingDeFallback, buscarBranding } from '../services/brandingService';
import type { FederacaoBranding } from '../services/brandingService';
import { BrandingContext } from './brandingContextStore';
import type { BrandingContextValue } from './brandingContextStore';
import { aplicarCorPrimaria, aplicarFavicon } from './tema';
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
 * POR QUE NÃO PASSA PELO REACT QUERY
 *
 * O queryClient e o interceptor de auth são infraestrutura da aplicação
 * logada. Esta chamada acontece antes disso tudo, uma vez só, e não é
 * recarregada nem invalidada em nenhum momento da sessão.
 */
export function BrandingProvider({ children }: { children: ReactNode }) {
    const [branding, setBranding] = useState<FederacaoBranding | null>(null);
    const [usandoFallback, setUsandoFallback] = useState(false);

    useEffect(() => {
        let ativo = true;

        buscarBranding(ENV.TENANT_SLUG)
            .then((resposta) => {
                if (!ativo) return;
                setBranding(resposta);
            })
            .catch((erro) => {
                if (!ativo) return;
                // Não é fatal: a aplicação abre com o que dá para saber sem a
                // API. O aviso fica no console porque, em produção, branding
                // faltando costuma significar API fora — e isso o usuário vai
                // descobrir na tela seguinte de qualquer forma.
                console.warn('[branding] não foi possível carregar; usando fallback local.', erro);
                setBranding(brandingDeFallback());
                setUsandoFallback(true);
            });

        return () => {
            ativo = false;
        };
    }, []);

    // useLayoutEffect, e não useEffect: roda depois da montagem do DOM e ANTES
    // do navegador pintar. É o que evita o frame em que o conteúdo já apareceu
    // mas ainda está com a paleta e o título antigos.
    useLayoutEffect(() => {
        if (!branding) return;

        document.title = `Portal ${branding.nome}`;
        aplicarFavicon(branding.logo_url);
        aplicarCorPrimaria(branding.cor_primaria);
    }, [branding]);

    const valor = useMemo<BrandingContextValue | null>(() => {
        if (!branding) return null;
        return {
            branding,
            nome: branding.nome,
            nomeDoPortal: `Portal ${branding.nome}`,
            anoDefault: branding.ano_default,
            usandoFallback,
        };
    }, [branding, usandoFallback]);

    if (!valor) {
        return <FullPageSpinner />;
    }

    return <BrandingContext.Provider value={valor}>{children}</BrandingContext.Provider>;
}
