import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layout/MainLayout';
import LoginPage from './features/auth/LoginPage';
import ProtectedRoute from './auth/ProtectedRoute';
import FullPageSpinner from './components/FullPageSpinner';

const DashboardPage   = lazy(() => import('./features/dashboard/DashboardPage'));
const ComparacaoPage  = lazy(() => import('./features/comparacao/ComparacaoPage'));
const EventosPage     = lazy(() => import('./features/eventos/EventosPage'));
const SimulacaoPage   = lazy(() => import('./features/simulacao/SimulacaoPage'));
const EmpresaPage     = lazy(() => import('./features/empresa/EmpresaPage'));
const IndicadoresPage = lazy(() => import('./features/indicadores/IndicadoresPage'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<FullPageSpinner />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/empresas/:idEj" element={<EmpresaPage />} />
            <Route path="/comparacao" element={<ComparacaoPage />} />
            <Route path="/eventos" element={<EventosPage />} />
            <Route path="/indicadores" element={<IndicadoresPage />} />
            <Route path="/simulacao" element={<SimulacaoPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
