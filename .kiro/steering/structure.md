# Estrutura do repositório

Monorepo. Cada subprojeto tem seu próprio `AGENTS.md`.

```
projetos/
├── portal_fejepe/            # BACKEND (FastAPI + Supabase)
│   ├── app/
│   │   ├── main.py           # app, CORS, health, routers
│   │   ├── config.py         # settings (env)
│   │   ├── dependencies.py   # get_supabase (client singleton)
│   │   ├── models/           # schemas Pydantic
│   │   ├── routers/          # endpoints /api/v1 (empresas, rede, eventos)
│   │   ├── services/         # regra de negócio (calculo_service = fonte de verdade)
│   │   └── utils/            # constants.py, cluster.py
│   ├── tests/                # pytest
│   ├── banco.md              # esquema das tabelas
│   ├── calculos.md           # fórmulas estratégicas oficiais
│   ├── estrutura.md          # visão de produto / módulos
│   └── docs/API.md
│
├── front_portal_fejepe/      # FRONTEND (React + Vite)
│   ├── src/
│   │   ├── auth/             # Supabase Auth (context, guard, hook)
│   │   ├── services/         # api.ts, supabase.ts, queryClient.ts
│   │   ├── config/           # env.ts, ejLogos.ts (hardcoded PE)
│   │   ├── features/         # dashboard, empresa, comparacao, indicadores,
│   │   │                     #   simulacao, cluster-track, eventos, auth
│   │   ├── layout/           # MainLayout
│   │   ├── components/       # UI compartilhada
│   │   ├── types/            # tipos de domínio (à mão)
│   │   └── utils/            # formatters
│   ├── public/               # assets estáticos (logos das EJs, logo_fejepe.svg)
│   ├── Dockerfile, nginx.conf, vite.config.ts, openapi.json, designsystem.json
│
├── calculadora_cluster/      # app auxiliar (calculadora de cluster)
├── docker-compose.yml
├── AGENTS.md                 # guia do monorepo
├── ARCHITECTURE.md           # arquitetura + modelo de dados detalhado
├── ROADMAP_SAAS.md           # plano de migração para SaaS
└── .kiro/steering/           # product.md, tech.md, structure.md, saas-migration.md
```

## Onde mexer

| Quero… | Vá para… |
|--------|----------|
| Mudar uma fórmula/cálculo | `portal_fejepe/app/services/calculo_service.py` + `calculos.md` + testes |
| Adicionar/alterar endpoint | `portal_fejepe/app/routers/` + `models/` + `services/` |
| Adicionar tela no front | `front_portal_fejepe/src/features/<feature>/` (Page + service + hook) |
| Ajustar branding | `front_portal_fejepe/src/index.css`, `components/Navbar.tsx`, `config/` |
| Mudar constantes de negócio | `portal_fejepe/app/utils/constants.py` |
| Entender o banco | `portal_fejepe/banco.md` e `ARCHITECTURE.md` |
