# Proposta revisada de planos do Portal das Federações

Pesquisa em 06/10/2026. Status: proposta comercial para validação com federações; não é oferta contratada nem altera o plano de um tenant. Os valores da migração 03 continuam sendo placeholders até a adoção de um catálogo comercial em migração nova.

## Correção de escopo em 07/10/2026

Heitor esclareceu que o produto gera uma aplicação de evento em React, tomando o CirandaMEJ como referência, com briefing longo, identidade visual e métricas específicas. O [desenho revisado](arquitetura-dashboards-aplicacoes-2026-10-07.md) passa a orientar a implementação. As estimativas anteriores de chamadas curtas e a quantidade de 30 ajustes não fundamentam uma oferta desse novo escopo. Os preços abaixo permanecem hipóteses comerciais e exigem nova medição.

## Recomendação

Cobrar pela federação, com acesso da equipe e franquias de IA compartilhadas. A mensalidade remunera o portal, sua operação e manutenção. A franquia limita o uso; seu valor não deve ser apresentado como se fosse o custo da API.

| Plano proposto | Mensalidade por federação | Novos dashboards completos/mês | Revisões com IA/mês | Consultas ao Nexo/mês, propostas |
|---|---:|---:|---:|---:|
| Essencial | R$ 99, a revalidar | 2 | Orçamento a medir | 500 |
| Gestão | R$ 149, a revalidar | 2 | Orçamento a medir | 1.500 |
| Rede | R$ 249, a revalidar | 2 | Orçamento a medir | 5.000 |

O alvo é entregar duas novas aplicações de dashboard por mês, com orçamento suficiente para revisar o código gerado. Um briefing reúne título, descrição, propósito, métricas e visibilidade. A aplicação pode ter várias seções, gráficos, rankings, busca e identidade do evento, como no Ciranda. Não há um teto de seis gráficos definido como requisito do produto.

A quantidade de revisões precisa ser dimensionada após medir geração, contexto, alterações de arquivos e reparos de build. As 30 alterações da proposta anterior ficam como referência histórica, sem garantia de franquia. Um ajuste pequeno e a reconstrução de várias seções não têm o mesmo custo.

As funcionalidades centrais de gestão, isolamento por federação e publicação de dashboards devem existir nos três planos. O acesso da equipe não acrescenta uma mensalidade por usuário. Isso não representa capacidade técnica ilimitada; armazenamento, tráfego público e demanda de suporte precisam ser acompanhados.

Manter contagem de aplicações concluídas separada do orçamento de revisão e do custo do provedor. Dashboards anteriores permanecem salvos. Visualização, busca e filtros já implementados, atualização de dados autorizados e publicação não usam o gerador. Pedidos que alteram o código gerado consomem o orçamento de revisão, com informação de consumo antes da execução.

O código atual gera uma visualização por registro. Faltam geração de frontend React, ambiente isolado, composição, versionamento e revisão de código. As quantidades mensais de Nexo também são propostas pendentes de implementação. O piloto atual de 100 criações não representa a franquia comercial de duas aplicações.

Começar a venda pelo Essencial e Gestão; apresentar Rede apenas para uso que justifique a franquia maior. Não vincular os planos ao número de EJs: uma federação grande pode fazer poucas criações, e uma pequena pode usar intensamente a ferramenta.

## Custo de geração de aplicações: medição pendente

A estimativa anterior de 4.000 tokens de entrada e 1.500 de saída tratava de um plano estruturado de componentes. A geração de uma aplicação como o Ciranda inclui arquivos React/TypeScript/CSS, histórico de edição, validação e eventuais chamadas para corrigir um build. As tabelas anteriores de R$ 0,44 por duas montagens e 30 ajustes foram retiradas da proposta porque não dimensionam esse trabalho.

Medir uma geração equivalente ao Ciranda e uma sequência de revisões com dados sintéticos. Registrar o modelo, tokens de entrada/cache/saída/raciocínio quando aplicável, número de chamadas, tentativas que falham, tempo de build e custo financeiro. Contabilizar o uso do Nexo separadamente. A oferta precisa prever orçamento por aplicação, revisão e plataforma, além do limite de duas entregas concluídas.

