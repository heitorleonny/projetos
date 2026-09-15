# AGENTS.md — Portal FEJEPE (monorepo)

Guia para agentes de IA e desenvolvedores que trabalham neste repositório.
Leia este arquivo antes de fazer qualquer alteração.

## O que é este projeto

Plataforma de inteligência estratégica para **Federações de Empresas Juniores**.
Centraliza, compara, simula e analisa os dados das Empresas Juniores (EJs) de uma
federação: faturamento, metas, CSAT, engajamento, clusters e rankings.

Origem: construído para a **FEJEPE** (Federação das Empresas Juniores do Estado de
Pernambuco). Objetivo atual: **evoluir para um SaaS multi-federação**, onde qualquer
federação do Brasil (Ceará, RN, RS, etc.) possa usar com seus próprios dados isolados
e branding customizado.

> Estado atual: **single-tenant** (assume uma única federação, a FEJEPE). A migração
> multi-tenant está fora do escopo imediato — ver `CLAUDE.md` e
> `docs/adr-001-supabase-vs-postgres.md`.

## Estrutura do monorepo

```
projetos/
├── portal_fejepe/          # Backend — FastAPI + Supabase (Python 3.11+)
├── front_portal_fejepe/    # Frontend — React 19 + Vite + TypeScript
├── calculadora_cluster/    # App auxiliar — calculadora de cluster (React + Vite)
├── infra/db/               # Postgres local do laboratório de dados do TCC
├── docs/                   # Decisões de arquitetura (ADRs)
├── docker-compose.yml      # Stack completa — ver perfis abaixo
├── Makefile                # Atalhos (`make help`)
├── AGENTS.md               # Este arquivo
└── CLAUDE.md               # Camada de TCC sobre este repositório
```

Cada subprojeto tem seu próprio `AGENTS.md` com detalhes específicos da stack.

## Comandos rápidos

### Backend (`portal_fejepe/`)
```bash
cd portal_fejepe
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # preencher SUPABASE_URL e SUPABASE_KEY
uvicorn app.main:app --reload --port 8000
pytest                        # rodar testes
```
Docs interativas: http://localhost:8000/docs (Swagger) e /redoc.

### Frontend (`front_portal_fejepe/`)
```bash
cd front_portal_fejepe
npm install
cp .env.example .env          # preencher VITE_API_BASE_URL, VITE_SUPABASE_*
npm run dev                   # servidor de desenvolvimento (Vite)
npm run build                 # tsc -b && vite build
npm run lint                  # eslint
```

### Tudo junto (Docker)
```bash
cp .env.example .env          # preencher credenciais do Supabase
make up                       # frontend :8080, backend :8000
make dev                      # hot reload (Vite :5173)
make test                     # pytest dentro do container
make lab                      # Postgres local do laboratório do TCC
make help                     # lista todos os atalhos
```
O nginx do frontend faz proxy de `/api/` para o backend, então a imagem não
depende de uma URL de API fixada em build time.

> Nunca inicie dev servers ou watchers de forma bloqueante em automações. Rode
> `npm run build`/`pytest` para validar e deixe o usuário rodar `dev` manualmente.

## Convenções gerais

- **Idioma:** código, comentários, docstrings e documentação em **português**. Nomes de
  domínio em português (`empresa_junior`, `faturamento_acumulado`, `cluster`).
- **Cálculos estratégicos ficam no backend.** Nunca replique fórmulas de SDE, cluster,
  ritmo ou projeção no frontend. A fonte de verdade é `app/services/calculo_service.py`
  e a documentação em `portal_fejepe/calculos.md`.
- **Uma fonte de verdade para constantes de negócio:** faixas de cluster e pesos de SDE
  vivem em `portal_fejepe/app/utils/constants.py`.
- Antes de mudar uma fórmula, leia `portal_fejepe/calculos.md` e `estrutura.md`.

## Regras de segurança (importante)

1. ~~O backend não valida o JWT do Supabase.~~ **Corrigido** (set/2026, ainda não
   commitado): `get_current_user` em `app/dependencies.py` valida o token via
   `sb.auth.get_user`, e os três routers aplicam a dependency. Cobertura em
   `tests/test_seguranca.py`.
2. ~~CORS aberto com `allow_origins=["*"]`.~~ **Corrigido**: `app/main.py` usa
   `settings.cors_origin_list`. Confira o valor de `CORS_ORIGINS` em cada ambiente.
3. Nunca commitar segredos. `portal_fejepe/.env` e `front_portal_fejepe/.env` são
   locais. A `anon key` do Supabase é pública por design, mas a `service key` **não**
   pode ir para o frontend nem para o bundle.
4. Não há isolamento de dados por federação (tenant). Todo `SELECT` traz a rede inteira.

## Git

- Branch principal: `main`. Faça o trabalho em branches de feature.
- Só faça commit quando o usuário pedir explicitamente.
- Prefira adicionar arquivos específicos a `git add .`.

## Onde olhar primeiro

- Entender o negócio → `portal_fejepe/estrutura.md` e `portal_fejepe/calculos.md`
- Entender o banco → `portal_fejepe/banco.md`
- Entender o trabalho de TCC em curso → `CLAUDE.md`
- Entender por que continuamos no Supabase → `docs/adr-001-supabase-vs-postgres.md`
