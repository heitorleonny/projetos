# ADR-002 — Testar Row Level Security num Postgres comum, sem a stack do Supabase

- **Data:** 20/09/2026
- **Status:** aceito
- **Contexto:** implementação das fases 1 a 3 do cronograma multi-tenant (modelar
  a federação, isolar dados com RLS, separar papéis)

## Questão

As políticas de RLS precisam ser verificadas antes de tocarem no Supabase
hospedado. Verificar RLS exige um banco com o schema `auth`, com as funções
`auth.jwt()`/`auth.uid()` e com um role que não seja dono das tabelas. O caminho
óbvio seria subir o Supabase local completo (`supabase start`). Vale?

## Decisão

**Não.** As políticas são testadas contra o Postgres do perfil `lab`, com um
arquivo de ~30 linhas — `infra/db/init/00-shim-auth-local.sql` — que recria a
interface de que elas dependem: o schema `auth`, as duas funções e os roles
`anon` / `authenticated` / `service_role`.

## Por quê

**1. O ADR-001 já rejeitou a stack completa, e por um motivo que continua de
pé:** são sete containers a mais para uma necessidade que um container resolve.
Nada no que precisa ser verificado aqui depende do GoTrue, do Studio ou do
Realtime.

**2. O shim não é uma aproximação — é a mesma interface.** Em produção, quem
informa quem é o usuário não é o GoTrue: é o PostgREST, que injeta os claims do
JWT como configuração de sessão (`request.jwt.claims`). As funções `auth.jwt()`
e `auth.uid()` do Supabase apenas leem essa configuração. Reproduzir isso num
Postgres comum é copiar duas funções de leitura.

A consequência prática: **as políticas de `07-rls-policies.sql` sobem no
Supabase hospedado sem uma linha de alteração**, porque dependem só de
`auth.jwt()` — que lá é nativa. O arquivo de shim é o único que não se aplica lá.

**3. O teste que importa exige um role separado, e isso o shim dá.** RLS não se
aplica ao dono da tabela nem a superusuário. Se os testes conectassem como
`portal`, todos passariam — inclusive com política errada, inclusive sem
política nenhuma. O role `app_authenticated` existe para que o teste de
isolamento realmente teste isolamento. Verificado por mutação: trocar a política
de `empresa_junior` por `USING (true)` quebra 10 dos 49 testes.

## O que ficou de fora, de propósito

Registrado aqui para que a ausência não seja lida como esquecimento:

- **Cobrança e limites de plano.** `plano` é catálogo: as colunas
  `limite_usuarios` e `limite_creditos_ia_mes` existem, e nada as lê. Os preços
  semeados são placeholder inventado, não a precificação real.
- **Convite por e-mail e criação de usuário.** `usuario` é desenho de tabela. Não
  há fluxo de convite, não há tela, não há endpoint.
- **Vínculo real com o Supabase Auth.** A coluna `usuario.auth_user_id` existe e
  fica `NULL`. Sem ela preenchida, o hook de access token não encontra ninguém e
  devolve o token intacto.
- **Catálogo de indicadores.** As colunas de métrica nomeadas
  (`meta_faturamento`, `faturamento_mes`, `csat`, …) continuam como estão. Não há
  tabela `indicador`, não há pivô para linha-por-indicador. A generalização feita
  foi só da dimensão de tenant. Pivotar quebraria os 22 pontos de acesso via
  PostgREST e os testes que fixam valores exatos.
- **O destino de `cluster_2023..cluster_2026`.** Estava em aberto quando este ADR
  foi escrito; foi decidido depois, na migração 08: as colunas viraram a tabela
  `cluster_historico (id_ej, ano, cluster)` e as antigas sobreviveram com sufixo
  `_legado`. O problema delas era de PERÍODO (uma coluna por ano), não de tenant —
  por isso a saída foi normalizar, e não repetir o que 05 fez com `metas` e
  `monitoramento`. Isso não reabre a generalização das colunas de métrica, que
  continua descartada: `cluster_historico` é uma tabela para UM fato, não um
  catálogo `indicador`.
- **Políticas de INSERT/UPDATE/DELETE.** Só SELECT. Escrita entra junto com a
  regra de permissão por papel na aplicação, não antes.

## O que precisa acontecer MANUALMENTE no Supabase hospedado

Nada nesta entrega tocou a nuvem. Quando o projeto for de fato conectado, nesta
ordem:

