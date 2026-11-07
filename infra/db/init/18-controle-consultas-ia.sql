-- Política OPERACIONAL, não crédito comercial: 6 chamadas por usuário e
-- 30 por federação, em janela fixa de um minuto. Configuração só via SQL pelo
-- administrador do banco; identidade e limites não são argumentos do RPC.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ia_limitador') THEN
        CREATE ROLE ia_limitador NOLOGIN NOINHERIT;
    END IF;
END $$;
-- Supabase postgres não é superuser: não tentar ALTER NOSUPERUSER/NOBYPASSRLS.
-- Novos roles têm privilégios privilegiados falsos por padrão. Validar também
-- um role já existente e falhar fechado se não for dedicado e seguro.
ALTER ROLE ia_limitador NOLOGIN NOINHERIT;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ia_limitador'
               AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication
                    OR rolcanlogin OR rolinherit)) THEN
        RAISE EXCEPTION 'ia_limitador deve ser um papel dedicado sem privilégios ampliados.';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.ia_controle_config (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    limite_usuario integer NOT NULL CHECK (limite_usuario BETWEEN 1 AND 10000),
    limite_federacao integer NOT NULL CHECK (limite_federacao BETWEEN 1 AND 100000)
);
CREATE TABLE IF NOT EXISTS public.ia_controle_janela (
    federacao_id bigint NOT NULL REFERENCES public.federacao(id) ON DELETE CASCADE,
    chave text NOT NULL,
    inicio timestamptz NOT NULL,
    chamadas integer NOT NULL CHECK (chamadas >= 0),
    PRIMARY KEY (federacao_id, chave)
);
COMMENT ON TABLE public.ia_controle_janela IS
    'Janela atual por usuário (usr:UUID) e federação (fed); sem prompt, resposta ou histórico de janelas.';
ALTER TABLE public.ia_controle_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ia_controle_config FORCE ROW LEVEL SECURITY;
ALTER TABLE public.ia_controle_janela ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ia_controle_janela FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.ia_controle_config, public.ia_controle_janela FROM PUBLIC, anon, authenticated;
-- O dono administrativo pode ajustar a política operacional mesmo sem BYPASSRLS.
DROP POLICY IF EXISTS ia_config_administrador ON public.ia_controle_config;
CREATE POLICY ia_config_administrador ON public.ia_controle_config TO CURRENT_USER USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS ia_janela_administrador ON public.ia_controle_janela;
CREATE POLICY ia_janela_administrador ON public.ia_controle_janela TO CURRENT_USER USING (true) WITH CHECK (true);
INSERT INTO public.ia_controle_config VALUES (true, 6, 30) ON CONFLICT DO NOTHING;
GRANT USAGE ON SCHEMA public TO ia_limitador;
GRANT SELECT ON public.usuario, public.ia_controle_config TO ia_limitador;
GRANT SELECT, INSERT, UPDATE ON public.ia_controle_janela TO ia_limitador;
-- auth pertence ao GoTrue na demo; o migrador postgres não pode conceder
-- USAGE desse schema. Helpers privados executam com o administrador que já
-- tem acesso, retornando somente os dois valores indispensáveis (nunca JWT).
CREATE OR REPLACE FUNCTION public.ia_identidade_usuario() RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog
AS $$ SELECT auth.uid() $$;
CREATE OR REPLACE FUNCTION public.ia_identidade_federacao() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog
AS $$ SELECT auth.jwt() ->> 'federacao_id' $$;
REVOKE ALL ON FUNCTION public.ia_identidade_usuario(), public.ia_identidade_federacao() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ia_identidade_usuario(), public.ia_identidade_federacao() TO ia_limitador;
DROP POLICY IF EXISTS ia_config_leitura_limitador ON public.ia_controle_config;
CREATE POLICY ia_config_leitura_limitador ON public.ia_controle_config FOR SELECT TO ia_limitador USING (true);
DROP POLICY IF EXISTS ia_janela_limitador ON public.ia_controle_janela;
CREATE POLICY ia_janela_limitador ON public.ia_controle_janela TO ia_limitador USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS usuario_leitura_ia_limitador ON public.usuario;
CREATE POLICY usuario_leitura_ia_limitador ON public.usuario FOR SELECT TO ia_limitador USING (auth_user_id = public.ia_identidade_usuario());

DO $$ BEGIN
    IF current_setting('server_version_num')::integer >= 160000 THEN
        EXECUTE 'GRANT ia_limitador TO ' || quote_ident(current_user) || ' WITH INHERIT TRUE, SET TRUE';
    ELSE
        EXECUTE 'GRANT ia_limitador TO ' || quote_ident(current_user);
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.reservar_consulta_ia() RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    identidade uuid := public.ia_identidade_usuario();
    tenant bigint;
    janela timestamptz;
    chave_usuario text;
    limite_usr integer;
    limite_fed integer;
    atual_usr integer;
    atual_fed integer;
BEGIN
    BEGIN
        tenant := nullif(public.ia_identidade_federacao(), '')::bigint;
    EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN
        RAISE EXCEPTION 'Identidade sem federação válida.' USING ERRCODE = '42501';
    END;
    IF identidade IS NULL OR tenant IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.usuario u
        WHERE u.auth_user_id = identidade AND u.ativo AND u.federacao_id = tenant
    ) THEN
        RAISE EXCEPTION 'Usuário sem vínculo ativo com a federação.' USING ERRCODE = '42501';
    END IF;
    -- Serializa somente reservas desta federação, inclusive processos distintos.
    PERFORM pg_advisory_xact_lock(hashtextextended('nexo:' || tenant::text, 0));
    janela := date_trunc('minute', clock_timestamp());
    chave_usuario := 'usr:' || identidade::text;
    SELECT limite_usuario, limite_federacao INTO STRICT limite_usr, limite_fed
      FROM public.ia_controle_config WHERE singleton;
    SELECT chamadas INTO atual_usr FROM public.ia_controle_janela
      WHERE federacao_id = tenant AND chave = chave_usuario AND inicio = janela;
    SELECT chamadas INTO atual_fed FROM public.ia_controle_janela
      WHERE federacao_id = tenant AND chave = 'fed' AND inicio = janela;
    IF coalesce(atual_usr, 0) >= limite_usr OR coalesce(atual_fed, 0) >= limite_fed THEN
        RETURN false;
    END IF;
    INSERT INTO public.ia_controle_janela (federacao_id, chave, inicio, chamadas)
      VALUES (tenant, chave_usuario, janela, 1), (tenant, 'fed', janela, 1)
      ON CONFLICT (federacao_id, chave) DO UPDATE SET
        inicio = EXCLUDED.inicio,
        chamadas = CASE WHEN ia_controle_janela.inicio = EXCLUDED.inicio
                        THEN ia_controle_janela.chamadas + 1 ELSE 1 END;
    RETURN true;
END $$;
-- Papel definer isolado, sem login, sem bypass e sem dados de gestão da rede.
-- CREATE temporário permite transferir a propriedade; retirado em seguida.
GRANT CREATE ON SCHEMA public TO ia_limitador;
ALTER FUNCTION public.reservar_consulta_ia() OWNER TO ia_limitador;
DO $$ BEGIN
    EXECUTE 'REVOKE ia_limitador FROM ' || quote_ident(current_user);
END $$;
REVOKE CREATE ON SCHEMA public FROM ia_limitador;
REVOKE ALL ON FUNCTION public.reservar_consulta_ia() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reservar_consulta_ia() TO authenticated;
NOTIFY pgrst, 'reload schema';
COMMIT;
