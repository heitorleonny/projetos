-- ============================================================================
-- 07 — Row Level Security: o isolamento entre federações
--
-- A regra única deste arquivo: uma linha só é visível se o tenant dela bater
-- com o `federacao_id` que veio no JWT. O claim é lido sempre do mesmo jeito:
--
--     nullif(auth.jwt() ->> 'federacao_id', '')::bigint
--
-- Sem claim, `auth.jwt()` devolve '{}', o `->>` devolve NULL, a comparação vira
-- NULL, e NULL não é TRUE — logo, NENHUMA linha passa. Esse é o comportamento
-- mais importante daqui: token sem tenant vê conjunto vazio, nunca a tabela
-- inteira. Está coberto por tests/test_rls.py.
--
-- ESCOPO: só políticas de SELECT, e só para `authenticated`. Não há política de
-- INSERT/UPDATE/DELETE porque não há escrita na API hoje; quando houver, ela
-- vem junto com a regra de permissão por papel, não antes.
--
-- Nota sobre quem escapa da RLS, de propósito:
--   * o DONO das tabelas (o usuário `portal` no lab, `postgres` no Supabase) —
--     é quem roda migração e carga de dados;
--   * `service_role` (BYPASSRLS) — scripts administrativos.
--   Por isso a service key NÃO pode aparecer no caminho de request da
--   aplicação: com ela, toda política deste arquivo é decorativa.
-- ============================================================================


-- ── federacao ───────────────────────────────────────────────────────────────

ALTER TABLE federacao ENABLE ROW LEVEL SECURITY;

CREATE POLICY federacao_select_proprio_tenant ON federacao
    FOR SELECT TO authenticated
    USING (id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint);

GRANT SELECT ON federacao TO authenticated;


-- ── nucleo ──────────────────────────────────────────────────────────────────

ALTER TABLE nucleo ENABLE ROW LEVEL SECURITY;

CREATE POLICY nucleo_select_proprio_tenant ON nucleo
    FOR SELECT TO authenticated
    USING (federacao_id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint);

GRANT SELECT ON nucleo TO authenticated;


-- ── usuario ─────────────────────────────────────────────────────────────────
--
-- Um usuário enxerga os colegas da própria federação — inclusive o e-mail
-- deles. Restringir mais (cada um só se vê, ou só admin lista) é regra de
-- papel, e papel ainda não entrou nas políticas. Fica registrado como decisão
-- consciente, não como esquecimento.
--
-- O hook `custom_access_token_hook` (06) lê esta tabela sem esbarrar na
-- política porque é SECURITY DEFINER e o dono da função é o dono da tabela.

ALTER TABLE usuario ENABLE ROW LEVEL SECURITY;

CREATE POLICY usuario_select_proprio_tenant ON usuario
    FOR SELECT TO authenticated
    USING (federacao_id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint);

GRANT SELECT ON usuario TO authenticated;


-- ── empresa_junior ──────────────────────────────────────────────────────────

ALTER TABLE empresa_junior ENABLE ROW LEVEL SECURITY;

CREATE POLICY empresa_junior_select_proprio_tenant ON empresa_junior
    FOR SELECT TO authenticated
    USING (federacao_id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint);

GRANT SELECT ON empresa_junior TO authenticated;


-- ── metas e monitoramento: os três caminhos até o tenant ────────────────────
--
-- Depois de 05, a linha pode pendurar em qualquer um dos três níveis. A
-- política precisa cobrir os três, e cobre com um OR só — três políticas
-- separadas dariam no mesmo resultado (políticas permissivas se somam em OR),
-- mas espalhariam a regra por três lugares para manter em sincronia.
--
--   via id_ej        → a EJ dona da linha é da minha federação
--   via id_nucleo    → o núcleo dono da linha é da minha federação
--   via id_federacao → a linha é da minha federação, direto
--
-- O CHECK `num_nonnulls(...) = 1` garante que exatamente um ramo se aplica por
-- linha; os outros dois avaliam para NULL/FALSE sem estrago.

ALTER TABLE metas ENABLE ROW LEVEL SECURITY;

CREATE POLICY metas_select_proprio_tenant ON metas
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM empresa_junior ej
             WHERE ej.id_ej = metas.id_ej
               AND ej.federacao_id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint
        )
        OR EXISTS (
            SELECT 1 FROM nucleo n
             WHERE n.id = metas.id_nucleo
               AND n.federacao_id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint
        )
        OR metas.id_federacao = nullif(auth.jwt() ->> 'federacao_id', '')::bigint
    );

GRANT SELECT ON metas TO authenticated;


ALTER TABLE monitoramento ENABLE ROW LEVEL SECURITY;

CREATE POLICY monitoramento_select_proprio_tenant ON monitoramento
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM empresa_junior ej
             WHERE ej.id_ej = monitoramento.id_ej
               AND ej.federacao_id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint
        )
        OR EXISTS (
            SELECT 1 FROM nucleo n
             WHERE n.id = monitoramento.id_nucleo
               AND n.federacao_id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint
        )
        OR monitoramento.id_federacao = nullif(auth.jwt() ->> 'federacao_id', '')::bigint
    );

GRANT SELECT ON monitoramento TO authenticated;


-- ── plano ───────────────────────────────────────────────────────────────────
--
-- Catálogo, não dado de tenant: os mesmos três planos valem para as 27
-- federações. RLS ligada mesmo assim — defesa em profundidade. Nenhuma tabela
-- deste schema fica sem RLS, para que "tem RLS?" nunca precise ser respondido
-- caso a caso.

ALTER TABLE plano ENABLE ROW LEVEL SECURITY;

CREATE POLICY plano_select_catalogo_publico ON plano
    FOR SELECT TO authenticated
    USING (true);

GRANT SELECT ON plano TO authenticated;


-- ── `anon` não recebe nada ──────────────────────────────────────────────────
--
-- Ausência proposital de GRANT: requisição sem autenticação não lê tabela
-- nenhuma. Política de RLS não substitui GRANT (e nem o contrário) — sem o
-- GRANT o role sequer chega a ser avaliado pela política.

-- Conferência rápida após rodar:
--   SELECT tablename, rowsecurity FROM pg_tables
--    WHERE schemaname = 'public' ORDER BY tablename;   -- rowsecurity = t em todas
--   SELECT tablename, policyname, cmd FROM pg_policies WHERE schemaname = 'public';
