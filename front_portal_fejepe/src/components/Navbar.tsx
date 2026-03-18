import { NavLink } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../auth/useAuth';

const navLinks = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/comparacao', label: 'Comparação' },
    { to: '/indicadores', label: 'Indicadores' },
    { to: '/simulacao', label: 'Simulação' },
];

export default function Navbar() {
    const [menuOpen, setMenuOpen] = useState(false);
    const { user, signOut } = useAuth();

    const handleLogout = async () => {
        await signOut();
    };

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 glass-nav h-16">
            <div className="max-w-[1280px] mx-auto h-full px-4 sm:px-6 flex items-center justify-between">
                {/* Logo */}
                <NavLink to="/dashboard" className="flex items-center gap-3 no-underline group">
                    <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center shrink-0 opacity-90 group-hover:opacity-100 transition-opacity shadow-glow">
                        <span className="text-white font-heading font-black text-sm leading-none">FJ</span>
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
                <button
                    onClick={() => setMenuOpen(!menuOpen)}
                    className="md:hidden text-white/70 hover:text-white p-2 rounded-lg hover:bg-white/5 transition-all cursor-pointer"
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
    );
}
