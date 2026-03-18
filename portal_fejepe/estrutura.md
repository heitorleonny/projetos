🎯 VISÃO DO PORTAL FEJEPE

Objetivo central:

Centralizar, comparar, simular e analisar dados das EJs da FEJEPE de forma simples, estratégica e orientada à decisão.

🏗 MÓDULOS PRINCIPAIS DA PLATAFORMA

Você tem 5 grandes blocos:

Dashboard Geral da Rede

Perfil Individual da EJ

Comparação entre EJs

Simulador de Cenários

Assistente de IA

Vou estruturar cada um como casos de uso + regras + cálculos envolvidos.

1️⃣ DASHBOARD GERAL DA REDE
🎯 Objetivo

Visão macro da rede da FEJEPE.

👤 Usuário

Time FEJEPE (estratégico e operacional)

📊 O que exibir
🔹 Filtros

Ano

Mês

Cluster

Comunidade

Status da EJ

🔹 Ordenações

Ordem alfabética

Faturamento

Faturamento colab

Cluster

Comunidade

🔢 Indicadores da Rede (Top Section)

Exemplo:

Faturamento total da rede

Faturamento colab total

Nº total de projetos

Média de CSAT

Nº EJs fora do zero

SDE da rede

Crescimento vs ano anterior

📋 Tabela de EJs

Colunas sugeridas:

Nome

Cluster

Comunidade

Faturamento acumulado

Faturamento colab acumulado

Projetos totais

CSAT

% meta atingida

Status (fora do zero, ritmo mínimo, significativo, etc.)

🧠 Cálculos que o sistema precisa fazer

SDE da rede

% meta atingida

Tracking de cluster (sobe, mantém, desce)

Classificação de ritmo

Participação percentual da EJ na rede

2️⃣ PERFIL DA EJ
🎯 Objetivo

Visão estratégica individual.

⚙ Comportamento

Ano padrão: 2026

Pode alterar ano

Pode alterar mês

Atualiza gráficos dinamicamente

📊 Seções do Perfil
🔹 Resumo Geral

Faturamento acumulado

Faturamento colab acumulado

Projetos totais

CSAT médio

% meta atingida

Status do cluster

🔹 Gráficos

Linha → Faturamento mês a mês

Linha → Faturamento colab

Barra → Projetos por mês

Linha comparativa → Ano atual vs ano anterior

🔹 Metas vs Realizado

Meta faturamento vs atual

Meta CSAT vs atual

Meta colab vs atual

Meta impacto

🧠 Cálculos necessários

Crescimento mensal

Crescimento anual

Tendência (regressão simples)

Projeção até dezembro

Ritmo necessário para bater meta

Isso aqui já começa a ficar poderoso.

3️⃣ ABA DE COMPARAÇÃO
🎯 Objetivo

Comparar EJs lado a lado.

⚙ Funcionamento

Usuário pode:

Selecionar várias EJs

Selecionar vários anos

Escolher mês de referência

📊 Visualização

Formato lista comparativa:

| EJ | Ano | Faturamento | Colab | Projetos | CSAT | % Meta |

🧠 Cálculos importantes

Ranking dinâmico

Diferença percentual entre EJs

Gap de faturamento

Gap de meta

🔥 Extra interessante

Adicionar:

Ranking por cluster

Ranking por comunidade

Ranking geral da rede

4️⃣ SIMULADOR DE CENÁRIOS

Esse aqui é o mais estratégico.

🎯 Objetivo

Simular como mudanças individuais impactam a rede.

⚙ Interface

Tela parecida com comparação, mas:

Apenas ano atual

Cada EJ tem um botão ✏️ editar

✏ O que pode ser alterado

Faturamento acumulado

Faturamento colab

Projetos

CSAT

Projetos de impacto

🔄 Após alterar

Sistema recalcula:

Faturamento total da rede

SDE

Ranking

Distribuição de cluster

% meta atingida da rede

Crescimento anual

🧠 Importante

Simulação não altera banco real.

Deve:

Rodar em memória

Ou usar JSON temporário

5️⃣ ASSISTENTE DE IA

Você pensou inicialmente como:

Chat lateral que orienta sobre a plataforma.

Eu concordo como primeira versão.

🔹 Fase 1 — Assistente operacional

Ele responde:

Como usar a plataforma

O que significa SDE

Como calcular taxa de colab

Como interpretar o cluster

Explicar indicadores

🔹 Fase 2 — Assistente estratégico

Depois pode evoluir para:

"Quais EJs estão em risco?"

"Qual cluster está com pior desempenho?"

"Se quisermos crescer 15%, onde atuar?"

"Quais EJs têm maior potencial de impacto?"

🔢 CÁLCULOS ESTRUTURAIS QUE A PLATAFORMA PRECISA TER

Você citou tracking de cluster.

Sugiro separar os cálculos em:

📌 Cálculos de EJ

% meta atingida

Crescimento mês vs mês

Crescimento ano vs ano

Projeção anual

Taxa de colaboração

Classificação de ritmo

📌 Cálculos de Rede

Faturamento total

Média CSAT

Nº fora do zero

SDE

Crescimento da rede

Distribuição por cluster

Participação por comunidade

🧱 ARQUITETURA LÓGICA DA PLATAFORMA
Camada 1 → Banco (dados brutos)
Camada 2 → Camada de cálculo (Python)
Camada 3 → API
Camada 4 → Frontend (React)
Camada 5 → IA


Muito importante:

⚠ Não deixe todos os cálculos no frontend
⚠ Centralize regra estratégica no backend