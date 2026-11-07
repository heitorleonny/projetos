-- 21 — Privilégios de clientes independentes da RLS.
-- TRUNCATE não avalia políticas RLS. O Supabase concede ALL por padrão;
-- o laboratório não. Convertemos ambos à mesma lista explícita de acesso.
-- Executar como o dono das tabelas/migrações (postgres no Supabase).
-- Não altera dados, policies, ingestao, ia_limitador ou service_role.
BEGIN;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, anon, authenticated;

-- Revogar SELECT de tabela acima mantém os GRANTs POR COLUNA existentes:
-- branding (09/14/17) e snapshot público (20). Tornamos a lista explícita.
GRANT SELECT (slug, nome, logo_url, cor_primaria, slogan, cor_secundaria, cor_acento)
    ON public.federacao TO anon;
GRANT SELECT ON public.federacao, public.nucleo, public.usuario,
    public.empresa_junior, public.metas, public.monitoramento, public.plano,
    public.cluster_historico, public.ingestao_carga, public.ingestao_staging_ej
    TO authenticated;

-- A escrita administrativa continua por coluna e sujeita às policies 13/17.
GRANT UPDATE (nome, status, logo_url, cor_primaria, updated_at, slogan,
    cor_secundaria, cor_acento) ON public.federacao TO authenticated;
GRANT INSERT (federacao_id, nome, email, papel) ON public.usuario TO authenticated;
GRANT UPDATE (federacao_id, nome, papel, ativo, updated_at)
    ON public.usuario TO authenticated;

-- Compatível também com a demo que ainda não recebeu 19/20. Controles IA
-- privados continuam privados; só a tabela de dashboard tem leitura direta.
DO $$ BEGIN
    IF to_regclass('public.dashboard_evento_ia') IS NOT NULL THEN
        GRANT SELECT ON public.dashboard_evento_ia TO authenticated;
        GRANT SELECT (id, publico, resultado_publico)
            ON public.dashboard_evento_ia TO anon;
    END IF;
END $$;

-- Nenhum cliente usa nextval/setval diretamente. Ingestão conserva seus
-- próprios privilégios; identity BY DEFAULT não exige USAGE do cliente.
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, anon, authenticated;

-- Defaults valem para o CRIADOR dos objetos, não para o schema inteiro.
-- As migrações devem usar este mesmo dono. Se outro role criar objetos,
-- executar as revogações de defaults também sob esse role. Não ampliar
-- membership para poder alterar supabase_admin em Supabase gerenciado.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
-- Também neutraliza concessões globais: defaults por schema só adicionam
-- privilégios e não podem cancelar os privilégios do nível global.
ALTER DEFAULT PRIVILEGES REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
-- PostgreSQL concede EXECUTE a PUBLIC globalmente: revogação global é
-- necessária, pois uma revogação por schema não cancela a concessão global.
-- RPCs já existentes conservam ACLs; novas RPCs exigem GRANT explícito.
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

COMMIT;
