-- ============================================================================
-- 14 — Slogan da federação, como dado e não como texto no código
--
-- O subtítulo do Dashboard ("RNN 7 - Acreditamos e trabalhamos por uma
-- federação de impacto.") estava escrito em DashboardPage.tsx. É frase da
-- FEJEPE, e a FEJEMG passou a vê-la quando entrou na demo (29/09/2026).
--
-- Vira coluna opcional de `federacao`, lida junto com o resto do branding.
-- Federação sem slogan: o Dashboard não mostra o subtítulo.
--
-- Aditiva e idempotente: pode rodar de novo sem efeito.
-- ============================================================================

ALTER TABLE federacao ADD COLUMN IF NOT EXISTS slogan TEXT;

COMMENT ON COLUMN federacao.slogan IS 'Frase exibida sob o título do Dashboard. Nula: sem subtítulo.';

-- O texto que já aparecia na tela, copiado sem mudança: com esta linha, o
-- portal da FEJEPE continua mostrando exatamente o que mostrava.
UPDATE federacao
   SET slogan     = 'RNN 7 - Acreditamos e trabalhamos por uma federação de impacto.',
       updated_at = now()
 WHERE slug = 'fejepe'
   AND slogan IS NULL;

-- Mesma regra de 09: `anon` lê branding por coluna. O slogan é branding —
-- aparece antes de qualquer dado — então entra na lista.
GRANT SELECT (slogan) ON federacao TO anon;
