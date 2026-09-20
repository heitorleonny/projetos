-- ============================================================================
-- ############################################################################
-- ##                                                                        ##
-- ##   ESTE ARQUIVO É SÓ PARA O LABORATÓRIO LOCAL.                          ##
-- ##   NUNCA RODAR CONTRA O SUPABASE HOSPEDADO.                             ##
-- ##                                                                        ##
-- ##   Lá o schema `auth`, as funções `auth.jwt()` / `auth.uid()` e os      ##
-- ##   roles `anon` / `authenticated` / `service_role` JÁ EXISTEM, nativos.  ##
-- ##   Aplicar isto lá, na melhor das hipóteses, não faz nada; na pior,     ##
-- ##   sobrescreve função de plataforma. Ao migrar o schema para o Supabase, ##
-- ##   aplique 01 a 07 e PULE este arquivo.                                  ##
-- ##                                                                        ##
-- ############################################################################
--
-- POR QUE ELE EXISTE
--
-- As políticas de RLS de `07-rls-policies.sql` precisam saber quem é o usuário
-- da requisição. Em produção quem responde isso é o PostgREST: ele injeta os
-- claims do JWT como configuração de sessão (`request.jwt.claims`), e as
-- funções `auth.jwt()`/`auth.uid()` do Supabase apenas leem essa configuração.
--
-- Reproduzir isso localmente custa as ~30 linhas abaixo. A alternativa seria
-- subir a stack completa do Supabase (Postgres + PostgREST + GoTrue + Studio +
-- ...), avaliada e rejeitada em docs/adr-001-supabase-vs-postgres.md por peso:
-- sete containers a mais para uma necessidade que um container resolve.
--
-- O ganho concreto: as políticas escritas em 07 rodam SEM ALTERAÇÃO NENHUMA no
-- Supabase hospedado, porque dependem só de `auth.jwt()` — que lá é nativa.
-- O shim não é uma simulação aproximada; é a mesma interface.
-- ============================================================================


-- ── Schema e funções ────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS auth;

COMMENT ON SCHEMA auth IS 'SHIM LOCAL. No Supabase hospedado este schema é da plataforma — não versionar de lá para cá.';

-- Lê os claims que o PostgREST injeta na sessão. Sem sessão configurada
-- devolve '{}': o resultado disso, nas políticas, é claim NULL — e portanto
-- nenhuma linha visível. Falhar fechado é o comportamento desejado.
CREATE OR REPLACE FUNCTION auth.jwt()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(
        nullif(current_setting('request.jwt.claims', true), '')::jsonb,
        '{}'::jsonb
    );
$$;

COMMENT ON FUNCTION auth.jwt() IS 'SHIM LOCAL: claims da sessão (request.jwt.claims). No Supabase é nativa.';

-- `sub` é o id do usuário no Supabase Auth. Ausente ou malformado → NULL,
-- nunca erro: uma política que estoura derruba a query inteira, e isso
-- esconderia um bug de claim atrás de um erro de banco.
CREATE OR REPLACE FUNCTION auth.uid()
RETURNS uuid
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    valor text;
BEGIN
    valor := auth.jwt() ->> 'sub';
    IF valor IS NULL OR valor = '' THEN
        RETURN NULL;
    END IF;
    BEGIN
        RETURN valor::uuid;
    EXCEPTION WHEN invalid_text_representation THEN
        RETURN NULL;
    END;
END;
$$;

COMMENT ON FUNCTION auth.uid() IS 'SHIM LOCAL: claim `sub` como uuid, ou NULL. No Supabase é nativa.';


-- ── Roles ───────────────────────────────────────────────────────────────────
--
-- Por que os roles importam, e muito: RLS NÃO se aplica ao dono da tabela nem a
-- superusuário. O usuário `portal` do laboratório é as duas coisas. Se os
-- testes de RLS conectassem como ele, TODOS passariam — inclusive com política
-- errada, inclusive sem política nenhuma. Sem um role separado, o teste de
-- isolamento não testa isolamento.
--
-- A nomenclatura é a mesma do Supabase de propósito: os GRANTs de 07 falam dos
-- mesmos nomes de role nos dois lugares.

DO $$
BEGIN
    -- `anon`: requisição sem autenticação. NÃO recebe SELECT em nada (ver 07).
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;

    -- `authenticated`: requisição com JWT válido. É o role do caminho de request.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;

    -- `service_role`: scripts administrativos. BYPASSRLS espelha o que a
    -- service key faz no Supabase — e é exatamente por isso que ela não pode
    -- aparecer no caminho de request da aplicação.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN BYPASSRLS;
    END IF;

    -- Role de LOGIN usado pelos testes (tests/test_rls.py). Não existe no
    -- Supabase: lá quem conecta é o PostgREST, que troca de role por
    -- requisição. Aqui precisamos de alguém que consiga abrir conexão e que
    -- NÃO seja dono nem superusuário.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_authenticated') THEN
        CREATE ROLE app_authenticated LOGIN PASSWORD 'app_authenticated' IN ROLE authenticated;
    END IF;
END
$$;

-- Senha de laboratório, em texto claro e versionada de propósito: este role só
-- existe num Postgres local que não guarda dado real. Nenhuma credencial de
-- verdade entra neste repositório.

GRANT USAGE ON SCHEMA auth   TO anon, authenticated, service_role;
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
