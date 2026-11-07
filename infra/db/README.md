# Laboratório de dados — Postgres local

Para que serve: verificar modelagem multi-tenant, ingestão e isolamento por RLS.
`make test` usa outro banco, descartável, e reaplica todas as migrações sem
apagar este laboratório ou tocar na produção.

```bash
make lab                      # sobe o Postgres em localhost:55432
```

Os scripts `init/00..NN` são executados automaticamente na primeira subida
(o Postgres só executa `/docker-entrypoint-initdb.d` com o volume vazio —
para recriar, rode `make clean` antes).

A migração 21 (`21-privilegios-minimos.sql`) normaliza os privilégios de
clientes entre laboratório e Supabase: remove ALL histórico, conserva a
lista explícita de leituras/escritas autorizadas e exige GRANT em objetos
novos. Ela pode ser aplicada isoladamente num banco existente sem reset.
Defaults pertencem ao role criador: executar sob o dono das migrações e
inventariar outros criadores antes do deploy. Consulte
[a verificação de 07/10](../../docs/verificacao-privilegios-2026-10-07.md).

## Carregar dados

A planilha de monitoramento do Portal BJ (nível EJ) entra pela ingestão
versionada em `backend/app/ingestao/`, que substitui o fluxo de n8n:

```bash
make lab
# primeiro simule: roda a carga inteira e desfaz no fim
make importar ARQUIVO=~/Documents/TCC/dados/monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx \
              ANO=2026 ESCOPO=--todas-federacoes DRY=1
# depois grave
make importar ARQUIVO=~/Documents/TCC/dados/monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx \
              ANO=2026 ESCOPO=--todas-federacoes
```

`ESCOPO="--federacao fejepe"` grava só a fatia de uma federação e conta o resto
como ignorado. Não há default de escopo, de propósito.
O [levantamento das exportações](../../docs/etl-planilhas-portal-bj.md) explica
por que o acumulado é a única planilha necessária para as telas atuais.

A carga conecta como `app_ingestao` (papel sujeito a RLS, sem DELETE — ver
`init/10` e `init/11`) e se recusa a rodar como `portal`, que é dono das tabelas
e passa por cima da RLS. É upsert idempotente: rodar o mesmo arquivo de novo não
muda nada, e uma exportação nova sobrescreve os meses corrigidos. Cada carga fica
em `ingestao_carga` (com o relatório em `resumo`) e as linhas brutas em
`ingestao_staging_ej`.

> Nunca versione as exportações: são dados reais de EJs. `infra/db/seed/` está
> no `.gitignore`, e as planilhas ficam em `~/Documents/TCC/dados/`, fora do
> repositório.

## Os scripts de `init/` só rodam com o volume vazio

Isto não é óbvio e já custou tempo: o Postgres executa
`/docker-entrypoint-initdb.d` **uma única vez**, na primeira subida, quando o
diretório de dados ainda está vazio. Criar ou editar um arquivo em `init/` e
rodar `make lab` de novo **não aplica nada** — o container sobe, fica saudável,
e o schema continua o antigo. Para uma migração aditiva, como a 16, preserve o
volume e aplique só o arquivo pendente:

```bash
psql postgresql://portal:portal@127.0.0.1:55432/portal_lab \
  -X -v ON_ERROR_STOP=1 -f infra/db/init/16-projetos-colaborativos.sql
```

Para recriar o laboratório inteiro (operação destrutiva):

```bash
make clean && make lab      # APAGA o volume e roda init/ do zero
```

Depois de subir, confira que nenhum script falhou (o Postgres segue de pé mesmo
com erro de SQL no meio do init):

```bash
docker compose --profile lab logs db | grep -iE "ERROR|FATAL|WARNING"
```

Ordem de execução: alfabética. Daí a numeração — um arquivo que depende do
anterior precisa de um número maior. É por isso que o shim de `auth` é `00-`:
as políticas de RLS de `07-` referenciam funções que ele cria.

## O que já está no schema

