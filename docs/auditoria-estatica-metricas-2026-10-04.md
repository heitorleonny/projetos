# Auditoria estática das métricas do portal — 04/10/2026

Escopo: Dashboard, Perfil da EJ, Indicadores, Comparação, Cluster Track e
Simulador. Eventos ficaram fora da auditoria funcional; recebem o
`cluster_calculado` da mesma função corrigida nesta revisão. A origem inspecionada
é `monitoring_acumulated_2026_1220261004-1-xflnk9.xlsx`, aba
`EMPRESAS_JUNIORES`, junto com o contrato versionado em
`portal_fejepe/app/ingestao/contrato.py`. Nenhum valor individual de EJ é
reproduzido aqui.

## Linhagem dos campos

| Origem Portal BJ | Tabela/coluna | Regra na API | Exibição |
|---|---|---|---|
| `ID`, `EMPRESA_JUNIOR`, `CIDADE`, `UNIVERSIDADE`, `CNPJ`, `FEDERACAO` | `empresa_junior`, vinculada a `federacao_id` | último mês da EJ define cadastro (`transform.py:230–266`); tenant filtra a consulta | cartões, perfil, Cluster Track, filtros e comparação |
| `CLUSTER_<ano>` | `cluster_historico` | cluster oficial do ano (`utils/cluster.py`) | selo e filtro nas telas, pizza de Indicadores, base do SDE |
| `META_DE_REVENUE`, `META_DE_CSAT`, `META_DE_MEJ_ENGAGED_MEMBERS`, `META_DE_COLLABORATIVE_RATE` | `metas` por EJ/ano | % da meta = faturamento/meta; meta de engajamento da planilha é 0–100 e vira fração nas fórmulas (`calculo_service.py`) | progresso da meta, Metas vs Realizado, Tracking e índices |
| `FATURAMENTO`, `FATURAMENTO_ACUMULADO` | `monitoramento.faturamento_mes`, `faturamento_acumulado` | mês: valor da linha; acumulado: última linha até o mês pedido; nulo lido como 0 | faturamento, ritmo, projeção, crescimento, gráficos e SDE |
| `FATURAMENTO_COLABORATIVO`, `FATURAMENTO_COLABORATIVO_ACUMULADO` | `monitoramento.faturamento_colab_mes`, `faturamento_colab_acumulado` | mês: coluna mensal; acumulado: **coluna acumulada do BJ**, decisão do usuário em 04/10. Taxa = acumulado colab/acumulado total | gráfico mensal, perfil, Cluster Track, comparação e índices |
| `CONTRATOS`, `NUMERO_DE_CONTRATOS_QUE_REALIZOU_ACAO_COLABORATIVA` | `monitoramento.projetos_vendidos_mes`, `projetos_colab_mes` | soma dos meses até o recorte | Projetos, Proj. Colab., comparação e exportação |
| `CSAT`, `PORCENTAGEM_DE_COLETA_CSAT` | `monitoramento.csat` | CSAT 0 sem coleta vira nulo no ETL; média simples dos meses válidos e depois média entre EJs na rede | CSAT, índices, Cluster Track |
| `MEMBROS`, `QUANTIDADE_DE_MEMBROS_ENGAJADOS_COM_MEJ` | `monitoramento.numero_membros`, `membros_engajados_mes` | máximo de engajados ÷ membros da última linha | engajamento real e índices |

O ETL é `portal_fejepe/app/ingestao/transform.py:245–318`. As fórmulas centrais
estão em `portal_fejepe/app/services/calculo_service.py`; o cálculo individual
fica em `empresa_service.py:488–683` e o consolidado em `rede_service.py`.

## Mapa por tela

