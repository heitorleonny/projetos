# Laboratório de dados — Postgres local

Para que serve: rodar a modelagem preditiva do TCC sobre uma cópia dos dados,
sem tocar na base de produção da FEJEPE.

```bash
make lab                      # sobe o Postgres em localhost:5432
```

O schema em `init/01-schema.sql` é criado automaticamente na primeira subida
(o Postgres só executa `/docker-entrypoint-initdb.d` com o volume vazio —
para recriar, rode `make clean` antes).

## Carregar dados

Ainda não há carga automatizada. O caminho previsto:

1. Exportar as três tabelas do Supabase em CSV (Table Editor → Export, ou
   `pg_dump` via a connection string do projeto).
2. Copiar os CSVs para `infra/db/seed/`.
3. `\copy empresa_junior FROM 'seed/empresa_junior.csv' CSV HEADER` (idem para
   as outras duas, nesta ordem por causa das foreign keys).

> Nunca versione os CSVs: são dados reais de EJs. `infra/db/seed/` está no
> `.gitignore`.
