import { useRef, useState } from 'react';
import { useAuth } from '../auth/useAuth';
import AssistentePanel from '../features/assistente/AssistentePanel';
import NexoMascot from './NexoMascot';

function escopoDaSessao(token?: string, metadata?: Record<string, unknown>) {
    if (!token) return '';
    try {
        const claims = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        // Apenas particiona estado local; a API continua verificando a identidade.
        return `${claims.federacao_id ?? claims.app_metadata?.federacao_id ?? metadata?.federacao_id ?? ''}:${claims.papel ?? claims.app_metadata?.papel ?? metadata?.papel ?? ''}`;
    } catch { return token; }
}

export default function ChatButton() {
    const [open, setOpen] = useState(false);
    const { session, user } = useAuth();
    const botao = useRef<HTMLButtonElement>(null);
    const escopo = `${user?.id ?? ''}:${escopoDaSessao(session?.access_token, user?.app_metadata)}`;

    function fechar() {
        setOpen(false);
        botao.current?.focus();
    }

    if (!session) return null;
    return <>
        <AssistentePanel key={escopo} aberto={open} fechar={fechar} />
        <button ref={botao} onClick={() => setOpen(true)}
            className="fixed bottom-5 right-5 z-40 flex h-12 items-center gap-2 rounded-lg border border-primary-300/25 bg-primary-600 px-4 text-white shadow-md transition hover:bg-primary-500 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary-300"
            aria-label="Abrir Nexo, assistente da rede" aria-controls="assistente-rede" aria-haspopup="dialog" aria-expanded={open} title="Nexo · Pergunte à sua rede">
            <NexoMascot size={32} className="text-white" />
            <span className="hidden text-sm font-semibold sm:block">Nexo</span>
        </button>
    </>;
}
