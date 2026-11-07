-- ============================================================================
-- 13 — Painel administrativo: papel `plataforma`, escrita em `usuario` e
--      `federacao`, e o último login de cada usuário
--
-- Até aqui a API só LIA. Este arquivo abre as primeiras escritas pelo caminho
-- de request (`authenticated`), e só estas:
--
--   * `federacao` — status e branding, e só pelo papel `plataforma`;
--   * `usuario`   — cadastro, papel, ativo e federação, pelo `plataforma` (em
--                   qualquer federação) e pelo `admin` (só na própria).
--
-- Também dá ao papel `plataforma` a leitura de `ingestao_carga` inteira, e cria
-- a função que devolve a lista de usuários com o último login, que mora em
-- `auth.users` e não é legível pela API.
--
-- O PAPEL `plataforma` E A REGRA "PAPEL NUNCA AMPLIA TENANT"
--
-- `plataforma` é o operador do portal, acima das 27 federações. É a primeira e
-- única exceção à regra, e ela é ESTREITA: o papel enxerga todas as linhas de
-- `federacao`, `usuario` e `ingestao_carga` — o cadastro da plataforma. Não
-- enxerga EJ, meta, monitoramento, cluster nem staging de outra federação: as
-- políticas de 07, 08 e 10 dessas tabelas não foram tocadas, e continuam
-- filtrando pelo `federacao_id` do token. No dashboard, um usuário
-- `plataforma` vê a federação a que está vinculado, como qualquer outro.
-- Ver docs/adr-003-painel-admin.md.
--
-- A FONTE DA VERDADE DO PAPEL, AQUI, É O BANCO
--
-- As políticas de 07 comparam com o CLAIM do token, que é uma fotografia de
-- `usuario` no momento do login. Para ESCREVER, fotografia não basta: um admin
-- rebaixado continuaria admin até o token expirar. Por isso as políticas deste
-- arquivo perguntam a `usuario` (por `auth.uid()`), via funções SECURITY
-- DEFINER, se quem está na sessão é hoje, e ativo, `plataforma` ou `admin`.
--
-- ATENÇÃO — OS GRANTS DO SUPABASE NÃO SÃO OS DO LABORATÓRIO
--
-- No laboratório, `authenticated` só tem o que 07 concedeu (SELECT). No
-- Supabase, os default privileges do schema `public` dão ALL — INSERT, UPDATE,
-- DELETE e TRUNCATE — a `anon` e `authenticated` em toda tabela criada pelo
-- `postgres` (conferido na demo em 29/09/2026). Até agora isso não abria nada
-- porque não havia política de escrita, e sem política a RLS nega. A partir das
-- políticas abaixo, abriria: um admin poderia reescrever `auth_user_id` e se
-- apropriar da conta de outra pessoa. Por isso, nas duas tabelas que passam a
-- aceitar escrita, o privilégio de tabela é REVOGADO e a escrita é concedida
-- POR COLUNA.
-- ============================================================================


-- ── 1. O papel `plataforma` ─────────────────────────────────────────────────

ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_papel_check;
ALTER TABLE usuario ADD CONSTRAINT usuario_papel_check
    CHECK (papel IN ('admin', 'membro', 'plataforma'));

COMMENT ON COLUMN usuario.papel IS
    'membro, admin (da própria federação) ou plataforma (operador do portal; vê o cadastro de todas as federações, não o dado de gestão delas).';


-- ── 2. `auth.users` no laboratório ──────────────────────────────────────────
--
-- O último login mora em `auth.users.last_sign_in_at`, tabela do GoTrue. No
-- Supabase (hospedado e demo) ela existe e este bloco não faz nada. No
-- laboratório não há GoTrue, e o shim de 00 só criou `auth.jwt()` e
-- `auth.uid()`; sem a tabela, a função do passo 6 nem compila. Aqui entra só o
-- mínimo que ela lê, com os mesmos nomes de coluna do GoTrue.

DO $$
BEGIN
    IF to_regclass('auth.users') IS NULL THEN
        CREATE TABLE auth.users (
            id              UUID PRIMARY KEY,
            email           TEXT,
            last_sign_in_at TIMESTAMPTZ
        );
        COMMENT ON TABLE auth.users IS
            'SHIM LOCAL (13): só as colunas que admin_listar_usuarios lê. No Supabase é do GoTrue.';
    END IF;
END
$$;


-- ── 3. Quem está na sessão, segundo o banco ─────────────────────────────────
--
-- As três leem `usuario` por `auth.uid()` (o `sub` do token), exigindo `ativo`.
-- SECURITY DEFINER porque a política de SELECT de `usuario` (07) filtra pelo
-- claim — e a pergunta aqui é justamente sobre o banco, não sobre o claim.
-- O dono das funções é o dono da tabela, que não passa pela RLS: é isso que
-- evita recursão quando uma política de `usuario` chama uma delas.
--
-- Elas só respondem sobre quem chama. Não recebem id de usuário.

