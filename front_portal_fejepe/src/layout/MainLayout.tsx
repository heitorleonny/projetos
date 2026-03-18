import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar';
import ChatButton from '../components/ChatButton';
import WelcomeModal from '../components/WelcomeModal';

export default function MainLayout() {
    return (
        <div className="min-h-screen bg-[#060C1A] bg-grid-pattern relative">
            {/* Ambient glow effects */}
            <div className="fixed top-0 left-1/4 w-96 h-96 bg-primary-500/5 rounded-full blur-3xl pointer-events-none" />
            <div className="fixed bottom-0 right-1/4 w-96 h-96 bg-primary-600/5 rounded-full blur-3xl pointer-events-none" />

            <Navbar />

            <main className="relative pt-24 pb-10 px-4 sm:px-6 max-w-[1280px] mx-auto">
                <Outlet />
            </main>

            <footer className="relative border-t border-neutral-800 py-4 text-center text-xs text-neutral-500">
                Não conseguiu algum dado? Fale com{' '}
                <a
                    href="https://t.me/heitorfejepe"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-400 hover:text-primary-300 transition-colors"
                >
                    @heitorfejepe
                </a>
                {' '}(Telegram)
            </footer>

            <ChatButton />
            <WelcomeModal />
        </div>
    );
}
