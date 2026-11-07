-- Créditos mensais para gerações de dashboards por federação.
-- Uma unidade representa uma criação/alteração concluída, independente do modelo.
-- O catálogo do plano comercial tem valores placeholder; por isso a cota
-- operacional vem de um default configurável e de overrides por federação.
BEGIN;

CREATE TABLE IF NOT EXISTS public.ia_creditos_config (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    creditos_dashboard_mes_padrao integer NOT NULL
        CHECK (creditos_dashboard_mes_padrao BETWEEN 0 AND 1000000)
);
COMMENT ON TABLE public.ia_creditos_config IS
    'Configuração operacional global de créditos mensais de IA. Não representa preço nem saldo financeiro.';
INSERT INTO public.ia_creditos_config (singleton, creditos_dashboard_mes_padrao)
VALUES (true, 100) ON CONFLICT (singleton) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.ia_creditos_federacao_config (
    federacao_id bigint PRIMARY KEY REFERENCES public.federacao(id) ON DELETE CASCADE,
    creditos_dashboard_mes integer NOT NULL
        CHECK (creditos_dashboard_mes BETWEEN 0 AND 1000000),
    atualizado_em timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.ia_creditos_federacao_config IS
    'Override de cota mensal para dashboards de uma federação. Sem linha, aplica-se o default operacional.';

CREATE TABLE IF NOT EXISTS public.ia_creditos_mes (
    federacao_id bigint NOT NULL REFERENCES public.federacao(id) ON DELETE CASCADE,
    mes date NOT NULL CHECK (extract(day FROM mes) = 1),
    cota integer NOT NULL CHECK (cota BETWEEN 0 AND 1000000),
    reservados integer NOT NULL DEFAULT 0 CHECK (reservados >= 0),
    consumidos integer NOT NULL DEFAULT 0 CHECK (consumidos >= 0),
    atualizado_em timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (federacao_id, mes),
    CHECK (reservados + consumidos <= cota)
);
COMMENT ON TABLE public.ia_creditos_mes IS
    'Contador mensal por federação; reserva em andamento ocupa cota e só vira consumo após sucesso.';

CREATE TABLE IF NOT EXISTS public.ia_creditos_reserva (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    federacao_id bigint NOT NULL,
    usuario_id uuid NOT NULL,
    mes date NOT NULL,
    recurso text NOT NULL CHECK (recurso IN ('dashboard')),
    unidades integer NOT NULL CHECK (unidades BETWEEN 1 AND 10),
    estado text NOT NULL DEFAULT 'reservada'
        CHECK (estado IN ('reservada', 'consumida', 'estornada')),
    criada_em timestamptz NOT NULL DEFAULT now(),
    finalizada_em timestamptz,
    FOREIGN KEY (federacao_id, mes)
        REFERENCES public.ia_creditos_mes(federacao_id, mes) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_ia_creditos_reserva_tenant_mes
    ON public.ia_creditos_reserva (federacao_id, mes, criada_em);
COMMENT ON TABLE public.ia_creditos_reserva IS
    'Auditoria de unidades de IA por usuário e tenant; não armazena prompts, respostas ou credenciais.';

-- Reutiliza o executor restrito criado pela migração 18. Os clientes autenticados
-- não recebem acesso direto às tabelas, apenas às RPCs que validam os claims.
ALTER TABLE public.ia_creditos_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ia_creditos_config FORCE ROW LEVEL SECURITY;
ALTER TABLE public.ia_creditos_federacao_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ia_creditos_federacao_config FORCE ROW LEVEL SECURITY;
ALTER TABLE public.ia_creditos_mes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ia_creditos_mes FORCE ROW LEVEL SECURITY;
ALTER TABLE public.ia_creditos_reserva ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ia_creditos_reserva FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.ia_creditos_config, public.ia_creditos_federacao_config,
    public.ia_creditos_mes, public.ia_creditos_reserva FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.ia_creditos_config, public.ia_creditos_federacao_config TO ia_limitador;
GRANT SELECT, INSERT, UPDATE ON public.ia_creditos_mes TO ia_limitador;
GRANT SELECT, INSERT, UPDATE ON public.ia_creditos_reserva TO ia_limitador;
GRANT SELECT ON public.federacao, public.plano TO ia_limitador;

DROP POLICY IF EXISTS ia_creditos_config_executor ON public.ia_creditos_config;
CREATE POLICY ia_creditos_config_executor ON public.ia_creditos_config
    FOR SELECT TO ia_limitador USING (true);
DROP POLICY IF EXISTS ia_creditos_config_administrador ON public.ia_creditos_config;
CREATE POLICY ia_creditos_config_administrador ON public.ia_creditos_config
    TO CURRENT_USER USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS ia_creditos_override_executor ON public.ia_creditos_federacao_config;
CREATE POLICY ia_creditos_override_executor ON public.ia_creditos_federacao_config
    FOR SELECT TO ia_limitador
    USING (federacao_id = nullif(public.ia_identidade_federacao(), '')::bigint);
DROP POLICY IF EXISTS ia_creditos_override_administrador ON public.ia_creditos_federacao_config;
CREATE POLICY ia_creditos_override_administrador ON public.ia_creditos_federacao_config
    TO CURRENT_USER USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS ia_creditos_mes_executor ON public.ia_creditos_mes;
CREATE POLICY ia_creditos_mes_executor ON public.ia_creditos_mes
    TO ia_limitador USING (federacao_id = nullif(public.ia_identidade_federacao(), '')::bigint)
    WITH CHECK (federacao_id = nullif(public.ia_identidade_federacao(), '')::bigint);
DROP POLICY IF EXISTS ia_creditos_reserva_executor ON public.ia_creditos_reserva;
CREATE POLICY ia_creditos_reserva_executor ON public.ia_creditos_reserva
    TO ia_limitador USING (
        federacao_id = nullif(public.ia_identidade_federacao(), '')::bigint
        AND usuario_id = public.ia_identidade_usuario()
    ) WITH CHECK (
        federacao_id = nullif(public.ia_identidade_federacao(), '')::bigint
        AND usuario_id = public.ia_identidade_usuario()
    );
GRANT EXECUTE ON FUNCTION public.ia_identidade_usuario(), public.ia_identidade_federacao()
    TO ia_limitador;
DROP POLICY IF EXISTS federacao_select_ia_creditos ON public.federacao;
CREATE POLICY federacao_select_ia_creditos ON public.federacao
    FOR SELECT TO ia_limitador
    USING (id = nullif(public.ia_identidade_federacao(), '')::bigint);
DROP POLICY IF EXISTS plano_select_ia_creditos ON public.plano;
CREATE POLICY plano_select_ia_creditos ON public.plano
    FOR SELECT TO ia_limitador USING (true);

CREATE OR REPLACE FUNCTION public.reservar_creditos_ia(
    p_federacao_id bigint,
    p_usuario_id uuid,
    p_recurso text DEFAULT 'dashboard',
    p_unidades integer DEFAULT 1
) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    tenant bigint := nullif(public.ia_identidade_federacao(), '')::bigint;
    identidade uuid := public.ia_identidade_usuario();
    periodo date := date_trunc('month', clock_timestamp() AT TIME ZONE 'UTC')::date;
    limite integer;
    reserva uuid;
BEGIN
    IF identidade IS NULL OR tenant IS NULL OR p_usuario_id IS DISTINCT FROM identidade
       OR p_federacao_id IS DISTINCT FROM tenant OR p_recurso <> 'dashboard'
       OR p_unidades IS NULL OR p_unidades < 1 OR p_unidades > 10 THEN
        RAISE EXCEPTION 'Identidade, tenant ou solicitação de créditos inválidos.' USING ERRCODE = '42501';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.usuario u
         WHERE u.auth_user_id = identidade AND u.ativo AND u.federacao_id = tenant
    ) THEN
        RAISE EXCEPTION 'Usuário sem vínculo ativo com a federação.' USING ERRCODE = '42501';
    END IF;

    PERFORM pg_advisory_xact_lock(hashtextextended('ia-creditos:' || tenant::text || ':' || periodo::text, 0));
    SELECT fc.creditos_dashboard_mes INTO limite
      FROM public.ia_creditos_federacao_config fc WHERE fc.federacao_id = tenant;
    IF limite IS NULL THEN
        SELECT p.limite_creditos_ia_mes INTO limite
          FROM public.federacao f
          LEFT JOIN public.plano p ON p.id = f.plano_id
         WHERE f.id = tenant;
    END IF;
    IF limite IS NULL THEN
        SELECT c.creditos_dashboard_mes_padrao INTO STRICT limite
          FROM public.ia_creditos_config c WHERE c.singleton;
    END IF;

    INSERT INTO public.ia_creditos_mes (federacao_id, mes, cota)
    VALUES (tenant, periodo, limite)
    ON CONFLICT (federacao_id, mes) DO NOTHING;

    -- Congela a cota no primeiro uso do mês; alteração administrativa vale no mês seguinte.
    UPDATE public.ia_creditos_mes
       SET reservados = reservados + p_unidades, atualizado_em = clock_timestamp()
     WHERE federacao_id = tenant AND mes = periodo
       AND reservados + consumidos + p_unidades <= cota;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'A federação esgotou os créditos mensais para criar dashboards.' USING ERRCODE = '54000';
    END IF;

    INSERT INTO public.ia_creditos_reserva (federacao_id, usuario_id, mes, recurso, unidades)
    VALUES (tenant, identidade, periodo, p_recurso, p_unidades)
    RETURNING id INTO reserva;
    RETURN reserva;
END $$;

CREATE OR REPLACE FUNCTION public.confirmar_creditos_ia(p_reserva_id uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE r public.ia_creditos_reserva%ROWTYPE;
BEGIN
    SELECT * INTO r FROM public.ia_creditos_reserva WHERE id = p_reserva_id FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    IF r.usuario_id IS DISTINCT FROM public.ia_identidade_usuario()
       OR r.federacao_id IS DISTINCT FROM nullif(public.ia_identidade_federacao(), '')::bigint THEN
        RAISE EXCEPTION 'Reserva não pertence à identidade autenticada.' USING ERRCODE = '42501';
    END IF;
    IF r.estado = 'consumida' THEN RETURN true; END IF;
    IF r.estado <> 'reservada' THEN RETURN false; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('ia-creditos:' || r.federacao_id::text || ':' || r.mes::text, 0));
    UPDATE public.ia_creditos_mes
       SET reservados = reservados - r.unidades,
           consumidos = consumidos + r.unidades,
           atualizado_em = clock_timestamp()
     WHERE federacao_id = r.federacao_id AND mes = r.mes AND reservados >= r.unidades;
    IF NOT FOUND THEN RAISE EXCEPTION 'Contador de créditos inconsistente.'; END IF;
    UPDATE public.ia_creditos_reserva SET estado = 'consumida', finalizada_em = clock_timestamp()
     WHERE id = r.id;
    RETURN true;
END $$;

CREATE OR REPLACE FUNCTION public.estornar_creditos_ia(p_reserva_id uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE r public.ia_creditos_reserva%ROWTYPE;
BEGIN
    SELECT * INTO r FROM public.ia_creditos_reserva WHERE id = p_reserva_id FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    IF r.usuario_id IS DISTINCT FROM public.ia_identidade_usuario()
       OR r.federacao_id IS DISTINCT FROM nullif(public.ia_identidade_federacao(), '')::bigint THEN
        RAISE EXCEPTION 'Reserva não pertence à identidade autenticada.' USING ERRCODE = '42501';
    END IF;
    IF r.estado = 'estornada' THEN RETURN true; END IF;
    IF r.estado <> 'reservada' THEN RETURN false; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('ia-creditos:' || r.federacao_id::text || ':' || r.mes::text, 0));
    UPDATE public.ia_creditos_mes
       SET reservados = reservados - r.unidades, atualizado_em = clock_timestamp()
     WHERE federacao_id = r.federacao_id AND mes = r.mes AND reservados >= r.unidades;
    IF NOT FOUND THEN RAISE EXCEPTION 'Contador de créditos inconsistente.'; END IF;
    UPDATE public.ia_creditos_reserva SET estado = 'estornada', finalizada_em = clock_timestamp()
     WHERE id = r.id;
    RETURN true;
END $$;

-- Definer dedicado e sem login; funções ficam indisponíveis a anon/PUBLIC.
GRANT CREATE ON SCHEMA public TO ia_limitador;
ALTER FUNCTION public.reservar_creditos_ia(bigint, uuid, text, integer) OWNER TO ia_limitador;
ALTER FUNCTION public.confirmar_creditos_ia(uuid) OWNER TO ia_limitador;
ALTER FUNCTION public.estornar_creditos_ia(uuid) OWNER TO ia_limitador;
DO $$ BEGIN
    EXECUTE 'REVOKE ia_limitador FROM ' || quote_ident(current_user);
END $$;
REVOKE CREATE ON SCHEMA public FROM ia_limitador;
-- Estas RPCs são primitivas internas, não endpoints de consumo. A migração 20
-- chama reserve + confirm no mesmo statement que persiste o dashboard; clientes
-- authenticated nunca recebem execute direto e portanto não podem reter reservas.
REVOKE ALL ON FUNCTION public.reservar_creditos_ia(bigint, uuid, text, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.confirmar_creditos_ia(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.estornar_creditos_ia(uuid) FROM PUBLIC, anon, authenticated;


NOTIFY pgrst, 'reload schema';
COMMIT;