| Arquivo | O que faz |
|---|---|
| `00-shim-auth-local.sql` | `auth.jwt()`/`auth.uid()` e os roles do Supabase, **só para o lab** |
| `01-schema.sql` | as três tabelas originais (`empresa_junior`, `metas`, `monitoramento`) |
| `02-federacao.sql` | tabela `federacao` + seed das 27 federações |
| `03-nucleo-e-plano.sql` | tabelas `nucleo` e `plano` (catálogo, sem cobrança) |
| `04-federacao-id-empresa-junior.sql` | `federacao_id` NOT NULL; `federacao` → `federacao_legado` |
| `05-metas-monitoramento-generalizacao.sql` | tenant de `metas`/`monitoramento` nos três níveis |
| `06-usuario.sql` | tabela `usuario` + hook de access token do Supabase |
| `07-rls-policies.sql` | RLS ligada e políticas de SELECT por tenant |
| `08-cluster-historico.sql` | cluster por EJ por ano; colunas `cluster_20XX` viram `_legado` |
| `09-federacao-branding.sql` | logo e cor por federação; leitura pública das colunas de branding para `anon` |
| `10-ingestao-staging.sql` | papel `ingestao`; `ingestao_carga` (proveniência) e `ingestao_staging_ej` (linha bruta), com RLS |
| `11-ingestao-escrita.sql` | PKs geradas; núcleo único por (federação, nome); escrita do papel `ingestao` sob RLS, por coluna |
| `12-nucleo-portal-bj.sql` | seed dos 26 núcleos com o ID do Portal BJ |
| `13-painel-admin.sql` | papel `plataforma`; escrita em `usuario`/`federacao` pelo painel; `admin_listar_usuarios()` com o último login; shim de `auth.users` só no lab (ver ADR-003) |
| `14-federacao-slogan.sql` | slogan opcional e leitura pública como branding |
| `15-painel-admin-slogan.sql` | UPDATE de `federacao.slogan` para o operador |
| `16-projetos-colaborativos.sql` | Contratos colaborativos mensais para o filtro e a comparação |
| `18-controle-consultas-ia.sql` | Limites operacionais por usuário/federação por minuto para o Nexo |
| `19-creditos-ia-tenant.sql` | Cota mensal de criação de dashboards por federação, reserva/consumo/estorno via RPC autenticada |

## Carregar dados depois destas migrações

`empresa_junior.federacao_id` é **NOT NULL e sem default**. Um `\copy` direto de
CSV só funciona se o arquivo trouxer a coluna. Isso é intencional: sem default,
uma carga que esqueceu o tenant falha na hora, em vez de rotular as EJs de outra
federação como FEJEPE. A ingestão (`make importar`) resolve o tenant de cada
linha pela coluna FEDERACAO e aborta se aparecer federação desconhecida.

## Por que a porta é 55432

Postgres instalado na máquina (Homebrew `postgresql@16`, Postgres.app) escuta em
`127.0.0.1:5432`. O container publica no coringa `*:5432`, e o bind específico
ganha: toda conexão a `localhost:5432` vai para o banco da máquina, não para o
laboratório. O sintoma é `FATAL: role "portal" does not exist` — e o sintoma
ruim é quando o banco da máquina *tem* um role com esse nome, e aí a consulta
responde do lugar errado sem reclamar.

Daí o default `POSTGRES_PORT=55432`. Para conferir com qual você está falando:

```bash
docker compose ps db                       # confere a porta publicada
psql postgresql://portal:portal@localhost:55432/portal_lab -c "select current_database()"
```

## Destino novo de testes externos (Supabase gerenciado ou self-hosted)

`init/` continua sendo a fonte única. Não copie os arquivos para outra pasta de
migrações. Use Python 3.11 e instale `backend/requirements.lock` com
`pip install --require-hashes -r backend/requirements.lock`.

Configure `PORTAL_DATABASE_URL` na sessão por um gerenciador de segredos ou leitura
oculta; use conexão direta ao PostgreSQL (não pooler em modo transaction), TLS no
destino externo e o dono das migrações. Não inclua DSN/senha no histórico, argumentos
ou relatório. Do diretório `backend/`:

```bash
python -m scripts.migrar_banco                         # somente leitura, mostra SHA256
python -m scripts.migrar_banco --apply --confirm-database postgres
python -m scripts.migrar_banco                         # deve mostrar zero pendentes
```

