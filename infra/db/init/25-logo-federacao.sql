-- 25 — Logo enviada pela própria federação. Aditiva: não altera dados existentes.
--
-- O arquivo fica no banco, numa tabela sem nenhum GRANT para os papéis de cliente.
-- Escrita só pelas RPCs estreitas abaixo, no mesmo padrão da paleta (17): papel,
-- vínculo ativo e tenant do JWT precisam coincidir com a tabela `usuario`.
--
-- Leitura pública por slug (`logo_da_federacao`): a tela de login mostra a logo
-- antes de existir token, e `federacao.logo_url` já é legível por `anon` (09/21).
-- A logo é branding, não dado estratégico; só federações ativas respondem.
--
-- Só PNG, JPEG e WebP, até 512 KB, conferidos pelos bytes iniciais aqui e na API.
-- SVG fica de fora: pode carregar script.

CREATE TABLE IF NOT EXISTS public.federacao_logo (
    federacao_id  bigint      PRIMARY KEY REFERENCES public.federacao(id) ON DELETE CASCADE,
    conteudo      bytea       NOT NULL CHECK (octet_length(conteudo) BETWEEN 1 AND 524288),
    tipo          text        NOT NULL CHECK (tipo IN ('image/png', 'image/jpeg', 'image/webp')),
    versao        text        NOT NULL CHECK (versao ~ '^[0-9a-f]{16}$'),
    atualizado_em timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.federacao_logo IS
    'Logo enviada pela federação. Sem GRANT para clientes: escrita por definir/remover_logo_da_federacao, leitura por logo_da_federacao.';

-- RLS ligada e sem política: mesmo que um GRANT apareça por engano, nada é lido.
ALTER TABLE public.federacao_logo ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.federacao_logo FROM PUBLIC, anon, authenticated;


-- Federação de quem chama, só para admin/plataforma ativo do próprio tenant.
CREATE OR REPLACE FUNCTION public.federacao_que_administro()
RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT u.federacao_id FROM public.usuario u
    WHERE u.auth_user_id = auth.uid() AND u.ativo
      AND u.papel IN ('admin', 'plataforma')
      AND u.federacao_id::text = auth.jwt()->>'federacao_id';
$$;
REVOKE ALL ON FUNCTION public.federacao_que_administro() FROM PUBLIC, anon, authenticated;


CREATE OR REPLACE FUNCTION public.definir_logo_da_federacao(p_conteudo bytea, p_tipo text)
RETURNS TABLE (slug text, nome text, logo_url text, cor_primaria text,
               cor_secundaria text, cor_acento text, slogan text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_federacao_id bigint := public.federacao_que_administro();
    v_versao text;
BEGIN
    IF v_federacao_id IS NULL THEN
        RAISE EXCEPTION 'Permissão insuficiente para definir a logo.' USING ERRCODE = '42501';
    END IF;
    IF p_conteudo IS NULL OR octet_length(p_conteudo) NOT BETWEEN 1 AND 524288 THEN
        RAISE EXCEPTION 'A logo deve ter até 512 KB.' USING ERRCODE = '22023';
    END IF;
    IF NOT (
        (p_tipo = 'image/png'  AND substring(p_conteudo FROM 1 FOR 8) = '\x89504e470d0a1a0a'::bytea)
     OR (p_tipo = 'image/jpeg' AND substring(p_conteudo FROM 1 FOR 3) = '\xffd8ff'::bytea)
     OR (p_tipo = 'image/webp' AND substring(p_conteudo FROM 1 FOR 4) = '\x52494646'::bytea
                               AND substring(p_conteudo FROM 9 FOR 4) = '\x57454250'::bytea)
    ) THEN
        RAISE EXCEPTION 'Use uma imagem PNG, JPEG ou WebP.' USING ERRCODE = '22023';
    END IF;
    v_versao := substr(md5(p_conteudo), 1, 16);
    INSERT INTO public.federacao_logo AS l (federacao_id, conteudo, tipo, versao, atualizado_em)
    VALUES (v_federacao_id, p_conteudo, p_tipo, v_versao, now())
    ON CONFLICT (federacao_id) DO UPDATE
        SET conteudo = EXCLUDED.conteudo, tipo = EXCLUDED.tipo,
            versao = EXCLUDED.versao, atualizado_em = now();
    -- A versão na URL troca o endereço a cada envio: o navegador pode guardar
    -- a imagem em cache por muito tempo sem mostrar a logo antiga.
    RETURN QUERY UPDATE public.federacao f SET
        logo_url = '/api/v1/federacao/logo?slug=' || f.slug || '&v=' || v_versao,
        updated_at = now()
    WHERE f.id = v_federacao_id
    RETURNING f.slug, f.nome, f.logo_url, f.cor_primaria, f.cor_secundaria, f.cor_acento, f.slogan;
END;
$$;


-- Remove só a logo enviada. Um endereço externo definido pela plataforma fica.
CREATE OR REPLACE FUNCTION public.remover_logo_da_federacao()
RETURNS TABLE (slug text, nome text, logo_url text, cor_primaria text,
               cor_secundaria text, cor_acento text, slogan text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_federacao_id bigint := public.federacao_que_administro();
BEGIN
    IF v_federacao_id IS NULL THEN
        RAISE EXCEPTION 'Permissão insuficiente para remover a logo.' USING ERRCODE = '42501';
    END IF;
    DELETE FROM public.federacao_logo l WHERE l.federacao_id = v_federacao_id;
    RETURN QUERY UPDATE public.federacao f SET
        logo_url = CASE WHEN f.logo_url LIKE '/api/v1/federacao/logo?%' THEN NULL ELSE f.logo_url END,
        updated_at = now()
    WHERE f.id = v_federacao_id
    RETURNING f.slug, f.nome, f.logo_url, f.cor_primaria, f.cor_secundaria, f.cor_acento, f.slogan;
END;
$$;


CREATE OR REPLACE FUNCTION public.logo_da_federacao(p_slug text)
RETURNS TABLE (conteudo bytea, tipo text, versao text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT l.conteudo, l.tipo, l.versao
    FROM public.federacao_logo l
    JOIN public.federacao f ON f.id = l.federacao_id
    WHERE f.slug = lower(btrim(p_slug)) AND f.status = 'ativa';
$$;

REVOKE ALL ON FUNCTION public.definir_logo_da_federacao(bytea, text) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.remover_logo_da_federacao() FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.logo_da_federacao(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.definir_logo_da_federacao(bytea, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.remover_logo_da_federacao() TO authenticated;
GRANT EXECUTE ON FUNCTION public.logo_da_federacao(text) TO anon, authenticated;
COMMENT ON FUNCTION public.definir_logo_da_federacao(bytea, text) IS
    'Somente a logo da própria federação. Papel/vínculo/ativo atuais no banco e tenant do JWT devem coincidir.';
COMMENT ON FUNCTION public.logo_da_federacao(text) IS
    'Leitura pública da logo de federação ativa, para a tela de login. Branding, não dado estratégico.';
