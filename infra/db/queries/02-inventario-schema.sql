-- ============================================================================
-- 02 — Inventário do schema real (Supabase)
--
-- Objetivo: substituir a documentação (banco.md, init/01-schema.sql) por uma
-- fonte de verdade extraída do banco, ANTES de escrever a primeira migração
-- multi-tenant. Nenhuma query aqui escreve nada.
--
-- Como rodar: Supabase → SQL Editor. Rode um bloco por vez e exporte cada
-- resultado em CSV (botão "Download CSV"). Guarde os CSVs em infra/db/seed/
-- (que está no .gitignore) ou cole o resultado no chat.
--
-- Alternativa preferível, se você tiver a connection string:
--   pg_dump --schema-only --no-owner --no-privileges \
--     --schema=public "$SUPABASE_DB_URL" > infra/db/dump-producao-schema.sql
-- Esse dump é o baseline ideal e pode ser versionado (não contém dado de EJ).
-- ============================================================================


-- ── A. Colunas: nome, tipo, nullability, default ────────────────────────────
-- Responde: quais colunas existem de fato, e quais já são NOT NULL.
select
    c.table_name,
    c.ordinal_position,
    c.column_name,
    c.data_type,
    c.character_maximum_length,
    c.numeric_precision,
    c.is_nullable,
    c.column_default
from information_schema.columns c
where c.table_schema = 'public'
order by c.table_name, c.ordinal_position;


-- ── B. Constraints: PK, FK, UNIQUE, CHECK ───────────────────────────────────
-- Responde: id_ej é realmente UNIQUE? as FKs de metas/monitoramento existem
-- no banco ou só na documentação? há CHECK em mes?
select
    con.conrelid::regclass          as tabela,
    con.conname                     as constraint_name,
    case con.contype
        when 'p' then 'PRIMARY KEY'
        when 'f' then 'FOREIGN KEY'
        when 'u' then 'UNIQUE'
        when 'c' then 'CHECK'
        else con.contype::text
    end                             as tipo,
    pg_get_constraintdef(con.oid)   as definicao
from pg_constraint con
join pg_class rel on rel.oid = con.conrelid
where con.connamespace = 'public'::regnamespace
  and rel.relkind = 'r'
order by tabela::text, tipo, constraint_name;


-- ── C. Índices existentes ───────────────────────────────────────────────────
-- Responde: qual é a linha de base de índices, para medir o efeito dos
-- índices com federacao_id como coluna líder (evidência para o Cap. 5).
select
    tablename,
    indexname,
    indexdef
from pg_indexes
where schemaname = 'public'
order by tablename, indexname;


-- ── D. Estado da Row Level Security ─────────────────────────────────────────
-- Responde: a RLS está ligada em alguma tabela? existe alguma policy hoje?
-- Se relrowsecurity = false em tudo, o isolamento atual é 100% aplicação.
select
    rel.relname                as tabela,
    rel.relrowsecurity         as rls_habilitada,
    rel.relforcerowsecurity    as rls_forcada_para_owner
from pg_class rel
where rel.relnamespace = 'public'::regnamespace
  and rel.relkind = 'r'
order by rel.relname;

select
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual        as usando,
    with_check  as com_check
from pg_policies
where schemaname = 'public'
order by tablename, policyname;


-- ── E. Volume por tabela ────────────────────────────────────────────────────
-- Responde: o backfill cabe numa transação só? (com poucos milhares de linhas,
-- sim — não é preciso migração em lotes nem NOT VALID/VALIDATE).
select
    relname                          as tabela,
    n_live_tup                       as linhas_estimadas,
    pg_size_pretty(pg_total_relation_size(relid)) as tamanho_total
from pg_stat_user_tables
where schemaname = 'public'
order by n_live_tup desc;


-- ── F. Views, funções e triggers em public ──────────────────────────────────
-- Responde: existe algo além das tabelas que a migração possa quebrar?
select table_name, view_definition
from information_schema.views
where table_schema = 'public';

select p.proname as funcao, pg_get_function_identity_arguments(p.oid) as args
from pg_proc p
where p.pronamespace = 'public'::regnamespace
order by p.proname;

select event_object_table as tabela, trigger_name, action_timing, event_manipulation
from information_schema.triggers
where trigger_schema = 'public'
order by tabela, trigger_name;


-- ── G. Usuários e claims (decisão usuário ↔ federação) ──────────────────────
-- Responde: quantos usuários existem, e já há algum dado de tenant no
-- app_metadata que possa virar a claim da policy de RLS?
-- (Se o SQL Editor não permitir ler auth.users, pule — dá para ver na aba
-- Authentication → Users.)
select
    id,
    email,
    created_at,
    last_sign_in_at,
    raw_app_meta_data,
    raw_user_meta_data
from auth.users
order by created_at;
