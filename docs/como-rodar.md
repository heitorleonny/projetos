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
