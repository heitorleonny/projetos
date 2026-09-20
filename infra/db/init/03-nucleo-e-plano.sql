-- ============================================================================
-- 03 — Tabelas `plano` e `nucleo`
--
-- Duas entidades que o modelo multi-tenant precisa e que hoje não existem em
-- lugar nenhum. As duas nascem como DESENHO DE TABELA, sem nenhuma regra de
-- negócio pendurada:
--
--   `plano`  — catálogo de planos comerciais. NÃO há cobrança, NÃO há bloqueio
--              por limite de usuários nem por créditos de IA. As colunas de
--              limite existem para que a migração que ligar o enforcement não
--              precise mexer na tabela de novo.
--
--   `nucleo` — subdivisão interna de uma federação. Entra agora porque
--              `empresa_junior.comunidade` é texto livre e vocabulário
--              exclusivo de FEJEPE (ver docs/levantamento-semana1-multitenant.md,
--              seção 4): o resto do movimento chama isso de núcleo, com ID
--              próprio no Portal BJ. Este arquivo cria só a tabela e a FK
--              nulável; migrar `comunidade` para cá é outra decisão, ainda
--              em aberto.
--
-- Fonte: docs/levantamento-semana1-multitenant.md (extraído em 18/09/2026).
-- ============================================================================


-- ── plano ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS plano (
    id                     BIGINT  PRIMARY KEY,
    nome                   TEXT    NOT NULL,
    limite_usuarios        INTEGER,          -- NULL = sem limite definido
    limite_creditos_ia_mes INTEGER,          -- NULL = sem limite definido
    preco_mensal           NUMERIC           -- em BRL; NULL = a definir
);

COMMENT ON TABLE  plano                        IS 'Catálogo de planos. Sem enforcement: nada no código lê estes limites ainda.';
COMMENT ON COLUMN plano.limite_usuarios        IS 'Teto de usuários por federação. NULL = sem limite. Não é aplicado por nenhuma regra hoje.';
COMMENT ON COLUMN plano.limite_creditos_ia_mes IS 'Teto mensal de créditos de IA. NULL = sem limite. Não é aplicado por nenhuma regra hoje.';
COMMENT ON COLUMN plano.preco_mensal           IS 'PLACEHOLDER. A precificação real não foi definida.';

-- ATENÇÃO: os valores abaixo são PLACEHOLDER, inventados só para a tabela não
-- ficar vazia durante o desenvolvimento. Não são a precificação real do produto,
-- não foram validados com ninguém e não devem ser citados em lugar nenhum como
-- se fossem. Trocar antes de qualquer uso que não seja teste local.
INSERT INTO plano (id, nome, limite_usuarios, limite_creditos_ia_mes, preco_mensal) VALUES
    (1, 'Gratuito',    3, 100,    0.00),
    (2, 'Pro',        15, 1000, 199.00),
    (3, 'Federação', NULL, NULL,  NULL)
ON CONFLICT (id) DO NOTHING;

-- Vínculo federação → plano. Nulável e sem backfill: nenhuma federação tem
-- plano decidido, e inventar um default aqui seria fabricar uma decisão
-- comercial que não foi tomada.
ALTER TABLE federacao ADD COLUMN IF NOT EXISTS plano_id BIGINT REFERENCES plano(id);

COMMENT ON COLUMN federacao.plano_id IS 'Plano contratado. NULL enquanto não houver decisão comercial — é o estado de todas as 27 hoje.';


-- ── nucleo ──────────────────────────────────────────────────────────────────

-- Onde núcleo existe de fato: em 5 das 27 federações, segundo as exportações do
-- Portal BJ — FEJEMG (7), FEJEPAR (7), FEJESC (4), FEJESP (4) e UNIJr-BA (4),
-- somando 26 núcleos com ID próprio e fato mensal próprio.
-- [CONFIRMAR] o texto do levantamento diz "6 federações" mas lista 5; a lista
-- é que bate com o total de 26. Conferir contra a exportação antes de usar
-- essa contagem em qualquer lugar que não seja este comentário.
--
-- FEJEPE NÃO tem núcleo registrado na BJ — as "comunidades" do portal são uma
-- subdivisão interna dela. A segunda federação já escolhida para o projeto,
-- FEJEPAR, tem núcleo real: o Núcleo Maringá (22 das 138 EJs, 9 meses de série),
-- que é justamente o dado que torna a demonstração de isolamento honesta.
--
-- Nenhum núcleo é semeado aqui: o ID do Núcleo Maringá no Portal BJ ainda não
-- foi extraído, e inventar um ID contamina a chave de origem.
CREATE TABLE IF NOT EXISTS nucleo (
    id           BIGINT PRIMARY KEY,   -- ID do Portal BJ, mesmo critério de `federacao.id`
    federacao_id BIGINT NOT NULL REFERENCES federacao(id),
    nome         TEXT   NOT NULL
);

COMMENT ON TABLE  nucleo    IS 'Subdivisão interna de uma federação. Existe em 5 das 27; FEJEPE não tem.';
COMMENT ON COLUMN nucleo.id IS 'ID do núcleo no Portal Brasil Júnior; não é serial.';

-- Sob RLS o predicado de tenant entra em toda query; o índice nasce com
-- federacao_id na frente.
CREATE INDEX IF NOT EXISTS idx_nucleo_federacao ON nucleo (federacao_id);

-- Nulável: nem toda EJ pertence a um núcleo (nenhuma de FEJEPE pertence).
ALTER TABLE empresa_junior ADD COLUMN IF NOT EXISTS nucleo_id BIGINT REFERENCES nucleo(id);

COMMENT ON COLUMN empresa_junior.nucleo_id IS 'Núcleo da EJ. NULL quando a federação não usa núcleo. Não substitui `comunidade` — essa migração é outra decisão.';

CREATE INDEX IF NOT EXISTS idx_ej_nucleo ON empresa_junior (nucleo_id);
