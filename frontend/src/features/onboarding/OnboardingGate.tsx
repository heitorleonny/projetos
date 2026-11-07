import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';
import { onboardingVisto } from './onboardingStorage';

export default function OnboardingGate({ children }: { children: ReactNode }) {
    const { user } = useAuth();
    const location = useLocation();
    if (user && location.pathname !== '/onboarding' && !onboardingVisto(user.id)) {
        return <Navigate to="/onboarding" replace state={{ from: location.pathname + location.search + location.hash }} />;
    }
    return children;
}