CREATE OR REPLACE FUNCTION public.usuario_atual()
RETURNS TABLE (id bigint, federacao_id bigint, papel text, nome text, email text)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT u.id, u.federacao_id, u.papel, u.nome, u.email
      FROM usuario u
     WHERE u.auth_user_id = auth.uid()
       AND u.ativo
$$;

CREATE OR REPLACE FUNCTION public.eh_plataforma()
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
           AND u.papel = 'plataforma'
    )
$$;

CREATE OR REPLACE FUNCTION public.eh_admin_da_federacao(p_federacao_id bigint)
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
           AND u.papel = 'admin'
           AND u.federacao_id = p_federacao_id
    )
$$;

COMMENT ON FUNCTION public.usuario_atual()                 IS 'A linha de `usuario` de quem está na sessão (auth.uid()), se ativa.';
COMMENT ON FUNCTION public.eh_plataforma()                 IS 'Quem está na sessão é, hoje, `plataforma` e ativo. Lê o banco, não o claim.';
COMMENT ON FUNCTION public.eh_admin_da_federacao(bigint)   IS 'Quem está na sessão é, hoje, `admin` ativo daquela federação. Lê o banco, não o claim.';

-- Mesmo cuidado de 06 e 11: função nova em `public` nasce executável por
-- PUBLIC, e no Supabase o PostgREST a exporia a `anon`. `authenticated` precisa
-- de EXECUTE porque as políticas rodam com os privilégios de quem consulta.
REVOKE EXECUTE ON FUNCTION public.usuario_atual()               FROM PUBLIC, anon;
REVOKE EXECUTE ON FUNCTION public.eh_plataforma()               FROM PUBLIC, anon;
REVOKE EXECUTE ON FUNCTION public.eh_admin_da_federacao(bigint) FROM PUBLIC, anon;
GRANT  EXECUTE ON FUNCTION public.usuario_atual()               TO authenticated;
GRANT  EXECUTE ON FUNCTION public.eh_plataforma()               TO authenticated;
GRANT  EXECUTE ON FUNCTION public.eh_admin_da_federacao(bigint) TO authenticated;


-- ── 4. `federacao`: o operador edita status e branding ──────────────────────
--
-- Só `plataforma`. O admin de uma federação não muda o status dela (seria
-- poder se reativar) nem a marca (decisão de não abrir isso agora; se entrar,
-- é uma política a mais, com WITH CHECK na própria federação).
--
-- `id`, `slug` e `uf` ficam fora do GRANT: o id é o do Portal BJ, e o slug é
-- o que o deploy usa para achar o tenant (TENANT_SLUG). Nenhum dos dois é
-- editável pelo painel.

DROP POLICY IF EXISTS federacao_select_plataforma ON federacao;
CREATE POLICY federacao_select_plataforma ON federacao
    FOR SELECT TO authenticated
    USING (public.eh_plataforma());

DROP POLICY IF EXISTS federacao_update_plataforma ON federacao;
CREATE POLICY federacao_update_plataforma ON federacao
    FOR UPDATE TO authenticated
    USING (public.eh_plataforma())
    WITH CHECK (public.eh_plataforma());

-- REVOKE antes do GRANT: revogar o privilégio de tabela também revoga os de
-- coluna, então a ordem inversa desfaria o GRANT.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON federacao FROM anon, authenticated;
GRANT UPDATE (nome, status, logo_url, cor_primaria, updated_at) ON federacao TO authenticated;


-- ── 5. `usuario`: cadastro pelo painel ──────────────────────────────────────
--
-- Regra única para INSERT e UPDATE, antes e depois da mudança:
--
--   plataforma  → qualquer linha;
--   admin       → só linhas da PRÓPRIA federação, e nunca de papel
--                 `plataforma` — nem para ler antes (USING), nem para gravar
--                 depois (WITH CHECK). Assim um admin não se promove, não
--                 promove ninguém a operador e não move usuário para outra
--                 federação: a linha que sairia da própria federação falha no
--                 WITH CHECK.
--
-- Colunas fora do GRANT, de propósito:
--   auth_user_id     — é o vínculo com a conta do Supabase Auth. Quem pudesse
--                      escrevê-lo poderia apontar a própria federação para a
--                      conta de outra pessoa. Só o convite grava (service key,
--                      ver app/services/convite_service.py e ADR-003).
--   conta_principal  — decisão de contrato, não de painel.
--   id, created_at   — do banco.
--
-- DELETE continua sem GRANT: usuário se desativa (`ativo = false`), não se
-- apaga. `ingestao_carga.carregado_por` aponta para cá.

