import { useState } from 'react';

const STORAGE_KEY = 'portal-fejepe-welcome-v1.0';
const SHOW_AFTER_LOGIN_KEY = 'portal-fejepe-show-welcome-after-login';

function shouldOpenWelcomeModal(): boolean {
    if (sessionStorage.getItem(SHOW_AFTER_LOGIN_KEY) === '1') {
        sessionStorage.removeItem(SHOW_AFTER_LOGIN_KEY);
        return true;
    }

    return !localStorage.getItem(STORAGE_KEY);
}

export default function WelcomeModal() {
    const [open, setOpen] = useState(shouldOpenWelcomeModal);

    function handleClose() {
        localStorage.setItem(STORAGE_KEY, '1');
        setOpen(false);
    }

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="relative w-full max-w-md mx-4 bg-neutral-900 border border-neutral-700 rounded-2xl p-6 shadow-2xl">
                {/* Header */}
                <div className="text-center mb-4">
                    <span className="text-4xl">🚀</span>
                    <h2 className="text-xl font-bold text-white mt-2">
                        Bem-vindo ao Portal FEJEPE
                    </h2>
                    <span className="inline-block mt-1 text-xs font-medium text-primary-400 bg-primary-400/10 px-2 py-0.5 rounded-full">
                        Versão 1.0
                    </span>
                </div>

                {/* Description */}
                <p className="text-sm text-neutral-300 text-center leading-relaxed mb-5">
                    Nesta versão é possível <span className="text-white font-medium">visualizar os dados</span> das
                    empresas juniores e <span className="text-white font-medium">comparar com outros anos</span> (2022, 2023, 2024 e 2025).
                </p>

                {/* Next steps */}
                <div className="bg-white/[0.03] border border-neutral-800 rounded-xl p-4 mb-5">
                    <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">
                        Próximos passos
                    </p>
                    <ul className="space-y-2.5">
                        <li className="flex items-start gap-2.5 text-sm text-neutral-300">
                            <span className="text-base leading-none mt-0.5">📊</span>
                            <span>Construção de simulador</span>
                        </li>
                        <li className="flex items-start gap-2.5 text-sm text-neutral-300">
                            <span className="text-base leading-none mt-0.5">🦁</span>
                            <span>Assistente Virtual <span className="text-primary-400 font-medium">Lamps</span></span>
                        </li>
                        <li className="flex items-start gap-2.5 text-sm text-neutral-300">
                            <span className="text-base leading-none mt-0.5">🔄</span>
                            <span>Atualização dos dados dos anos passados</span>
                        </li>
                    </ul>
                </div>

                {/* CTA */}
                <button
                    onClick={handleClose}
                    className="w-full py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer"
                >
                    Explorar o Portal
                </button>
            </div>
        </div>
    );
}
