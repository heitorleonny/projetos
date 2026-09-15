# Tecnologia — Portal FEJEPE

## Visão geral
Monorepo com dois serviços principais e um app auxiliar, orquestrados por Docker Compose.

```
Frontend (React/Vite) ──HTTP──► Backend (FastAPI) ──► Supabase (PostgreSQL + Auth)
        │                                                    ▲
        └──────────────── Supabase Auth (login) ─────────────┘
```

## Backend — `portal_fejepe/`
- Python 3.11+, FastAPI `0.115.*`, Uvicorn.
- Supabase (`supabase 2.*`) como banco e auth. Client singleton em `dependencies.py`.
- Pydantic v2 + pydantic-settings. numpy para cálculos. pytest para testes.
- Prefixo de API: `/api/v1`. Docs em `/docs` e `/redoc`.
- Toda regra de negócio em `app/services/` (fonte de verdade: `calculo_service.py`).

## Frontend — `front_portal_fejepe/`
- React 19 + TypeScript + Vite 7.
- react-router-dom 7 (rotas lazy), @tanstack/react-query 5 + axios.
- @supabase/supabase-js para auth (e-mail/senha).
- Tailwind CSS 4 (tokens em `src/index.css`), recharts, html2canvas.
- Organização por feature vertical (Page + service + hook).

## Banco de dados (Supabase / PostgreSQL)
Três tabelas ligadas por `id_ej`:
- `empresa_junior` — cadastro da EJ.
- `metas` — metas anuais por EJ (`ano`).
- `monitoramento` — dados mensais por EJ (`ano`, `mes`).

Cluster por ano em colunas `cluster_2023`…`cluster_2026` (fallback `cluster`), resolvido
via `app/utils/cluster.py`. Detalhes em `portal_fejepe/banco.md`.

## Convenções técnicas
- **Cálculos só no backend.** Frontend consome valores prontos; formata em `utils/`.
- Constantes de negócio centralizadas em `app/utils/constants.py`.
- Env no backend via `config.py` (`settings.*`); no front via `config/env.ts` (`ENV.*`).
- Nomes de domínio e documentação em português.

## Ambiente e execução
- Backend: `uvicorn app.main:app --reload --port 8000`.
- Frontend: `npm run dev` (Vite). Build: `npm run build`. Lint: `npm run lint`.
- Docker: `docker compose up --build` (front :80, back :8000).
- Não rodar dev servers de forma bloqueante em automações; validar com `build`/`pytest`.

## Dívidas técnicas conhecidas
- Backend **não valida JWT**; CORS aberto (`["*"]`).
- Sem isolamento por tenant no banco nem nas queries.
- Frontend sem cliente gerado do OpenAPI (tipos escritos à mão).
- URL da API é "baked" no build do frontend (Dockerfile), dificultando multi-ambiente.
