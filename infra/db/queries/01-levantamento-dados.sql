-- ============================================================
-- Levantamento de volume e qualidade dos dados — Porta de decisão 1 do TCC
-- ============================================================
-- Rode no SQL Editor do Supabase (ou no Postgres do laboratório, depois da carga).
-- Cada bloco responde a uma pergunta do cronograma. Rode um de cada vez e
-- anote os números: eles decidem se a modelagem preditiva é viável.
--
-- Escrito a partir de portal_fejepe/banco.md — [CONFIRMAR] os nomes de coluna
-- de cluster por ano (cluster_2023..cluster_2026) contra o schema real.

-- ── 1. Cobertura geral ──────────────────────────────────────
-- Quantas EJs, quantos períodos, quantas observações no total.
SELECT
    COUNT(DISTINCT id_ej)                    AS ejs_distintas,
    COUNT(DISTINCT ano)                      AS anos,
    MIN(ano)                                 AS primeiro_ano,
    MAX(ano)                                 AS ultimo_ano,
    COUNT(*)                                 AS linhas_monitoramento
FROM monitoramento;

-- ── 2. Completude por ano ───────────────────────────────────
-- Onde a série é confiável e onde tem buraco.
SELECT
    ano,
    COUNT(DISTINCT id_ej)                                        AS ejs,
    COUNT(DISTINCT mes)                                          AS meses_com_dado,
    COUNT(*)                                                     AS linhas,
    ROUND(100.0 * COUNT(faturamento_mes)        / COUNT(*), 1)   AS pct_faturamento,
    ROUND(100.0 * COUNT(csat)                   / COUNT(*), 1)   AS pct_csat,
    ROUND(100.0 * COUNT(numero_membros)         / COUNT(*), 1)   AS pct_membros,
    ROUND(100.0 * COUNT(membros_engajados_mes)  / COUNT(*), 1)   AS pct_engajados
FROM monitoramento
GROUP BY ano
ORDER BY ano;

-- ── 3. Séries contínuas por EJ ──────────────────────────────
-- Quantas EJs têm histórico longo o bastante para gerar features de tendência.
WITH meses_por_ej AS (
    SELECT id_ej, COUNT(*) AS n_meses
    FROM monitoramento
    WHERE faturamento_mes IS NOT NULL
    GROUP BY id_ej
)
SELECT
    COUNT(*)                                          AS ejs_total,
    COUNT(*) FILTER (WHERE n_meses >= 6)              AS com_6_meses_ou_mais,
    COUNT(*) FILTER (WHERE n_meses >= 12)             AS com_12_meses_ou_mais,
    COUNT(*) FILTER (WHERE n_meses >= 24)             AS com_24_meses_ou_mais,
    ROUND(AVG(n_meses), 1)                            AS media_meses,
    MAX(n_meses)                                      AS max_meses
FROM meses_por_ej;

-- ── 4. Rótulo candidato A — queda de cluster (anual) ────────
-- Mede quantos EVENTOS de rótulo existem. Se este número for baixo
-- (menos de ~30 positivos), o rótulo anual não sustenta modelagem.
WITH transicoes AS (
    SELECT id_ej, 2024 AS ano, cluster_2023 AS anterior, cluster_2024 AS atual FROM empresa_junior
    UNION ALL
    SELECT id_ej, 2025, cluster_2024, cluster_2025 FROM empresa_junior
    UNION ALL
    SELECT id_ej, 2026, cluster_2025, cluster_2026 FROM empresa_junior
)
SELECT
    ano,
    COUNT(*) FILTER (WHERE anterior IS NOT NULL AND atual IS NOT NULL) AS transicoes_observaveis,
    COUNT(*) FILTER (WHERE atual < anterior)                           AS quedas,
    COUNT(*) FILTER (WHERE atual > anterior)                           AS subidas,
    COUNT(*) FILTER (WHERE atual = anterior)                           AS manteve
FROM transicoes
GROUP BY ano
ORDER BY ano;

-- ── 5. Rótulo candidato B — risco de ritmo (mensal) ─────────
-- Usa a classificação oficial de ritmo (calculos.md): sem_vendas quando
-- faturamento_mes = 0. Conta quantas observações mensais e quantos positivos
-- cada definição produziria. Compare com o bloco 4 antes de escolher.
SELECT
    COUNT(*)                                                    AS observacoes_mensais,
    COUNT(*) FILTER (WHERE faturamento_mes = 0)                 AS meses_sem_vendas,
    ROUND(100.0 * COUNT(*) FILTER (WHERE faturamento_mes = 0) / NULLIF(COUNT(*),0), 1)
                                                                AS pct_sem_vendas
FROM monitoramento
WHERE faturamento_mes IS NOT NULL;

-- ── 6. Rótulo candidato C — descolamento da meta ────────────
-- EJ cujo acumulado no mês está abaixo do ritmo necessário para a meta anual.
-- Proporcional: até o mês M, o esperado é meta_anual * M/12.
SELECT
    m.ano,
    COUNT(*)                                                             AS observacoes,
    COUNT(*) FILTER (
        WHERE mt.meta_faturamento > 0
          AND m.faturamento_acumulado < mt.meta_faturamento * m.mes / 12.0 * 0.7
    )                                                                    AS abaixo_de_70pct_do_ritmo
FROM monitoramento m
JOIN metas mt ON mt.id_ej = m.id_ej AND mt.ano = m.ano
WHERE m.faturamento_acumulado IS NOT NULL
GROUP BY m.ano
ORDER BY m.ano;

-- ── 7. Sanidade: duplicidade e furos ────────────────────────
SELECT id_ej, ano, mes, COUNT(*) AS repeticoes
FROM monitoramento
GROUP BY id_ej, ano, mes
HAVING COUNT(*) > 1
ORDER BY repeticoes DESC
LIMIT 20;
