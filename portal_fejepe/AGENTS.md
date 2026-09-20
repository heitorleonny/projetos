# AGENTS.md — Backend (portal_fejepe)

API do Portal FEJEPE. Consulta dados no Supabase e devolve indicadores estratégicos
calculados. **Toda a regra de negócio vive aqui**, nunca no frontend.

## Stack

- **Python 3.11+**, **FastAPI** (`0.115.*`), **Uvicorn**
- **Supabase** (`supabase 2.*`) como banco (PostgreSQL gerenciado) + Auth
- **Pydantic v2** + **pydantic-settings** para schemas e config
- **pytest** + **pytest-asyncio** para testes
- **numpy** para cálculos

## Comandos

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # SUPABASE_URL, SUPABASE_KEY, CORS_ORIGINS
uvicorn app.main:app --reload --port 8000  # dev (rode manualmente)
pytest                                     # testes
pytest tests/test_calculo_service.py -q    # um arquivo
```

Sempre rode `pytest` após mudar qualquer coisa em `services/` ou `utils/`.

## Estrutura

```
app/
├── main.py            # App FastAPI, CORS, health check, registro de routers
├── config.py          # Settings via env (SUPABASE_URL/KEY, CORS, ANO_DEFAULT)
├── dependencies.py    # get_supabase() — client singleton injetado via Depends
├── models/            # Schemas Pydantic (espelham as tabelas + respostas)
│   ├── empresa.py         # EmpresaJunior, EmpresaComIndicadores, enums (Ritmo, etc.)
│   ├── meta.py            # metas anuais
│   ├── monitoramento.py   # dados mensais
│   ├── evento.py          # aba de eventos
│   └── indicadores.py     # KPIs da rede, SDE, ranking
├── routers/           # Endpoints (prefixo /api/v1)
│   ├── empresas.py        # /empresas, /empresas/comparar, /empresas/{id_ej}
│   ├── rede.py            # /rede/indicadores, /ritmo-mensal, /sde, /ranking
│   └── eventos.py         # /eventos, /eventos/{id}
├── services/          # Lógica de negócio
│   ├── calculo_service.py # ⭐ TODAS as fórmulas estratégicas (fonte de verdade)
│   ├── empresa_service.py # consulta + enriquece EJs com indicadores
│   ├── rede_service.py    # KPIs consolidados, SDE em 3 cenários, ritmo mensal
│   └── evento_service.py  # metas de eventos (ex.: CirandaMEJ'26)
└── utils/
    ├── constants.py       # CLUSTER_RANGES, SDE_WEIGHTS, ANO_DEFAULT
    └── cluster.py         # resolve coluna de cluster por ano (cluster_2026 etc.)
```

## Modelo de dados (Supabase / PostgreSQL)

Três tabelas, todas ligadas por `id_ej`. Detalhes em `banco.md`.

- `empresa_junior` — cadastro da EJ (nome, cnpj, cluster, comunidade, estado, cidade…)
- `metas` — metas anuais por EJ (`id_ej`, `ano`, meta_faturamento, meta_csat…)
- `monitoramento` — dados mensais por EJ (`id_ej`, `ano`, `mes`, faturamento, csat…)

> Colunas de cluster por ano: `cluster_2023`…`cluster_2026`, com fallback para `cluster`.
> Resolver sempre via `app/utils/cluster.py`, nunca ler a coluna direto.

## Regras de negócio (não improvisar)

Referência oficial: **`calculos.md`**. Principais conceitos:
- **Ritmo:** `sem_vendas` (fat_mês = 0), `minimo` (fat_mês > 0), `significativo`
  (fat_mês ≥ meta_anual/12).
- **Pontos de cluster:** `Faturamento × CSAT × (1+%Engaj) × (1+%Colab) × 100`.
- **Fórmula adaptativa** por trimestre (Q1 usa metas, Q3/Q4 usa valores reais).
- **SDE:** soma ponderada de subidas − descidas por cluster (pesos em `constants.py`).
- **Cluster** é classificado por faixas de pontuação (`CLUSTER_RANGES`).

Ao alterar qualquer fórmula: atualize `calculos.md`, `constants.py` e os testes juntos.

## Convenções

- Docstrings e comentários em português.
- Routers finos: validam entrada e chamam services. Nenhum cálculo no router.
- Services recebem o `Client` do Supabase por parâmetro (injeção), não importam global.
- Novos endpoints seguem o prefixo `/api/v1` e recebem tags no Swagger.
- Tipos de resposta sempre em `models/` com `response_model=` no decorator.

## Estado da segurança

- [x] **JWT do Supabase validado** em `get_current_user` (`app/dependencies.py`),
  aplicado como dependency nos três routers. Testes em `tests/test_seguranca.py`.
- [x] **CORS restrito** via `settings.cors_origin_list` em `app/main.py`.
- [x] **Documentação interativa fechada em produção.** `/docs`, `/redoc` e
  `/openapi.json` seguem a flag `DOCS_ENABLED` (`app/config.py`), ligada por padrão
  em desenvolvimento e `false` no serviço `backend` do compose. Pôr o Swagger UI
  atrás do gate de auth não resolveria: o browser não envia o Bearer ao navegar.
- [x] **Chave publicável em uso.** A `SUPABASE_KEY` configurada tem prefixo
  `sb_publishable_` (equivalente à `anon key`), e não a `service key` — condição
  necessária para que a RLS seja respeitada.
- [ ] **Confirmar a RLS no Supabase.** Usar a `anon key` só tem efeito se as tabelas
  tiverem Row Level Security ativa; isso não é verificável pelo código, apenas no
  painel do Supabase. Sem RLS, o gate autentica o usuário mas não limita quais
  linhas ele lê.
- [ ] **Validar o JWT localmente** (assinatura via JWKS/segredo) em vez de chamar
  `sb.auth.get_user()`. Hoje cada requisição a `/api/v1` faz um round-trip HTTP ao
  Supabase Auth — custa latência e consome rate limit. A troca ganha desempenho mas
  deixa de detectar na hora um token revogado; trabalho futuro.
- [ ] Coluna/claim de **federação (tenant)** filtrando todo `SELECT` — fora do escopo
  atual (ver `CLAUDE.md`), mantido como trabalho futuro.