| Tela/campo | API e cálculo | Apresentação |
|---|---|
| Dashboard — total de EJs, faturamento, projetos | `GET /empresas` com todos os filtros, busca de todas as páginas via `fetchTodasEmpresas`, soma de `faturamento_acumulado`/`projetos_totais` e contagem da lista completa em `useDashboardResumo.ts`. Os cartões de EJ continuam paginados. | `DashboardPage.tsx:55–104`; agora os totais não crescem com “Carregar mais”. |
| Dashboard — EJ e CSV | `listar_empresas` calcula acumulados, projetos, ritmo, % meta, cluster e tendência; filtros locais multicluster/ritmo são aplicados à lista completa antes de paginar. | `EjCard.tsx:10–109`; `ExportModal.tsx:10–89` exporta o recorte completo. |
| Perfil — KPIs e metas | `GET /empresas/{id}` usa `_calcular_indicadores_ej`; % meta = acumulado/meta × 100, CSAT médio, projetos e engajamento. | `EmpresaPage.tsx:140–354`. |
| Perfil — série e projeções | `buscar_empresa` devolve `faturamento_mes`, `faturamento_colab_mes` e acumulado oficial por mês; projeção por regressão linear; ritmo necessário = (meta − realizado)/meses restantes; crescimentos mensal e anual. O anual agora compara o mesmo mês do ano anterior. | `EmpresaPage.tsx:285–339`, tooltip do gráfico em `:389–459`. |
| Perfil — Índice real, Índice c/ Meta CSAT, Tracking | `calcular_pontos_cluster` com faturamento real ou anualizado, CSAT real/meta, engajamento real/meta e taxa colaborativa; `classificar_cluster` aplica faixas oficiais. | `EmpresaPage.tsx:204–270` e `:506–611`. |
| Cluster Track — cada coluna | Mesmos `EmpresaComIndicadores` da listagem: cluster oficial/track, acumulado/meta, colab/taxa, CSAT/meta, engajamento/meta, pontos e falta para próximo cluster. | `ClusterTrackPage.tsx:139–260`; busca todas as páginas. |
| Indicadores — quatro KPIs e pizza | `/rede/indicadores`: soma do último acumulado por EJ, nº de EJs, fora do zero e crescimento no mesmo período; distribuição do cluster oficial. | `IndicadoresPage.tsx:550–569` e `:759–794`. |
| Indicadores — Escalonado, cidade | `fetchTodasEmpresas` obtém todas as EJs; Escalonado posiciona cada EJ por % da meta e usa mês do calendário para as cores; cidade soma faturamento das EJs e mostra top 10. | `IndicadoresPage.tsx:157–255`, `:646–757`, `:870–903`. |
| Indicadores — ritmo, linha, SDE | `/rede/ritmo-mensal` classifica o faturamento **do mês** contra meta anual/12; frontend converte contagens em percentuais. Linha chama `/rede/indicadores?mes=m` para cada mês. `/rede/sde` compara três índices com o cluster oficial e aplica pesos 0,30/0,25/0,15/0,15/0,15. | `indicadoresService.ts:41–69,124–137`; `IndicadoresPage.tsx:796–935`. |
| Comparação — anos e EJs | `fetchComparacaoAnos` chama todas as páginas de `/empresas` por ano/mês e exclui ano sem monitoramento. Cards somam faturamento/projetos das EJs daquele ano e fazem média simples de % meta; barras usam valores individuais. | `ComparacaoPage.tsx:118–205,309–349,508–619`; CSV em `:220–286`. |
| Simulador — SDE hipotético | Totais por cluster vêm de `/rede/indicadores`; usuário informa subidas/descidas; cálculo local Σ peso × (subidas − descidas), com C5 sem subidas. | `SimulacaoPage.tsx:7–32,69–110,163–237`. |

## Correções feitas nesta revisão

1. **Escala da meta de engajamento (P1):** Q1/Q2 do cluster adaptativo agora
   divide por 100 a meta que a planilha grava em 0–100. Com meta 50,
   faturamento acumulado hipotético de R$ 30.000 até março, CSAT 4,5 e taxa
   colaborativa 10%, o cálculo anterior produziria 3.029.400.000 pontos; o
   correto é 89.100.000. Afeta cluster calculado, tendência, filtro/CSV e
   qualquer evento que use esse campo. `calculo_service.py:185–203`.
