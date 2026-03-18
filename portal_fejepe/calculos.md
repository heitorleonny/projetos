📊 Cálculos Estratégicos – Portal FEJEPE
🎯 Objetivo

Documentar oficialmente as fórmulas estratégicas utilizadas no Portal FEJEPE para:

SDE da rede

Classificação de Ritmo

Tracking de Cluster

Pontuação de Cluster

Fórmula adaptativa durante o ano

1️⃣ Cálculo do SDE
📌 Definição

O SDE mede o saldo de movimentação de EJs entre clusters, considerando:

Quantas estão subindo

Quantas estão descendo

A fórmula pondera cada cluster com pesos diferentes.

🔢 Fórmula do SDE
SDE = 
0,3  * (S1 - D1) +
0,25 * (S2 - D2) +
0,15 * (S3 - D3) +
0,15 * (S4 - D4) +
0,15 * (S5 - D5)


Onde:

S1 a S5 = Número de EJs subindo no cluster 1 a 5

D1 a D5 = Número de EJs descendo no cluster 1 a 5

2️⃣ Classificação de Ritmo
🟢 Ritmo Mínimo

Toda EJ que já vendeu no mês.

Critério:

faturamento_mes > 0

🚀 Ritmo Significativo

Toda EJ que já vendeu no mês valor igual ou superior à meta mensal.

Meta mensal:

meta_mensal = meta_anual / 12


Critério:

faturamento_mes >= meta_mensal

3️⃣ Tracking de Cluster

O cluster final é definido com base na Pontuação de Cluster.

4️⃣ Tabela de Classificação de Cluster
Pontuação mínima	Pontuação máxima	Cluster
0,00	12.000.000,00	1
12.000.000,01	24.000.000,00	2
24.000.000,01	61.000.000,00	3
61.000.000,01	130.000.000,00	4
130.000.000,01	Infinito	5
5️⃣ Fórmula Oficial de Pontos de Cluster (Final do Ano)
Pontos = 
Faturamento
* CSAT
* (1 + % Engajamento com o MEJ)
* (1 + % Faturamento Colaborativo)
* 100


Onde:

Faturamento = faturamento anual

CSAT = média anual

% Engajamento MEJ = valor decimal (ex: 0.25)

% Faturamento Colaborativo = valor decimal

Multiplicado por 100 como fator de escala

6️⃣ Fórmula Adaptativa de Cluster (Durante o Ano)
📌 Motivação

CSAT e Engajamento com o MEJ só são mensurados com precisão no final do ano.
Por isso, a fórmula varia em 3 fases, usando gradualmente mais dados reais
à medida que o ano avança.

Em todas as fases, o faturamento é anualizado:
```
Faturamento_anualizado = (faturamento_acumulado / mês_atual) * 12
```

🔢 Fase 1 — Mês 1 a 3 (Q1)

Usa metas como proxy para CSAT e Engajamento.

```
Pontos = Fat_anualizado * meta_CSAT * (1 + meta_Engajamento_MEJ) * (1 + % Fat_Colab_real) * 100
```

🔢 Fase 2 — Mês 4 a 6 (Q2)

CSAT ainda usa a meta. Engajamento é condicional:
- Se `engajamento_real >= meta_engajamento * 0.25` → usa `meta_engajamento` (EJ está no caminho)
- Senão → usa `engajamento_real / 0.25` (penalização por baixo engajamento)

```
engaj_ajustado = SE(engaj_real >= meta_engaj * 0,25; meta_engaj; engaj_real / 0,25)

Pontos = Fat_anualizado * meta_CSAT * (1 + engaj_ajustado) * (1 + % Fat_Colab_real) * 100
```

🔢 Fase 3 — Mês 7 a 12 (Q3/Q4)

Usa valores reais de CSAT e Engajamento.

```
Pontos = Fat_anualizado * CSAT_real * (1 + engaj_real) * (1 + % Fat_Colab_real) * 100
```

📌 Observação

No final do ano (mês 12), o faturamento anualizado converge com o faturamento real
e todos os indicadores são os definitivos, equivalendo à fórmula oficial.