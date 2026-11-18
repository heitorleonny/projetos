# Regras de negócio do Portal FEJEPE — inventário para a remodelagem

Levantamento de 21/09/2026, feito lendo o backend, o frontend, a calculadora de
cluster, `portal_fejepe/calculos.md`, `portal_fejepe/estrutura.md`, os testes e o
levantamento de 18/09 (`docs/levantamento-semana1-multitenant.md`).

Branch lida: `feat/multi-tenant-fases-1-3`. **A lógica de negócio desta branch é
idêntica à da `main`.** Só mudam duas coisas: de onde vem o cluster oficial
(na `main`, colunas `cluster_20XX`; aqui, a tabela `cluster_historico`) e o
filtro por federação. Todo o resto vale igualmente para as duas.

**Para que serve este documento.** Registrar o que o portal calcula e mostra
hoje, inclusive o que está errado, antes de trocar o modelo de dados. Assim cada
regra é reimplementada de propósito, preservada ou corrigida, em vez de quebrar
por acidente.

**Convenções**

- `[CONFIRMAR]`: não verifiquei no dado real (só no código ou na documentação),
  ou a regra não está escrita em lugar nenhum.
- ⚠️: divergência, bug ou ambiguidade. Todas estão juntas na [seção 9](#9-divergências-e-decisões-pendentes), numeradas.
- **Regra oficial**: está em `calculos.md` (fórmulas nacionais do MEJ).
  **Regra do portal**: só existe no código; não sei se é oficial.

## Sumário

1. [Respostas curtas](#1-respostas-curtas)
2. [Dados de entrada](#2-dados-de-entrada)
3. [Como o portal recorta a série mensal](#3-como-o-portal-recorta-a-série-mensal)
4. [Métricas por EJ](#4-métricas-por-ej)
5. [Cluster: os cinco "clusters" do portal](#5-cluster-os-cinco-clusters-do-portal)
6. [Métricas da rede](#6-métricas-da-rede)
7. [Eventos: CirandaMEJ'26](#7-eventos-cirandamej26)
8. [Regras que moram no frontend](#8-regras-que-moram-no-frontend)
9. [Divergências e decisões pendentes](#9-divergências-e-decisões-pendentes)
10. [Mapa tela → métrica](#10-mapa-tela--métrica)
11. [O que a nova modelagem precisa fornecer](#11-o-que-a-nova-modelagem-precisa-fornecer)

---

## 1. Respostas curtas

| Pergunta | Resposta | Onde |
|---|---|---|
| O que mantém uma EJ **no verde**? | Ter faturado no acumulado pelo menos a fração da meta anual correspondente aos meses já passados: `% da meta ≥ mês ÷ 12 × 100`. Em setembro, 75% da meta; no "verde de maio" do CirandaMEJ'26, 41,7%. Existe um segundo "verde", sem relação com o mês, nas barras de meta (≥ 80%). | [§8.1](#81-escalonado-de-faturamento--o-que-é-estar-no-verde), [§7](#7-eventos-cirandamej26), [§4.3](#43--da-meta-atingida) |
| O que é o **Saldo de Evolução (SDE)**? | Um número que resume se a rede está subindo ou descendo de cluster: soma ponderada de (EJs subindo − EJs descendo), com peso maior para quem sai do cluster 1. Positivo quer dizer que a rede está evoluindo. O portal calcula três versões, uma para cada índice de cluster. | [§6.3](#63-sde--saldo-de-evolução) |
| O que é **ritmo mínimo**? | A EJ faturou alguma coisa no mês. | [§4.2](#42-ritmo-sem-vendas--ritmo-mínimo--ritmo-significativo) |
| O que é **ritmo significativo**? | A EJ faturou no mês pelo menos 1/12 da meta anual. | [§4.2](#42-ritmo-sem-vendas--ritmo-mínimo--ritmo-significativo) |
| O que é **fora do zero**? | Faturamento acumulado no ano maior que zero. "Fora do zero de colab" tem duas definições diferentes no portal (⚠️ 9.4). | [§4.1](#41-faturamento-acumulado-e-fora-do-zero), [§4.5](#45-faturamento-colaborativo-projetos-colab-e-fora-do-zero-de-colab) |
| O que é **Cluster Track**? | O cluster que a EJ alcançaria em dezembro se mantivesse o ritmo atual de faturamento e cumprisse as metas de CSAT e de engajamento. | [§5.5](#55-tracking-de-cluster-cluster-track) |

O nome da sigla SDE aparece de dois jeitos no código: "Saldo de Desenvolvimento
Estratégico" (título da tela de Indicadores, `calculo_service.py`) e "Saldo de
Evolução" (comentário em `formatters.ts`). `[CONFIRMAR]` qual é o nome oficial do
movimento.

---

## 2. Dados de entrada

### 2.1 Colunas que as regras leem

**`empresa_junior`** (cadastro)

| Coluna | Para que é usada |
|---|---|
| `id_ej` | chave de junção com `metas`, `monitoramento` e `cluster_historico` |
| `id` | chave React no front; não entra em cálculo |
| `nome` | exibição, busca (`ilike`), ordenação |
| `status` | filtro; no evento, decide se a EJ é "ativa" (⚠️ 9.20) |
| `cidade`, `universidade` | filtro (`ilike`); gráfico "Faturamento por Cidade" |
| `foto_url` | logo |
| `cnpj`, `ano_federacao`, `federacao` (`federacao_legado` na branch), `estado`, `curso` | só exibição no perfil |
| `federacao_id` (branch) | tenant |

**`cluster_historico`** (branch) ou `cluster_2023..2026` (`main`): o cluster
oficial da EJ naquele ano. Não é calculado pelo portal, vem do banco. Na `main`,
um ano sem coluna mapeada (2022, por exemplo) cai na coluna `cluster`, que o
levantamento de 18/09 mostrou **não existir** no banco real, e o resultado é nulo.
O banco real tem `cluster_2022..2026`; o código só mapeava de 2023 a 2026.

**`metas`** (uma linha por EJ por ano)

| Coluna | Usada em | Escala |
|---|---|---|
| `meta_faturamento` | % da meta, ritmo significativo, ritmo necessário, "verde" | R$ por ano |
| `meta_csat` | Índice c/ Meta CSAT, Tracking, adaptativo (meses 1–6), falta para o próximo cluster | 0–5 (3,5 a 5,0 na exportação de 21/09) |
| `meta_engajamento_mej` | Tracking e adaptativo (dividida por 100), SDE | **0–100** na planilha e no banco; cálculo em fração |
| `meta_taxa_colaboracao` | só exibição ("Metas vs Realizado" mostra `valor%`) | percentual 0–100 na exportação de 21/09, com 4 valores acima de 100 ([9.A](#9a-resolvidas-contra-a-exportação-de-2109)) |
| `meta_projetos_impacto` | exibição: coluna "Projeto de Impacto" do Cluster Track e linha de "Metas vs Realizado" do perfil | inteiro (0 ou 1 na exportação de 21/09) |
| `meta_pdi` | nada lê | booleano |

**`monitoramento`** (uma linha por EJ por mês)

| Coluna | Como é lida | Alimenta |
|---|---|---|
| `faturamento_mes` | valor da última linha do recorte | ritmo, "Fat. Mês", crescimento mensal, projeção, série |
| `faturamento_acumulado` | valor da última linha (**não é somado**) | % da meta, fora do zero, índices de cluster, totais da rede |
| `faturamento_colab_mes` | valor de cada linha | série mensal de faturamento colaborativo |
| `faturamento_colab_acumulado` | valor da última linha | faturamento colab acumulado da EJ e da rede, taxa de colaboração, índices e SDE |
| `projetos_vendidos_mes` | somado quando `projetos_totais` falta | projetos totais |
| `projetos_totais` | valor da última linha | ⚠️ 9.3: a coluna não existe no banco real |
| `projetos_colab_mes` | somado | projetos colab, filtro "fora do zero de colab" (⚠️ 9.3: ausente no schema do lab) |
| `csat` | média dos valores não nulos | CSAT médio |
| `numero_membros` | valor da última linha | denominador do engajamento |
| `membros_engajados_mes` | **máximo** do recorte | numerador do engajamento |

### 2.2 Valores fixos no código

| O quê | Onde |
|---|---|
| Faixas de cluster, pesos do SDE, `ANO_DEFAULT = 2026`, `MESES_ANO = 12`, fator 100 | [constants.py](../portal_fejepe/app/utils/constants.py) (fonte oficial) |
| Pesos do SDE, **duplicados** | [SimulacaoPage.tsx:8](../front_portal_fejepe/src/features/simulacao/SimulacaoPage.tsx#L8) |
| Faixas de cluster e fórmula, **duplicadas** | [calculadora_cluster/src/App.tsx:4](../calculadora_cluster/src/App.tsx#L4) |
| Evento CirandaMEJ'26: metas de 72/34/30/67%, mês de referência 5 | [evento_service.py:45](../portal_fejepe/app/services/evento_service.py#L45) |
| Cores da barra de meta (80% / 50%) | [EjCard.tsx:92](../front_portal_fejepe/src/features/dashboard/EjCard.tsx#L92), [EmpresaPage.tsx:233](../front_portal_fejepe/src/features/empresa/EmpresaPage.tsx#L233) |
| Regra do projeto de impacto (cluster real ≤ C3 sem projeto) | `aplicar_regra_projeto_impacto` em `calculo_service.py`; constantes `CLUSTER_EXIGE_PROJETO_IMPACTO` e `CLUSTER_MAXIMO_SEM_PROJETO_IMPACTO` em `constants.py`. Substituiu a antiga regra temporária do cluster 4 no SDE (9.18). |

---

## 3. Como o portal recorta a série mensal

Todas as métricas de EJ partem do mesmo recorte, e ele é a regra mais fácil de
quebrar numa migração, porque não aparece em nenhuma fórmula.

1. Filtra `monitoramento` por `ano`. Se o usuário escolheu um mês, filtra também
   `mes ≤ mês escolhido`. Sem mês escolhido, usa o ano inteiro disponível.
2. Ordena por mês. **O "mês atual" da EJ é o maior mês que tem linha no recorte.**
   Não é o mês do calendário, nem o mês escolhido.
3. Cada coluna é lida de um jeito ([tabela 2.1](#21-colunas-que-as-regras-leem)):
   acumulados vêm da última linha, colab é somado, CSAT é média, engajamento é
   máximo ÷ membros do último mês.

Código: [empresa_service.py:490-527](../portal_fejepe/app/services/empresa_service.py#L490-L527).

Consequências que valem hoje:

- Uma EJ que parou de reportar em junho aparece, em setembro, com o ritmo e o
  "faturamento do mês" de **junho**, e é anualizada por 6 meses em vez de 9 (⚠️ 9.7).
- Uma EJ sem nenhuma linha no recorte fica com faturamento 0, ritmo "Sem vendas",
  CSAT e engajamento nulos, e Cluster Track igual ao cluster oficial.
- ~~Não sei se o banco grava uma linha com zero para o mês sem venda ou
  simplesmente não grava linha.~~ **Resolvido em 21/09 (9.7):** toda EJ tem linha
  em todo mês, com zero no mês sem venda. A EJ "que parou de reportar" do item
  acima não aparece na exportação do Portal BJ; ela só existiria num banco
  carregado de outra origem.

---

## 4. Métricas por EJ

Todas são calculadas em `_calcular_indicadores_ej`
([empresa_service.py:473](../portal_fejepe/app/services/empresa_service.py#L473)),
usado pela listagem, pela comparação, pelo perfil e pelos eventos. As fórmulas
puras ficam em [calculo_service.py](../portal_fejepe/app/services/calculo_service.py).

**Exemplo usado ao longo desta seção e da próxima.** "EJ Exemplo", 2026, dados até
agosto (mês 8):

| Dado | Valor |
|---|---|
| `faturamento_acumulado` em agosto | R$ 80.000 |
| Soma de `faturamento_colab_mes` | R$ 8.000 |
| `faturamento_mes` de agosto | R$ 9.000 |
| CSAT dos meses | 4,6 · (vazio) · 4,8 · 4,7 |
| `numero_membros` em agosto / melhor mês de `membros_engajados_mes` | 40 / 12 |
| Metas | faturamento R$ 150.000 · CSAT 4,5 · engajamento 25 (%) |
| Cluster oficial 2026 | 3 |

Os valores do exemplo foram calculados rodando as próprias funções de `calculo_service.py`.

### 4.1 Faturamento acumulado e fora do zero

- **Em linguagem de gestor:** quanto a EJ faturou no ano até o mês do recorte.
- **Fórmula:** a coluna `faturamento_acumulado` da última linha. O portal não
  recalcula a partir de `faturamento_mes` (⚠️ 9.23).
- **Fora do zero:** `faturamento_acumulado > 0`.
- **Aparece em:** card "Faturamento" do Dashboard; KPI "Faturamento" e barra
  "Realizado" do Perfil; Comparação; Cluster Track; coluna "Zeradas" do
  Escalonado; KPI "EJs Fora do Zero" de Indicadores; meta 1 do Ciranda.

### 4.2 Ritmo (Sem vendas / Ritmo Mínimo / Ritmo Significativo)

**Regra oficial** (`calculos.md` §2). Código: [calculo_service.py:47](../portal_fejepe/app/services/calculo_service.py#L47).

- **Em linguagem de gestor:** como foi o mês da EJ em vendas.
- **Fórmula**, sobre o `faturamento_mes` do "mês atual" da EJ ([§3](#3-como-o-portal-recorta-a-série-mensal)):

  ```
  se faturamento_mes ≤ 0                                    → Sem vendas
  senão, se meta_faturamento > 0
         e faturamento_mes ≥ meta_faturamento ÷ 12          → Ritmo Significativo
  senão                                                     → Ritmo Mínimo
  ```

- **Casos de borda:** EJ sem meta cadastrada chega no máximo a "Ritmo Mínimo".
  Faturamento negativo conta como "Sem vendas". No backend as três classes são
  exclusivas: uma EJ significativa não é contada como mínima.
- **Exemplo:** meta de R$ 150.000 dá meta mensal de R$ 12.500. Agosto com R$ 9.000
  é Ritmo Mínimo.
- **Aparece em:** selo no cabeçalho do Perfil; card do Dashboard; filtro "Ritmo" do
  Dashboard (aplicado no navegador, ⚠️ 9.15); CSV do Dashboard e da Comparação;
  gráfico "Ritmo Mínimo e Ritmo Significativo" de Indicadores ([§6.2](#62-ritmo-mensal-da-rede)),
  onde a barra "Ritmo Mínimo" **inclui** as significativas.
- **Cores** ([formatters.ts:79](../front_portal_fejepe/src/utils/formatters.ts#L79)):
  significativo verde `#16A34A`, mínimo âmbar `#F59E0B`, sem vendas vermelho `#DC2626`.

### 4.3 % da meta atingida

Código: [calculo_service.py:22](../portal_fejepe/app/services/calculo_service.py#L22).

- **Em linguagem de gestor:** quanto da meta **anual** de faturamento a EJ já fez.
- **Fórmula:** `faturamento_acumulado ÷ meta_faturamento × 100`, duas casas.
  Sem meta, ou meta ≤ 0, fica nulo ("—").
- A comparação é com a meta do ano inteiro, não com a parcela proporcional ao
  mês. A proporcionalidade só entra no "verde" do Escalonado e do Ciranda.
- **Exemplo:** 80.000 ÷ 150.000 = **53,33%**.
- **Aparece em:** barra "Meta atingida" do Dashboard; KPI "Meta Atingida", barra
  "Progresso da Meta" e linha "Faturamento" de "Metas vs Realizado" no Perfil;
  indicador "% Meta" e "meta média" por ano na Comparação; Escalonado; meta 3 do
  Ciranda; ordenação "% Meta".
- **Cores da barra** (Dashboard e Perfil): ≥ 80% verde, ≥ 50% âmbar, abaixo disso
  vermelho. **Não depende do mês.** A EJ do exemplo fica âmbar na barra e vermelha
  no Escalonado ao mesmo tempo (⚠️ 9.5).

### 4.4 Taxa de colaboração

Código: [calculo_service.py:82](../portal_fejepe/app/services/calculo_service.py#L82).

- **Em linguagem de gestor:** que parte do faturamento veio de projetos colaborativos.
- **Fórmula:** `faturamento colab acumulado ÷ faturamento_acumulado`, decimal com 4
  casas. Nula se o faturamento for ≤ 0. O numerador vem da coluna acumulada
  oficial do Portal BJ no último mês do recorte.
- Entra como `(1 + taxa)` em todas as pontuações de cluster; se for nula, entra como 0.
- **Na série mensal do Perfil**, a taxa do mês *m* é o colab acumulado informado pelo Portal BJ em *m* ÷ o
  `faturamento_acumulado` do mês *m* ([empresa_service.py:267](../portal_fejepe/app/services/empresa_service.py#L267)).
- **Exemplo:** 8.000 ÷ 80.000 = **0,10** (10%).
- **Aparece em:** Perfil (Informações Cadastrais, Metas vs Realizado, tooltip do
  gráfico mensal); Comparação ("Taxa Colab"); Cluster Track ("Fat. Colab real / taxa").

### 4.5 Faturamento colaborativo, projetos colab e fora do zero de colab

- **Faturamento colab acumulado:** EJ e rede leem a coluna
  `faturamento_colab_acumulado` do último mês do recorte. O gráfico mensal
  mantém `faturamento_colab_mes` para o valor de cada mês.
- **Projetos colab:** soma de `projetos_colab_mes`.
- **"Fora do zero de colab" tem duas definições** (⚠️ 9.4):
  - checkbox do Dashboard (`fora_do_zero_colab=true`,
    [empresa_service.py:168](../portal_fejepe/app/services/empresa_service.py#L168)):
    **projetos** colab > 0. A descrição do parâmetro no router diz "faturamento
    colaborativo > 0";
  - meta 2 do Ciranda: **faturamento** colab acumulado > 0.

### 4.6 Projetos totais

`projetos_totais` da última linha; se vier 0 ou nulo, soma de
`projetos_vendidos_mes`. Como a coluna não existe no banco real, na prática é
sempre a soma `[CONFIRMAR]`. Aparece no Dashboard, no Perfil e na Comparação.

### 4.7 CSAT médio

Código: [calculo_service.py:564](../portal_fejepe/app/services/calculo_service.py#L564).

- **Fórmula:** média simples dos `csat` não nulos do recorte, duas casas. **Zero
  conta como nota**; só o nulo é ignorado. Desde a ingestão de 21/09, o CSAT 0
  sem coleta chega ao banco como nulo (✅ 9.8); o zero que sobra é nota zero de
  verdade.
- **Exemplo:** (4,6 + 4,8 + 4,7) ÷ 3 = **4,70**.
- **Aparece em:** KPI "CSAT Médio" e "Metas vs Realizado" do Perfil; Cluster Track
  (real / meta); CSV.
- **Alimenta:** Índice de Cluster e cluster adaptativo a partir do mês 7.

### 4.8 Engajamento com o MEJ (real)

Código: [empresa_service.py:517](../portal_fejepe/app/services/empresa_service.py#L517).

- **Em linguagem de gestor:** que fração da EJ participou de evento do MEJ, no
  melhor mês do ano.
- **Fórmula:** `máx(membros_engajados_mes no recorte) ÷ numero_membros da última
  linha`, 4 casas. Nulo se não houver membros.
- ⚠️ 9.9: numerador e denominador vêm de meses diferentes. Se a EJ encolheu, o
  valor pode passar de 100%.
- **Exemplo:** 12 ÷ 40 = **0,30** (30%).
- **Aparece em:** "Metas vs Realizado" do Perfil; Cluster Track (real / meta).

### 4.9 Projeção anual (Perfil)

**Regra do portal.** Código: [calculo_service.py:369](../portal_fejepe/app/services/calculo_service.py#L369).

- **Em linguagem de gestor:** quanto a EJ deve fechar o ano se a tendência dos
  meses se mantiver.
- **Fórmula:** regressão linear simples sobre `faturamento_mes`, com x = 1, 2, …, n
  (a **posição** na série, não o número do mês). A projeção é a soma da reta nos 12
  meses, com mínimo zero. Exige pelo menos 2 meses.
- ⚠️ 9.22: a docstring diz "acumulado + previsão dos meses restantes", mas o código
  soma a reta inteira, trocando os meses realizados pelos valores ajustados. Com
  meses faltando, o x fica desalinhado do calendário.
- **Exemplo:** meses 8.000 · 9.000 · 11.000 · 10.000 · 12.000 · 10.000 · 11.000 ·
  9.000 (soma 80.000) projetam **R$ 124.571,43**.

### 4.10 Ritmo necessário (Perfil)

Código: [calculo_service.py:410](../portal_fejepe/app/services/calculo_service.py#L410),
chamada em [empresa_service.py:308](../portal_fejepe/app/services/empresa_service.py#L308).

- **Em linguagem de gestor:** quanto a EJ precisa faturar por mês, daqui até
  dezembro, para bater a meta.
- **Fórmula:** `(meta − acumulado) ÷ meses_restantes`, com
  `meses_restantes = 12 − número de linhas da série` (⚠️ 9.22: conta linhas, não
  usa o último mês). Meta já batida dá 0. Sem meta ou sem meses restantes, "—".
- **Exemplo:** (150.000 − 80.000) ÷ 4 = **R$ 17.500/mês**.

### 4.11 Crescimento mensal e anual (Perfil)

Fórmula comum ([calculo_service.py:344](../portal_fejepe/app/services/calculo_service.py#L344)):
`(atual − anterior) ÷ anterior × 100`. Anterior ≤ 0 dá "—". Na tela, verde se ≥ 0
e vermelho se < 0.

- **Mensal:** `faturamento_mes` da última linha contra a penúltima linha, que não
  são necessariamente meses seguidos.
- **Anual** ([empresa_service.py](../portal_fejepe/app/services/empresa_service.py)):
  acumulado atual contra o acumulado do último mês disponível **até o mesmo mês**
  do ano anterior. Sem dados no período atual ou anterior, exibe "—".

---

## 5. Cluster: os cinco "clusters" do portal

É a parte que mais confunde. O portal mostra um cluster que vem do banco e calcula
quatro outros, com a mesma fórmula e insumos diferentes.

### 5.1 Fórmula de pontos

**Regra oficial** (`calculos.md` §5). Código: [calculo_service.py:107](../portal_fejepe/app/services/calculo_service.py#L107).

```
Pontos = Faturamento × CSAT × (1 + Engajamento MEJ) × (1 + Taxa de colaboração) × 100
```

Engajamento e taxa entram em decimal (0,25 = 25%).

### 5.2 Faixas de cluster

**Regra oficial** (`calculos.md` §4). Código: [calculo_service.py:249](../portal_fejepe/app/services/calculo_service.py#L249).

| Pontos | Cluster | Cor no portal | Cor na calculadora |
|---|---|---|---|
| 0 a 12.000.000 | 1 | vermelho | cinza |
| 12.000.000,01 a 24.000.000 | 2 | âmbar | azul |
| 24.000.000,01 a 61.000.000 | 3 | azul | roxo |
| 61.000.000,01 a 130.000.000 | 4 | roxo | âmbar |
| acima de 130.000.000 | 5 | verde | verde |

Pontuação negativa, ou que caia entre faixas, vira cluster 1. As cores divergem
entre o portal e a calculadora (⚠️ 9.19).

### 5.3 Quadro comparativo

| Nome na tela | Campo da API | Faturamento | CSAT | Engajamento | Colab | Onde aparece |
|---|---|---|---|---|---|---|
| **Cluster** (oficial, "cadastral") | `cluster` | — vem do banco | — | — | — | todos os selos de cluster, filtros por cluster, pizza "Distribuição por Cluster", base do SDE e da tendência |
| **Cluster calculado** (adaptativo) | `pontos_cluster`, `cluster_calculado` | anualizado | meta (meses 1–6), real (7–12) | meta (1–3), condicional (4–6), real (7–12) | real | só no CSV do Dashboard; indiretamente, na **Tendência** |
| **Índice de Cluster** | `indice_cluster`, `indice_cluster_calculado` | acumulado, **sem** anualizar | real | real | real | card no Perfil, coluna "Índice Real" do Cluster Track, cenário 1 do SDE |
| **Índice c/ Meta CSAT** | `indice_meta_csat`, `indice_meta_csat_calculado` (só no perfil) | acumulado | meta | real | real | card no Perfil, cenário 2 do SDE |
| **Tracking de Cluster** (Cluster Track) | `tracking_cluster`, `tracking_cluster_calculado` | anualizado | meta | meta (÷ 100) | real | card e "Falta para o Cluster N" no Perfil, Cluster Track, cenário 3 do SDE, meta 4 do Ciranda |

"Anualizado" é sempre `faturamento_acumulado ÷ mês atual da EJ × 12`, com o mês
atual definido na [§3](#3-como-o-portal-recorta-a-série-mensal).

**Exemplo** (EJ Exemplo, cluster oficial 3):

| Índice | Conta | Pontos | Cluster |
|---|---|---|---|
| Índice de Cluster | 80.000 × 4,7 × 1,30 × 1,10 × 100 | 53.768.000 | 3 |
| Índice c/ Meta CSAT | 80.000 × 4,5 × 1,30 × 1,10 × 100 | 51.480.000 | 3 |
| Tracking | 120.000 × 4,5 × 1,25 × 1,10 × 100 | 74.250.000 | 4 |
| Adaptativo (mês 8, fase 3) | 120.000 × 4,7 × 1,30 × 1,10 × 100 | 80.652.000 | 4 |

A mesma EJ, no mesmo mês, aparece como cluster 3 em dois cards do Perfil e como
cluster 4 no terceiro.

### 5.4 Cluster calculado adaptativo

**Regra oficial** (`calculos.md` §6). Código: [calculo_service.py:139](../portal_fejepe/app/services/calculo_service.py#L139).

- **Em linguagem de gestor:** estimativa do cluster de fim de ano que usa metas
  como substitutas enquanto CSAT e engajamento ainda não foram medidos, e troca
  para os valores reais conforme o ano avança.
- **Fórmula:** faturamento sempre anualizado; taxa colab sempre real (nula → 0).

  | Fase | Meses | CSAT | Engajamento |
  |---|---|---|---|
  | 1 | 1–3 | `meta_csat` | `meta_engajamento_mej` |
  | 2 | 4–6 | `meta_csat` | se `real ≥ meta × 0,25`, usa a meta; senão, `real ÷ 0,25` |
  | 3 | 7–12 | CSAT real | engajamento real (nulo → 0) |

- **Casos de borda:** nulo se o faturamento for ≤ 0, se o mês for 0, ou se faltar o
  CSAT da fase (meta nas fases 1–2, real na fase 3). Sem pontos, o cluster calculado
  fica nulo e a tendência também.
- **Escala corrigida em 04/10:** a exportação e a tabela `metas` guardam
  `meta_engajamento_mej` em 0–100. A fórmula adaptativa divide por 100 antes das
  fases 1 e 2, como Tracking e SDE já faziam. Com meta 50, faturamento de R$ 30.000
  até março, CSAT 4,5 e taxa colaborativa 10%, a pontuação passa de
  **3.029.400.000** incorretos para **89.100.000** pontos.

### 5.5 Tracking de Cluster (Cluster Track)

**Regra do portal** (não está em `calculos.md`; o assistente de IA a documenta).
Código: [empresa_service.py:560](../portal_fejepe/app/services/empresa_service.py#L560)
(listagem) e [empresa_service.py:359](../portal_fejepe/app/services/empresa_service.py#L359) (perfil).

- **Em linguagem de gestor:** se a EJ mantiver o ritmo de faturamento e cumprir as
  metas de qualidade, em que cluster termina o ano.
- **Fórmula:** `faturamento anualizado × meta_csat × (1 + meta_engajamento_mej ÷ 100)
  × (1 + taxa colab real) × 100`.
- **Casos de borda** na listagem, que alimenta Cluster Track, Ciranda e filtro:
  - sem nenhuma linha de monitoramento: cluster track = cluster oficial (sem
    oficial, 1);
  - faturamento ≤ 0: cluster track = **1**;
  - sem `meta_csat`: cluster track = cluster oficial.
- **No perfil** os mesmos casos dão cluster track **nulo** (o card mostra "—"). A
  mesma EJ tem cluster track diferente conforme a tela (⚠️ 9.12).
- **Exemplo:** 74.250.000 pontos, cluster 4.
- **Cluster real × cluster apontado (09/11/2026):** o tracking só **aponta** o cluster
  (`tracking_cluster_calculado`). O cluster **real** (`tracking_cluster_efetivo`) é o
  apontado limitado pela regra do projeto de impacto — ver [§5.8](#58-projeto-de-impacto-e-os-clusters-4-e-5).

### 5.6 Índice de Cluster e Índice c/ Meta CSAT

**Regra do portal.** Código: [empresa_service.py:585](../portal_fejepe/app/services/empresa_service.py#L585)
(listagem) e [empresa_service.py:327-357](../portal_fejepe/app/services/empresa_service.py#L327-L357) (perfil).

- **Índice de Cluster:** fórmula oficial com faturamento **acumulado** (sem
  anualizar), CSAT real, engajamento real e colab real. A tela chama de "Snapshot
  atual — valores reais". Exige CSAT real, engajamento real e faturamento > 0.
- **Índice c/ Meta CSAT:** o mesmo, trocando o CSAT real pela meta. Só o perfil
  devolve esse campo.
- ⚠️ 9.10: antes de dezembro, o faturamento acumulado é uma fração do anual, então
  este índice subestima o cluster por construção. É ele que alimenta o cenário 1
  do SDE.

### 5.7 Tendência de cluster (sobe / mantém / desce)

Código: [empresa_service.py:709](../portal_fejepe/app/services/empresa_service.py#L709).

- **Fórmula:** compara o **cluster calculado adaptativo** com o **cluster oficial do
  mesmo ano**: maior → sobe; menor → desce; igual → mantém. Se algum dos dois for
  nulo, a tendência é nula.
- **Aparece em:** CSV do Dashboard ("Tendência Cluster") e selo no card da meta 4 do
  Ciranda (⚠️ 9.11: o selo mostra "↑ sobe" ou "→ mantém"; uma EJ que **desce**
  aparece como "mantém").
- ⚠️ 9.11: a meta 4 do Ciranda, "se mantendo ou subindo", **não** usa a tendência:
  usa o Tracking. O selo exibido na lista e o critério de entrada na lista são
  métricas diferentes.

### 5.8 Falta para o próximo cluster

**Regra do portal.** Duas versões.

**Pelo faturamento** ([calculo_service.py:442](../portal_fejepe/app/services/calculo_service.py#L442)).
Isola o faturamento acumulado na fórmula do Tracking:

```
qualidade        = meta_csat × (1 + meta_engaj ÷ 100) × (1 + taxa colab) × 100
fat_necessario   = limiar_min_do_próximo_cluster × mês_atual ÷ (12 × qualidade)
falta            = máx(0, fat_necessario − faturamento_acumulado)
```

Se o cluster track já é 5, ou falta meta de CSAT, fica nulo. Exemplo: para o
cluster 5 (limiar 130.000.000,01), qualidade 618,75 e mês 8, faltam
**R$ 60.067,34** de faturamento acumulado.
Aparece no card de Tracking do Perfil ("Falta para o Cluster N") e na última coluna
do Cluster Track ("Cluster máx." quando é 5).

**Pelo faturamento colaborativo** ([calculo_service.py:505](../portal_fejepe/app/services/calculo_service.py#L505)).
Supõe que cada real colab entra duas vezes (soma no faturamento e na taxa):
`falta = (limiar ÷ (meta_csat × (1 + engaj REAL) × 100) − fat − fat_colab) ÷ 2`,
partindo do cluster do **Índice real**, sem anualizar. Exemplo: R$ 8.136,75.
**A API devolve esse campo, mas nenhuma tela o mostra.** A calculadora tem uma
versão diferente, que anualiza e usa a meta de engajamento (⚠️ 9.13).

---

### 5.8 Projeto de impacto e os clusters 4 e 5

**Regra de negócio** (Heitor, 09/11/2026), ainda **não** consta em `calculos.md` oficial
do MEJ. O alcance até o C4 foi definido por Heitor em 09/11/2026 (inicialmente a regra
 valia só para o C5); `[CONFIRMAR]` com a Brasil Júnior.

- **Em linguagem de gestor:** projeto de impacto é obrigatório nos clusters 4 e 5. O
  tracking pode apontar subida para o C4 ou o C5, mas o cluster **real** só chega a eles, e
  só permanece neles, se a EJ tiver ao menos um projeto de impacto. Sem projeto o cluster
  real fica limitado ao **C3**.
- **Regra:** `cluster real = min(cluster apontado, 3)` quando `projetos_impacto < 1`; senão
  o apontado. Do C3 para baixo a regra não mexe em nada. Salto de mais de um cluster
  (C2 apontando C5) também para no C3.
- **Dado:** coluna `PROJETOS_DE_IMPACTO` da planilha → `monitoramento.projetos_impacto`
  (migração `26`). Em 21/09 vem vazio ou 1; uma vez 1, repete-se até o último mês. **Vazio
  significa nenhum projeto.** A EJ "tem projeto" se o **máximo** das linhas lidas for ≥ 1
  (não a última linha: se a EJ parou de reportar e a última veio vazia, o projeto não some).
- **Onde vale:** perfil da EJ (3 índices), Cluster Track, e SDE (3 cenários). **Não** foi
  aplicada a: tendência de cluster (`tendencia_cluster`), meta 4 da Ciranda e filtro
  `cluster_track` — todos continuam pelo cluster apontado. `[CONFIRMAR]` se devem passar a
  usar o cluster real.
- **Campos da API:** `*_calculado` = o que o índice aponta; `*_efetivo` = o real. No SDE,
  `EjMovimento.cluster_calculado` já é o real, `cluster_apontado` é o de antes da regra e
  `limitado_por_projeto_impacto` marca quem foi barrado.
- **Efeito na exportação de 21/09** (cluster oficial 2026 × projeto realizado, última linha
  por EJ): C5 = 87 EJs, **24 com projeto**; C4 = 80 EJs, **5 com projeto** (167 EJs nos dois
  clusters, 29 com projeto). Sob a regra, só as EJs com projeto sustentam o C4 e o C5. Linhas gravadas antes da migração 26 ficam com
  `projetos_impacto` nulo (= sem projeto) até a próxima carga da planilha.

## 6. Métricas da rede

### 6.1 Indicadores da rede (`GET /rede/indicadores`)

Código: [rede_service.py:28](../portal_fejepe/app/services/rede_service.py#L28).
Universo: todas as EJs do filtro (ano, mês, cluster oficial),
**qualquer status**. Para cada EJ, usa a última linha do recorte.

| Campo | Fórmula | Aparece? |
|---|---|---|
| `faturamento_total` | Σ `faturamento_acumulado` | KPI "Faturamento Total" (Indicadores) e gráfico mês a mês ([§6.5](#65-faturamento-acumulado-da-rede-mês-a-mês)) |
| `total_ejs` | nº de EJs no filtro, com ou sem dado | KPI "EJs na Rede" |
| `ejs_fora_do_zero` | EJs com linha e `faturamento_acumulado > 0` | KPI "EJs Fora do Zero" |
| `crescimento_vs_ano_anterior` | Σ acumulado atual vs Σ do último acumulado de cada EJ disponível **até o mesmo mês** do ano anterior | KPI "Crescimento", verde ≥ 0 |
| `distribuicao_clusters` | contagem por cluster oficial; **EJ sem cluster no ano conta como 1** (⚠️ 9.14) | pizza "Distribuição por Cluster"; totais do Simulador |
| `faturamento_colab_total` | Σ da coluna `faturamento_colab_acumulado` da última linha de cada EJ | não |
| `total_projetos` | Σ `projetos_vendidos_mes` dos meses do recorte | não |
| `media_csat` | média das médias de CSAT de cada EJ | não |
| `ejs_ritmo_minimo`, `ejs_ritmo_significativo` | ritmo da última linha de cada EJ | não |
| `sde` | sempre nulo; o SDE tem endpoint próprio | não |

### 6.2 Ritmo mensal da rede

Backend: [rede_service.py:484](../portal_fejepe/app/services/rede_service.py#L484). Front: [indicadoresService.ts:126](../front_portal_fejepe/src/features/indicadores/indicadoresService.ts#L126).

- Para cada mês de 1 a 12, classifica cada EJ pelo `faturamento_mes` **daquele
  mês**. EJ sem linha no mês conta como "Sem vendas". Meta usada: a anual ÷ 12.
- O front transforma em percentual sobre o total de EJs:
  - barra **"Ritmo Mínimo"** = (mínimo + significativo) ÷ total, ou seja, quem
    vendeu qualquer coisa. Isso bate com `calculos.md` ("toda EJ que já vendeu no mês");
  - barra **"Ritmo Significativo"** = significativo ÷ total.
- Aparece no gráfico de barras "Ritmo Mínimo e Ritmo Significativo" de Indicadores.
- ⚠️ 9.7: o KPI de ritmo da rede usa a última linha disponível, e este gráfico usa
  o mês exato. Para uma EJ sem linha em setembro, um diz "Ritmo Mínimo" (de
  agosto) e o outro diz "Sem vendas".

### 6.3 SDE — Saldo de Evolução

**Regra oficial** para a fórmula (`calculos.md` §1); **regra do portal** para os
três cenários e os casos de borda. Código: [rede_service.py:290](../portal_fejepe/app/services/rede_service.py#L290),
[calculo_service.py:303](../portal_fejepe/app/services/calculo_service.py#L303).

**Fórmula**

```
SDE = 0,30·(S1 − D1) + 0,25·(S2 − D2) + 0,15·(S3 − D3) + 0,15·(S4 − D4) + 0,15·(S5 − D5)
```

`Sk` e `Dk` são as EJs subindo e descendo **cujo cluster oficial atual é k**, ou
seja, contadas pelo cluster de **origem**. Uma EJ que pula do 1 para o 3 conta uma
subida com peso 0,30. `calculos.md` diz "subindo no cluster k", o que também
poderia ser o destino. `[CONFIRMAR]` qual é a leitura oficial.

**Como cada EJ é classificada**, em cada um dos três cenários:

1. Cluster atual = cluster oficial do ano (sem cluster, conta como 1).
2. Sem nenhuma linha de monitoramento: **mantém** nos três cenários.
3. Faturamento acumulado ≤ 0: cluster calculado **1** nos três (desce, se o atual for > 1).
4. Calcula o índice do cenário ([§5.3](#53-quadro-comparativo)). Se faltar insumo,
   **mantém**: CSAT real e engajamento real nos cenários 1 e 2 (o 2 também exige os
   dois, pela estrutura do `if`), meta de CSAT nos cenários 2 e 3.
5. **Regra do projeto de impacto** ([§5.8](#58-projeto-de-impacto-e-os-clusters-4-e-5)), nos
   **três** cenários: o cluster calculado é limitado a C3 se a EJ não tem projeto de
   impacto. EJ sem projeto **não sobe** para o C4 nem para o C5; EJ do C4 ou do C5 sem
   projeto **desce** para o C3. Isso substituiu a antiga regra temporária ("todo cluster 4 desce no
   cenário 1"), que existia por falta deste indicador (⚠️ 9.18, resolvida). Sem dado
   suficiente para o cenário a EJ parte do cluster atual (mantém), mas a regra continua
   valendo: C4 e C5 sem projeto não permanecem onde estão. Sem nenhuma linha de monitoramento não há
   como saber do projeto e a EJ mantém.
6. Compara o calculado com o atual: maior sobe, menor desce, igual mantém.

| Cenário | Índice usado |
|---|---|
| 1. "Índice de Cluster" | faturamento real × CSAT real × engajamento real × colab |
| 2. "Índice c/ Meta CSAT" | faturamento real × meta CSAT × engajamento real × colab |
| 3. "Tracking de Cluster" | faturamento anualizado × meta CSAT × meta engajamento (÷ 100) × colab |

**Exemplo:** 3 EJs subindo a partir do C1, 1 descendo do C3 e 2 descendo do C4:
0,30·3 − 0,15·1 − 0,15·2 = **+0,45**.

**Na tela** (Indicadores, seção "SDE"): três cards com o valor em 4 casas (verde se
> 0, vermelho se < 0, âmbar se = 0), contadores subindo / mantendo / descendo e a
lista expansível "C{atual} → C{calculado}". Universo: até 1.000 EJs do filtro, com
qualquer status.

### 6.4 Ranking (`GET /rede/ranking`)

[rede_service.py:182](../portal_fejepe/app/services/rede_service.py#L182). Ordena
por faturamento, CSAT, projetos ou colab. **Nenhuma tela chama este endpoint.** Os
critérios "colab" e "projetos" leem colunas que não existem no banco real (⚠️ 9.2, 9.3).

### 6.5 Faturamento acumulado da rede mês a mês

Montado no front ([indicadoresService.ts:43](../front_portal_fejepe/src/features/indicadores/indicadoresService.ts#L43)):
uma chamada a `/rede/indicadores?mes=m` para cada mês até o mês do calendário (ou
12, para ano passado), pegando `faturamento_total`. Aparece no gráfico de linha
"Faturamento Acumulado" de Indicadores.

---

## 7. Eventos: CirandaMEJ'26

**Regra do portal**, fixa no código ([evento_service.py:45-83](../portal_fejepe/app/services/evento_service.py#L45-L83)).

- **Recorte:** ano = `ANO_DEFAULT` (2026) e mês = **5 (maio)**. A tela não envia
  mês, então é sempre maio. O banner escreve "Recorte: Maio" como texto fixo.
- **Universo ("EJs ativas"):** a listagem completa de EJs com `mes = 5`, tirando as
  de status `inativa`, `inativo`, `desativada` ou `desativado`. Status vazio conta
  como ativa ([evento_service.py:254](../portal_fejepe/app/services/evento_service.py#L254)).
- **Contas comuns às quatro metas:**
  - `meta_contagem = teto(meta% × total)`. Com 40 EJs ativas e meta de 72%, a meta
    é 29 EJs;
  - `resultado% = contagem ÷ total × 100`, uma casa;
  - `gap = máx(meta_contagem − contagem, 0)`. Com gap 0, o card mostra "✓ Meta
    atingida"; senão, "Faltam N EJs (x%)";
  - barra de progresso = contagem ÷ meta_contagem, limitada a 100%.

| # | Card | Quem entra | Meta |
|---|---|---|---|
| 1 | Fora do zero de faturamento | `faturamento_acumulado` até maio > 0 | 72% |
| 2 | Fora do zero de colab | faturamento colab (soma até maio) > 0 | 34% |
| 3 | No verde de maio | `% da meta` (acumulado até maio ÷ meta anual) ≥ 5/12 × 100 = **41,67%** | 30% |
| 4 | Se mantendo ou subindo de cluster | `tracking_cluster_calculado` até maio ≥ cluster oficial 2026 (sem cluster, 1) | 67% |

Observações:

- Meta 3: o código calcula uma "submeta" de EJs dos clusters 1 e 2, mas o
  percentual dela nunca foi definido (é nulo, e vira 0). Nenhuma tela exibe (⚠️ 9.21).
- Meta 4: pelos fallbacks do Tracking ([§5.5](#55-tracking-de-cluster-cluster-track)),
  EJ sem monitoramento ou sem meta de CSAT entra automaticamente como "mantendo".
  EJ com faturamento zero só entra se o cluster oficial dela for 1 (⚠️ 9.11).
- A lista de cada card mostra o valor relevante: faturamento, colab, "% da meta" ou,
  na meta 4, o selo de tendência (⚠️ 9.11).

---

## 8. Regras que moram no frontend

O `AGENTS.md` diz que nenhuma fórmula estratégica deve ficar no front. Estas ficam,
e são regra de negócio visível ao usuário.

### 8.1 Escalonado de faturamento — o que é estar "no verde"

Código: [IndicadoresPage.tsx:172-258](../front_portal_fejepe/src/features/indicadores/IndicadoresPage.tsx#L172-L258).

Universo: as primeiras **100** EJs (em ordem alfabética) da listagem, com o filtro
de ano e cluster da tela e **sem mês**, ou seja, acumulado até o último
mês com dado. Se houver mais de 100, a tela avisa.

Com `m` = **mês do calendário** (setembro = 9):

| Cor | Regra | Em linguagem de gestor | Coluna da escada |
|---|---|---|---|
| Cinza, "Zeradas" | faturamento acumulado ≤ 0 | não vendeu nada no ano | ZERADAS |
| Azul | % da meta ≥ 100 | já bateu a meta do ano | DEZEMBRO |
| **Verde** | % da meta ≥ m ÷ 12 × 100 (setembro: 75%) | **em dia**: já fez a parcela da meta correspondente aos meses passados | mês equivalente |
| Amarelo | % da meta ≥ (m − 1) ÷ 12 × 100 (setembro: 66,7%) | atrasada menos de um mês | mês equivalente |
| Vermelho | abaixo disso, **ou sem meta cadastrada** | atrasada um mês ou mais | mês equivalente (sem meta: JANEIRO) |

"Mês equivalente" é `piso(% da meta × 12 ÷ 100)`, entre 1 e 12: a qual mês do ano o
acumulado corresponde. A EJ Exemplo (53,33% em setembro) fica **vermelha na coluna
JUNHO**, isto é, com o faturamento de junho em pleno setembro. Abaixo da escada, a
tela conta quantas EJs há em cada cor e quantas estão sem meta.

⚠️ 9.5: o limiar usa o mês do **calendário**, mesmo quando o ano selecionado já
terminou (2025 inteiro comparado com "75% até setembro") e mesmo quando o dado só
vai até julho. O Ciranda usa a mesma régua com o mês de referência do evento.

### 8.2 Cor da barra de % da meta

≥ 80% verde, ≥ 50% âmbar, < 50% vermelho. Vale para o card do Dashboard, para o
KPI e a barra do Perfil e para a coluna "%" de "Metas vs Realizado". Não depende do
mês ([§4.3](#43--da-meta-atingida)).

### 8.3 Gráfico de ritmo

A barra "Ritmo Mínimo" soma mínimo e significativo ([§6.2](#62-ritmo-mensal-da-rede)).

### 8.4 Simulador de SDE

Código: [SimulacaoPage.tsx:24](../front_portal_fejepe/src/features/simulacao/SimulacaoPage.tsx#L24).
O usuário digita, por cluster, quantas EJs sobem e descem. O total de cada cluster
vem de `distribuicao_clusters` do ano padrão, só para exibição, e não entra na
conta. O C5 não tem campo "subindo". O SDE usa pesos copiados de `constants.py` e
mostra a contribuição de cada cluster. Nada impede subir + descer > total.

### 8.5 Comparação entre anos

Código: [ComparacaoPage.tsx](../front_portal_fejepe/src/features/comparacao/ComparacaoPage.tsx).

- Uma listagem por ano selecionado (padrão: ano de referência e o anterior), até
  100 EJs cada, com o mesmo mês para todos os anos. Sem mês, o ano corrente
  (parcial) é comparado com anos cheios.
- Indicadores selecionáveis: Faturamento (acumulado), Fat. Mês, Taxa Colab, Cluster
  (oficial do ano), % Meta, Projetos.
- **Variação** ([ComparacaoPage.tsx:544](../front_portal_fejepe/src/features/comparacao/ComparacaoPage.tsx#L544)):
  `(valor do último ano − valor do primeiro) ÷ |primeiro| × 100`. Primeiro ano nulo
  ou zero: sem selo. Verde ▲, vermelho ▼.
- **Resumo por ano:** nº de EJs, faturamento somado, projetos somados e
  **"meta média"** = média simples do % da meta das EJs que têm meta.

### 8.6 Perfil: setas e "valores utilizados"

- Os cards "Índice c/ Meta CSAT" e "Tracking" ganham seta comparando com o Índice
  de Cluster: acima de 1,001× sobe, abaixo de 0,999× desce, entre os dois mantém
  ([EmpresaPage.tsx:537](../front_portal_fejepe/src/features/empresa/EmpresaPage.tsx#L537)).
- O card de Tracking mostra "Valores utilizados". O faturamento anualizado dessa
  caixa é **recalculado no front** (acumulado ÷ último mês da série × 12), e a meta
  de engajamento aparece crua, sem ÷ 100.

### 8.7 Dashboard: totais e filtros feitos no navegador

- Mês padrão = **mês do calendário** ([DashboardPage.tsx:13](../front_portal_fejepe/src/features/dashboard/DashboardPage.tsx#L13)).
  Ordem padrão: faturamento decrescente.
- "Faturamento Total", "Projetos" e "Total de EJs" do topo são calculados sobre
  **todas as EJs do recorte filtrado**, independentes do botão "Carregar mais".
- Seleção de mais de um cluster e filtro de ritmo são aplicados no navegador
  depois de buscar todas as EJs do recorte e antes de paginar.

### 8.8 Faturamento por cidade

Soma do faturamento acumulado por `cidade` entre todas as EJs carregadas, top 10.
Cidade vazia vira "Nao informada".

### 8.9 Calculadora de cluster (app separado)

[calculadora_cluster/src/App.tsx](../calculadora_cluster/src/App.tsx). Reimplementa
a fórmula e as faixas. Recebe faturamento, faturamento colab, CSAT real e meta
(0–5), engajamento real e meta (0–100, dividido por 100), e usa o **mês do
calendário** para anualizar. Mostra os três índices do perfil e quanto falta, em
faturamento, colab, CSAT e engajamento, para o próximo cluster pelo Tracking. A
versão colab dela é diferente da do backend (⚠️ 9.13).

---

## 9. Divergências e decisões pendentes

"Preservar ou corrigir" é decisão sua. O que está marcado como provável bug é
minha leitura, não fato.

| # | O quê | Impacto | Decisão |
|---|---|---|---|
| 9.1 | **Escala de `meta_engajamento_mej`.** O dado vem em 0–100; a fórmula usa fração. | Sem conversão, o cluster calculado dos meses 1–6 fica inflado. | ✅ **Corrigida em 04/10:** adaptativo divide a meta por 100 antes do cálculo; Tracking e SDE já faziam isso. Teste com meta realista fixa a pontuação. |
| 9.2 | A coluna acumulada do Portal BJ difere da soma mensal em parte das EJs. | Rede, perfil, comparação e SDE mostravam valores diferentes para a mesma métrica. | ✅ **Decisão de 04/10:** `FATURAMENTO_COLABORATIVO_ACUMULADO` é a fonte oficial em todas as telas e cálculos acumulados; `FATURAMENTO_COLABORATIVO` continua no gráfico mensal. Na exportação de 04/10, 570 de 1.502 EJs divergem (> R$ 0,01) entre as duas formas. |
| 9.3 | `projetos_totais` não existe no banco real; `projetos_colab_mes` falta no schema do lab. | `total_projetos` da rede dá 0 (não aparece em tela). Projetos colab e o filtro "fora do zero de colab" dependem de uma coluna não confirmada. | `[CONFIRMAR]` com `pg_dump --schema-only` do Supabase. **Decisão de 21/09:** a ingestão **não** grava `projetos_totais`. A candidata, `SOLUCOES`, é valor do mês (cai de um mês para o outro em 2.377 casos), e gravá-la ali mudaria o KPI "Projetos". Fica só na staging, e o portal segue somando `projetos_vendidos_mes` (`CONTRATOS`). |
| 9.4 | "Fora do zero de colab": o filtro do Dashboard usa **projetos** colab > 0; o Ciranda usa **faturamento** colab > 0. | Contagens diferentes para o mesmo nome. | Escolher uma definição. |
| 9.5 | Três "verdes": barra de meta (≥ 80%), Escalonado (≥ mês/12, com o mês do **calendário**) e Ciranda (≥ mês/12, com o mês do evento). | A mesma EJ pode estar âmbar, vermelha e verde em telas diferentes. O Escalonado de ano passado usa o mês de hoje. | Definir o limiar pelo mês dos dados ou pelo mês selecionado. |
| 9.6 | Crescimento anual (EJ e rede) comparava o ano parcial com o ano anterior cheio. | Crescimento negativo artificial até dezembro. | ✅ **Corrigida em 04/10:** compara o acumulado ao mesmo mês do ano anterior, escolhendo a última linha do período em vez do maior valor. |
| 9.7 | "Mês atual" é a última linha de cada EJ. EJ que parou de reportar mantém o ritmo e a anualização do último mês reportado. O ritmo mensal usa o mês exato. | KPI e gráfico de ritmo discordam; Tracking anualiza por menos meses. | ✅ **Resolvida (21/09): mês sem venda tem linha com zero.** 13.563 linhas = 1.507 EJs × 9 meses, sem buraco; `FATURAMENTO` nunca vem vazio, e 9.603 linhas são zero legítimo. Zero é dado e vazio é ausência: a ingestão não troca zero por nulo (fora o CSAT da 9.8) e não cria linha para mês que não veio. |
| 9.8 | CSAT zero entra na média. | Derruba a média se 0 significar "sem coleta". | ✅ **Resolvida (21/09): CSAT 0 com coleta 0 significa "sem coleta".** Das 9.280 linhas com CSAT 0, 9.276 têm `PORCENTAGEM_DE_COLETA_CSAT` = 0. Só 4 têm nota zero com coleta real (100%, um detrator). A ingestão grava NULL quando CSAT = 0 e coleta = 0, e o valor que veio em qualquer outro caso. |
| 9.9 | Engajamento = melhor mês ÷ membros do **último** mês. | Pode passar de 100%. | Manter ou normalizar. |
| 9.10 | Índice de Cluster usa o acumulado sem anualizar. | Subestima antes de dezembro; o cenário 1 do SDE tende a "descer" a rede no começo do ano. | Intencional? |
| 9.11 | Tendência usa o adaptativo; a meta 4 do Ciranda usa o Tracking; o selo mostra "mantém" quando a EJ desce. EJ sem dado entra como "mantendo". | Lista e critério contam histórias diferentes. | Alinhar a métrica. |
| 9.12 | Tracking: na listagem cai no cluster oficial (ou 1) quando falta dado; no perfil fica nulo. | Cluster Track e Perfil mostram coisas diferentes para a mesma EJ. | Um comportamento só. |
| 9.13 | Falta em faturamento colab: backend (Índice real, engajamento real, sem anualizar) ≠ calculadora (Tracking, meta de engajamento, anualizado). O do backend nem aparece em tela. | Números diferentes para a mesma pergunta. | Escolher a versão oficial. |
| 9.14 | EJ sem cluster no ano conta como cluster 1 na distribuição e no SDE. | Infla o C1 e mexe no SDE. | Tratar como "sem cluster". **Lado da ingestão resolvido (21/09):** a planilha traz cluster **0** para EJ sem cluster no ano (82 EJs em 2025, 35 em 2026; 75 das 82 foram federadas em 2025 ou 2026). A ingestão não grava linha em `cluster_historico` para o 0, então "sem cluster" fica distinguível no banco. O código do portal continua trocando ausente por 1 (`or 1`): essa parte segue aberta. |
| 9.15 | Multi-cluster e filtro de ritmo eram aplicados no navegador, sobre a página carregada. | Resultados incompletos e total errado. | ✅ **Corrigida em 04/10:** busca todo o recorte antes de aplicar filtros locais e paginar. Ainda convém levar os filtros ao backend para reduzir consultas. |
| 9.16 | Totais do topo do Dashboard somavam só a página carregada. | "Faturamento Total" mudava ao clicar "Carregar mais". | ✅ **Corrigida em 04/10:** os totais vêm de uma consulta a todas as EJs do recorte, com os mesmos filtros do Dashboard. `/rede/indicadores` não cobre busca, cidade, universidade, multicluster e ritmo. |
| 9.17 | Limites fixos: 100 EJs (Escalonado, Comparação, Cluster Track), 1.000 (SDE), 5.000 (eventos). | FEJEPE tem 42 EJs federadas na BJ; FEJEMG tem 285 e já estoura o limite de 100. | ✅ **Resolvida (29/09).** Os números certos são 43 e 291. A causa maior era o teto de 1000 linhas do PostgREST, que zerava 139 EJs da FEJEMG; os services agora paginam (`app/services/leitura.py`) e as telas buscam todas as páginas. Ver `docs/achado-9.17-limites-com-segundo-tenant.md`. |
| 9.18 | Regra temporária: todo cluster 4 desce no cenário 1 do SDE, sem indicar qual indicador falta. | SDE do cenário 1 enviesado para baixo. | ✅ **Resolvida (09/11):** o indicador que faltava era o projeto de impacto. A regra temporária saiu e entrou a regra de [§5.8](#58-projeto-de-impacto-e-os-clusters-4-e-5), nos três cenários. |
| 9.19 | Cores de cluster diferentes entre portal e calculadora. | Confunde quem usa as duas. | Cosmético. |
| 9.20 | "EJ ativa" só existe no evento. Indicadores, SDE e Dashboard contam EJs inativas. | "EJs na Rede" inclui inativas. | Definir se inativa entra nos indicadores. |
| 9.21 | Submeta de "verde de maio" sem percentual definido. | Código morto. | Remover ou definir. |
| 9.22 | Projeção soma a reta nos 12 meses (a docstring diz outra coisa) e usa a posição na série como x; ritmo necessário conta linhas, não meses. | Com meses faltando, projeção e ritmo necessário ficam distorcidos. | Usar o número do mês. |
| 9.23 | `faturamento_acumulado` é lido da coluna, não recalculado. | Se a coluna e a soma dos meses divergirem, vale a coluna. | ✅ **Resolvida (21/09): vale a coluna.** Ela bate com a soma corrida dos meses em 1.506 de 1.507 EJs. Uma EJ diverge por ajuste negativo na origem; o relatório de carga registra a ocorrência sem publicar sua identidade ou valores individuais. A coluna vem **vazia** quando a soma corrida é ≤ 0 (5.509 linhas); a ingestão grava NULL, que o portal já lê como 0. |
| 9.24 | Evento Ciranda tem metas fixas no código. | A configuração do evento ainda não generaliza para outra federação. | A seção de comunidades foi retirada do portal; o Ciranda só aparece para a FEJEPE (`federacao_slug` em `evento_service.py`). As metas do evento continuam no código. |

### 9.A Resolvidas contra a exportação de 21/09

Evidência: `monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx`, aba
`EMPRESAS_JUNIORES`, exportada do Portal BJ em 21/09/2026 (13.563 linhas ×
98 colunas, 1.507 EJs × 9 meses, 27 federações). As regras abaixo foram
implementadas na ingestão (`portal_fejepe/app/ingestao/transform.py`), e cada
carga relata quantas linhas cada uma afetou.

| # | O que o dado mostrou | O que a ingestão faz |
|---|---|---|
| 9.1 | `META_DE_MEJ_ENGAGED_MEMBERS`: mínimo 50, máximo 75, média 61,4. Escala 0–100. | Grava 0–100, como vem. Desde 04/10, o cálculo adaptativo divide por 100 antes das fases 1–2; Tracking e SDE já faziam isso. |
| 9.7 | 1.507 × 9 = 13.563 linhas, sem buraco. `FATURAMENTO` nunca vazio; 9.603 zeros. | Zero é dado, vazio é ausência. Nenhuma linha inventada para mês que não veio, nenhuma apagada quando deixa de vir. |
| 9.8 | 9.280 linhas com CSAT 0; 9.276 delas com coleta 0. | CSAT 0 + coleta 0 → NULL; o resto grava como veio. É a transformação com mais impacto em número de tela: 9.276 zeros derrubariam a média de CSAT de toda federação. |
| 9.23 | Coluna × soma corrida dos meses: 1.506 de 1.507 EJs batem na exportação de referência; a divergente teve ajuste negativo. A coluna vem vazia quando a soma corrida é ≤ 0. | Grava a coluna como vem (vazio → NULL, que o portal lê como 0) e relata as divergentes em toda carga, sem publicar dados individuais. |

**Outros achados da mesma exportação**, registrados porque afetam a modelagem do TCC:

- **`MEMBROS` é foto, não série.** O valor é o mesmo em todos os meses para as
  1.507 EJs: é o cadastro no dia da exportação, repetido. A ingestão grava em
  `monitoramento.numero_membros` mês a mês, como pedido, mas cada exportação nova
  sobrescreve os meses anteriores com o valor de hoje. **Para o modelo de risco,
  `numero_membros` de um mês passado carrega informação posterior a ele** e não
  pode ser usada como feature daquele mês.
- **Cluster 0 = sem cluster** no ano (ver 9.14). Não é gravado.
- **`SOLUCOES` é valor do mês**, não total (ver 9.3). Fica só na staging.
- **`FATURAMENTO_COLABORATIVO_ACUMULADO` não é a soma do colaborativo mensal**
  em 564 EJs na exportação de 21/09 (570 na de 04/10; ver 9.2). É gravado
  como vem e usado como fonte oficial do acumulado.
- **`META_DE_COLLABORATIVE_RATE`** é percentual (0 a 25 em quase todas), mas 4
  EJs têm valor acima de 100: 108 (25.000), 201 (1.200), 227 (1.825) e 2492
  (500). Gravado como veio. `[CONFIRMAR]` com as EJs ou com a federação se é
  erro de digitação.
- **Cadastro que varia entre os meses:** `CIDADE` muda de um mês para outro em 2
  EJs (3167 Manner Jr., 3258 RELAB Jr. Consultoria). Vale o mês mais recente, e
  a carga avisa.

---

## 10. Mapa tela → métrica

| Tela | Elemento | Campo / regra |
|---|---|---|
| **Dashboard** | cards do topo | resumo de todas as EJs do recorte filtrado, independente da página exibida (9.16 resolvida em 04/10) |
| | card da EJ | cluster oficial (selo), faturamento acumulado, projetos totais, ritmo, projetos colab, barra "Meta atingida" (80/50) |
| | filtros | busca, cidade, universidade, clusters (1 no backend, vários no navegador após busca completa), mês (padrão: mês do calendário), ritmo (navegador após busca completa), fora do zero de colab (projetos colab > 0), ordenação |
| | CSV | 18 campos da listagem, incluindo `cluster_calculado` (adaptativo) e `tendencia_cluster` |
| **Perfil da EJ** | cabeçalho | cluster oficial, selo de ritmo, cadastro |
| | KPIs | faturamento acumulado, projetos, projetos colab, CSAT médio, % da meta (80/50) |
| | Índices de Cluster | Índice de Cluster, Índice c/ Meta CSAT, Tracking (+ falta p/ próximo cluster, + valores utilizados) |
| | barra de meta | % da meta, realizado vs meta |
| | gráfico mensal | `faturamento_mes`; tooltip com colab do mês, colab acumulado e taxa, projetos, CSAT |
| | Metas vs Realizado | faturamento (%), CSAT, taxa colab, engajamento MEJ |
| | Projeção & Crescimento | projeção anual, ritmo necessário, crescimento mensal, crescimento anual |
| **Cluster Track** | tabela | cluster oficial / track, faturamento / meta, colab / taxa, CSAT real / meta, engajamento real / meta, Índice real (cluster e pontos), Track (cluster e pontos), falta pelo tracking. O filtro é pelo cluster **oficial**; o parâmetro `cluster_track` da API não é usado por nenhuma tela. |
| **Comparação** | cartões por ano, tabela com variação, gráfico | [§8.5](#85-comparação-entre-anos) |
| **Eventos** | quatro cards do Ciranda | [§7](#7-eventos-cirandamej26) |
| **Indicadores** | KPIs | faturamento total, EJs na rede, EJs fora do zero, crescimento |
| | Escalonado | [§8.1](#81-escalonado-de-faturamento--o-que-é-estar-no-verde) |
| | pizza | distribuição por cluster oficial |
| | barras de ritmo | [§6.2](#62-ritmo-mensal-da-rede) |
| | linha | faturamento acumulado da rede, mês a mês |
| | barras horizontais | faturamento por cidade, top 10 |
| | SDE | três cenários ([§6.3](#63-sde--saldo-de-evolução)) |
| **Simulação** | tabela por cluster | SDE digitado ([§8.4](#84-simulador-de-sde)) |

---

## 11. O que a nova modelagem precisa fornecer

Para que as regras acima continuem funcionando (preservadas ou corrigidas de
propósito), a modelagem nova precisa entregar, por EJ:

- [x] **série mensal** com faturamento do mês e faturamento acumulado, e uma decisão
      sobre qual dos dois é a fonte da verdade (9.23: a coluna, resolvida em 21/09);
- [ ] faturamento colaborativo do mês;
- [ ] projetos vendidos no mês e projetos colaborativos no mês (9.3);
- [x] CSAT do mês, com nulo distinto de zero (9.8, resolvida em 21/09);
- [ ] número de membros e membros engajados em evento MEJ, por mês — membros engajados vêm por mês; **número de membros não**: a exportação traz a foto do cadastro repetida em todos os meses ([9.A](#9a-resolvidas-contra-a-exportação-de-2109));
- [x] uma regra explícita para "mês sem reporte": linha com zero ou ausência (9.7: linha com zero, resolvida em 21/09);
- [x] **metas anuais**: faturamento, CSAT, engajamento MEJ **numa escala única e
      documentada** (9.1: engajamento em 0–100, resolvida em 21/09), taxa de colaboração;
- [ ] **cluster oficial por ano** (já resolvido por `cluster_historico`), distinguindo
      "sem cluster" de "cluster 1" (9.14);
- [ ] status da EJ, com a definição de "ativa" (9.20);
- [ ] cidade/universidade para filtros;
- [ ] as metas de evento (percentuais, mês de referência) fora do código (9.24).

**Decisões que eu tomaria antes de migrar qualquer tabela:**

1. **9.1 (escala do engajamento):** é a única divergência que muda cluster e
   tendência na tela hoje. ~~Uma consulta ao Supabase resolve.~~ Resolvida pela
   exportação de 21/09 (0–100). Falta a correção do adaptativo, em mudança própria.
2. **Preservar bug a bug ou corrigir.** As duas opções:
   - *Preservar tudo na migração e corrigir depois, em PRs separados.* Prós: dá para
     provar que a migração não mudou nada, comparando a saída antes e depois. Contras:
     reimplementa comportamento que você sabe estar errado.
   - *Corrigir durante a migração.* Prós: uma passada só. Contras: se um número mudar
     na tela, não dá para saber se foi a migração ou a correção.

   Eu recomendo a primeira. Ela pede um passo antes: **testes de caracterização**
   que fixem a saída atual de `listar_empresas`, `buscar_empresa`,
   `calcular_indicadores_rede`, `calcular_sde_cenarios` e `calcular_evento` sobre um
   conjunto de dados de exemplo que cubra os casos de borda deste documento.
3. **Tirar do front as regras da [seção 8](#8-regras-que-moram-no-frontend)**
   (Escalonado, totais do Dashboard, filtros no navegador) ou aceitar que elas
   continuem lá. Se continuarem, a modelagem nova também precisa servi-las.
