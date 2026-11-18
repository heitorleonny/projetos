-- ============================================================================
-- 28 — Métricas personalizadas: o operador `plataforma` também gere
--
-- Decisão de Heitor (13/11/2026): além do `admin`, o admin master (`plataforma`)
-- cria, edita, arquiva e exclui métricas, SÓ na federação vinculada à própria
-- conta. Papel continua sem ampliar tenant: o claim `federacao_id` e o
-- `usuario.federacao_id` do banco precisam coincidir com a linha.
--
-- Aditiva: função nova e políticas de escrita de 27 recriadas com ela.
-- A leitura (todos da federação) não muda.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.pode_gerir_metricas(p_federacao_id bigint)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM usuario u
         WHERE u.auth_user_id = auth.uid()
           AND u.ativo
           AND u.papel IN ('admin', 'plataforma')
           AND u.federacao_id = p_federacao_id
    )
$$;

COMMENT ON FUNCTION public.pode_gerir_metricas(bigint) IS
    'Quem está na sessão é, hoje, admin ou plataforma ATIVO vinculado àquela federação. Lê o banco, não o claim.';

REVOKE EXECUTE ON FUNCTION public.pode_gerir_metricas(bigint) FROM PUBLIC, anon;
GRANT  EXECUTE ON FUNCTION public.pode_gerir_metricas(bigint) TO authenticated;

DROP POLICY IF EXISTS metrica_admin_insert ON public.metrica_personalizada;
CREATE POLICY metrica_admin_insert ON public.metrica_personalizada
    FOR INSERT TO authenticated
    WITH CHECK (
        federacao_id = nullif(auth.jwt()->>'federacao_id', '')::bigint
        AND public.pode_gerir_metricas(federacao_id)
        AND criado_por = auth.uid()
    );

DROP POLICY IF EXISTS metrica_admin_update ON public.metrica_personalizada;
CREATE POLICY metrica_admin_update ON public.metrica_personalizada
    FOR UPDATE TO authenticated
    USING (
        federacao_id = nullif(auth.jwt()->>'federacao_id', '')::bigint
        AND public.pode_gerir_metricas(federacao_id)
    )
    WITH CHECK (
        federacao_id = nullif(auth.jwt()->>'federacao_id', '')::bigint
        AND public.pode_gerir_metricas(federacao_id)
        AND (atualizado_por IS NULL OR atualizado_por = auth.uid())
    );

DROP POLICY IF EXISTS metrica_admin_delete ON public.metrica_personalizada;
CREATE POLICY metrica_admin_delete ON public.metrica_personalizada
    FOR DELETE TO authenticated
    USING (
        federacao_id = nullif(auth.jwt()->>'federacao_id', '')::bigint
        AND public.pode_gerir_metricas(federacao_id)
        AND arquivada_em IS NOT NULL
    );

COMMIT;
