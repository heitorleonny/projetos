import { useMemo, useState } from 'react';
import { resolveEjLogoPath } from '../config/ejLogos';

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
    const mappedLogo = useMemo(() => resolveEjLogoPath(nome), [nome]);
    const cleanedFotoUrl = fotoUrl?.trim() ? fotoUrl.trim() : null;
    const primarySrc = cleanedFotoUrl ?? mappedLogo ?? null;
    const secondarySrc = cleanedFotoUrl && mappedLogo && mappedLogo !== cleanedFotoUrl ? mappedLogo : null;
    const sourceKey = `${primarySrc ?? ''}|${secondarySrc ?? ''}`;

    return (
        <LogoWithFallback
            key={sourceKey}
            nome={nome}
            primarySrc={primarySrc}
            secondarySrc={secondarySrc}
            sizeClassName={sizeClassName}
            roundedClassName={roundedClassName}
            className={className}
            initialsClassName={initialsClassName}
        />
    );
}

type LogoWithFallbackProps = {
    nome: string;
    primarySrc: string | null;
    secondarySrc: string | null;
    sizeClassName: string;
    roundedClassName: string;
    className: string;
    initialsClassName: string;
};

function LogoWithFallback({
    nome,
    primarySrc,
    secondarySrc,
    sizeClassName,
    roundedClassName,
    className,
    initialsClassName,
}: LogoWithFallbackProps) {
    const [failedPrimary, setFailedPrimary] = useState(false);
    const [failedSecondary, setFailedSecondary] = useState(false);

    const currentSrc = !failedPrimary
        ? primarySrc
        : (!failedSecondary ? secondarySrc : null);

    const handleError = () => {
        if (!failedPrimary) {
            setFailedPrimary(true);
            return;
        }
        setFailedSecondary(true);
    };

    const baseClass = `${sizeClassName} ${roundedClassName} ${className}`.trim();

    if (currentSrc) {
        return (
            <img
                src={currentSrc}
                alt={`Logo ${nome}`}
                className={`${baseClass} object-cover`}
                loading="lazy"
                onError={handleError}
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
