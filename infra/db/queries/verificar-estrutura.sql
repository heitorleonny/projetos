-- Diagnóstico somente leitura, sem nomes, contatos ou valores de EJs.
-- Executar com psql -X -v ON_ERROR_STOP=1 -f neste arquivo, no lab ou na demo.
BEGIN READ ONLY;

SELECT tablename AS tabela, rowsecurity AS rls_ativa
  FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

SELECT tablename AS tabela, cmd AS operacao, count(*) AS politicas
  FROM pg_policies WHERE schemaname = 'public'
 GROUP BY tablename, cmd ORDER BY tablename, cmd;

SELECT c.relname AS tabela, con.contype AS tipo, count(*) AS restricoes
  FROM pg_constraint con
  JOIN pg_class c ON c.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public'
 GROUP BY c.relname, con.contype ORDER BY c.relname, con.contype;

SELECT tablename AS tabela, indexname AS indice, indexdef AS definicao
  FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;

SELECT grantee AS papel, table_name AS tabela,
       string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privilegios
  FROM information_schema.role_table_grants
 WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')
 GROUP BY grantee, table_name ORDER BY grantee, table_name;

SELECT rolname AS papel, rolsuper AS superusuario, rolbypassrls AS ignora_rls
  FROM pg_roles
 WHERE rolname IN ('anon', 'authenticated', 'ingestao', 'app_ingestao', 'app_authenticated')
 ORDER BY rolname;

SELECT count(*) AS ejs_com_nucleo_de_outra_federacao
  FROM public.empresa_junior ej
  JOIN public.nucleo n ON n.id = ej.nucleo_id
 WHERE ej.federacao_id <> n.federacao_id;

COMMIT;
