import { Outlet, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import ChatButton from '../components/ChatButton';
import TourGuiado from '../features/onboarding/TourGuiado';
import OnboardingGate from '../features/onboarding/OnboardingGate';

export default function MainLayout() {
    const location = useLocation();
    return (
        <div className="min-h-screen relative">
            <Navbar />

            <main className="relative pt-24 pb-16 px-4 sm:px-6 max-w-[1280px] mx-auto">
                <OnboardingGate><Outlet /></OnboardingGate>
            </main>

            <footer className="relative border-t border-neutral-800 py-4 text-center text-xs text-neutral-500">
                Dúvidas sobre o portal? Fale com{' '}
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

            {location.pathname !== '/onboarding' && <ChatButton />}
            <TourGuiado />
        </div>
    );
}
