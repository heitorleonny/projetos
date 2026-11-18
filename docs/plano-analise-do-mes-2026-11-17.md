# Plano — Análise do mês: briefing por IA, EJs em alerta e EJs em ascensão

Data: 17/11/2026 (America/Recife). Status: **etapas 1–4 implementadas localmente**
(regras, rota, tela e briefing por IA com guardas), sem commit. Etapa 5 (avaliação real)
e calibração dos alertas feitas (§12–13). Etapa 6 (monografia) pendente.
Escopo: pedido de Heitor de 17/11/2026. Não altera fórmulas oficiais, migrações já
aplicadas, a monografia nem os módulos inativos de dashboards/créditos.

## 1. O que se quer

Uma tela **Análise do mês**, a primeira coisa que o gestor vê ao entrar no portal, com
três blocos:

1. **Briefing do mês**: um parágrafo curto, redigido por IA, que resume como a federação
   está no mês de referência e o que mudou em relação ao mês anterior. Cada frase aponta
   para a consulta do Nexo que a sustenta.
2. **EJs em alerta**: lista de EJs que precisam de atenção agora, cada uma com o motivo.
3. **EJs em ascensão**: lista de EJs que foram bem no mês, cada uma com o motivo.

Os números e as listas vêm **só** das regras determinísticas abaixo. A IA apenas redige o
texto do briefing a partir desses fatos. Sem IA configurada, a tela continua funcionando
(listas e cartões aparecem; o briefing é substituído por um resumo em frases fixas).

## 2. Conflito de escopo que precisa de decisão antes de tudo

Duas tensões com decisões anteriores:

- **Retomada de 23/10** ([retomada-escopo-reduzido](retomada-escopo-reduzido-2026-10-23.md)):
  pede para evitar funcionalidades novas que não resolvam impedimento da demonstração.
  Esta feature não é a que foi retirada (não gera código, não publica aplicação, não usa
  franquia de dashboard). Mas é escopo novo a 13 dias da entrega (30/11).
- **Previsão de risco abandonada**: "EJ em alerta" **não pode** virar previsão. Os alertas
  aqui são **descritivos**: dizem o que já aconteceu nos dados ("3 meses sem venda",
  "caiu de cluster"), nunca "vai entrar em risco". No texto do TCC e na interface, usar
  "alerta" / "atenção", e não "risco" ou "previsão".

## 3. Regras (determinísticas, sem IA)

Mês de referência `m` = último mês com monitoramento carregado para a federação (ou o
escolhido no filtro). Todas as leituras usam o cliente da requisição e
`filtrar_por_tenant`, como o Nexo.

### 3.1 EJs em alerta

Uma EJ entra na lista se cumprir **pelo menos um** critério. Cada critério gera um
"motivo" exibido como etiqueta.

| Código | Critério | Base existente | Gravidade |
|---|---|---|---|
| `A1_sem_vendas_seguidas` | `faturamento_mes = 0` nos últimos **N = 3** meses seguidos (até `m`) | `classificar_ritmo` | alta |
| `A2_caiu_cluster` | Tendência de cluster `desce` | `calcular_tendencia_cluster` | alta |
| `A3_fora_do_verde` | `% da meta < m ÷ 12 × 100` (estava no verde em `m−1` e saiu em `m`) | regra do verde, [regras-de-negocio §8.1](regras-de-negocio.md) | média |
| `A4_queda_faturamento` | Faturamento do mês caiu ≥ **50%** vs. média dos 3 meses anteriores, com média > 0 | `calcular_crescimento` | média |
| `A5_csat_abaixo_meta` | CSAT do mês abaixo de `meta_csat` da EJ | tabela `metas` | baixa |
| `A6_sem_reporte` | EJ ativa sem linha de monitoramento em `m` | `monitoramento` | média |

Ordenação: maior gravidade primeiro, depois número de motivos, depois nome. Limite de 10
na tela, com "ver todas".

### 3.2 EJs em ascensão

| Código | Critério | Base existente |
|---|---|---|
| `S1_subiu_cluster` | Tendência de cluster `sobe` | `calcular_tendencia_cluster` |
| `S2_entrou_no_verde` | Fora do verde em `m−1`, no verde em `m` | regra do verde |
| `S3_ritmo_significativo` | Ritmo `significativo` em `m` (faturou ≥ meta anual ÷ 12) | `classificar_ritmo` |
| `S4_bateu_meta` | Passou a `meta_atingida` em `m` | `classificar_faixa_meta` |
| `S5_maior_crescimento` | Entre as 5 EJs com maior crescimento de faturamento do mês vs. `m−1` (com `m−1` > 0) | `calcular_crescimento` |
| `S6_primeira_venda` | Primeira venda do ano em `m` (saiu do zero) | predicado fora do zero |