As [tarifas oficiais da API](https://developers.openai.com/api/docs/pricing) são uma entrada da conta; elas não estabelecem o preço de uma aplicação pronta. A escolha do modelo depende da qualidade de geração e da compatibilidade com o executor. Não houve geração paga ou medição desse novo fluxo nesta revisão.

## Infraestrutura e manutenção

O projeto compartilha backend e banco entre tenants. Considerar uma infraestrutura inicial com [Supabase Pro a partir de US$ 25/mês](https://supabase.com/pricing) e backend de 2 GB no [Render a US$ 25/mês](https://render.com/docs/render-vs-heroku-comparison). O dimensionamento de 2 GB é uma hipótese prudente para planejamento, não um teste de capacidade do portal. O total de referência é **US$ 50/mês**, aproximadamente **R$ 300** ao câmbio de planejamento, compartilhados pela plataforma.

Acrescentar as seguintes hipóteses operacionais:

| Item | Reserva mensal proposta |
|---|---:|
| Banco e backend compartilhados | R$ 300 |
| Domínio, e-mail, observabilidade e imprevistos operacionais | R$ 60 |
| Manutenção recorrente: 4 horas a R$ 50/h | R$ 200 |
| Total fixo de planejamento | R$ 560 |

R$ 50/h é somente a remuneração adotada neste cenário, não uma tarifa profissional recomendada. Se o trabalho for remunerado a R$ 100/h, a reserva fixa sobe para R$ 760. Desenvolvimento de novas funcionalidades, migração inicial de dados e aquisição de clientes ficam fora dessa conta e precisam de verba própria.

Considerar ainda R$ 15, R$ 20 e R$ 30 por tenant/mês de reserva de suporte nos planos Essencial, Gestão e Rede, respectivamente. Isso é um orçamento operacional para atendimento assíncrono limitado, não horas de consultoria prometidas. Reservar também 10% da receita para taxas de pagamento e obrigações fiscais, como hipótese a validar com o meio de cobrança e a contabilidade, sem presumir uma alíquota legal específica.

## Sustentabilidade dos preços: recalcular após medir geração

A reserva fixa de R$ 560 e as hipóteses de suporte e taxas acima continuam referências de operação. Os saldos anteriores que usavam interpretação curta de IA foram retirados; não representam a margem da geração de aplicações.

A conta revisada precisa ser:

```text
saldo operacional = receita das federações
                  - custos fixos
                  - suporte e taxas
                  - custo das gerações, revisões e falhas
                  - custo do Nexo
```

As mensalidades de R$ 99/R$ 149/R$ 249 devem ser revalidadas com esses custos e com a capacidade de pagamento das federações. Dar duas aplicações com folga de revisão requer um orçamento medido, sem presumir que todo modelo ou tarefa caiba na mesma franquia. Não usar o número de gráficos como proxy do custo de geração.

## Acessibilidade e referência de mercado

R$ 99/mês estabelece uma entrada abaixo de R$ 100 para a organização inteira. Como referência de licenciamento, a [Microsoft publica Power BI Pro por R$ 80,20 por usuário/mês, pago anualmente e sem impostos](https://www.microsoft.com/pt-br/power-platform/products/power-bi/pricing). Cinco licenças correspondem a R$ 401/mês nessa tabela. Produtos, benefícios incluídos em outras licenças e condições para organizações elegíveis diferem; isso serve como referência de cobrança por equipe, não demonstra equivalência funcional.

A capacidade de pagamento das federações não foi pesquisada por entrevistas nem demonstrada por orçamento público. Validar a proposta com 5–8 federações, pedindo a quem aprova a despesa que avalie R$ 99 e R$ 149 e informe quanto suporte e importação manual espera. O número de EJs sozinho não mede capacidade de pagamento.

Para reduzir a barreira de entrada, oferecer avaliação de 30 dias, com uma aplicação de dashboard, orçamento de revisão medido e 50 consultas ao Nexo, depois de implementar o período de avaliação e suas cotas. Uma campanha fundadora de R$ 79 por até três meses pode ser subsidiada deliberadamente; não a usar como preço permanente sem refazer a conta. Uma federação com restrição de caixa pode ter uma bolsa patrocinada, em que o parceiro cobre a diferença. Evitar um gratuito permanente dependente de manutenção sem financiamento.

Não vender pacotes adicionais antes de observar uso real. Duas aplicações completas com orçamento de revisão reservado são o alvo inicial; avaliar a folga em sessões reais de autoria e geração de código. Se houver demanda sazonal, dimensionar um adicional pequeno de um dashboard com ajustes próprios, com preço definido após medir uso e suporte.

## Ajustes antes de uma oferta pública

1. Adotar os valores comerciais em migração nova, preservando as migrações anteriores e sem atribuir plano automaticamente às federações existentes.
2. Implementar geração de aplicações React, isolamento, versões, edição de código com IA, limite mensal de duas entregas e orçamento de revisões. Implementar as franquias mensais do Nexo antes de anunciar os números da tabela. Continuar aplicando proteção de chamadas por minuto.
3. Medir tokens, custo, falhas e consumo por tenant sem registrar dados de negócio no provedor desnecessariamente; definir teto financeiro central.
4. Validar o modelo econômico com o catálogo real e com pedidos ambíguos. Preço baixo não substitui qualidade de interpretação.
5. Registrar o que suporte inclui, como funcionam reajuste e cancelamento, e o período do piloto; cobrar customizações e serviços manuais separadamente.
6. Reavaliar custos e preços após 30–60 dias de operação e entrevistas. Preservar direitos de exportação dos dados ao encerrar uma assinatura.

Não foi feita chamada a modelo nesta pesquisa. As referências de infraestrutura foram consultadas em fontes oficiais e seus valores são hipóteses de planejamento. A proposta de R$ 99 / R$ 149 / R$ 249 permanece em revisão; geração de aplicações ainda precisa de medição de custo antes da adoção comercial.
