> **05/11/2026:** o caminho Supabase abaixo é histórico. Heitor escolheu PostgreSQL próprio + Docker. Consulte `docs/entrega-tcc-2026-11-05.md` e o README da raiz para o estado da substituição. Não usar estas instruções antigas para o novo ambiente.

# Como rodar e testar

Atualizado em 04/10/2026. Execute os comandos na raiz `projetos/`.

## Preparar a máquina

- Python 3.11+; Node 22.12+ e npm.
- Docker Desktop iniciado, com Docker Compose v2.
- Para navegar na demo: Supabase CLI e `psql` no PATH.

```bash
make setup       # .venv na raiz, requirements do backend e npm ci no frontend
make doctor      # ferramentas, dependências e Docker; não imprime segredos
make help
```

`setup` não copia nem sobrescreve `.env`. No macOS, a CLI pode ser instalada por
`brew install supabase/tap/supabase`; `psql` vem do PostgreSQL/libpq.

## Testar com um comando

```bash
make check
```

Executa backend, build TypeScript/Vite e lint do frontend. O backend usa um
Postgres **descartável**, sem porta publicada e com dados em memória: aplica
`infra/db/init/00..NN`, verifica RLS e ingestão e remove esse banco ao terminar.
O laboratório e a demo são preservados. `--require-lab` faz o pytest falhar caso
haja testes pulados. Não precisa de planilha real, credenciais da nuvem ou CLI.

```bash
make test        # só backend e banco descartável, dentro do Docker
make test-local  # Python do host + lab persistente; exige schema atualizado
make front-build
make front-lint
```

Um `pytest -q` avulso ainda pode pular testes de banco quando o lab está
indisponível. Para verificar migrações novas sem apagar o lab, use `make test`.

## Demo com autenticação real

```bash
make demo
```

Na primeira execução, sobe o Supabase e aplica `infra/db/init/01..NN` (o shim
`00` só pertence ao lab). Nas seguintes, reutiliza schema e dados. Confere a
presença dos objetos mais recentes sem reaplicar migrações antigas; essa
checagem não substitui uma comparação completa de schema. Se estiver antigo
ou parcialmente migrado, o comando para com uma orientação.

Na primeira preparação, depois do schema:

```bash
make demo-dados ARQUIVO=/caminho/exportacao.xlsx ANO=2026 DRY=1
make demo-dados ARQUIVO=/caminho/exportacao.xlsx ANO=2026
make demo-seed
```

Use a exportação original de monitoramento acumulado do Portal BJ, mantendo o
nome do arquivo. As planilhas ficam fora do repositório. O atalho
`make demo-tudo ARQUIVO=... ANO=2026` executa preparação, carga nacional e seed.
O [levantamento do ETL](etl-planilhas-portal-bj.md) explica por que uma planilha
acumulada por ano basta para as telas atuais. Para uma comparação 2025 × 2026
com valores, carregue também o acumulado de 2025 com `ANO=2025`.

Em **dois terminais**, ambos na raiz:

```bash
# Terminal 1
make demo-backend
```

```bash
# Terminal 2
make demo-frontend
```

Abra **http://localhost:5173**. API/Swagger: http://localhost:8000/docs.
Os comandos descobrem as chaves da demo e configuram URL, CORS, tenant
obrigatório e conexão da importação. A chave de serviço só vai para o backend;
as chaves não são copiadas para arquivos. O Vite usa dados reais da demo.

O backend assume `ANO_DEFAULT=2026`, alterável no ambiente. `TENANT_SLUG=fejepe`
define a marca do login; após autenticar, marca e dados seguem o usuário. Se a
senha do papel de carga mudou, exporte `INGESTAO_SENHA` também ao iniciar a API.

| Usuário local | Papel | Federação |
|---|---|---|
| `um@teste.local` | admin | FEJEPE |
| `dois@teste.local` | admin | FEJEMG |
| `<slug>@teste.local` | admin | Cada uma das outras 25 federações |
| `op@teste.local` | plataforma | FEJEPE nos dados de EJ; gestão de todas no painel |

