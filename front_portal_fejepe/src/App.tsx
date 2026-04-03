import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layout/MainLayout';
import DashboardPage from './features/dashboard/DashboardPage';
import ComparacaoPage from './features/comparacao/ComparacaoPage';
import EventosPage from './features/eventos/EventosPage';
import SimulacaoPage from './features/simulacao/SimulacaoPage';
import EmpresaPage from './features/empresa/EmpresaPage';
import IndicadoresPage from './features/indicadores/IndicadoresPage';
import LoginPage from './features/auth/LoginPage';
import ProtectedRoute from './auth/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  );
}

export default App;
