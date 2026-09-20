-- ============================================================================
-- 09 — Branding por federação: logo, cor e leitura pública
--
-- O QUE ENTRA AQUI, E POR QUÊ
--
-- O frontend nasceu assumindo uma federação só: nome do produto, logo, favicon
-- e paleta de cores estão escritos no código e compilados no bundle. Trocar de
-- federação exigiria rebuildar a imagem. Estas duas colunas movem isso para o
-- banco, onde é dado do tenant como qualquer outro.
--
-- `nome` já existe (02-federacao.sql) e continua sendo o nome de exibição —
-- não há coluna nova para isso. O que faltava era logo e cor.
--
-- A EXCEÇÃO DE RLS DESTE ARQUIVO (leia antes de copiar o padrão)
--
-- 07-rls-policies.sql não dá GRANT nenhum ao role `anon`: requisição sem
-- autenticação não lê tabela alguma. Branding não cabe nessa regra, por um
-- motivo concreto: a tela de login mostra nome e logo ANTES de existir
-- qualquer JWT. Um endpoint público sem token chega ao PostgREST como `anon`,
-- sem claim `federacao_id`, e a política de tenant devolveria conjunto vazio —
-- a tela ficaria sem marca nenhuma.
--
-- A liberação é a menor possível, em três camadas:
--
--   1. GRANT por COLUNA — `anon` só enxerga slug, nome, logo_url e
--      cor_primaria. `id`, `uf`, `status`, `created_at` e `updated_at` ficam
--      fora: uma consulta anônima que as peça é recusada pelo Postgres, não
--      pela aplicação.
--   2. Política própria, só para `anon`, filtrando `status = 'ativa'` —
--      federação inativa ou em piloto não se anuncia.
--   3. Só SELECT. Escrita anônima continua não existindo em lugar nenhum.
--
-- O que isso expõe, no pior caso: o nome, o logo e a cor de federações ativas,
-- que são exatamente o que cada uma publica no próprio site. Nenhum dado de
-- EJ, de meta ou de usuário passa por aqui.
--
-- `status` aparece no USING da política mas NÃO no GRANT de coluna, e isso é
-- proposital: o filtro da política é avaliado pelo banco, não pelo cliente, e
-- portanto não exige privilégio de leitura na coluna. Quem é `anon` é filtrado
-- por `status` sem conseguir lê-lo.
-- ============================================================================


-- ── Colunas ─────────────────────────────────────────────────────────────────

ALTER TABLE federacao ADD COLUMN IF NOT EXISTS logo_url     TEXT;
ALTER TABLE federacao ADD COLUMN IF NOT EXISTS cor_primaria TEXT;

COMMENT ON COLUMN federacao.logo_url     IS 'Logo de exibição. Caminho público servido pelo frontend ou URL absoluta.';
COMMENT ON COLUMN federacao.cor_primaria IS 'Cor da marca em hexadecimal (#RRGGBB). Vira --color-primary-500 no frontend.';

-- O valor vai direto para uma custom property de CSS no navegador. O CHECK
-- existe para que só um hexadecimal de 6 dígitos chegue lá — o frontend valida
-- de novo, mas a garantia mais barata é a que fica no banco.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'federacao'::regclass
           AND conname  = 'federacao_cor_primaria_hex'
    ) THEN
        ALTER TABLE federacao
            ADD CONSTRAINT federacao_cor_primaria_hex
            CHECK (cor_primaria IS NULL OR cor_primaria ~ '^#[0-9A-Fa-f]{6}$');
    END IF;
END
$$;


-- ── Branding da FEJEPE ──────────────────────────────────────────────────────
--
-- Os dois valores são os que já estão no frontend hoje, copiados sem mudança:
--   logo_url     → o arquivo público servido em front_portal_fejepe/public/
--                  (o caminho é referenciado, não duplicado)
--   cor_primaria → --color-primary-500 de src/index.css
--
-- É isso que faz a troca ser invisível: com esta linha no banco, abrir o
-- portal continua mostrando exatamente o que mostrava antes desta migração.

UPDATE federacao
   SET logo_url     = '/logo_fejepe.svg',
       cor_primaria = '#0D6EFD',
       updated_at   = now()
 WHERE slug = 'fejepe';


-- ── Leitura pública das colunas de branding ─────────────────────────────────

DROP POLICY IF EXISTS federacao_select_branding_publico ON federacao;

CREATE POLICY federacao_select_branding_publico ON federacao
    FOR SELECT TO anon
    USING (status = 'ativa');

-- GRANT por coluna: é ele, e não a política, que impede `anon` de pedir `id`,
-- `uf` ou `status`. Política restringe LINHA; GRANT restringe COLUNA. As duas
-- coisas são necessárias e nenhuma substitui a outra.
GRANT SELECT (slug, nome, logo_url, cor_primaria) ON federacao TO anon;


-- Conferência rápida após rodar:
--   SELECT slug, nome, logo_url, cor_primaria FROM federacao WHERE slug = 'fejepe';
--   -- esperado: FEJEPE | /logo_fejepe.svg | #0D6EFD
--
--   SET ROLE anon;
--   SELECT slug, nome, logo_url, cor_primaria FROM federacao;  -- 27 linhas ativas
--   SELECT id FROM federacao;                                  -- ERRO: permission denied
--   SELECT * FROM empresa_junior;                              -- ERRO: permission denied
--   RESET ROLE;
