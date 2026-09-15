# Produto — Portal FEJEPE → SaaS de Federações de EJs

## O problema
Federações de Empresas Juniores (EJs) acompanham dezenas de EJs com planilhas soltas:
faturamento, metas, CSAT, engajamento, movimentação entre clusters. Falta uma visão
consolidada, comparável e orientada à decisão.

## O produto
Uma plataforma web que centraliza os dados das EJs de uma federação e entrega:

1. **Dashboard da rede** — KPIs consolidados (faturamento total, CSAT médio, EJs fora
   do zero, distribuição por cluster, crescimento vs ano anterior).
2. **Perfil da EJ** — visão individual com série temporal, metas vs realizado, projeção
   anual, ritmo necessário e crescimento.
3. **Comparação** — EJs lado a lado, rankings por faturamento/CSAT/projetos/colab.
4. **Simulador de cenários** — simula mudanças e recalcula SDE, ranking e distribuição
   sem alterar o banco.
5. **Eventos** — acompanhamento de metas de eventos da federação (ex.: CirandaMEJ).
6. **Assistente de IA** (planejado) — orientação sobre a plataforma e, depois, análise
   estratégica ("quais EJs estão em risco?").

## Usuários
- **Hoje:** time estratégico e operacional da FEJEPE.
- **Visão SaaS:** qualquer federação de EJs do Brasil (Ceará, RN, RS, etc.), cada uma
  com seus dados isolados, seu branding e seus usuários com papéis distintos.

## Conceitos de negócio (vocabulário do domínio)
- **EJ** — Empresa Junior. Identificada por `id_ej`.
- **Federação** — organização que agrupa EJs de um estado. Será o **tenant** do SaaS.
- **Comunidade / núcleo** — agrupamento de EJs dentro da federação.
- **Cluster (1–5)** — faixa de maturidade/porte da EJ, por pontuação.
- **SDE** — Saldo de Desenvolvimento Estratégico: saldo ponderado de EJs subindo vs
  descendo de cluster.
- **Ritmo** — sem_vendas / mínimo / significativo, conforme o faturamento do mês.
- **CSAT** — satisfação do cliente. **Engajamento MEJ** — participação em eventos do MEJ.

## Norte do produto (SaaS)
Cada federação deve conseguir:
- Isolar totalmente seus dados de outras federações.
- Personalizar marca (nome, logo, cores) e vocabulário (comunidades, anos).
- Ter usuários com papéis (admin da federação, gestor, visualizador).
- Definir suas próprias metas e, no futuro, ajustar parâmetros de cluster.
