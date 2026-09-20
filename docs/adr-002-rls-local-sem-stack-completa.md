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
- **O destino de `cluster_2023..cluster_2026`.** Decisão em aberto. As colunas não
  foram normalizadas, renomeadas nem apagadas — e nem sequer indexadas, porque um
  índice já fixaria o formato delas.
- **Políticas de INSERT/UPDATE/DELETE.** Só SELECT. Escrita entra junto com a
  regra de permissão por papel na aplicação, não antes.

## O que precisa acontecer MANUALMENTE no Supabase hospedado

Nada nesta entrega tocou a nuvem. Quando o projeto for de fato conectado, nesta
ordem:

1. **Aplicar as migrações** `01` a `07` de `infra/db/init/` pelo SQL Editor ou
   pela CLI. **Pular `00-shim-auth-local.sql`** — lá o schema `auth`, as funções
   e os roles são da plataforma. Conferir antes, com
   `infra/db/queries/02-inventario-schema.sql`, que o schema real bate com o que
   as migrações assumem; `01-schema.sql` foi derivado da documentação, não de um
   dump.
2. **Revisar o backfill de `federacao_id`.** `04-federacao-id-empresa-junior.sql`
   assume que toda EJ é da FEJEPE (id 12). A premissa vale hoje e é datada —
   conferir contra `federacao_legado` antes de rodar, e nunca rodar duas vezes.
3. **Preencher `usuario.auth_user_id`** para cada usuário existente do Auth. Sem
   isso o hook não acha ninguém.
4. **Ativar o Custom Access Token Hook**: Dashboard → Authentication → Hooks →
   Customize Access Token → selecionar `public.custom_access_token_hook` →
   Enable. A função existe desde `06-usuario.sql`, mas **não roda sozinha** — até
   alguém ligar o gatilho, nenhum JWT emitido carrega `federacao_id` nem `papel`.
5. **Trocar as chaves no ambiente**: `SUPABASE_ANON_KEY` no backend (é a que
   respeita RLS); `SUPABASE_SERVICE_KEY` só onde script administrativo roda, e
   nunca no container da API.
6. **Virar `TENANT_CLAIM_OBRIGATORIO=true`** — no mesmo dia em que o hook for
   ativado, não antes. Antes, ela trancaria todo mundo para fora; depois, ela
   transforma "token sem tenant" de tolerado em 403.

Até o passo 4, o comportamento observável da API é o de hoje: todo autenticado
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
