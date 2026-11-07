-- 22 — Administração master: agregados do cadastro e gestão de planos.
-- Sem concessão de leitura nacional dos dados de EJs ou alteração de cotas já abertas.
BEGIN;
CREATE OR REPLACE FUNCTION public.master_resumo_federacoes()
RETURNS TABLE (id bigint, nome text, uf text, status text, plano_id bigint,
    usuarios_total bigint, usuarios_ativos bigint, administradores bigint, usuarios_sem_vinculo bigint)
LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path = public, pg_temp AS $$
BEGIN
    IF NOT public.eh_plataforma() THEN
        RAISE EXCEPTION 'Requer operador ativo da plataforma' USING ERRCODE = '42501';
    END IF;
    RETURN QUERY
    SELECT f.id, f.nome, f.uf::text, f.status, f.plano_id,
        count(u.id), count(u.id) FILTER (WHERE u.ativo),
        count(u.id) FILTER (WHERE u.ativo AND u.papel = 'admin'),
        count(u.id) FILTER (WHERE u.ativo AND u.auth_user_id IS NULL)
    FROM public.federacao f LEFT JOIN public.usuario u ON u.federacao_id = f.id
    GROUP BY f.id ORDER BY f.nome;
END $$;

-- Escrita nominal por RPC: conceder UPDATE(plano_id) na tabela permitiria
-- que a policy de aparência do admin também autorizasse trocar seu plano.
CREATE OR REPLACE FUNCTION public.master_vincular_plano(p_federacao_id bigint, p_plano_id bigint)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
    IF NOT public.eh_plataforma() THEN
        RAISE EXCEPTION 'Requer operador ativo da plataforma' USING ERRCODE = '42501';
    END IF;
    UPDATE public.federacao SET plano_id = p_plano_id, updated_at = now() WHERE id = p_federacao_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Federação não encontrada' USING ERRCODE = 'P0002'; END IF;
    RETURN p_federacao_id;
END $$;

CREATE OR REPLACE FUNCTION public.master_salvar_plano(p_id bigint, p_nome text,
    p_limite_usuarios integer, p_limite_creditos_ia_mes integer, p_preco_mensal numeric)
RETURNS SETOF public.plano LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE novo_id bigint;
BEGIN
    IF NOT public.eh_plataforma() THEN
        RAISE EXCEPTION 'Requer operador ativo da plataforma' USING ERRCODE = '42501';
    END IF;
    IF p_nome IS NULL OR length(trim(p_nome)) NOT BETWEEN 1 AND 120
        OR p_limite_usuarios < 0 OR p_limite_usuarios > 1000000
        OR p_limite_creditos_ia_mes < 0 OR p_limite_creditos_ia_mes > 1000000
        OR p_preco_mensal < 0 OR p_preco_mensal > 1000000
        OR p_preco_mensal::text IN ('NaN', 'Infinity', '-Infinity') THEN
        RAISE EXCEPTION 'Valores inválidos para o plano' USING ERRCODE = '23514';
    END IF;
    -- Serializa criações; IDs existentes permanecem intactos, sem sequence pública.
    IF p_id IS NULL THEN
        PERFORM pg_advisory_xact_lock(hashtextextended('master-catalogo-planos', 0));
        SELECT coalesce(max(id), 0) + 1 INTO novo_id FROM public.plano;
        RETURN QUERY INSERT INTO public.plano (id, nome, limite_usuarios, limite_creditos_ia_mes, preco_mensal)
            VALUES (novo_id, trim(p_nome), p_limite_usuarios, p_limite_creditos_ia_mes, p_preco_mensal) RETURNING *;
    ELSE
        RETURN QUERY UPDATE public.plano SET nome = trim(p_nome), limite_usuarios = p_limite_usuarios,
            limite_creditos_ia_mes = p_limite_creditos_ia_mes, preco_mensal = p_preco_mensal
            WHERE id = p_id RETURNING *;
        IF NOT FOUND THEN RAISE EXCEPTION 'Plano não encontrado' USING ERRCODE = 'P0002'; END IF;
    END IF;
END $$;
REVOKE ALL ON FUNCTION public.master_resumo_federacoes(), public.master_vincular_plano(bigint, bigint),
    public.master_salvar_plano(bigint, text, integer, integer, numeric) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.master_resumo_federacoes(), public.master_vincular_plano(bigint, bigint),
    public.master_salvar_plano(bigint, text, integer, integer, numeric) TO authenticated;
COMMIT;
