-- ============================================================================
-- 02 — Tabela `federacao` + seed das 27 federações estaduais
--
-- Fonte: exportações do Portal BJ em ~/Documents/TCC/dados/
--   `federations_2026...xlsx`  → ID e nome oficial de cada federação (27)
--   `ejs_members_2026...xlsx`  → contagem de EJs federadas por federação (1.484)
-- Extraído em 18/09/2026.
--
-- Por que este arquivo pode ser escrito ANTES do dump do schema real: ele só
-- CRIA uma tabela nova. Não faz ALTER, não faz backfill, não depende de como
-- as tabelas existentes estão de fato. As migrações que tocam empresa_junior,
-- metas e monitoramento ficam para depois do inventário (queries/02).
--
-- Decisão embutida: a PK é o ID do Portal BJ, não um serial próprio. Assim o
-- identificador do tenant é o mesmo identificador que o movimento já usa, e a
-- ingestão das exportações não precisa de tabela de-para. Os IDs 1 e 27 não
-- existem na origem — a sequência tem buracos, e isso é esperado.
-- ============================================================================

CREATE TABLE IF NOT EXISTS federacao (
    id         BIGINT      PRIMARY KEY,               -- ID do Portal BJ
    slug       TEXT        NOT NULL UNIQUE,           -- identificador em URL/subdomínio
    nome       TEXT        NOT NULL,                  -- nome oficial, para exibição
    uf         CHAR(2)     NOT NULL,                  -- [CONFIRMAR] inferido, ver nota
    status     TEXT        NOT NULL DEFAULT 'ativa'
                           CHECK (status IN ('ativa', 'inativa', 'piloto')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  federacao      IS 'Tenant do portal. Uma linha por federação estadual.';
COMMENT ON COLUMN federacao.id   IS 'ID da federação no Portal Brasil Júnior; não é serial.';
COMMENT ON COLUMN federacao.slug IS 'Derivado do nome, sem acento e em minúsculas.';
COMMENT ON COLUMN federacao.uf   IS 'UF sede. Inferido do nome da federação — confirmar com a BJ.';

-- Nota sobre `uf`: a coluna NÃO existe em nenhuma exportação. Os valores abaixo
-- foram inferidos do nome de cada federação. O resultado cobre exatamente as 27
-- unidades federativas, uma por federação, o que sustenta a inferência — mas
-- Concentro (DF) historicamente atende também o entorno goiano, então UF é a
-- sede, não a área de atuação. Confirmar antes de usar `uf` em qualquer regra.

-- Nota sobre CNPJ: a exportação traz o MESMO CNPJ (1328030000194) para FEJEMG e
-- Tocantins Júnior, e nulo em 11 das 27. CNPJ não serve como chave alternativa.

INSERT INTO federacao (id, slug, nome, uf) VALUES
    (  2, 'fejers', 'FEJERS', 'RS'),  -- 61 EJs federadas
    (  3, 'fejesc', 'FEJESC', 'SC'),  -- 69 EJs federadas
    (  4, 'fejepar', 'FEJEPAR', 'PR'),  -- 138 EJs federadas
    (  5, 'fejesp', 'FEJESP', 'SP'),  -- 221 EJs federadas
    (  6, 'riojunior', 'RioJunior', 'RJ'),  -- 75 EJs federadas
    (  7, 'fejemg', 'FEJEMG', 'MG'),  -- 285 EJs federadas
    (  8, 'juniores', 'Juniores', 'ES'),  -- 28 EJs federadas
    (  9, 'unijr-ba', 'UNIJr-BA', 'BA'),  -- 77 EJs federadas
    ( 10, 'serjunior', 'SERJÚNIOR', 'SE'),  -- 24 EJs federadas
    ( 11, 'fejea', 'FEJEA', 'AL'),  -- 34 EJs federadas
    ( 12, 'fejepe', 'FEJEPE', 'PE'),  -- 42 EJs federadas
    ( 13, 'pb-junior', 'PB júnior', 'PB'),  -- 44 EJs federadas
    ( 14, 'rn-junior', 'RN Júnior', 'RN'),  -- 64 EJs federadas
    ( 15, 'fejece', 'FEJECE', 'CE'),  -- 65 EJs federadas
    ( 16, 'maranhao-junior', 'Maranhão Júnior', 'MA'),  -- 28 EJs federadas
    ( 17, 'goias-junior', 'Goiás Júnior', 'GO'),  -- 39 EJs federadas
    ( 18, 'concentro', 'Concentro', 'DF'),  -- 58 EJs federadas
    ( 19, 'fejems', 'FEJEMS', 'MS'),  -- 26 EJs federadas
    ( 20, 'para-junior', 'Pará Júnior', 'PA'),  -- 34 EJs federadas
    ( 21, 'piaui-junior', 'Piauí Júnior', 'PI'),  -- 12 EJs federadas
    ( 22, 'acre-junior', 'Acre Júnior', 'AC'),  -- 6 EJs federadas
    ( 23, 'femtej', 'FEMTEJ', 'MT'),  -- 18 EJs federadas
    ( 24, 'bare-junior', 'Baré Júnior', 'AM'),  -- 13 EJs federadas
    ( 25, 'fejero', 'FEJERO', 'RO'),  -- 6 EJs federadas
    ( 26, 'tocantins-junior', 'Tocantins Júnior', 'TO'),  -- 12 EJs federadas
    ( 28, 'roraima-junior', 'Roraima Júnior', 'RR'),  -- 2 EJs federadas
    ( 29, 'fejeap', 'FEJEAP', 'AP')   -- 3 EJs federadas
ON CONFLICT (id) DO UPDATE
    SET slug = EXCLUDED.slug,
        nome = EXCLUDED.nome,
        uf   = EXCLUDED.uf,
        updated_at = now();

-- Conferência rápida após rodar:
--   SELECT count(*) FROM federacao;                      -- esperado: 27
--   SELECT count(DISTINCT uf) FROM federacao;            -- esperado: 27
--   SELECT * FROM federacao WHERE slug = 'fejepe';       -- id 12, PE
