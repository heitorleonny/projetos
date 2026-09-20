-- ============================================================================
-- 04 — `empresa_junior.federacao_id`: a coluna de tenant vira FK de verdade
--
-- Hoje a federação de uma EJ é uma coluna de TEXTO LIVRE (`federacao`), que o
-- inventário do schema mostrou ser implicitamente monotenant e de grafia não
-- confiável (ver docs/levantamento-semana1-multitenant.md, seções 1 e 6). Texto
-- livre não serve de predicado de RLS: a política precisa comparar o claim do
-- JWT com uma chave estável, não com uma string que cada carga escreveu de um
-- jeito.
--
-- Ordem deste arquivo: adicionar nulável → backfill → SET NOT NULL. Fazer o
-- NOT NULL antes do backfill quebraria a subida em qualquer base que já tenha
-- linhas.
-- ============================================================================


-- ── 1. Coluna nova, ainda nulável ───────────────────────────────────────────

ALTER TABLE empresa_junior ADD COLUMN IF NOT EXISTS federacao_id BIGINT REFERENCES federacao(id);

COMMENT ON COLUMN empresa_junior.federacao_id IS 'Tenant da EJ. É o predicado de toda política de RLS sobre esta tabela.';


-- ── 2. Backfill ─────────────────────────────────────────────────────────────
--
-- PREMISSA, e ela é datada: TODO dado que existe hoje é da FEJEPE (id 12).
-- Por isso o UPDATE não olha a coluna de texto `federacao` — ela pode estar
-- inconsistente, e conferir grafia aqui só introduziria um jeito novo de errar.
--
-- Isso DEIXA DE SER VERDADE a partir do segundo tenant. Quando o dado de
-- FEJEPAR (Núcleo Maringá) entrar, a carga tem de trazer `federacao_id`
-- explícito — este UPDATE não pode ser rodado de novo, e não existe DEFAULT
-- nesta coluna justamente para que uma carga sem tenant falhe alto, em vez de
-- rotular silenciosamente a EJ errada.
UPDATE empresa_junior SET federacao_id = 12 WHERE federacao_id IS NULL;


-- ── 3. Agora sim, obrigatória ───────────────────────────────────────────────

ALTER TABLE empresa_junior ALTER COLUMN federacao_id SET NOT NULL;


-- ── 4. A coluna de texto antiga vira registro de auditoria ──────────────────
--
-- NÃO apagada: renomeada. O backfill acima é uma premissa, não uma leitura do
-- dado — enquanto ela não for validada contra a base real da FEJEPE, a única
-- evidência do que cada linha dizia antes é esta coluna. É a mesma política de
-- proveniência que o levantamento de dados do projeto adota.
--
-- Dropar só numa migração futura, depois de conferir que
-- `federacao_legado` e `federacao_id` concordam em 100% das linhas
-- (infra/db/queries/03-diagnostico-tenant.sql).
ALTER TABLE empresa_junior RENAME COLUMN federacao TO federacao_legado;

COMMENT ON COLUMN empresa_junior.federacao_legado IS 'Texto livre anterior ao backfill. Auditoria: não ler em código, dropar só após validar o backfill.';


-- ── 5. Índices ──────────────────────────────────────────────────────────────
--
-- Sob RLS o predicado de tenant entra em TODA query, então federacao_id é a
-- primeira coluna de todo índice composto novo. Os compostos abaixo seguem os
-- filtros que os services realmente usam (`listar_empresas` em
-- app/services/empresa_service.py, `calcular_indicadores_rede` e `gerar_ranking`
-- em app/services/rede_service.py): `comunidade` e `status` por igualdade.
--
-- O que ficou DE FORA, de propósito:
--   * (federacao_id, ano_federacao) — o enunciado sugeria, mas `ano_federacao`
--     não é filtro em nenhum service; só aparece no modelo de resposta
--     (app/models/empresa.py). Índice que nada usa é custo de escrita sem
--     ganho de leitura.
--   * nome / cidade / universidade — filtrados com ILIKE '%termo%'. Curinga à
--     esquerda não usa índice btree; resolver isso é caso para trigram (pg_trgm),
--     que é outra discussão.
--   * cluster_2023..cluster_2026 — são filtro real, mas indexá-las fixaria o
--     formato dessas colunas. Decisão em aberto, ver docs/ — nenhum índice
--     sobre elas até o destino delas ser decidido.

CREATE INDEX IF NOT EXISTS idx_ej_federacao            ON empresa_junior (federacao_id);
CREATE INDEX IF NOT EXISTS idx_ej_federacao_comunidade ON empresa_junior (federacao_id, comunidade);
CREATE INDEX IF NOT EXISTS idx_ej_federacao_status     ON empresa_junior (federacao_id, status);

-- Este não é para filtro de usuário: é para o JOIN que as políticas de RLS de
-- `metas` e `monitoramento` fazem (EXISTS ... WHERE ej.id_ej = ? AND
-- ej.federacao_id = <claim>). Com as duas colunas no índice o EXISTS resolve
-- sem ir ao heap.
CREATE INDEX IF NOT EXISTS idx_ej_id_ej_federacao      ON empresa_junior (id_ej, federacao_id);
