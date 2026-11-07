import { Outlet, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import ChatButton from '../components/ChatButton';
import OnboardingTour from '../features/onboarding/OnboardingTour';
import { abasDoPortal } from '../config/navigation';
import OnboardingGate from '../features/onboarding/OnboardingGate';

export default function MainLayout() {
    const location = useLocation();
    const guia = new URLSearchParams(location.search).get('guia');
    const emVisita = abasDoPortal.some(aba => aba.id === guia && aba.to === location.pathname);
    return (
        <div className="min-h-screen relative">
            <Navbar />

            <main className={`relative pt-24 ${emVisita ? 'pb-80 sm:pb-64' : 'pb-16'} px-4 sm:px-6 max-w-[1280px] mx-auto`}>
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

            {location.pathname !== '/onboarding' && !emVisita && <ChatButton />}
            <OnboardingTour />
        </div>
    );
}
