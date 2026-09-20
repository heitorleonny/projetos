-- ============================================================================
-- 05 — `metas` e `monitoramento` passam a aceitar os três níveis de tenant
--
-- Hoje as duas tabelas só sabem falar de EJ: `id_ej` é NOT NULL. Mas o Portal BJ
-- tem fato mensal próprio de NÚCLEO (26 núcleos × 9 meses) e a federação também
-- registra meta agregada. Sem isto, esses fatos não teriam onde morar — ou
-- virariam tabela nova, ou uma EJ-fantasma representando o núcleo.
--
-- O QUE ESTE ARQUIVO FAZ: troca uma FK obrigatória por três FKs opcionais e
-- mutuamente exclusivas. Só isso.
--
-- O QUE ELE NÃO FAZ, DE PROPÓSITO: as colunas de métrica nomeadas
-- (meta_faturamento, faturamento_mes, csat, ...) continuam exatamente como
-- estão. Não há catálogo `indicador`, não há pivô para linha-por-indicador.
-- Generalizar as métricas quebraria os 22 pontos de acesso via PostgREST nos
-- services e os testes que fixam valores exatos (tests/test_seguranca.py,
-- tests/test_empresas.py). A generalização de hoje é da DIMENSÃO DE TENANT,
-- não das métricas.
--
-- Nenhum backfill é necessário: toda linha existente já tem `id_ej` preenchido,
-- e `id_nucleo`/`id_federacao` nascem NULL — o que já satisfaz o CHECK.
-- ============================================================================


-- ── metas ───────────────────────────────────────────────────────────────────

ALTER TABLE metas ALTER COLUMN id_ej DROP NOT NULL;
ALTER TABLE metas ADD COLUMN IF NOT EXISTS id_nucleo    BIGINT REFERENCES nucleo(id);
ALTER TABLE metas ADD COLUMN IF NOT EXISTS id_federacao BIGINT REFERENCES federacao(id);

-- `num_nonnulls` é função nativa do Postgres e existe exatamente para este
-- caso; escrever a exclusividade à mão com OR/AND dá uma expressão mais longa
-- e mais fácil de errar na hora de estender para um quarto nível.
ALTER TABLE metas ADD CONSTRAINT metas_tenant_exclusivo
    CHECK (num_nonnulls(id_ej, id_nucleo, id_federacao) = 1);

COMMENT ON CONSTRAINT metas_tenant_exclusivo ON metas IS 'Exatamente um dos três níveis por linha: EJ, núcleo ou federação.';

-- Espelha idx_metas_ej_ano para os outros dois níveis: agora uma consulta pode
-- filtrar por qualquer um dos três.
CREATE INDEX IF NOT EXISTS idx_metas_nucleo_ano    ON metas (id_nucleo, ano);
CREATE INDEX IF NOT EXISTS idx_metas_federacao_ano ON metas (id_federacao, ano);


-- ── monitoramento ───────────────────────────────────────────────────────────

ALTER TABLE monitoramento ALTER COLUMN id_ej DROP NOT NULL;
ALTER TABLE monitoramento ADD COLUMN IF NOT EXISTS id_nucleo    BIGINT REFERENCES nucleo(id);
ALTER TABLE monitoramento ADD COLUMN IF NOT EXISTS id_federacao BIGINT REFERENCES federacao(id);

ALTER TABLE monitoramento ADD CONSTRAINT monitoramento_tenant_exclusivo
    CHECK (num_nonnulls(id_ej, id_nucleo, id_federacao) = 1);

COMMENT ON CONSTRAINT monitoramento_tenant_exclusivo ON monitoramento IS 'Exatamente um dos três níveis por linha: EJ, núcleo ou federação.';

CREATE INDEX IF NOT EXISTS idx_mon_nucleo_periodo    ON monitoramento (id_nucleo, ano, mes);
CREATE INDEX IF NOT EXISTS idx_mon_federacao_periodo ON monitoramento (id_federacao, ano, mes);


-- ── Uma lacuna conhecida, deixada em aberto de propósito ────────────────────
--
-- As UNIQUE existentes — metas (id_ej, ano) e monitoramento (id_ej, ano, mes) —
-- não protegem mais nada nas linhas de núcleo e de federação: com `id_ej` NULL,
-- o índice único aceita repetição (NULL nunca conflita com NULL no Postgres).
-- Ou seja, nada impede hoje duas metas 2026 do mesmo núcleo.
--
-- O conserto seria um índice único parcial por nível
-- (ex.: UNIQUE (id_nucleo, ano) WHERE id_nucleo IS NOT NULL). Não está aqui
-- porque ainda não existe uma linha sequer desses níveis, e porque a regra de
-- unicidade do fato de núcleo precisa ser confirmada contra a exportação do
-- Portal BJ antes de virar constraint. Registrado para não passar despercebido.