DROP POLICY IF EXISTS usuario_select_plataforma ON usuario;
CREATE POLICY usuario_select_plataforma ON usuario
    FOR SELECT TO authenticated
    USING (public.eh_plataforma());

DROP POLICY IF EXISTS usuario_insert_gestao ON usuario;
CREATE POLICY usuario_insert_gestao ON usuario
    FOR INSERT TO authenticated
    WITH CHECK (
        public.eh_plataforma()
        OR (public.eh_admin_da_federacao(federacao_id) AND papel <> 'plataforma')
    );

DROP POLICY IF EXISTS usuario_update_gestao ON usuario;
CREATE POLICY usuario_update_gestao ON usuario
    FOR UPDATE TO authenticated
    USING (
        public.eh_plataforma()
        OR (public.eh_admin_da_federacao(federacao_id) AND papel <> 'plataforma')
    )
    WITH CHECK (
        public.eh_plataforma()
        OR (public.eh_admin_da_federacao(federacao_id) AND papel <> 'plataforma')
    );

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON usuario FROM anon, authenticated;
GRANT INSERT (federacao_id, nome, email, papel)                ON usuario TO authenticated;
GRANT UPDATE (federacao_id, nome, papel, ativo, updated_at)    ON usuario TO authenticated;


-- ── 6. `ingestao_carga`: o operador vê todas, inclusive as nacionais ────────
--
-- 10 diz que a carga nacional "é registro de operação da plataforma e NÃO
-- aparece para federação nenhuma". Continua valendo: `plataforma` não é
-- federação, é o operador — é para ele que esse registro existe.

DROP POLICY IF EXISTS ingestao_carga_select_plataforma ON ingestao_carga;
CREATE POLICY ingestao_carga_select_plataforma ON ingestao_carga
    FOR SELECT TO authenticated
    USING (public.eh_plataforma());


-- ── 7. Lista de usuários com o último login ─────────────────────────────────
--
-- `last_sign_in_at` está em `auth.users`, que a API não lê (e não deve ler: a
-- tabela tem hash de senha, tokens de recuperação e metadados). Esta função
-- devolve SÓ o último login, e só das linhas que a regra de gestão do passo 5
-- deixaria o chamador editar: tudo para `plataforma`, a própria federação sem
-- operadores para `admin`, nada para os demais.
--
-- `vinculado` = já existe conta no Supabase Auth ligada à linha. Vinculado e
-- sem último login é convite ainda não aceito.

CREATE OR REPLACE FUNCTION public.admin_listar_usuarios()
RETURNS TABLE (
    id              bigint,
    federacao_id    bigint,
    federacao_nome  text,
    nome            text,
    email           text,
    papel           text,
    ativo           boolean,
    conta_principal boolean,
    vinculado       boolean,
    ultimo_login    timestamptz,
    criado_em       timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT u.id, u.federacao_id, f.nome, u.nome, u.email, u.papel, u.ativo,
           u.conta_principal, u.auth_user_id IS NOT NULL, au.last_sign_in_at, u.created_at
      FROM usuario u
      JOIN federacao f       ON f.id  = u.federacao_id
      LEFT JOIN auth.users au ON au.id = u.auth_user_id
     WHERE public.eh_plataforma()
        OR (public.eh_admin_da_federacao(u.federacao_id) AND u.papel <> 'plataforma')
     ORDER BY f.nome, u.nome
$$;

COMMENT ON FUNCTION public.admin_listar_usuarios() IS
    'Usuários que o chamador pode gerir, com auth.users.last_sign_in_at. Nada além do último login sai de auth.users.';

REVOKE EXECUTE ON FUNCTION public.admin_listar_usuarios() FROM PUBLIC, anon;
GRANT  EXECUTE ON FUNCTION public.admin_listar_usuarios() TO authenticated;


-- Conferência rápida após rodar:
--   SELECT policyname, cmd FROM pg_policies
--    WHERE tablename IN ('federacao', 'usuario', 'ingestao_carga') ORDER BY 1;
--   SELECT privilege_type FROM information_schema.table_privileges
--    WHERE grantee = 'authenticated' AND table_name = 'usuario';   -- só SELECT
--   SELECT column_name, privilege_type FROM information_schema.column_privileges
--    WHERE grantee = 'authenticated' AND table_name = 'usuario'
--      AND privilege_type IN ('INSERT', 'UPDATE') ORDER BY 2, 1;   -- sem auth_user_id
