import { useState } from 'react';

export default function ChatButton() {
    const [open, setOpen] = useState(false);

    return (
        <div className="fixed bottom-6 right-6 z-50">
            {open && (
                <div className="absolute bottom-16 right-0 w-72 bg-neutral-900 border border-neutral-700 rounded-xl p-4 shadow-2xl animate-in fade-in slide-in-from-bottom-2 duration-200">
                    <button
                        onClick={() => setOpen(false)}
                        className="absolute top-2 right-2 text-neutral-500 hover:text-white transition-colors cursor-pointer"
                        aria-label="Fechar"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-lg">🦁</span>
                        <span className="text-sm font-semibold text-white">Lamps</span>
                    </div>
                    <p className="text-xs text-neutral-400 leading-relaxed">
                        Em breve teremos o <span className="text-primary-400 font-medium">Lamps</span>, nosso assistente virtual com IA, para te auxiliar no uso do Portal FEJEPE! 🚀
                    </p>
                </div>
            )}

            <button
                onClick={() => setOpen(prev => !prev)}
                className="w-14 h-14 
                     bg-gradient-to-br from-primary-500 to-primary-700
                     text-white rounded-full 
                     transition-all duration-300 hover:scale-110
                     flex items-center justify-center cursor-pointer
                     animate-pulse-ring
                     shadow-[0_0_20px_rgba(13,110,253,0.3)]
                     hover:shadow-[0_0_30px_rgba(13,110,253,0.5)]"
                aria-label="Abrir assistente de IA"
                title="Assistente IA — Lamps"
            >
                <span className="text-2xl leading-none">🦁</span>
            </button>
        </div>
    );
}
