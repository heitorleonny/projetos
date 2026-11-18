type NexoMascotProps = {
    className?: string;
    size?: number;
    expressive?: boolean;
};

/** Vaga-lume do Lamps (o componente mantém o nome antigo). Decorativo: o nome acessível fica no controle ou título. */
export default function NexoMascot({ className = '', size = 40, expressive = false }: NexoMascotProps) {
    return <svg width={size} height={size} viewBox="0 0 80 80" fill="none"
        className={className} aria-hidden="true" focusable="false">
        <circle cx="40" cy="43" r="34" fill="currentColor" opacity=".08" />
        <path d="M29 40C12 28 8 48 21 57L36 60M51 40C68 28 72 48 59 57L44 60"
            fill="currentColor" fillOpacity=".22" stroke="currentColor" strokeOpacity=".45" strokeWidth="2" />
        <path d="M35 20L29 12M45 20L51 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="28" cy="11" r="3" fill="currentColor" />
        <circle cx="52" cy="11" r="3" fill="currentColor" />
        <rect x="28" y="33" width="24" height="33" rx="12" fill="currentColor" fillOpacity=".7" />
        <path d="M28 52H52V55C52 62 47 68 40 68C33 68 28 62 28 55V52Z" fill="#FDE68A" />
        <path d="M34 58L40 62L46 58" stroke="#92671A" strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="34" cy="58" r="2" fill="#92671A" />
        <circle cx="40" cy="62" r="2" fill="#92671A" />
        <circle cx="46" cy="58" r="2" fill="#92671A" />
        <rect x="24" y="18" width="32" height="29" rx="14" fill="#F8FAFC" stroke="currentColor" strokeWidth="2" />
        <ellipse cx="33" cy="31" rx="2.2" ry="3" fill="#172033" />
        <ellipse cx="47" cy="31" rx="2.2" ry="3" fill="#172033" />
        <path d={expressive ? 'M35 37C38 42 42 42 45 37' : 'M36 38C39 40 41 40 44 38'}
            stroke="#172033" strokeWidth="1.8" strokeLinecap="round" />
        {expressive && <>
            <circle cx="29" cy="37" r="2.5" fill="currentColor" opacity=".22" />
            <circle cx="51" cy="37" r="2.5" fill="currentColor" opacity=".22" />
            <path d="M66 17V23M63 20H69M12 66V70M10 68H14" stroke="#FDE68A" strokeWidth="2" strokeLinecap="round" />
        </>}
    </svg>;
}