1. **Aplicar as migrações** `01` a `08` de `infra/db/init/` pelo SQL Editor ou
   pela CLI. **Pular `00-shim-auth-local.sql`** — lá o schema `auth`, as funções
   e os roles são da plataforma. Conferir antes, com
   `infra/db/queries/02-inventario-schema.sql`, que o schema real bate com o que
   as migrações assumem; `01-schema.sql` foi derivado da documentação, não de um
   dump.
2. **Revisar o backfill de `federacao_id`.** `04-federacao-id-empresa-junior.sql`
   assume que toda EJ é da FEJEPE (id 12). A premissa vale hoje e é datada —
   conferir contra `federacao_legado` antes de rodar, e nunca rodar duas vezes.
3. **Reconferir o backfill de `cluster_historico` (migração 08) antes de rodá-lo.**
   O backfill lê `cluster_2023..cluster_2026` e, como último recurso, a coluna
   `cluster` sem sufixo. **Essa coluna pode não existir de verdade no Supabase:**
   `01-schema.sql` foi derivado da documentação do projeto, não de um dump
   (docs/levantamento-semana1-multitenant.md, seção 1, registra a divergência
   entre schema real e documentado). Rodar `infra/db/queries/02-inventario-schema.sql`
   primeiro e conferir quais dessas cinco colunas existem de fato; se a `cluster`
   bare não existir, o segundo INSERT do arquivo 08 sai da migração — e nada se
   perde, porque ele só cobre EJs sem nenhuma coluna anual preenchida. Isso não
   bloqueia nada no laboratório local, onde as cinco colunas existem.
4. **Preencher `usuario.auth_user_id`** para cada usuário existente do Auth. Sem
   isso o hook não acha ninguém.
5. **Ativar o Custom Access Token Hook**: Dashboard → Authentication → Hooks →
   Customize Access Token → selecionar `public.custom_access_token_hook` →
   Enable. A função existe desde `06-usuario.sql`, mas **não roda sozinha** — até
   alguém ligar o gatilho, nenhum JWT emitido carrega `federacao_id` nem `papel`.
6. **Trocar as chaves no ambiente**: `SUPABASE_ANON_KEY` no backend (é a que
   respeita RLS); `SUPABASE_SERVICE_KEY` só onde script administrativo roda, e
   nunca no container da API.
7. **Virar `TENANT_CLAIM_OBRIGATORIO=true`** — no mesmo dia em que o hook for
   ativado, não antes. Antes, ela trancaria todo mundo para fora; depois, ela
   transforma "token sem tenant" de tolerado em 403.

Até o passo 5, o comportamento observável da API é o de hoje: todo autenticado
lê, com papel `membro` assumido e sem filtro de tenant no código. O isolamento
já está no banco esperando o claim.

## Consequências

- A suíte ganhou uma dependência de teste (`psycopg`) e um módulo que só roda com
  `make lab` no ar. Sem o laboratório, `tests/test_rls.py` é pulado e `pytest -q`
  continua verde — quem não subiu o Docker não fica bloqueado, mas também não
  está verificando RLS. Rodar com o lab no ar antes de confiar no resultado.
- O laboratório passou a publicar em **55432**, não 5432: um Postgres instalado na
  máquina (Homebrew, Postgres.app) ocupa a 5432 e sequestra as conexões a
  `localhost`. O sintoma foi `role "portal" does not exist`; o sintoma perigoso
  seria responder do banco errado sem reclamar.
- O filtro por `federacao_id` no código é redundante com a RLS **de propósito**.
  Quem achar isso desnecessário num refactor futuro: ver `app/services/tenant.py`,
  que explica por que as duas camadas existem.

---

## Adendo (22/09/2026) — agora são DOIS ambientes locais

Quem chegar neste repositório, ler o ADR-001, ver que ele rejeitou a stack
completa do Supabase, e então encontrar um `supabase/config.toml` versionado,
vai achar que alguém mudou de ideia sem escrever. Não mudou. O que aconteceu
foi outra coisa: apareceu um caso de uso que nenhum dos dois ADRs cobria.

### O que este adendo não é

**Não é a revogação do ADR-001 nem deste ADR.** As duas decisões seguem de pé
para o que elas decidiram: o Supabase continua sendo o banco da aplicação, e o
teste de RLS continua rodando no Postgres do perfil `lab`, com o shim, porque
ali um container resolve o que sete resolveriam.

