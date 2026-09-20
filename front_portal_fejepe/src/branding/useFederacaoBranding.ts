import { useContext } from 'react';
import { BrandingContext } from './brandingContextStore';

/**
 * Nome, logo, cor e ano de referência da federação servida por este deploy.
 *
 * Sempre devolve valor preenchido: o provider bloqueia o render até o branding
 * chegar (ou até o fallback entrar), então nenhuma tela precisa tratar estado
 * de carregamento nem valor nulo.
 */
export function useFederacaoBranding() {
    const contexto = useContext(BrandingContext);
    if (!contexto) {
        throw new Error('useFederacaoBranding precisa estar dentro de BrandingProvider');
    }
    return contexto;
}
