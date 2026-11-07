-- Dashboards por evento: plano fechado + snapshot público aprovado.
BEGIN;

CREATE TABLE IF NOT EXISTS public.dashboard_evento_ia (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    federacao_id bigint NOT NULL REFERENCES public.federacao(id) ON DELETE CASCADE,
    criado_por uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    evento_id text NOT NULL CHECK (length(evento_id) BETWEEN 1 AND 80),
    titulo text NOT NULL CHECK (length(titulo) BETWEEN 3 AND 100),
    plano jsonb NOT NULL CHECK (
        jsonb_typeof(plano) = 'object'
        AND plano ?& ARRAY['titulo','metrica','agregacao','dimensao','visualizacao','ano','mes_inicio','mes_fim','limite']
        AND (plano->>'metrica') IN ('faturamento_mes','projetos_vendidos_mes','csat')
        AND (plano->>'agregacao') IN ('soma','media')
        AND (plano->>'dimensao') IN ('ej','mes')
        AND (plano->>'visualizacao') IN ('ranking','barras','linha','cartao')
        AND (plano->>'mes_inicio')::integer BETWEEN 1 AND 12
        AND (plano->>'mes_fim')::integer BETWEEN (plano->>'mes_inicio')::integer AND 12
    ),
    publico boolean NOT NULL DEFAULT false,
    resultado_publico jsonb,
    criado_em timestamptz NOT NULL DEFAULT now(),
    atualizado_em timestamptz NOT NULL DEFAULT now(),
    CHECK ((publico AND resultado_publico IS NOT NULL) OR (NOT publico AND resultado_publico IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_dashboard_evento_tenant_criado
    ON public.dashboard_evento_ia (federacao_id, criado_em DESC);

ALTER TABLE public.dashboard_evento_ia ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboard_evento_ia FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.dashboard_evento_ia FROM PUBLIC, anon;
REVOKE INSERT, UPDATE, DELETE ON public.dashboard_evento_ia FROM authenticated;
GRANT SELECT ON public.dashboard_evento_ia TO authenticated, ia_limitador;
GRANT INSERT, UPDATE ON public.dashboard_evento_ia TO ia_limitador;
-- Anon só tem coluna e linha de snapshots que o gestor publicou.
GRANT SELECT (id, publico, resultado_publico) ON public.dashboard_evento_ia TO anon;

DROP POLICY IF EXISTS dashboard_evento_tenant_select ON public.dashboard_evento_ia;
CREATE POLICY dashboard_evento_tenant_select ON public.dashboard_evento_ia
    FOR SELECT TO authenticated
    USING (federacao_id = nullif(auth.jwt()->>'federacao_id','')::bigint);

DROP POLICY IF EXISTS dashboard_evento_owner_insert ON public.dashboard_evento_ia;
CREATE POLICY dashboard_evento_owner_insert ON public.dashboard_evento_ia
    FOR INSERT TO ia_limitador
    WITH CHECK (
        federacao_id = nullif(public.ia_identidade_federacao(),'')::bigint
        AND criado_por = public.ia_identidade_usuario()
        AND public.eh_admin_da_federacao(federacao_id)
    );

DROP POLICY IF EXISTS dashboard_evento_owner_update ON public.dashboard_evento_ia;
CREATE POLICY dashboard_evento_owner_update ON public.dashboard_evento_ia
    FOR UPDATE TO ia_limitador
    USING (
        federacao_id = nullif(public.ia_identidade_federacao(),'')::bigint
        AND criado_por = public.ia_identidade_usuario()
        AND public.eh_admin_da_federacao(federacao_id)
    )
    WITH CHECK (
        federacao_id = nullif(public.ia_identidade_federacao(),'')::bigint
        AND criado_por = public.ia_identidade_usuario()
        AND public.eh_admin_da_federacao(federacao_id)
    );

-- A gravação e o débito são atômicos. As funções internas de reserva não são
-- executáveis pelos clientes; só esta operação validada pode consumi-las.
GRANT EXECUTE ON FUNCTION public.eh_admin_da_federacao(bigint) TO ia_limitador;
CREATE OR REPLACE FUNCTION public.persistir_dashboard_evento_ia(
    p_evento_id text,
    p_titulo text,
    p_plano jsonb,
    p_publico boolean,
    p_resultado_publico jsonb
) RETURNS SETOF public.dashboard_evento_ia
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    tenant bigint := nullif(public.ia_identidade_federacao(),'')::bigint;
    identidade uuid := public.ia_identidade_usuario();
    reserva uuid;
    registro public.dashboard_evento_ia%ROWTYPE;
BEGIN
    IF tenant IS NULL OR identidade IS NULL OR NOT public.eh_admin_da_federacao(tenant) THEN
        RAISE EXCEPTION 'Requer gestor ativo da federação autenticada.' USING ERRCODE = '42501';
    END IF;
    IF p_evento_id IS NULL OR length(p_evento_id) NOT BETWEEN 1 AND 80
       OR p_titulo IS NULL OR length(p_titulo) NOT BETWEEN 3 AND 100
       OR jsonb_typeof(p_plano) <> 'object'
       OR p_plano->>'titulo' IS DISTINCT FROM p_titulo
       OR (p_plano->>'metrica') NOT IN ('faturamento_mes','projetos_vendidos_mes','csat')
       OR (p_plano->>'agregacao') NOT IN ('soma','media')
       OR (p_plano->>'dimensao') NOT IN ('ej','mes')
       OR (p_plano->>'visualizacao') NOT IN ('ranking','barras','linha','cartao')
       OR (p_plano->>'ano')::integer NOT BETWEEN 2000 AND 2100
       OR (p_plano->>'mes_inicio')::integer NOT BETWEEN 1 AND 12
       OR (p_plano->>'mes_fim')::integer NOT BETWEEN (p_plano->>'mes_inicio')::integer AND 12
       OR (p_plano->>'limite')::integer NOT BETWEEN 1 AND 50
       OR ((p_plano->>'metrica') = 'csat' AND (p_plano->>'agregacao') <> 'media')
       OR ((p_plano->>'visualizacao') = 'ranking' AND (p_plano->>'dimensao') <> 'ej')
       OR ((p_plano->>'visualizacao') = 'linha' AND (p_plano->>'dimensao') <> 'mes')
       OR p_publico IS NULL
       OR (p_publico AND p_resultado_publico IS NULL)
       OR (NOT p_publico AND p_resultado_publico IS NOT NULL) THEN
        RAISE EXCEPTION 'Plano ou publicação fora do catálogo.' USING ERRCODE = '22023';
    END IF;

    reserva := public.reservar_creditos_ia(tenant, identidade, 'dashboard', 1);
    INSERT INTO public.dashboard_evento_ia
        (federacao_id, criado_por, evento_id, titulo, plano, publico, resultado_publico)
    VALUES
        (tenant, identidade, p_evento_id, p_titulo, p_plano, p_publico, p_resultado_publico)
    RETURNING * INTO registro;
    IF NOT public.confirmar_creditos_ia(reserva) THEN
        RAISE EXCEPTION 'Não foi possível confirmar o crédito.' USING ERRCODE = '55000';
    END IF;
    RETURN NEXT registro;
END $$;

CREATE OR REPLACE FUNCTION public.atualizar_publicacao_dashboard_evento_ia(
    p_dashboard_id uuid,
    p_publico boolean,
    p_resultado_publico jsonb
) RETURNS SETOF public.dashboard_evento_ia
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    tenant bigint := nullif(public.ia_identidade_federacao(),'')::bigint;
    identidade uuid := public.ia_identidade_usuario();
    registro public.dashboard_evento_ia%ROWTYPE;
BEGIN
    IF tenant IS NULL OR identidade IS NULL OR NOT public.eh_admin_da_federacao(tenant) THEN
        RAISE EXCEPTION 'Requer gestor ativo da federação autenticada.' USING ERRCODE = '42501';
    END IF;
    IF p_publico IS NULL OR (p_publico AND p_resultado_publico IS NULL)
       OR (NOT p_publico AND p_resultado_publico IS NOT NULL) THEN
        RAISE EXCEPTION 'Snapshot público inválido.' USING ERRCODE = '22023';
    END IF;
    UPDATE public.dashboard_evento_ia
       SET publico = p_publico,
           resultado_publico = p_resultado_publico,
           atualizado_em = clock_timestamp()
     WHERE id = p_dashboard_id AND federacao_id = tenant AND criado_por = identidade
     RETURNING * INTO registro;
    IF NOT FOUND THEN RETURN; END IF;
    RETURN NEXT registro;
END $$;

GRANT CREATE ON SCHEMA public TO ia_limitador;
ALTER FUNCTION public.persistir_dashboard_evento_ia(text, text, jsonb, boolean, jsonb) OWNER TO ia_limitador;
ALTER FUNCTION public.atualizar_publicacao_dashboard_evento_ia(uuid, boolean, jsonb) OWNER TO ia_limitador;
DO $$ BEGIN
    EXECUTE 'REVOKE ia_limitador FROM ' || quote_ident(current_user);
END $$;
REVOKE CREATE ON SCHEMA public FROM ia_limitador;
REVOKE ALL ON FUNCTION public.persistir_dashboard_evento_ia(text, text, jsonb, boolean, jsonb) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.atualizar_publicacao_dashboard_evento_ia(uuid, boolean, jsonb) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.persistir_dashboard_evento_ia(text, text, jsonb, boolean, jsonb) TO authenticated;
GRANT EXECUTE ON FUNCTION public.atualizar_publicacao_dashboard_evento_ia(uuid, boolean, jsonb) TO authenticated;


DROP POLICY IF EXISTS dashboard_evento_executor_select ON public.dashboard_evento_ia;
CREATE POLICY dashboard_evento_executor_select ON public.dashboard_evento_ia
    FOR SELECT TO ia_limitador
    USING (federacao_id = nullif(public.ia_identidade_federacao(),'')::bigint);

DROP POLICY IF EXISTS dashboard_evento_snapshot_anon ON public.dashboard_evento_ia;
CREATE POLICY dashboard_evento_snapshot_anon ON public.dashboard_evento_ia
    FOR SELECT TO anon
    USING (publico IS TRUE AND resultado_publico IS NOT NULL);

-- A rota pública só consegue ler o snapshot já aprovado pelo gestor. O anon
-- não recebe acesso a fatos, plano do modelo, nem qualquer coluna de EJ.
CREATE OR REPLACE FUNCTION public.dashboard_evento_publico(p_chave uuid)
RETURNS jsonb
LANGUAGE sql STABLE SET search_path = pg_catalog
AS $$
    SELECT d.resultado_publico
      FROM public.dashboard_evento_ia AS d
     WHERE d.id = p_chave
       AND d.publico IS TRUE
       AND d.resultado_publico IS NOT NULL
     LIMIT 1
$$;
REVOKE ALL ON FUNCTION public.dashboard_evento_publico(uuid) FROM PUBLIC, authenticated;
GRANT EXECUTE ON FUNCTION public.dashboard_evento_publico(uuid) TO anon;

-- Consulta quota no mesmo papel restrito usado pelas reservas; parâmetros de
-- tenant e usuário não são aceitos do cliente.
CREATE OR REPLACE FUNCTION public.consultar_creditos_dashboard_ia()
RETURNS TABLE (mes date, consumidos integer, reservados integer, limite integer, disponiveis integer)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    tenant bigint := nullif(public.ia_identidade_federacao(), '')::bigint;
    identidade uuid := public.ia_identidade_usuario();
    periodo date := date_trunc('month', now() AT TIME ZONE 'UTC')::date;
    teto integer;
    usados integer := 0;
    pendentes integer := 0;
BEGIN
    IF identidade IS NULL OR tenant IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.usuario u
         WHERE u.auth_user_id = identidade AND u.ativo AND u.federacao_id = tenant
    ) THEN
        RAISE EXCEPTION 'Usuário sem vínculo ativo com a federação.' USING ERRCODE = '42501';
    END IF;
    SELECT cota, consumidos, reservados INTO teto, usados, pendentes
      FROM public.ia_creditos_mes WHERE federacao_id = tenant AND ia_creditos_mes.mes = periodo;
    IF teto IS NULL THEN
        SELECT fc.creditos_dashboard_mes INTO teto
          FROM public.ia_creditos_federacao_config fc WHERE fc.federacao_id = tenant;
        IF teto IS NULL THEN
            SELECT p.limite_creditos_ia_mes INTO teto
              FROM public.federacao f LEFT JOIN public.plano p ON p.id = f.plano_id
             WHERE f.id = tenant;
        END IF;
        IF teto IS NULL THEN
            SELECT c.creditos_dashboard_mes_padrao INTO STRICT teto
              FROM public.ia_creditos_config c WHERE c.singleton;
        END IF;
    END IF;
    RETURN QUERY SELECT periodo, coalesce(usados,0), coalesce(pendentes,0), teto,
                        greatest(0, teto - coalesce(usados,0) - coalesce(pendentes,0));
END $$;
GRANT CREATE ON SCHEMA public TO ia_limitador;
DO $$ BEGIN
    EXECUTE 'GRANT ia_limitador TO ' || quote_ident(current_user);
END $$;
ALTER FUNCTION public.consultar_creditos_dashboard_ia() OWNER TO ia_limitador;
DO $$ BEGIN
    EXECUTE 'REVOKE ia_limitador FROM ' || quote_ident(current_user);
END $$;
REVOKE CREATE ON SCHEMA public FROM ia_limitador;
REVOKE ALL ON FUNCTION public.consultar_creditos_dashboard_ia() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.consultar_creditos_dashboard_ia() TO authenticated;


NOTIFY pgrst, 'reload schema';
COMMIT;
