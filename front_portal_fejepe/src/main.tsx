import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthContext'
import { BrandingProvider } from './branding/BrandingProvider'
import { queryClient } from './services/queryClient'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {/* Por fora do AuthProvider de propósito: o branding aparece na tela de
          login, antes de existir sessão. Ver src/branding/BrandingProvider.tsx. */}
      <BrandingProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrandingProvider>
    </QueryClientProvider>
  </StrictMode>,
)