Senha de desenvolvimento: `demo1234` (ou `DEMO_SENHA` usada no seed).
O `make demo-seed` cria essas 27 contas administrativas apenas na demo local;
o slug de cada federação aparece no painel da plataforma. Para acesso real,
é preciso cadastrar o endereço da pessoa responsável por cada federação.

```bash
make demo-smoke   # login, endpoints, paginação e acesso cruzado entre tenants
make demo-stop    # para o Supabase e preserva os dados
```

`demo-smoke` usa FastAPI TestClient com Auth e PostgREST reais, sem precisar de
uvicorn no ar; não imprime dados de EJs. Verifica leitura e isolamento, sem
convites ou uploads. Pare API e Vite com Ctrl+C nos respectivos terminais.

| Serviço | Endereço |
|---|---|
| API Supabase (Kong) | http://127.0.0.1:54421 |
| Banco demo | localhost:54422 |
| Studio | http://localhost:54423 |
| E-mails locais (Mailpit) | http://localhost:54424 |

`make demo-status` imprime também chaves: não compartilhe a saída.
`make demo-reset` **apaga os dados da demo** e recria schema; refaça carga e
seed depois. `demo-schema` é para banco novo: as migrações históricas não são
todas idempotentes. Não existe cópia delas em `supabase/migrations/`.

Se a demo já existia antes da migração 16, aplique **somente** esse arquivo,
preservando os dados, antes de iniciar a API:

```bash
psql postgresql://postgres:postgres@127.0.0.1:54422/postgres \
  -X -v ON_ERROR_STOP=1 -f infra/db/init/16-projetos-colaborativos.sql
```

Depois reenvie a exportação acumulada pelo painel (simular → gravar) para
preencher os contratos colaborativos das linhas antigas. O admin da federação
encontra o upload em **Administração → Importar planilha** e pode usar o arquivo
nacional; só as linhas da própria federação são aplicadas. Use a exportação
acumulada mais recente do ano e confira no relatório se o mês mais novo entrou.

## Docker para uma instalação configurada

```bash
cp .env.example .env   # somente se ainda não existir; preencha os valores
make up               # nginx :8080 + API :8000
make down
```

`make dev` inicia apenas `backend-dev` e `frontend-dev`, em segundo plano;
`make dev-down` para esses serviços. Não rode `up`, `dev` e a API no host ao
mesmo tempo: compartilham portas.

`SUPABASE_ANON_KEY` é a chave de leitura sob RLS. `SUPABASE_SERVICE_KEY` é
opcional, exclusiva do convite no backend. `INGESTAO_DSN` precisa usar o papel
`ingestao`. No Compose, `.env` é o da **raiz**. Swagger exige
`DOCS_ENABLED=true` no modo `up`; em desenvolvimento ele está ligado.

Para a demo local, prefira os comandos no host: `127.0.0.1` dentro de um
container aponta para esse container, não para a stack Supabase no host.

## Laboratório persistente

```bash
make lab        # aguarda o banco saudável em :55432
make lab-down   # para preservando o volume
```

O lab testa modelagem multi-tenant, RLS e ingestão; usa shim de Auth e não serve
login para o portal. Migrações só rodam automaticamente com volume vazio.
`make clean` **apaga volumes do Compose**, inclusive o lab. Detalhes em
[infra/db/README.md](../infra/db/README.md).

## Se der errado

| Sintoma | Ação |
|---|---|
| Docker indisponível | Abra Docker Desktop e rode `make doctor` |
| Dependência ausente | Rode `make setup` |
| Demo com schema antigo | Revise migrações; use `demo-reset` apenas se puder apagar os dados |
| Login falha | Confira `make demo-seed` e `DEMO_SENHA` |
| Porta ocupada | Pare a execução anterior; o Vite da demo recusa mudar de porta |
| Erro de CORS | Abra `localhost:5173`; confira a origem no backend |
| Convite responde 503 | Configure a chave de serviço no backend |
| Upload responde 503 | Configure `INGESTAO_DSN` com papel de ingestão |

O modo mock cobre parte das chamadas, mas o portal continua exigindo login;
ele não substitui a demo. A calculadora de cluster é um app Vite independente
em `tools/cluster-calculator/` (`npm ci && npm run dev`).