O migrador exclui `00` (shim estritamente local), aplica `01..23` ordenadamente,
registra cada arquivo no schema privado `portal_operacao`, valida checksums e usa
lock para serializar operadores. Cada migração e seu ledger são atômicos. O executor resolve a precondição
de membership temporária do role `ia_limitador` para migrações 18/19/20/23,
mantém a capacidade de administrar ACLs até o fim e restaura as concessões próprias
preexistentes (incluindo flags PG16). Outros grantors não são alterados. Os arquivos
históricos 19/20 permanecem intactos; não os execute diretamente com um dono
limitado fora deste executor. A migração aditiva 23 corrige ACLs de funções já
existentes, inclusive a 18 quando aplicada por scripts antigos. A revisão
padrão usa sessão somente leitura. O ledger impede reaplicar a migração 04, que
renomeia colunas. Banco já existente sem ledger é recusado: inventarie o schema,
aplique somente arquivos comprovadamente pendentes e preserve dados/volumes;
não registre migrações presumidas nem execute todas novamente.

Depois das migrações, ative `public.custom_access_token_hook` em **Authentication →
Hooks → Customize Access Token** no Supabase gerenciado; em self-hosted configure
GoTrue com o hook equivalente conforme `supabase/config.toml`. A existência da
função não significa que Auth a usa. Antes de compartilhar acesso, confirme num
login novo que o JWT carrega `federacao_id` e `papel` e que consultas retornam apenas
as linhas daquele tenant. Configure SMTP e URLs de callback/recuperação antes dos
convites. Para carga direta, crie login próprio membro de `ingestao` com senha nova,
sem privilégios de dono; confira USAGE em `auth` com o proprietário do schema.

### Criar primeiro operador novo

O script administrativo fica fora do request path; somente ele recebe
`SUPABASE_SERVICE_ROLE_KEY`. Configure também `SUPABASE_URL` e o DSN do mesmo
projeto. A revisão não chama Auth nem recebe senha; a aplicação exige confirmação
do hostname. A senha é solicitada sem eco, ou pode vir de
`PORTAL_OPERATOR_PASSWORD` via gerenciador de segredos. Sem senha padrão:

```bash
python -m scripts.criar_operador --email operador@seu-dominio.example \
  --nome 'Operador' --federacao fejepe
python -m scripts.criar_operador --email operador@seu-dominio.example \
  --nome 'Operador' --federacao fejepe --apply \
  --confirm-project seu-projeto.supabase.co
```

Escolha email real novo, senha de pelo menos 12 caracteres e federação existente.
A criação confirma o email explicitamente (bootstrap autorizado pelo operador),
confere que o UUID existe em `auth.users` do banco destino, cria vínculo ativo
`plataforma` e não promove usuários existentes. Se Auth e DSN apontarem a projetos
diferentes, recusa o vínculo e compensa a criação Auth. Se vínculo SQL
falhar, tenta remover apenas a conta Auth recém-criada. Se rede/timeout deixar
resultado Auth incerto, confira o Dashboard antes de repetir; não altera nem
remove contas anteriores. Nunca use `seed_demo` no remoto: tem emails e senha
exclusivos de demonstração local. Remova as variáveis administrativas depois.

### Conferência de privilégios e isolamento no destino

Execute pelo SQL Editor sob o dono, sem usuário de aplicação:

```sql
SELECT r.rolname, t.tablename,
       has_table_privilege(r.rolname, format('public.%I',t.tablename), 'TRUNCATE') AS truncate_permitido
FROM pg_roles r CROSS JOIN pg_tables t
WHERE r.rolname IN ('anon','authenticated') AND t.schemaname='public';
-- Todos os truncate_permitido devem ser false.
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public';
-- Tabelas tenant têm RLS; catálogo plano é compartilhado intencionalmente.
SELECT has_function_privilege('anon','public.custom_access_token_hook(jsonb)','EXECUTE'),
       has_function_privilege('authenticated','public.custom_access_token_hook(jsonb)','EXECUTE');
-- Ambos false. Confirme execução concedida somente ao Auth e demais donos administrativos.
```

Cadastre duas contas/tenants com dados sintéticos diferentes. Faça login real em
cada uma e consulte a API pública e PostgREST com cada JWT; nenhuma linha do outro
tenant deve aparecer, inclusive forçando IDs/slug da outra federação. Confira
conta inativa, sem vínculo, endpoints administrativos e cota IA. Não use service
key para essa prova. `make test` cobre DB descartável com claims simulados;
`make demo-smoke` cobre GoTrue/PostgREST local; só o teste pelo endereço público
com os JWTs emitidos no destino valida a implantação externa.
