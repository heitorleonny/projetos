import { useState } from 'react';
import { fotoUrlSegura } from '../utils/fotoUrl';

/**
 * Logo de uma EJ: a foto que a API manda, ou as iniciais do nome.
 *
 * O QUE SAIU DAQUI, E POR QUE
 *
 * Havia uma segunda fonte: um mapa fixo com ~40 nomes de arquivo PNG em
 * public/ (src/config/ejLogos.ts), casado por aproximação com o nome da EJ.
 * Era a lista de logos das EJs da FEJEPE escrita dentro do bundle — nenhuma
 * outra federação jamais apareceria ali, e manter a lista significava editar
 * código a cada EJ que entrasse ou trocasse de marca.
 *
 * A fonte agora é uma só: `foto_url`, que a API devolve em todo endpoint que
 * entrega EJ (nulo quando não há foto). Sem foto, as iniciais — que é o que o
 * componente já fazia quando o mapa não casava.
 *
 * Junto com o mapa saiu a troca automática de `.png` por `.webp` no
 * `<picture>`: os `.webp` existiam porque um script local os gerava ao lado
 * dos PNGs de public/. Para uma URL remota, pedir o `.webp` irmão é pedir um
 * arquivo que ninguém garantiu que existe — e `<picture>` não volta para o
 * `<img>` quando o `<source>` falha.
 */

type EjLogoProps = {
    nome: string;
    fotoUrl?: string | null;
    sizeClassName?: string;
    roundedClassName?: string;
    className?: string;
    initialsClassName?: string;
};

function getInitials(nome: string): string {
    const parts = nome.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return '?';
    return parts
        .slice(0, 2)
        .map((part) => part.charAt(0).toUpperCase())
        .join('');
}

export default function EjLogo({
    nome,
    fotoUrl,
    sizeClassName = 'w-10 h-10',
    roundedClassName = 'rounded-full',
    className = '',
    initialsClassName = 'text-sm',
}: EjLogoProps) {
    const src = fotoUrlSegura(fotoUrl);

    return (
        // `key` remonta o componente quando a URL muda, para que o estado de
        // "esta imagem falhou" não sobreviva à troca de EJ.
        <LogoComFallback
            key={src ?? ''}
            nome={nome}
            src={src}
            sizeClassName={sizeClassName}
            roundedClassName={roundedClassName}
            className={className}
            initialsClassName={initialsClassName}
        />
    );
}

type LogoComFallbackProps = {
    nome: string;
    src: string | null;
    sizeClassName: string;
    roundedClassName: string;
    className: string;
    initialsClassName: string;
};

function LogoComFallback({
    nome,
    src,
    sizeClassName,
    roundedClassName,
    className,
    initialsClassName,
}: LogoComFallbackProps) {
    const [falhou, setFalhou] = useState(false);

    const baseClass = `${sizeClassName} ${roundedClassName} ${className}`.trim();

    if (src && !falhou) {
        return (
            <img
                src={src}
                alt={`Logo ${nome}`}
                className={`${baseClass} object-contain`}
                loading="lazy"
                decoding="async"
                referrerPolicy="no-referrer"
                onError={() => setFalhou(true)}
            />
        );
    }

    return (
        <div
            className={`${baseClass} bg-gradient-to-br from-primary-500/20 to-primary-700/20 border border-white/10 flex items-center justify-center`}
            aria-label={`Sem logo para ${nome}`}
            title={nome}
        >
            <span className={`font-heading font-bold text-primary-300 ${initialsClassName}`}>
                {getInitials(nome)}
            </span>
        </div>
    );
}
