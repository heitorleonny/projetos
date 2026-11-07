# Dashboards de eventos montados por IA

> **Histórico — fora do escopo ativo desde 23/10/2026.** Heitor retirou dashboards
> gerados por IA para simplificar o TCC. Este documento preserva o desenho e as
> evidências anteriores; não é uma entrega pendente. Permanecem Nexo e painéis
> convencionais. Consulte o [plano de retomada](retomada-escopo-reduzido-2026-10-23.md).


## Oferta planejada de dashboards completos

Em 07/10/2026, Heitor esclareceu que o produto é a geração de uma aplicação de evento em React, tomando o CirandaMEJ como referência: briefing extenso, título, descrição, propósito, métricas específicas e publicação opcional por link. O alvo é duas aplicações por federação/mês, com orçamento reservado para revisão de código. O número de ajustes depende de medição; a sugestão anterior de 30 não é franquia garantida. Não há requisito de limitar um painel a seis gráficos.

O [desenho arquitetural baseado no Ciranda](arquitetura-dashboards-aplicacoes-2026-10-07.md) detalha geração isolada, versões, dados autorizados e rota pública por slug. A [proposta de planos](proposta-planos-2026-10-06.md) retirou as estimativas de chamadas curtas como base de custo. O código atual gera uma visualização por registro e não oferece geração/edição de aplicações; as seções abaixo descrevem essa base existente.

## Fronteira de cálculo

O modelo transforma um pedido em um `PlanoDashboard` validado pelo backend. O catálogo atual admite somente:

- Métricas armazenadas por EJ e mês: `faturamento_mes`, `projetos_vendidos_mes` e `csat`.
- Agregações: `soma` e `media`; para CSAT, somente média.
- Dimensões: EJ para ranking ou mês para série mensal agregada.
- Visualizações: ranking, barras, linha e cartão.
- Período de um ano, com meses inclusivos, e limite de ranking de até 50 EJs.

A API escolhe colunas fixas de `monitoramento`, restringe as EJs por `federacao_id`, aplica os filtros do período e agrega os valores existentes. O prompt e o modelo nunca recebem linhas do banco. Não há SQL, fórmula, nome de coluna ou filtro livre vindo do modelo. Métrica sem dados aparece sem valor, não como zero.

No exemplo “faturamento das EJs em setembro e outubro”, o backend soma `faturamento_mes` dos meses 9 e 10 do mesmo ano para cada EJ, ordena e aplica o limite. Isso é uma agregação permitida dos valores mensais persistidos; não é cálculo de indicador estratégico.

## Persistência e segurança

`dashboard_evento_ia` grava evento, plano tipado, federação, usuário criador e estado de publicação. Leitura autenticada aplica RLS ao `federacao_id` do JWT; as consultas a `empresa_junior` e `monitoramento` também carregam o JWT do usuário e usam a lista de EJs da própria federação. A API confere o tenant explicitamente. Criação e alteração exigem papel `admin`, além das políticas RLS com dono, tenant e papel.

Cada criação calcula a visualização sob o JWT do usuário e, no final, chama uma RPC que reserva, persiste e confirma um crédito mensal `dashboard` na mesma transação. Falha desfaz a reserva e o registro juntos. Clientes não têm escrita direta na tabela nem acesso às RPCs internas de reserva. Leitura e atualização de visibilidade não consomem créditos. `GET /api/v1/ia/dashboards/creditos` consulta consumidos, reservados, limite e saldo disponível via RPC que deriva identidade e tenant do JWT; a tela mostra o uso mensal da federação.

Um dashboard privado nunca é servido sem autenticação. Ao publicar, o gestor autoriza a divulgação do snapshot calculado, inclusive nomes e valores individuais se escolheu um ranking por EJ. O visitante anônimo só tem acesso às colunas `id`, `publico` e `resultado_publico`, com política RLS limitada a registros publicados. A rota pública lê o snapshot já aprovado; não consulta tabelas de EJs ou fatos. Tornar privado remove o snapshot público.

## Ativação

Aplicar `infra/db/init/19-creditos-ia-tenant.sql` e depois `infra/db/init/20-dashboards-evento-ia.sql` no Supabase. O backend usa o provedor configurado em `IA_PROVEDOR`, `IA_BASE_URL`, `IA_MODELO` e `IA_API_KEY`; a requisição de interpretação limita a resposta a 350 tokens. A interface mostra 1 crédito por dashboard concluído e a cota corrente da federação pelo endpoint de cota.