Ordenação: número de motivos, depois faturamento do mês. Limite de 10.

Uma EJ pode aparecer nas duas listas (ex.: subiu de cluster, mas CSAT abaixo da meta). A
interface mostra isso sem esconder nenhum dos dois.

**[CONFIRMAR] A2/S1:** o cluster oficial é **anual** (`cluster_historico`). A comparação
mês a mês precisa usar o cluster calculado pelo tracking em `m` vs. `m−1`, e não o oficial.
Conferir em `calculos.md` se isso é aceito pela regra nacional antes de implementar. Se
não for, A2/S1 passam a comparar o tracking com o cluster oficial do ano anterior.

Cada motivo é mostrado em linguagem de gestor ("sem vendas há 3 meses", "subiu do cluster
2 para o 3 no tracking"), nunca com o código.

Os limiares (N = 3, 50%, top 5) ficam em `app/utils/constants.py`, documentados em
`calculos.md`, para que a banca veja que são parâmetros e não "inteligência".

### 3.3 Fatos do briefing

Dicionário montado no backend, só com valores calculados:

```json
{
  "federacao": "FEJEPE", "ano": 2026, "mes": 10, "mes_anterior": 9,
  "total_ejs": 22,
  "fora_do_zero": {"atual": 14, "anterior": 12},
  "faturamento_acumulado": {"atual": 812000.0, "meta": 1140000.0, "percentual": 71.2},
  "projecao_anual_percentual": 94.0,
  "ritmo": {"sem_vendas": 6, "minimo": 9, "significativo": 7},
  "sde": 3.5,
  "alertas": {"total": 5, "por_motivo": {"A1_sem_vendas_seguidas": 2, "A2_caiu_cluster": 1}},
  "ascensao": {"total": 6, "por_motivo": {"S1_subiu_cluster": 3, "S3_ritmo_significativo": 7}},
  "destaques": [{"nome": "EJ X", "motivo": "S1_subiu_cluster"}]
}
```

## 4. Briefing com IA

### 4.1 Contrato

- Novo método no `Provedor`: `redigir_briefing(fatos: dict) -> Redacao`, com
  `Redacao(texto: str, frases: list[FraseBriefing], modelo, tokens_entrada, tokens_saida)`.
- `FraseBriefing(texto: str, fonte: Literal[...ferramentas do Nexo...], parametros: dict)`.
  O `fonte` permite o link "ver detalhes", que abre o Nexo com a pergunta já preenchida.
- Prompt: português, 3 a 5 frases, tom neutro, proibido inventar números, proibido usar
  "risco", "previsão", "vai cair". Exemplo de saída no prompt.

### 4.2 Guardas (falha fechada)

1. **Fidelidade numérica**: extrair todos os números do texto e conferir que cada um
   existe nos fatos (com tolerância de arredondamento e formatação BR). Se algum não
   existir → descartar a redação e usar o resumo fixo.
2. **Nomes**: só nomes de EJs presentes em `destaques` podem aparecer.
3. **Vocabulário proibido**: rejeitar texto com "risco", "previsão", "vai", "deve cair".
4. O provedor não recebe cliente de banco nem token (mesma regra do `provedor.py`).

### 4.3 Custo e cache

- Tabela nova `briefing_mensal(federacao_id, ano, mes, texto, frases jsonb, modelo,
  fatos_hash, criado_em)`, com RLS por federação, igual às demais.
- Gera **uma vez** por federação e mês; regenera só se `fatos_hash` mudar (nova carga).
- Geração disparada no primeiro acesso após a carga (sem job agendado), passando pelo
  `ProvedorComLimite` / `reservar_consulta_ia`.
- Botão "Regenerar" só para admin, também sob o limitador.

## 5. Backend

| Arquivo | Mudança |
|---|---|
| `app/services/analise_service.py` (novo) | `calcular_alertas`, `calcular_ascensao`, `montar_fatos`. Reusa `rede_service`, `calculo_service`, `cluster_service`. |
| `app/ia/briefing.py` (novo) | Monta prompt, chama provedor, aplica guardas, grava/lê cache. |
| `app/ia/provedor.py` e adaptadores | Método `redigir_briefing`; provedor falso para testes. |
| `app/models/analise.py` (novo) | `EjDestaque(id_ej, nome, motivos, gravidade?)`, `AnaliseMes`, `Briefing`. |
| `app/routers/analise.py` (novo) | `GET /api/v1/analise?ano=&mes=` → `AnaliseMes` (cartões + alertas + ascensão + briefing). `POST /api/v1/analise/briefing/regenerar` (admin). Exige claim de tenant como `/ia`. |
| `app/utils/constants.py` | Limiares da seção 3. |
| Migração nova | `briefing_mensal` + políticas RLS. Não mexer nas aplicadas. |
| `frontend/openapi.json` | Atualizar contrato. |

## 6. Frontend

- `features/analise/` (novo): `AnalisePage.tsx`, `BriefingCard.tsx`,
  `ListaDestaques.tsx` (reutilizada para alerta e ascensão), `analiseService.ts`,
  `useAnalise.ts`.
- Rota `/analise`. **Decisão D1**: virar a rota inicial (`/` → `/analise`) ou ficar como
  aba ao lado de `/dashboard`.
- Layout: cartões de resumo no topo (fora do zero, % da meta, projeção, SDE com seta vs.
  mês anterior), briefing logo abaixo, duas colunas: **Em alerta** (vermelho) e **Em
  ascensão** (verde), empilhadas no celular. Cada EJ abre `/empresas/:idEj`.
- Filtro de mês reaproveitando `DashboardFilters`.
- Estado sem IA: briefing mostra o resumo fixo com um aviso discreto.
- Cores pela paleta da federação (ADR-006), com o vermelho/verde semânticos fixos.

## 7. Testes

- Backend: um teste por regra A1–A6 e S1–S6 com dados sintéticos (inclusive limites:
  exatamente 3 meses, queda de exatamente 50%, EJ nas duas listas, `m−1` sem dados,
  janeiro sem mês anterior).
- Briefing: provedor falso que devolve (a) texto correto, (b) número inventado, (c) nome
  fora dos destaques, (d) palavra proibida → (a) aceito, (b–d) cai no resumo fixo.
- Isolamento: usuário da federação A não lê alertas nem briefing da B (padrão dos testes
  de RLS existentes).
- Frontend: render da página com e sem briefing; lista vazia ("nenhuma EJ em alerta").
- Avaliação com modelo real: 3 meses × 2 federações, conferência manual de fidelidade,
  registrada em `docs/ia-avaliacao-briefing-<data>.json`.

## 8. Etapas e estimativa (até 30/11)

| # | Etapa | Estimativa |
|---|---|---|
| 1 | Regras de alerta/ascensão + testes (`analise_service`) | 1 dia |
| 2 | Rota `/analise` sem IA + página com cartões e listas | 1,5 dia |
| 3 | Briefing: provedor, guardas, cache, migração | 1,5 dia |
| 4 | Integração do briefing na tela + link para o Nexo | 0,5 dia |
| 5 | Avaliação com modelo real e registro | 0,5 dia |
| 6 | Texto na monografia (desenvolvimento + limitações) | 1 dia |

As etapas 1–2 já entregam valor sozinhas. Se o prazo apertar, a etapa 3 pode ficar como
trabalho futuro sem quebrar a tela.

## 9. Decisões abertas

- **D1** — `/analise` vira a página inicial ou fica como aba?
- **D2** — Limiares: N = 3 meses sem venda, queda ≥ 50%, top 5 de crescimento. Ajustar
  com a federação?
- **D3** — Membros comuns veem a lista de alertas, ou só admin/gestor?
- **D4** — Entra na monografia como funcionalidade (exige o orientador) ou só no produto?
- **D5** — Exportar o briefing em PDF para reunião de diretoria agora ou depois?

## 10. Implementação das etapas 1–2 (17/11/2026)

Arquivos novos: `backend/app/models/analise.py`, `backend/app/services/analise_service.py`,
`backend/app/routers/analise.py`, `backend/tests/test_analise.py`,
`frontend/src/features/analise/` (`AnalisePage.tsx`, `analiseService.ts`, `useAnalise.ts`).
Alterados: `backend/app/main.py` (registro do router), `backend/app/utils/constants.py`
(limiares), `frontend/src/App.tsx`, `frontend/src/config/navigation.ts`,
`frontend/src/features/auth/LoginPage.tsx`, `frontend/openapi.json` (só `/api/v1/analise`
e seus schemas).

Escolhas feitas na implementação, todas reversíveis:

- **D1**: `/analise` virou a tela inicial (`/` e o pós-login apontam para ela) e a
  primeira aba do menu. Os demais links para `/dashboard` não mudaram.
- **D2**: limiares do plano (3 meses, 50%, janela de 3 meses, top 5) em `constants.py`.
- **D3**: mesma regra dos painéis (papel `membro`); o tenant é obrigatório (403 sem claim).
- **A2/S1**: comparam o `tracking_cluster_efetivo` (Cluster Track com a regra do projeto
  de impacto) calculado até `m` com o calculado até `m − 1`. Texto: "no Cluster Track".
  O [CONFIRMAR] da §3 continua valendo para a forma de citar isso no TCC.
- EJ sem linha de monitoramento em `m` só recebe A6 (se ativa) e nunca entra em ascensão:
  as demais regras leriam meses passados como se fossem o atual.
- Mês de referência padrão: o maior `mes` de monitoramento do ano entre as EJs da federação.
- O briefing desta etapa é o resumo em frases fixas (`gerado_por_ia=false`).

Verificação: backend **697 aprovados, 248 pulados** (pulados = suítes que exigem Postgres
local), sendo 26 novos em `test_analise.py`; frontend **40 testes aprovados**, lint e build
aprovados. **Não verificado**: a tela no navegador com dados reais (backend e banco locais
não estavam no ar) e a RLS em banco real.

## 11. Implementação das etapas 3–4: briefing por IA (17/11/2026)

Arquivos novos: `backend/app/ia/briefing.py`, `backend/tests/test_briefing.py`.
Alterados: `backend/app/models/analise.py` (`Briefing.modelo`, `RedacaoModelo`),
`backend/app/services/analise_service.py` (`analisar_mes_com_nomes`),
`backend/app/routers/analise.py`, `frontend/src/features/analise/*`, `frontend/openapi.json`.

Diferenças em relação à §4, todas para reduzir risco perto da entrega:

| Plano (§4) | Implementado | Por quê |
|---|---|---|
| Método novo no `Provedor` do Nexo | Redator próprio (`RedatorCompativel`), com contrato e prompt próprios, nos mesmos `IA_*` | Não mexe no provedor nem na avaliação já feita do Nexo; mesmo caminho adotado nas métricas (ADR-009) |
| Tabela `briefing_mensal` com RLS | Cache em memória do processo, por (federação, ano, mês, hash dos fatos) | Sem migração. Com tabela, qualquer membro poderia gravar texto lido pela federação inteira. Custo: uma chamada por federação/mês por processo reiniciado |
| Briefing dentro de `GET /analise` | Rota separada `GET /analise/briefing`; a tela mostra o resumo fixo e troca quando o texto chega | A primeira chamada do mês pode levar segundos; a tela não espera |
| Link "ver detalhes" para o Nexo por frase | Não implementado | Exigiria mexer na abertura do Nexo; os cartões e listas logo abaixo já são o detalhe |
| `POST /regenerar` | `POST /analise/briefing/regenerar`, papel `admin` (claim) | Igual ao plano |

**Mudança de princípio que precisa constar no TCC:** no Nexo e nas métricas o modelo só
interpreta e o texto exibido é fixo. Aqui o modelo **escreve o texto exibido**. A
contrapartida são as guardas, com falha fechada para o resumo fixo:

1. Todo número do texto precisa existir, como texto, nos fatos enviados (fatos já vão
   formatados em pt-BR; "R$ 812 mil" ou porcentagem calculada pelo modelo = recusa).
2. Os fatos não têm nome de EJ; texto que cite EJ da federação pelo nome = recusa.
3. Vocabulário de futuro, risco, previsão, tendência e recomendação = recusa.
4. 2 a 6 frases de até 280 caracteres, sem marcação, link ou HTML.

Recusa ou provedor fora do ar ficam guardados por 10 minutos (não insiste a cada acesso).
Limite por minuto (`reservar_consulta_ia`) só devolve o resumo fixo, sem guardar. Sem
`IA_*` configurado, nada é reservado nem chamado. O log `ia_briefing` registra tenant,
modelo, status (`aceito` ou o motivo da recusa), tokens e duração; nunca o texto.

Verificação: backend **719 aprovados, 248 pulados** (22 novos em `test_briefing.py`,
com redator falso); frontend **40 aprovados**, lint e build aprovados. **Não verificado**:
nenhuma chamada a modelo real, a tela no navegador e o comportamento com mais de um
worker (cada processo tem o próprio cache e gera uma vez).

Etapa 5 (avaliação real) proposta: 3 meses × 2 federações, registrar em
`docs/ia-avaliacao-briefing-<data>.json` a taxa de aceitação pelas guardas, os motivos de
recusa e a conferência manual de fidelidade das frases aceitas.

## 12. Etapa 5: avaliação com modelo real (17/11/2026)

**Procedimento.** Retrato local do Postgres da demo (Docker), exportado pelo dono do
banco para fora do repositório: duas federações (43 e 141 EJs), monitoramento de 2026
até novembro. A Análise e o redator são os da aplicação; só o acesso ao banco foi
trocado por um cliente em memória (`app/ia/avaliacao/briefing.py`). Modelo do deploy
(`.env.docker`): `anthropic/claude-haiku-5.5` via OpenRouter. Casos: 2 federações ×
meses 3, 7, 10 e 11. Arquivos versionados só com federação anonimizada, status, motivo
de recusa, tokens e duração; frases e números reais ficaram no scratchpad.

| Rodada | Arquivo | Aceitos pelas guardas | Frases conferidas | Fiéis | Número errado/trocado |
|---|---|---|---|---|---|
| Inicial | `docs/ia-avaliacao-briefing-2026-11-17-inicial.json` | 8/8 | 36 | 34 | 0 |
| Após ajuste | `docs/ia-avaliacao-briefing-2026-11-17.json` | 8/8 | 40 | 40 | 0 |

As 2 imprecisões da rodada inicial eram de quantificador: "a maioria" para 5 de 10
(empate) e para 20 de 42. A causa era o exemplo do próprio prompt. Ajuste: o prompt
pede "o motivo mais comum é … (n)" e a guarda recusa maioria/metade/minoria. Na segunda
rodada o empate foi descrito como empate. Custo total das duas rodadas: ~26,5 mil tokens
de entrada e ~3,9 mil de saída (16 chamadas); 1,7 a 3,4 s por chamada.

Limite da avaliação: as guardas garantem que o número existe nos fatos, não que esteja
ligado ao fato certo. Essa parte foi conferida à mão (uma pessoa, 16 textos). Não houve
avaliação com usuários.

### 12.1 Achado: as regras de alerta disparam demais nos dados reais

| Federação · mês | EJs em alerta (regras atuais) |
|---|---|
| A (43) · julho | 37 (86%) |
| A (43) · outubro | 42 (98%) |
| B (141) · julho | 127 (90%) |
| B (141) · outubro | 132 (94%) |

Causas medidas:

1. **Mês corrente parcial.** Em novembro (dia 17), só 4/43 e 7/141 EJs tinham venda.
   O padrão "último mês carregado" abre a tela num mês incompleto.
2. **A4 é ruidosa.** Faturamento de EJ é esporádico (30–45% das EJs vendem num mês
   típico); quem vendeu nos 3 meses anteriores e não vendeu agora aparece com queda de 100%.
3. **A1 inclui quem nunca vendeu no ano** (8/43 e 26/141), que fica em alerta o ano inteiro.
4. **A5 (CSAT do mês)** oscila mês a mês.

Simulação de ajustes, mesmos dados (EJs em alerta):

| Federação · mês | Atual | A4 trimestral¹ | + A1 sem "nunca vendeu"² | + sem A5 |
|---|---|---|---|---|
| A · julho | 37 | 24 | 16 | 11 (26%) |
| A · outubro | 42 | 33 | 25 | 18 (42%) |
| B · julho | 127 | 83 | 54 | 45 (32%) |
| B · outubro | 132 | 113 | 87 | 62 (44%) |

¹ Soma dos últimos 3 meses ≤ 50% da soma dos 3 anteriores (base > 0).
² Quem não vendeu no ano sai do A1 e vira um número no resumo ("x EJs ainda no zero").
Subir o N do A1 (3 → 4 → 6) não mudou nada com o A4 trimestral ativo.

**Decisão pendente (D2 revista):** quais ajustes aplicar. Também recomendado: o mês
padrão passa a ser o último mês **fechado** (anterior ao mês do calendário), com o mês
corrente selecionável e marcado como parcial.

## 13. Calibração aplicada (17/11/2026, decisão de Heitor: "aplicar tudo")

| Item | Antes | Depois |
|---|---|---|
| A1 sem vendas | ≥ 3 meses seguidos sem venda | igual, **só para quem já vendeu no ano**; quem nunca vendeu aparece como "x ainda sem venda no ano" no cartão de fora do zero |
| A4 queda | mês vs. média dos 3 anteriores, queda ≥ 50% | **trimestre móvel**: soma dos últimos 3 meses ≤ 50% da soma dos 3 anteriores (exige mês ≥ 6) |
| A5 CSAT do mês | alerta de gravidade baixa | **retirada** |
| Mês padrão | último mês com dados | **último mês fechado**; o mês corrente continua selecionável, marcado "(em andamento)", com aviso na tela, no resumo fixo e nos fatos do briefing (`mes_parcial`) |

EJs em alerta, mesmos dados da §12:

| Federação · mês | Antes | Depois |
|---|---|---|
| A (43) · março | 30 | 3 (7%) |
| A (43) · julho | 37 | 13 (30%) |
| A (43) · outubro | 42 | 18 (42%) |
| A (43) · novembro, parcial | 41 | 30 (70%) |
| B (141) · março | 88 | 4 (3%) |
| B (141) · julho | 127 | 49 (35%) |
| B (141) · outubro | 132 | 64 (45%) |
| B (141) · novembro, parcial | 137 | 79 (56%) |

Em 17/11 a tela abre em outubro (mês fechado). Os valores ainda altos de outubro vêm
de A1 e A4, que agora descrevem queda real e sustentada; se a federação achar muito,
os limiares estão em `constants.py`.

### 13.1 Briefing depois da calibração

Uma rodada intermediária (4 casos) mostrou um erro que as guardas não pegavam: "78,5%
… **acima** dos 83% esperados" (direção invertida) e um empate 12 × 12 descrito como um
motivo só. Ajustes: os fatos passaram a trazer `faturamento_frente_ao_esperado` e
`motivo_mais_comum_de_alerta/ascensao` prontos (empate escrito pelo backend), e uma
guarda nova recusa frase que compare com o esperado na direção contrária
(`comparacao_invertida`).

Rodada final (`docs/ia-avaliacao-briefing-2026-11-17-calibrado.json`): 8/8 aceitos,
40/40 frases fiéis na conferência manual, nenhuma comparação invertida. Observações só
de estilo: empate redigido como "o motivo mais comum é empate entre…" e aviso de mês
parcial no fim, não no início. Arquivo da rodada intermediária não foi mantido (versão
do código substituída).

Custo acumulado das avaliações de 17/11: 28 chamadas, ~49 mil tokens de entrada e
~7 mil de saída.

Verificação: backend **730 aprovados, 248 pulados**; frontend **40 aprovados**, lint e
build aprovados. Não verificado: a tela no navegador.

### 13.2 Conferência no navegador e ajustes finais (17/11/2026)

Demo PostgreSQL reconstruída (backend e frontend; Postgres e dados intactos, sem
migração) e conferida em `localhost:8080` com usuário da FEJEPE:

- abre em outubro (mês fechado); cartões, resumo por IA, 18 EJs em alerta e 7 em
  ascensão batem com a avaliação; novembro aparece como "(em andamento)" com aviso;
- 375 px de largura: sem rolagem horizontal, listas empilhadas.

Ajustes feitos na conferência:

- percentuais da tela com vírgula decimal (helper local; o `formatPercent` comum, usado
  em outras telas, continua com ponto) e "sem variação vs. <mês>" no lugar de "= 0";
- **A4 não aparece quando A1 já se aplica** (decisão de Heitor): com 3+ meses sem venda
  o trimestre recente é zero e o A4 só repetia "queda de 100%". O total de EJs em alerta
  não muda; muda a contagem por motivo (e, com ela, o motivo mais comum do briefing).

Observação fora do escopo: o botão flutuante do Lamps cobre o fim de linhas do resumo
em telas estreitas; acontece em todas as páginas.

Verificação: backend **731 aprovados, 248 pulados**; frontend **40 aprovados**, lint e
build aprovados. Nada commitado.
