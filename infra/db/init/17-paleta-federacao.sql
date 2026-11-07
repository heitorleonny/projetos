-- Paleta compartilhada por federação. Aditiva, sem ampliar UPDATE de admins.
ALTER TABLE public.federacao ADD COLUMN IF NOT EXISTS cor_secundaria text
    CHECK (cor_secundaria IS NULL OR cor_secundaria ~ '^#[0-9A-Fa-f]{6}$');
ALTER TABLE public.federacao ADD COLUMN IF NOT EXISTS cor_acento text
    CHECK (cor_acento IS NULL OR cor_acento ~ '^#[0-9A-Fa-f]{6}$');
GRANT SELECT (cor_secundaria, cor_acento) ON public.federacao TO anon;
GRANT UPDATE (cor_secundaria, cor_acento) ON public.federacao TO authenticated;

-- Uma política UPDATE para admin liberaria também status/nome, já concedidos
-- ao role authenticated para o operador. RPC estreita evita essa ampliação.
CREATE OR REPLACE FUNCTION public.definir_paleta_da_federacao(
    p_cor_primaria text, p_cor_secundaria text, p_cor_acento text
) RETURNS TABLE (slug text, nome text, logo_url text, cor_primaria text,
                 cor_secundaria text, cor_acento text, slogan text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_federacao_id bigint;
BEGIN
    SELECT u.federacao_id INTO v_federacao_id FROM public.usuario u
    WHERE u.auth_user_id = auth.uid() AND u.ativo
      AND u.papel IN ('admin', 'plataforma')
      AND u.federacao_id::text = auth.jwt()->>'federacao_id';
    IF v_federacao_id IS NULL THEN
        RAISE EXCEPTION 'Permissão insuficiente para definir a paleta.' USING ERRCODE = '42501';
    END IF;
    IF (p_cor_primaria IS NOT NULL AND p_cor_primaria !~ '^#[0-9A-Fa-f]{6}$')
       OR (p_cor_secundaria IS NOT NULL AND p_cor_secundaria !~ '^#[0-9A-Fa-f]{6}$')
       OR (p_cor_acento IS NOT NULL AND p_cor_acento !~ '^#[0-9A-Fa-f]{6}$') THEN
        RAISE EXCEPTION 'Cor inválida: use #RRGGBB.' USING ERRCODE = '22023';
    END IF;
    RETURN QUERY UPDATE public.federacao f SET
        cor_primaria = upper(p_cor_primaria), cor_secundaria = upper(p_cor_secundaria),
        cor_acento = upper(p_cor_acento), updated_at = now()
    WHERE f.id = v_federacao_id
    RETURNING f.slug, f.nome, f.logo_url, f.cor_primaria, f.cor_secundaria, f.cor_acento, f.slogan;
END;
$$;
REVOKE ALL ON FUNCTION public.definir_paleta_da_federacao(text,text,text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.definir_paleta_da_federacao(text,text,text) TO authenticated;
COMMENT ON FUNCTION public.definir_paleta_da_federacao(text,text,text) IS
    'Somente cores da própria federação. Papel/vínculo/ativo atuais no banco e tenant do JWT devem coincidir.';
NOTIFY pgrst, 'reload schema';
