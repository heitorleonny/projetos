# AGENTS.md — Frontend (front_portal_fejepe)

SPA do Portal FEJEPE: dashboards, perfis de EJ, comparação, simulador e eventos.
Consome a API FastAPI (`portal_fejepe`) e usa Supabase Auth para login.

## Stack

- **React 19** + **TypeScript** + **Vite 7**
- **react-router-dom 7** (rotas lazy)
- **@tanstack/react-query 5** (estado de servidor) + **axios** (HTTP)
- **@supabase/supabase-js** (autenticação e-mail/senha)
- **Tailwind CSS 4** (via `@tailwindcss/vite`) + tokens em `src/index.css`
- **recharts** (gráficos), **html2canvas** (export de imagem)

## Comandos

```bash
npm install
cp .env.example .env          # VITE_API_BASE_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm run dev                   # dev server (rode manualmente, não em automação)
npm run build                 # tsc -b && vite build — use para validar mudanças
npm run lint                  # eslint
npm run optimize-images       # otimiza imagens em public/ (sharp)
```

Após mudanças, valide com `npm run build` e `npm run lint`.

## Estrutura

```
src/
├── App.tsx            # Rotas (todas protegidas exceto /login)
├── main.tsx           # QueryClientProvider → AuthProvider → App
├── auth/              # AuthContext, ProtectedRoute, useAuth (Supabase Auth)
├── services/          # api.ts (axios + interceptors), supabase.ts, queryClient.ts
├── config/            # env.ts (VITE_*), ejLogos.ts (logos hardcoded das EJs)
├── features/          # feature vertical: Page + service + hook
│   ├── auth/              # LoginPage
│   ├── dashboard/         # DashboardPage, filtros, EjCard, export
│   ├── empresa/           # EmpresaPage (perfil individual /empresas/:idEj)
│   ├── comparacao/        # ComparacaoPage
│   ├── indicadores/       # IndicadoresPage (KPIs da rede)
│   ├── simulacao/         # SimulacaoPage (simulador de SDE)
│   ├── cluster-track/     # ClusterTrackPage
│   └── eventos/           # EventosPage (metas de eventos)
├── layout/            # MainLayout (Navbar + Outlet + footer + ChatButton)
├── components/        # UI compartilhada (Navbar, EjLogo, WelcomeModal, spinner…)
├── types/             # tipos de domínio escritos à mão (empresa.ts, evento.ts)
└── utils/             # formatters.ts (moeda, %, SDE, info de cluster)
```

## Padrões

- **Feature vertical:** cada feature agrupa sua página, `*Service.ts` (chamadas axios)
  e `use*` hook (React Query). Siga esse padrão ao adicionar telas.
- **Nunca calcule regra estratégica no front.** Consuma o valor já calculado pela API.
  Formatação e exibição podem ficar em `utils/formatters.ts`.
- **Autenticação:** o token do Supabase é injetado automaticamente pelo interceptor em
  `services/api.ts`. Um 401 dispara logout + redirect para `/login`.
- **Env:** leia sempre via `config/env.ts` (`ENV.*`), nunca `import.meta.env` espalhado.
- Mocks: `VITE_USE_MOCK=true` faz alguns services retornarem `mockData.ts` local.

## Acoplamento single-tenant a resolver (ver ROADMAP_SAAS.md)

O app assume que só existe a FEJEPE. Ao mexer nessas áreas, tenha o SaaS em mente:

- **Branding hardcoded:** "Portal FEJEPE", `/logo_fejepe.svg` (Navbar), cores em
  `index.css`, textos em LoginPage/WelcomeModal/DashboardPage/IndicadoresPage.
- **Logos das EJs:** `config/ejLogos.ts` — lista fixa de ~43 arquivos de PE. No SaaS,
  logos devem vir do backend por federação.
- **Comunidades hardcoded:** `COMUNIDADES` em `ComparacaoPage.tsx` (nomes de PE).
- **Ano fixo 2026:** espalhado por várias páginas/services. Tornar dinâmico/configurável.
- **Sem contexto de tenant, sem roles/RBAC:** todo usuário vê tudo. Falta um
  `TenantContext` + branding dinâmico + controle de acesso.

Meta: extrair tudo isso para configuração vinda da API por federação (tema em CSS vars
runtime, logos e comunidades por tenant, ano corrente dinâmico).
