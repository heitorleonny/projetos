import { createContext } from 'react';
import type { FederacaoBranding } from '../services/brandingService';

/**
 * Arquivo separado do provider pelo mesmo motivo de auth/authContextStore.ts:
 * um módulo que exporta componente E valor quebra o fast refresh do Vite
 * (regra `react-refresh/only-export-components` do eslint do projeto).
 */

export type BrandingContextValue = {
    /** O que a API devolveu — ou o fallback local, se ela não respondeu. */
    branding: FederacaoBranding;
    /** Nome da federação: 'FEJEPE'. Usado onde o texto já diz o resto. */
    nome: string;
    /** Nome do produto montado: 'Portal FEJEPE'. */
    nomeDoPortal: string;
    /** Ano de referência da plataforma, fonte única para as telas. */
    anoDefault: number;
    /** `true` quando a API não respondeu e o branding veio do fallback. */
    usandoFallback: boolean;
};

export const BrandingContext = createContext<BrandingContextValue | undefined>(undefined);
