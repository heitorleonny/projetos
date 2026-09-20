-- ============================================================================
-- 08 — `cluster_historico`: o cluster deixa de ser uma coluna por ano
--
-- O PROBLEMA, e por que ele é diferente do que 05 resolveu
--
-- `empresa_junior` tem hoje `cluster`, `cluster_2023`, `cluster_2024`,
-- `cluster_2025` e `cluster_2026`. Uma coluna nova por ano significa um ALTER
-- TABLE por ano, mais uma linha nova no mapa de `app/utils/cluster.py`, mais
-- uma passagem em cada service que filtra por cluster. O custo cresce com o
-- tempo e nunca é pago de uma vez.
--
-- Em `metas` e `monitoramento` (arquivo 05) a decisão foi a oposta: manter as
-- colunas de métrica nomeadas e generalizar só a dimensão de tenant. Não é
-- incoerência — lá o problema era de TENANT (uma EJ, um núcleo ou uma federação
-- podem ser donos do mesmo fato), e as métricas já eram estáveis no tempo. Aqui
-- o problema é de PERÍODO: o fato é um só (o cluster da EJ), e o que se repete é
-- o ano. Normalizar resolve o problema que existe, no único lugar onde ele está.
--
-- É também o mesmo padrão que a exportação do Portal BJ traz em RESULTADO
-- 2016..2024, e que o projeto já decidiu não reproduzir.
--
-- Escopo: UM fato, cluster por EJ por ano. Isto não é um catálogo `indicador`,
-- e não abre precedente para pivotar as colunas de métrica — essa generalização
-- continua descartada de propósito (ver 05 e docs/adr-002).
--
-- Sem os três níveis de tenant: cluster só existe no nível de EJ. Núcleo e
-- federação não têm cluster no movimento.
-- ============================================================================


-- ── A tabela ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cluster_historico (
    id_ej   BIGINT  NOT NULL REFERENCES empresa_junior(id_ej),
    ano     INTEGER NOT NULL,
    cluster INTEGER NOT NULL,
    PRIMARY KEY (id_ej, ano)
);

COMMENT ON TABLE cluster_historico IS 'Cluster da EJ por ano. Uma linha por EJ por ano — substitui as colunas cluster_20XX.';

-- A PK (id_ej, ano) já cobre a leitura por EJ. Este índice cobre o outro
-- sentido, que é o filtro dos services: "quais EJs estão no cluster N no ano X".
CREATE INDEX IF NOT EXISTS idx_cluster_historico_ano_cluster ON cluster_historico (ano, cluster);


-- ── Backfill ────────────────────────────────────────────────────────────────
--
-- Regra replicada de `app/utils/cluster.py::get_cluster_value_for_year`, como
-- ela era antes deste arquivo: usa a coluna do ano e, só na ausência dela, cai
-- para a coluna `cluster` sem sufixo. Nenhuma regra nova foi inventada aqui.

-- 1. O caso normal: cada coluna anual preenchida vira uma linha do seu ano.
INSERT INTO cluster_historico (id_ej, ano, cluster)
SELECT ej.id_ej, v.ano, v.cluster
  FROM empresa_junior ej
 CROSS JOIN LATERAL (VALUES
     (2023, ej.cluster_2023),
     (2024, ej.cluster_2024),
     (2025, ej.cluster_2025),
     (2026, ej.cluster_2026)
 ) AS v(ano, cluster)
 WHERE v.cluster IS NOT NULL
ON CONFLICT (id_ej, ano) DO NOTHING;

-- 2. O fallback, e aqui há uma DECISÃO DE MIGRAÇÃO — não um fato lido do dado:
--
--    Uma EJ sem NENHUMA coluna anual preenchida, mas com a coluna `cluster`
--    antiga, entra como ANO 2026. O 2026 vem de `settings.ANO_DEFAULT`: é o ano
--    corrente assumido pela aplicação, e portanto o único ano em que esse valor
--    solto tinha significado na prática.
--
--    O que se perde ao escolher isso: o código antigo caía para `cluster` em
--    QUALQUER ano consultado, então uma EJ com 2023 preenchido e 2024 vazio
--    respondia o `cluster` solto quando perguntada sobre 2024. Depois desta
--    migração ela responde NULL para 2024 — a ausência passa a ser ausência, em
--    vez de um valor de outro período disfarçado. Isso é o desejado: o dado do
--    TCC não pode ter cluster "emprestado" de um ano para outro sem registro.
INSERT INTO cluster_historico (id_ej, ano, cluster)
SELECT ej.id_ej, 2026, ej.cluster
  FROM empresa_junior ej
 WHERE ej.cluster IS NOT NULL
   AND ej.cluster_2023 IS NULL
   AND ej.cluster_2024 IS NULL
   AND ej.cluster_2025 IS NULL
   AND ej.cluster_2026 IS NULL
ON CONFLICT (id_ej, ano) DO NOTHING;


-- ── As colunas antigas viram legado ─────────────────────────────────────────
--
-- Renomeadas, não apagadas — mesma política de proveniência de
-- `federacao` → `federacao_legado` em 04. Enquanto o backfill não for conferido
-- contra a base real, elas são a única evidência do que cada linha dizia antes.
-- Dropar só depois dessa conferência, em migração própria.

ALTER TABLE empresa_junior RENAME COLUMN cluster      TO cluster_legado;
ALTER TABLE empresa_junior RENAME COLUMN cluster_2023 TO cluster_2023_legado;
ALTER TABLE empresa_junior RENAME COLUMN cluster_2024 TO cluster_2024_legado;
ALTER TABLE empresa_junior RENAME COLUMN cluster_2025 TO cluster_2025_legado;
ALTER TABLE empresa_junior RENAME COLUMN cluster_2026 TO cluster_2026_legado;

COMMENT ON COLUMN empresa_junior.cluster_legado IS 'Pré-normalização. Auditoria: não ler em código — o valor vivo está em cluster_historico.';


-- ── RLS ─────────────────────────────────────────────────────────────────────
--
-- Tabela nova entra com RLS ligada, como todas as outras (ver 07). O caminho
-- até o tenant é um só: a EJ dona da linha.

ALTER TABLE cluster_historico ENABLE ROW LEVEL SECURITY;

CREATE POLICY cluster_historico_select_proprio_tenant ON cluster_historico
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM empresa_junior ej
             WHERE ej.id_ej = cluster_historico.id_ej
               AND ej.federacao_id = nullif(auth.jwt() ->> 'federacao_id', '')::bigint
        )
    );

GRANT SELECT ON cluster_historico TO authenticated;


-- Conferência rápida após rodar, numa base com dados:
--   SELECT ch.id_ej, ch.ano, ch.cluster,
--          ej.cluster_2023_legado, ej.cluster_2024_legado,
--          ej.cluster_2025_legado, ej.cluster_2026_legado, ej.cluster_legado
--     FROM cluster_historico ch JOIN empresa_junior ej USING (id_ej)
--    ORDER BY ch.id_ej, ch.ano;
