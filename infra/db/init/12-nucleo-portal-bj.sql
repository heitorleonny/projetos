-- ============================================================================
-- 12 — Seed dos 26 núcleos, com o ID do Portal BJ
--
-- Fonte: exportação do Portal BJ em ~/Documents/TCC/dados/
--   `ejs_202620260918-1-ud88ae.xlsx`, aba "Todas as Federações" — planilha de
--   nível NÚCLEO (26 núcleos × 9 meses = 234 linhas), colunas ID, NÚCLEO e
--   FEDERAÇÃO. Extraído em 21/09/2026.
-- Conferido contra `metrics_premiss_202620260518-1-giv1qt.xlsx` (aba Núcleos,
-- 18/05/2026): os 26 pares (ID, nome) batem.
-- Conferido contra a planilha de EJ `monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx`
-- (21/09/2026): todo nome da coluna NUCLEOS está aqui, na federação certa.
--
-- POR QUE AGORA: 03 criou `nucleo` sem seed porque "o ID do Núcleo Maringá no
-- Portal BJ ainda não foi extraído, e inventar um ID contamina a chave de
-- origem". Foi extraído — é o 12. Com os IDs reais aqui, a carga da planilha de
-- EJ resolve NUCLEOS (que traz só o nome) sem inventar id nenhum.
--
-- Resolve também o `[CONFIRMAR]` de 03 sobre a contagem: são 5 federações com
-- núcleo (FEJEMG 7, FEJEPAR 7, FEJESC 4, FEJESP 4, UNIJr-BA 4), 26 núcleos.
--
-- Só o cadastro (id, federação, nome). O fato mensal e as metas de núcleo são
-- a próxima fase da ingestão.
-- ============================================================================

INSERT INTO nucleo (id, federacao_id, nome) VALUES
    ( 30, 7, 'Núcleo Central'),             -- FEJEMG, 48 EJs em 21/09
    ( 31, 7, 'Núcleo Vertentes'),           -- FEJEMG, 46 EJs em 21/09
    ( 32, 7, 'Núcleo Sul'),                 -- FEJEMG, 43 EJs em 21/09
    ( 33, 7, 'Núcleo Norte'),               -- FEJEMG, 22 EJs em 21/09
    ( 34, 7, 'Núcleo Triângulo'),           -- FEJEMG, 45 EJs em 21/09
    ( 35, 7, 'Núcleo da Mata'),             -- FEJEMG, 71 EJs em 21/09
    ( 43, 7, 'Núcleo Vale do Aço'),         -- FEJEMG, 16 EJs em 21/09
    (  9, 4, 'Núcleo Curitiba'),            -- FEJEPAR, 38 EJs em 21/09
    ( 11, 4, 'NEJ Londrina'),               -- FEJEPAR, 29 EJs em 21/09
    ( 12, 4, 'Núcleo Maringá'),             -- FEJEPAR, 22 EJs em 21/09
    ( 13, 4, 'Núcleo Ponta Grossa'),        -- FEJEPAR, 14 EJs em 21/09
    ( 27, 4, 'Núcleo Centro-Sul'),          -- FEJEPAR, 12 EJs em 21/09
    ( 28, 4, 'Núcleo Oeste'),               -- FEJEPAR, 10 EJs em 21/09
    ( 29, 4, 'Núcleo Noroeste'),            -- FEJEPAR, 14 EJs em 21/09
    ( 39, 3, 'Núcleo Floripa'),             -- FEJESC, 31 EJs em 21/09
    ( 44, 3, 'Núcleo Vale Boreal'),         -- FEJESC, 18 EJs em 21/09
    ( 45, 3, 'Núcleo Corrente'),            -- FEJESC, 11 EJs em 21/09
    ( 46, 3, 'Núcleo Potência'),            -- FEJESC, 9 EJs em 21/09
    ( 22, 5, 'Núcleo Bauru'),               -- FEJESP, 41 EJs em 21/09
    ( 23, 5, 'Núcleo Campinas'),            -- FEJESP, 47 EJs em 21/09
    ( 24, 5, 'Núcleo São Carlos'),          -- FEJESP, 67 EJs em 21/09
    ( 25, 5, 'Núcleo São Paulo'),           -- FEJESP, 69 EJs em 21/09
    ( 17, 9, 'NEJ Salvador'),               -- UNIJr-BA, 28 EJs em 21/09
    ( 21, 9, 'NEJ Vale'),                   -- UNIJr-BA, 11 EJs em 21/09
    ( 40, 9, 'NEJ Alumiar'),                -- UNIJr-BA, 21 EJs em 21/09
    ( 41, 9, 'NEJ Elementar')               -- UNIJr-BA, 14 EJs em 21/09
ON CONFLICT (id) DO UPDATE
    SET federacao_id = EXCLUDED.federacao_id,
        nome         = EXCLUDED.nome;

-- Conferência rápida após rodar:
--   SELECT f.nome, count(*) FROM nucleo n JOIN federacao f ON f.id = n.federacao_id
--    GROUP BY f.nome ORDER BY f.nome;         -- FEJEMG 7, FEJEPAR 7, FEJESC 4, FEJESP 4, UNIJr-BA 4
--   SELECT * FROM nucleo WHERE nome = 'Núcleo Maringá';   -- 12 | 4 | Núcleo Maringá
