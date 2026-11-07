-- ============================================================================
-- 15 — O painel também edita o slogan da federação
--
-- `federacao.slogan` nasceu em 14, depois da 13, que concedeu ao operador da
-- plataforma o UPDATE por coluna do branding (nome, status, logo, cor). A
-- coluna nova fica de fora daquele GRANT porque não existia quando ele rodou.
--
-- Nada muda na regra: quem alcança a linha é a política
-- `federacao_update_plataforma` de 13 (só `plataforma`). Isto só acrescenta a
-- coluna ao que ela pode gravar.
-- ============================================================================

GRANT UPDATE (slogan) ON federacao TO authenticated;
