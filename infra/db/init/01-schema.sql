-- Esquema do laboratório de dados do TCC.
--
-- Réplica local das tabelas do Supabase, usada APENAS para a modelagem
-- preditiva (detecção antecipada de risco). A API de produção continua
-- lendo do Supabase — ver docs/adr-001-supabase-vs-postgres.md.
--
-- Fonte: portal_fejepe/banco.md + app/utils/cluster.py
-- [CONFIRMAR] tipos e nullability contra o schema real antes de confiar
-- em qualquer carga; este arquivo foi derivado da documentação, não de
-- um dump do banco.

CREATE TABLE IF NOT EXISTS empresa_junior (
    id            BIGINT PRIMARY KEY,
    id_ej         BIGINT UNIQUE NOT NULL,
    nome          TEXT NOT NULL,
    cnpj          TEXT,
    ano_federacao INTEGER,
    federacao     TEXT,
    cluster       INTEGER,
    cluster_2023  INTEGER,
    cluster_2024  INTEGER,
    cluster_2025  INTEGER,
    cluster_2026  INTEGER,
    comunidade    TEXT,
    estado        TEXT,
    cidade        TEXT,
    universidade  TEXT,
    curso         TEXT,
    status        TEXT,
    foto_url      TEXT,
    created_at    TIMESTAMP,
    updated_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metas (
    id                    BIGINT PRIMARY KEY,
    id_ej                 BIGINT NOT NULL REFERENCES empresa_junior(id_ej),
    ano                   INTEGER NOT NULL,
    meta_faturamento      NUMERIC,
    meta_taxa_colaboracao NUMERIC,
    meta_csat             NUMERIC,
    meta_projetos_impacto INTEGER,
    meta_pdi              BOOLEAN,
    meta_engajamento_mej  NUMERIC,
    created_at            TIMESTAMP,
    UNIQUE (id_ej, ano)
);

CREATE TABLE IF NOT EXISTS monitoramento (
    id                          BIGINT PRIMARY KEY,
    id_ej                       BIGINT NOT NULL REFERENCES empresa_junior(id_ej),
    ano                         INTEGER NOT NULL,
    mes                         INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    faturamento_mes             NUMERIC,
    faturamento_acumulado       NUMERIC,
    faturamento_colab_mes       NUMERIC,
    faturamento_colab_acumulado NUMERIC,
    projetos_vendidos_mes       INTEGER,
    projetos_totais             INTEGER,
    csat                        NUMERIC,
    numero_membros              INTEGER,
    membros_engajados_mes       INTEGER,
    created_at                  TIMESTAMP,
    UNIQUE (id_ej, ano, mes)
);

-- A modelagem varre a série por EJ e por período; estes índices cobrem
-- o padrão de acesso previsto.
CREATE INDEX IF NOT EXISTS idx_mon_ej_periodo ON monitoramento (id_ej, ano, mes);
CREATE INDEX IF NOT EXISTS idx_mon_periodo    ON monitoramento (ano, mes);
CREATE INDEX IF NOT EXISTS idx_metas_ej_ano   ON metas (id_ej, ano);