### O caso que faltava

Os dois ADRs decidiram sobre **modelagem de dados e teste de política**. Para
isso o shim basta, e o argumento continua correto: em produção quem informa o
usuário às políticas não é o GoTrue, é o PostgREST, que injeta os claims do JWT
como configuração de sessão. Reproduzir isso é copiar duas funções de leitura.

O que apareceu depois foi **validação visual com autenticação real**: abrir a
tela, logar como gente de duas federações diferentes, e ver o isolamento
acontecer. E esse é exatamente o ponto onde o shim não serve — ele replica
`auth.jwt()`, **não o GoTrue que emite o token**. Sem GoTrue não há login, sem
login não há JWT, e sem JWT o Custom Access Token Hook nunca roda. O hook é o
que leva `federacao_id` e `papel` para dentro do token; até ele rodar, todo o
isolamento multi-tenant está no banco esperando um claim que ninguém emite.

Dito de outro jeito: o trabalho das fases 1 a 3 foi validado por teste e por
SQL, e ninguém nunca tinha aberto a tela com mais de uma federação dentro.

### Os dois ambientes, e quando usar cada um

| | `make lab` | `make demo` |
|---|---|---|
| O que sobe | 1 container: Postgres | 11 containers: a stack Supabase |
| Porta do banco | 55432 | 54422 |
| Schema `auth` | shim de `00-shim-auth-local.sql` | real, da plataforma |
| Quem diz quem é o usuário | `SET request.jwt.claims` no psycopg | GoTrue, com login de verdade |
| Custom Access Token Hook | não existe | ligado em `supabase/config.toml` |
| PostgREST / Studio | não | sim |
| Para que serve | `pytest -q`, `tests/test_rls.py`, modelagem do TCC | abrir a tela e olhar |
| Custo de subir | segundos | minutos, e ~10 GB de imagem |

**Use o `lab`** para qualquer coisa que uma consulta SQL responda: escrever
política, testar isolamento, rodar a suíte, explorar dado para a modelagem. É
o ambiente do dia a dia, e continua sendo.

**Use o `demo`** quando a pergunta só se responde olhando: a tela mostra o
número certo para esta federação? o branding cai no fallback sem quebrar? o
login devolve um token com tenant? É o ambiente de sessão de validação com
usuário, não o de desenvolvimento.

### Decisões de montagem que valem registrar

- **`infra/db/init/` continua fonte única.** As migrações **não** foram
  copiadas para `supabase/migrations/`. Duas cópias divergiriam na primeira
  migração nova, e aí ninguém sabe qual vale. O `make demo` aplica `01..12`
  por `psql`, com `ON_ERROR_STOP=1`.
- **O `00-shim-auth-local.sql` é pulado no `demo`**, pelo motivo que este ADR
  já dava para o Supabase hospedado: lá o schema `auth`, as funções e os roles
  são de verdade, e o shim por cima é conflito.
- **As portas são do bloco 544xx**, não o 543xx padrão da CLI. Não foi
  preferência: havia outra stack Supabase na máquina de desenvolvimento
  ocupando 54321-54327. O `project_id` também é próprio
  (`portal-fejepe-demo`), para os containers não colidirem no nome.
- **O login da ingestão é criado pelo `Makefile`, não pelo SQL.** A migração 10
  cria `ingestao` (NOLOGIN) sempre, mas só cria o login `app_ingestao` quando
  **não** detecta `supabase_auth_admin` — isto é, só no laboratório. No `demo`
  esse role existe, então o login é ação de operador, com a senha vindo de
  variável de ambiente e nunca de SQL versionado. É o mesmo desenho que a
  própria migração 10 descreve para o Supabase hospedado.

### O que o `demo` torna obsoleto na seção "o que precisa acontecer MANUALMENTE"

Os passos 4 e 5 daquela lista (preencher `usuario.auth_user_id` e ativar o
hook) continuam valendo **para o Supabase hospedado**, onde o hook é ação de
Dashboard. No ambiente local eles deixaram de ser manuais: o hook é
configuração versionada, e `scripts/seed_demo.py` cria os usuários no Auth e
grava `auth_user_id` na ordem certa — primeiro a linha em `usuario`, depois o
login, porque o hook procura em `usuario` e devolve o token intacto se não
achar ninguém.
