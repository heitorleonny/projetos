# AGENTS.md — Frontend

SPA React 19, TypeScript e Vite. Autenticação Supabase, requests via axios e React
Query, Tailwind e gráficos Recharts. Leia as regras da raiz antes de alterar.

- `npm ci`: instalação pelo lockfile; Node 22.12+.
- `npm test`: testes Node de URLs de fotos, paleta e onboarding por conta.
- `npm run lint` e `npm run build`: obrigatórios após mudanças no frontend.
- `npm run dev`: execução interativa; não deixar watcher bloqueando automação.

Features verticais em `src/features/`. Não calcular regras estratégicas no
frontend. Variáveis apenas por `src/config/env.ts`; jamais secret/service key no
bundle. Mocks desligados no deploy. O interceptor envia JWT do usuário; branding
após login segue `BrandingProvider`, não a marca pré-login. Acesso e papel real
continuam autorizados pelo backend/RLS, mesmo se a UI esconder controles.

Onboarding é identificado por conta, tolera armazenamento bloqueado e só aceita
retorno interno seguro. Após mudança de identidade, não manter histórico/resultado
privado da conta anterior. Vercel usa esta pasta como Root Directory; container
usa configuração pública em runtime. Veja `infra/deploy/README.md` na raiz.
