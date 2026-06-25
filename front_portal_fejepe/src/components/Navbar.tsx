import { NavLink } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../auth/useAuth';
import { ENV } from '../config/env';

const navLinks = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/cluster-track', label: 'Cluster Track' },
    { to: '/comparacao', label: 'Comparação' },
    { to: '/eventos', label: 'Eventos' },
    { to: '/indicadores', label: 'Indicadores' },
    { to: '/simulacao', label: 'Simulação' },
];

export default function Navbar() {
    const [menuOpen, setMenuOpen] = useState(false);
    const [feedbackOpen, setFeedbackOpen] = useState(false);
    const { user, signOut } = useAuth();
    const feedbackLink = ENV.FEEDBACK_FORM_URL || '#';

    const handleLogout = async () => {
        await signOut();
    };

    return (
        <>
            <nav className="fixed top-0 left-0 right-0 z-50 glass-nav h-16">
                <div className="max-w-[1280px] mx-auto h-full px-4 sm:px-6 flex items-center justify-between">
                    {/* Logo */}
                    <NavLink to="/dashboard" className="flex items-center gap-3 no-underline group">
                        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center shrink-0 opacity-90 group-hover:opacity-100 transition-opacity shadow-glow">
                            <img
                                src="/logo_fejepe.svg"
                                alt="Logo FEJEPE"
                                className="h-6 w-6 object-contain"
                            />
                        </div>
                        <div className="hidden sm:flex flex-col leading-none">
                            <span className="text-white font-heading font-bold text-base tracking-wide">
                                Portal FEJEPE
                            </span>
                            <span className="text-primary-300/60 text-[10px] font-medium uppercase tracking-widest">
                                Painel Estratégico
                            </span>
                        </div>
                    </NavLink>

                    {/* Desktop Navigation */}
                    <div className="hidden md:flex items-center gap-1">
                        {navLinks.map((link) => (
                            <NavLink
                                key={link.to}
                                to={link.to}
                                className={({ isActive }) =>
                                    `relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 no-underline ${isActive
                                        ? 'text-white bg-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]'
                                        : 'text-white/50 hover:text-white hover:bg-white/5'
                                    }`
                                }
                            >
                                {({ isActive }) => (
                                    <>
                                        {link.label}
                                        {isActive && (
                                            <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-primary-400 rounded-full" />
                                        )}
                                    </>
                                )}
                            </NavLink>
                        ))}
                        <div className="ml-3 pl-3 border-l border-white/10 flex items-center gap-2">
                            <button
                                onClick={() => setFeedbackOpen(true)}
                                aria-label="Reportar bug ou sugestao"
                                title="Reportar bug ou sugestao"
                                className="h-9 w-9 rounded-lg text-primary-300 hover:text-white hover:bg-white/5 transition-all cursor-pointer inline-flex items-center justify-center"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h8M8 14h5m7 7l-4-4H8a4 4 0 01-4-4V7a4 4 0 014-4h8a4 4 0 014 4v6a4 4 0 01-4 4h-1v4z" />
                                </svg>
                            </button>
                            <span className="text-xs text-white/60 max-w-[180px] truncate" title={user?.email ?? ''}>
                                {user?.email}
                            </span>
                            <button
                                onClick={handleLogout}
                                className="px-3 py-2 rounded-lg text-sm font-medium text-white/70 hover:text-white hover:bg-white/5 transition-all cursor-pointer"
                            >
                                Sair
                            </button>
                        </div>
                    </div>

                    {/* Mobile hamburger */}
                    <div className="md:hidden flex items-center gap-1">
                        <button
                            onClick={() => setFeedbackOpen(true)}
                            aria-label="Reportar bug ou sugestao"
                            title="Reportar bug ou sugestao"
                            className="text-primary-300 hover:text-white p-2 rounded-lg hover:bg-white/5 transition-all cursor-pointer"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h8M8 14h5m7 7l-4-4H8a4 4 0 01-4-4V7a4 4 0 014-4h8a4 4 0 014 4v6a4 4 0 01-4 4h-1v4z" />
                            </svg>
                        </button>
                        <button
                            onClick={() => setMenuOpen(!menuOpen)}
                            className="text-white/70 hover:text-white p-2 rounded-lg hover:bg-white/5 transition-all cursor-pointer"
                            aria-label="Abrir menu"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                {menuOpen ? (
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                ) : (
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                                )}
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Mobile Menu */}
                {menuOpen && (
                    <div className="md:hidden glass-nav border-t border-white/5 px-4 py-3 space-y-1">
                        {navLinks.map((link) => (
                            <NavLink
                                key={link.to}
                                to={link.to}
                                onClick={() => setMenuOpen(false)}
                                className={({ isActive }) =>
                                    `block px-4 py-3 rounded-lg text-sm font-medium transition-all no-underline ${isActive
                                        ? 'bg-white/10 text-white'
                                        : 'text-white/50 hover:text-white hover:bg-white/5'
                                    }`
                                }
                            >
                                {link.label}
                            </NavLink>
                        ))}
                        <button
                            onClick={handleLogout}
                            className="w-full text-left px-4 py-3 rounded-lg text-sm font-medium text-white/70 hover:text-white hover:bg-white/5 transition-all cursor-pointer"
                        >
                            Sair
                        </button>
                    </div>
                )}
            </nav>

            {feedbackOpen && (
                <div className="fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm px-4">
                    <div className="h-full w-full flex items-center justify-center">
                        <div className="w-full max-w-md bg-neutral-900 border border-neutral-700 rounded-2xl p-6 shadow-2xl">
                            <h3 className="text-lg font-semibold text-white mb-2 inline-flex items-center gap-2">
                                <svg className="w-5 h-5 text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h8M8 14h5m7 7l-4-4H8a4 4 0 01-4-4V7a4 4 0 014-4h8a4 4 0 014 4v6a4 4 0 01-4 4h-1v4z" />
                                </svg>
                                Encontrou um bug ou tem uma sugestao?
                            </h3>
                            <p className="text-sm text-neutral-300 mb-5">
                                Se quiser registrar um bug ou sugerir uma melhoria, clique no link abaixo para abrir o formulario.
                            </p>

                            <a
                                href={feedbackLink}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center justify-center w-full py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-sm font-semibold rounded-lg transition-colors"
                            >
                                Ir para o formulario
                            </a>

                            <button
                                onClick={() => setFeedbackOpen(false)}
                                className="mt-3 w-full py-2.5 bg-white/5 hover:bg-white/10 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer"
                            >
                                Fechar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
