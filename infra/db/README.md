# Laboratório de dados — Postgres local

Para que serve: rodar a modelagem preditiva do TCC sobre uma cópia dos dados,
sem tocar na base de produção da FEJEPE.

```bash
make lab                      # sobe o Postgres em localhost:55432
```

O schema em `init/01-schema.sql` é criado automaticamente na primeira subida
(o Postgres só executa `/docker-entrypoint-initdb.d` com o volume vazio —
para recriar, rode `make clean` antes).

## Carregar dados

A planilha de monitoramento do Portal BJ (nível EJ) entra pela ingestão
versionada em `portal_fejepe/app/ingestao/`, que substitui o fluxo de n8n:

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
e o schema continua o antigo. Para aplicar:

```bash
make clean && make lab      # APAGA o volume e roda init/ do zero
```

Depois de subir, confira que nenhum script falhou (o Postgres segue de pé mesmo
com erro de SQL no meio do init):

```bash
docker compose --profile lab logs db | grep -iE "ERROR|FATAL"
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
