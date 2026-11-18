-- ============================================================================
-- 26 — Projeto de impacto realizado (monitoramento) e o cluster que ele libera
--
-- A planilha do Portal BJ traz, além da META (`META_DE_IMPACT_PROJECTS`, já em
-- `metas.meta_projetos_impacto`), o REALIZADO: `PROJETOS_DE_IMPACTO`. Em 21/09
-- ele vem vazio ou 1 em cada linha mensal, e uma vez 1 repete-se até o último mês
-- do ano (306 de 13.563 linhas; nenhuma EJ perde o valor ao longo dos meses).
-- Vazio quer dizer "nenhum projeto de impacto", não "dado ausente".
--
-- REGRA DE NEGÓCIO (Heitor, 09/11/2026): projeto de impacto é obrigatório nos
-- clusters 4 e 5. O tracking pode apontar o C4 ou o C5, mas o cluster REAL só
-- chega a eles, e só permanece neles, se a EJ tiver ao menos um projeto de
-- impacto; sem projeto fica no C3. A regra vive no backend
-- (calculo_service.aplicar_regra_projeto_impacto); aqui só se guarda o dado.
--
-- Migração aditiva: coluna nova, nulável, sem default. Não reescreve dado
-- existente. Linhas gravadas antes desta migração ficam NULL até a próxima
-- carga da planilha (que traz a coluna); o backend lê NULL como "sem projeto".
-- ============================================================================

ALTER TABLE monitoramento
    ADD COLUMN IF NOT EXISTS projetos_impacto INTEGER;

COMMENT ON COLUMN monitoramento.projetos_impacto IS
    'Projetos de impacto realizados no ano até o mês da linha (PROJETOS_DE_IMPACTO). NULL = nenhum. Requisito para os clusters 4 e 5.';

-- Staging: a coluna tipada é GERADA de `linha`, como todas as outras (ver 10).
-- Linhas de cargas antigas não têm a chave e ficam NULL.
ALTER TABLE ingestao_staging_ej
    ADD COLUMN IF NOT EXISTS projetos_de_impacto INTEGER
        GENERATED ALWAYS AS ((linha ->> 'PROJETOS_DE_IMPACTO')::integer) STORED;

-- O papel `ingestao` grava por coluna (ver 11). A coluna nova entra na lista de
-- INSERT e de UPDATE; nada além disso é concedido.
GRANT INSERT (projetos_impacto) ON monitoramento TO ingestao;
GRANT UPDATE (projetos_impacto) ON monitoramento TO ingestao;
