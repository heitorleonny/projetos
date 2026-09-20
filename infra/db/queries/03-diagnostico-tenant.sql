-- ============================================================================
-- 03 — Diagnóstico pré-migração multi-tenant
--
-- Objetivo: responder, com dado e não com suposição, às decisões abertas da
-- semana 1: como normalizar a coluna `federacao`, se há órfãos que impedem a
-- FK composta, e se as colunas cluster_YYYY merecem normalização.
--
-- Rode DEPOIS do 02 (o bloco D depende de as colunas cluster_YYYY existirem
-- de fato — se o inventário mostrar que não existem, pule aquele bloco).
-- Nenhuma query aqui escreve nada.
-- ============================================================================


-- ── A. A coluna `federacao`: quantos tenants existem, e quão suja está ──────
-- Se `distintos_normalizados` < `distintos_crus`, há variação de caixa/espaço
-- que precisa virar uma linha só na tabela federacao.
select
    count(*)                                             as linhas,
    count(federacao)                                     as com_valor,
    count(*) - count(federacao)                          as nulos,
    count(distinct federacao)                            as distintos_crus,
    count(distinct upper(btrim(federacao)))              as distintos_normalizados
from empresa_junior;

-- Lista completa dos valores, para montar o seed da tabela federacao à mão.
select
    coalesce(federacao, '<NULL>')            as valor_cru,
    upper(btrim(coalesce(federacao, '')))    as normalizado,
    count(*)                                 as ejs
from empresa_junior
group by 1, 2
order by ejs desc, normalizado;

-- Agrupa por valor normalizado: cada linha aqui é um candidato a tenant.
select
    upper(btrim(federacao))               as federacao_normalizada,
    count(*)                              as ejs,
    array_agg(distinct federacao)         as variacoes_encontradas,
    array_agg(distinct estado)            as estados
from empresa_junior
where federacao is not null
group by 1
order by ejs desc;


-- ── B. Integridade referencial: a FK composta vai passar? ───────────────────
-- Qualquer resultado > 0 aqui vira trabalho de limpeza ANTES da migração.

-- id_ej duplicado em empresa_junior (impediria o UNIQUE (id_ej, federacao_id))
select id_ej, count(*) as ocorrencias
from empresa_junior
group by id_ej
having count(*) > 1;

-- metas apontando para EJ inexistente
select count(*) as metas_orfas
from metas m
where not exists (select 1 from empresa_junior e where e.id_ej = m.id_ej);

-- monitoramento apontando para EJ inexistente
select count(*) as monitoramento_orfao
from monitoramento mo
where not exists (select 1 from empresa_junior e where e.id_ej = mo.id_ej);

-- EJs sem nenhum dado mensal (ficam válidas, mas é bom saber o tamanho)
select count(*) as ejs_sem_monitoramento
from empresa_junior e
where not exists (select 1 from monitoramento m where m.id_ej = e.id_ej);


-- ── C. Cobertura temporal: o que o backfill vai carimbar ────────────────────
select ano, mes, count(*) as linhas, count(distinct id_ej) as ejs
from monitoramento
group by ano, mes
order by ano, mes;

select ano, count(*) as linhas, count(distinct id_ej) as ejs
from metas
group by ano
order by ano;


-- ── D. Colunas cluster_YYYY: normalizar ou assumir a dívida? ────────────────
-- Se o preenchimento for esparso (só 2025/2026 com dado), a tabela histórica
-- normalizada é barata. Se as quatro estiverem cheias, o custo de mexer no
-- empresa_service.py pesa mais.
-- ATENÇÃO: só rode se o inventário (02, bloco A) confirmar que estas colunas
-- existem — caso contrário a query falha.
select
    count(*)                as total_ejs,
    count(cluster)          as preenchidos_cluster,
    count(cluster_2023)     as preenchidos_2023,
    count(cluster_2024)     as preenchidos_2024,
    count(cluster_2025)     as preenchidos_2025,
    count(cluster_2026)     as preenchidos_2026
from empresa_junior;

-- Divergência entre a coluna legada e a do ano corrente (indica qual é a viva)
select
    cluster            as cluster_legado,
    cluster_2026       as cluster_2026,
    count(*)           as ejs
from empresa_junior
group by 1, 2
order by ejs desc;


-- ── E. Colunas de filtro que entram nos índices compostos ──────────────────
-- Cardinalidade de comunidade e status decide se vale índice próprio ou se
-- o índice em (federacao_id, cluster) já resolve.
select coalesce(comunidade, '<NULL>') as comunidade, count(*) as ejs
from empresa_junior group by 1 order by ejs desc;

select coalesce(status, '<NULL>') as status, count(*) as ejs
from empresa_junior group by 1 order by ejs desc;

select coalesce(estado, '<NULL>') as estado, count(*) as ejs
from empresa_junior group by 1 order by ejs desc;


-- ── F. Linha de base de desempenho (evidência para o Cap. 5) ────────────────
-- Rode ANTES da migração e guarde o plano. Depois de adicionar federacao_id e
-- os índices com ele como coluna líder, rode de novo e compare. Isso é o
-- "antes e depois" que sustenta a análise de custo do isolamento no texto.
explain (analyze, buffers, format text)
select e.id_ej, e.nome, m.faturamento_acumulado
from empresa_junior e
join monitoramento m on m.id_ej = e.id_ej
where m.ano = 2026
  and m.mes  = 8
  and e.cluster_2026 = 3;