2. **Crescimento anual (P1):** perfil e rede comparam acumulados até o mesmo mês
   do ano anterior; a rede usa a linha mais recente, mesmo após ajuste negativo,
   em vez do maior acumulado. `empresa_service.py:700–724`,
   `rede_service.py:526–557`.
3. **Acumulado colaborativo (P1):** a coluna acumulada do Portal BJ é a fonte
   oficial em EJ, série mensal acumulada e SDE; a coluna mensal permanece no
   gráfico. Na exportação de 04/10, 570 das 1.502 EJs têm diferença maior que
   R$ 0,01 entre o acumulado e a soma mensal, motivo pelo qual as telas
   divergiam. `empresa_service.py:269–287,514–525`, `rede_service.py:368–370`.
4. **Dashboard (P1):** totais e CSV do recorte completo e filtros locais
   aplicados antes da paginação (`DashboardPage.tsx`, `useDashboardResumo.ts`,
   `dashboardService.ts`).

## Pendências identificadas

| Gravidade | Achado, evidência e efeito | Próximo passo |
|---|---|
| P1 | `rede_service.py:96–98,135–137,323` substitui cluster ausente por C1. A origem usa 0 para “sem cluster”; a distribuição, o SDE e os totais do Simulador passam a incluir essas EJs em C1. | Criar categoria “sem cluster” e definir se participa do SDE. |
| P1 | `rede_service.py:405–409` força toda EJ oficialmente C4 a descer no primeiro cenário do SDE, mesmo se o índice calculado indicar C4/C5. | Confirmar a regra de negócio com a federação e, se não for oficial, removê-la. |
| P2 | `IndicadoresPage.tsx:170–228,653–658` usa o mês do calendário para o Escalonado mesmo ao selecionar outro ano ou quando a carga está atrasada. | Usar o último mês efetivamente importado do ano exibido. |
| P2 | `indicadoresService.ts:41–69` consulta até o mês do calendário; se faltarem meses na carga, `/rede/indicadores?mes=m` repete o último acumulado, criando linha plana que parece dado informado. Erros de mês são convertidos em zero. | Retornar disponibilidade mensal da API e preservar erro em vez de convertê-lo silenciosamente em zero. |
| P2 | `rede_service.py:503–520` devolve 12 meses de ritmo; meses sem monitoramento aparecem como 0% de vendas, inclusive futuros. | Diferenciar “sem dado” de “zero vendas”. |
| P2 | `empresa_service.py:163–167` define “fora do zero de colab” por **projetos colaborativos**, mas o nome sugere faturamento; Eventos usa faturamento acumulado. | Escolher e explicitar uma definição na interface. |
| P2 | `empresa_service.py:575–602` mantém cluster oficial como fallback do Tracking sem dados; `buscar_empresa` retorna índice/cluster de Tracking nulo nessas condições (`:361–377`). | Unificar a apresentação entre listagem/Cluster Track e Perfil. |
| P2 | `ComparacaoPage.tsx:532–572` apresenta variação percentual também para cluster e % da meta. Ex.: C2→C3 aparece como +50%, e 20%→30% da meta como +50%, não +10 p.p. | Mostrar diferença de clusters como passos e de percentual como pontos percentuais. |
| P2 | `ComparacaoPage.tsx:191–205` calcula o resumo antes da busca por nome (`:148–156`); a tabela filtra, mas os cartões por ano permanecem da rede inteira. | Fazer o resumo acompanhar a busca ou rotular seu escopo. |
| P2 | `SimulacaoPage.tsx:8–32,94–102` duplica os pesos do backend e aceita subidas/descidas maiores que o total de EJs do cluster. | Compartilhar constantes e validar movimentos possíveis. |

Validação das alterações backend: `125 passed` nos testes focados de cálculo,
empresas, segurança e crescimento. Esta é uma auditoria **estática**; ela não
substitui a navegação visual do portal nem a conferência de números individuais
com a federação.
