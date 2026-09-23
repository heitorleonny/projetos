# Como rodar o projeto

Resumo prático. Detalhes de stack ficam no `AGENTS.md` de cada subprojeto.

## Pré-requisitos

- Docker Desktop rodando (caminho recomendado), **ou** Python 3.11+ e Node 22+.
- Credenciais do Supabase (`SUPABASE_URL` e `SUPABASE_KEY`). O backend **não sobe sem
  elas** — são obrigatórias em `app/config.py`.

## Caminho rápido — Docker (tudo junto)

```bash
cp .env.example .env     # preencher SUPABASE_* e VITE_SUPABASE_*
make up                  # frontend :8080, backend :8000
```

- App: http://localhost:8080
- API + Swagger: http://localhost:8000/docs
- Derrubar: `make down`

O nginx do frontend faz proxy de `/api/v1` para o backend — por isso
`VITE_API_BASE_URL=/api/v1` no modo produção local.

### Desenvolvimento com hot reload

```bash
make dev                 # Vite :5173 + backend com --reload em :8000
```

Aqui o Vite fala direto com o backend (`VITE_API_BASE_URL_DEV`).

### Outros atalhos

```bash
make test        # pytest do backend dentro do container
make lab         # sobe só o Postgres do laboratório do TCC (:55432)
make logs / ps   # logs e estado dos containers
make clean       # derruba tudo e APAGA volumes (perde os dados do lab)
make help        # lista todos
```

## Caminho manual — sem Docker

Backend (`portal_fejepe/`):

```bash
cd portal_fejepe
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # SUPABASE_URL, SUPABASE_KEY, CORS_ORIGINS
uvicorn app.main:app --reload --port 8000
pytest                               # testes (não tocam na rede)
```

Frontend (`front_portal_fejepe/`):

```bash
cd front_portal_fejepe
npm install
cp .env.example .env                 # VITE_API_BASE_URL, VITE_SUPABASE_*
npm run dev                          # :5173
npm run build                        # tsc -b && vite build
npm run lint
```

Sem credenciais do Supabase, dá para ver a interface com `VITE_USE_MOCK=true` no
`.env` do frontend (dados falsos, backend não é chamado).

Calculadora de cluster (`calculadora_cluster/`) é um app Vite independente:
`npm install && npm run dev`.

## Laboratório de dados do TCC

`make lab` sobe um Postgres **separado do Supabase**, só para a modelagem preditiva.
O schema em `infra/db/init/01-schema.sql` roda sozinho na primeira subida.

```bash
psql postgresql://portal:portal@localhost:55432/portal_lab
```

Credenciais e porta saem de `POSTGRES_*` no `.env` da raiz.

## Se der errado

| Sintoma | Causa provável |
|---|---|
| Backend morre no start com erro de validação | falta `SUPABASE_URL`/`SUPABASE_KEY` no `.env` |
| Front carrega mas as chamadas falham com CORS | origem não está em `CORS_ORIGINS` |
| `make up` não acha variável | esqueceu de criar o `.env` **da raiz** (o compose lê esse) |
| Porta ocupada | ajuste `FRONTEND_PORT` / `BACKEND_PORT` / `POSTGRES_PORT` no `.env` |

---

## Ambiente de demonstração (stack Supabase completa)

Outro ambiente, outra finalidade. O `make lab` é 1 container de Postgres onde os
testes rodam rápido; o `make demo` é a stack inteira, onde se **abre a tela e
olha**, com login de verdade. Os dois convivem. Ver o adendo de
`docs/adr-002-rls-local-sem-stack-completa.md`.

**Pré-requisitos:** Docker no ar e a CLI do Supabase
(`brew tap supabase/tap && brew install supabase`). Verificado na **2.117.0**.

### Do zero até o portal navegável

```bash
# 1. stack + schema (infra/db/init/01..12) + papel de carga
make demo

# 2. dados (dry-run primeiro — a carga inteira roda e desfaz no fim)
make demo-dados ARQUIVO=~/Documents/TCC/dados/monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx ANO=2026 DRY=1
make demo-dados ARQUIVO=~/Documents/TCC/dados/monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx ANO=2026

# 3. usuários de teste — e a PROVA de que o hook está ligado:
#    o script loga, decodifica o JWT e falha se faltar federacao_id ou papel
make demo-seed
```

Atalho dos três: `make demo-tudo ARQUIVO=... ANO=2026`.

| | |
|---|---|
| API (Kong) | http://127.0.0.1:54421 |
| Banco | `postgresql://postgres:postgres@127.0.0.1:54422/postgres` |
| Studio | http://127.0.0.1:54423 |
| E-mails (Mailpit) | http://127.0.0.1:54424 |

Portas no bloco **544xx**, não no 543xx padrão da CLI: havia outra stack
Supabase na máquina ocupando as padrão. `make demo-status` reimprime tudo,
inclusive as chaves.

### Subir o portal contra a demo

Backend e frontend rodam **no host**, não em container — e por um motivo: o
backend dentro do Docker não alcança `127.0.0.1:54421` (precisaria de
`host.docker.internal`), e o navegador não alcança `host.docker.internal`. Como
o compose passa a mesma `SUPABASE_URL` para os dois serviços, não há um valor
que sirva aos dois. No host, ambos falam `127.0.0.1`.

```bash
export DEMO_SUPABASE_URL=http://127.0.0.1:54421
export DEMO_ANON=$(supabase status -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)["ANON_KEY"])')

# backend (:8000)
cd portal_fejepe && SUPABASE_URL=$DEMO_SUPABASE_URL SUPABASE_ANON_KEY=$DEMO_ANON \
  CORS_ORIGINS=http://localhost:5173,http://localhost:8080 ANO_DEFAULT=2026 \
  ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# frontend (:5173) — TENANT_SLUG decide o BRANDING, não o tenant dos dados
cd front_portal_fejepe && VITE_API_BASE_URL=http://localhost:8000/api/v1 \
  VITE_SUPABASE_URL=$DEMO_SUPABASE_URL VITE_SUPABASE_ANON_KEY=$DEMO_ANON \
  VITE_USE_MOCK=false VITE_TENANT_SLUG=fejepe npm run dev -- --port 5173
```

Abra **http://localhost:5173** — `localhost`, não `127.0.0.1`: o `CORS_ORIGINS`
do backend lista `localhost`, e para o CORS os dois não são a mesma origem.

**Usuários:** `um@teste.local` (FEJEPE, 43 EJs) e `dois@teste.local` (FEJEMG,
291 EJs), senha `demo1234` (ou `DEMO_SENHA`).

Para ver o branding da FEJEMG é preciso reiniciar o Vite com
`VITE_TENANT_SLUG=fejemg`: o branding vem do deploy, não do usuário logado.
Ver `docs/achado-9.17-limites-com-segundo-tenant.md`.

### Recomeçar

```bash
make demo-reset   # apaga os volumes e refaz stack + schema
make demo-stop    # só para, preservando os dados
```

`make demo-schema` **não** é idempotente: a migração 04 renomeia
`empresa_junior.federacao` para `federacao_legado` sem guarda, então reaplicar
por cima de um banco já migrado falha. É para isso que existe o `demo-reset`.
