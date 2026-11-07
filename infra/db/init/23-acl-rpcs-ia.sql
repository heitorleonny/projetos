-- 23 — Corrige ACLs de RPCs sob dono dedicado em Supabase não-superusuário.
-- O dono das migrações deve conservar membership até terminar REVOKE/GRANT.
-- O catálogo existente e os dados são preservados; não refaz 18/19/20.
BEGIN;
DO $$ BEGIN
    IF current_setting('server_version_num')::integer >= 160000 THEN
        EXECUTE 'GRANT ia_limitador TO ' || quote_ident(current_user) || ' WITH INHERIT TRUE, SET TRUE';
    ELSE
        EXECUTE 'GRANT ia_limitador TO ' || quote_ident(current_user);
    END IF;
END $$;
REVOKE ALL ON FUNCTION public.reservar_consulta_ia() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reservar_consulta_ia() TO authenticated;
REVOKE ALL ON FUNCTION public.reservar_creditos_ia(bigint, uuid, text, integer),
    public.confirmar_creditos_ia(uuid), public.estornar_creditos_ia(uuid)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.persistir_dashboard_evento_ia(text, text, jsonb, boolean, jsonb),
    public.atualizar_publicacao_dashboard_evento_ia(uuid, boolean, jsonb),
    public.consultar_creditos_dashboard_ia() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.persistir_dashboard_evento_ia(text, text, jsonb, boolean, jsonb),
    public.atualizar_publicacao_dashboard_evento_ia(uuid, boolean, jsonb),
    public.consultar_creditos_dashboard_ia() TO authenticated;
DO $$ BEGIN
    EXECUTE 'REVOKE ia_limitador FROM ' || quote_ident(current_user);
END $$;
NOTIFY pgrst, 'reload schema';
COMMIT;
