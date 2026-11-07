# Caracterização das cinco funções — 13/10/2026

## Resultado e limite da evidência

Foi acrescentado o pacote A3 de caracterização da **versão local atual**:
`backend/tests/test_caracterizacao.py` e
`backend/tests/fixtures/caracterizacao/baseline-2026-10-13.json`.
HEAD: `e84fa5b4a8d281688e00c926de71281d368214c7`, com alterações locais anteriores
preservadas. Esse commit sozinho não identifica o código atual; o baseline pertence
ao conteúdo de trabalho entregue nesta data. Nenhum código de aplicação foi alterado.

Os testes antigos de cálculos, empresas, eventos e leitura já verificavam fórmulas
e saídas pontuais, inclusive correções de colaboração. Não existia o arquivo de
caracterização com um corpus compartilhado e a saída completa das cinco funções.

Caracterização fixa **o comportamento observado**, incluindo inconsistências.
Não aprova as regras e não prova preservação da versão single-tenant de produção:
o retrato é posterior às correções de 04/10 e não há execução equivalente do código
de produção nesta tarefa. A regressão controlada A5 continua pendente.

## Corpus sintético e baseline literal

Há nove EJs fictícias em duas federações fictícias. O tenant A tem oito EJs; o B
contém uma EJ sentinela com valores muito maiores para tornar visível um filtro
esquecido. Nenhum dado real, CNPJ, foto ou credencial entra no corpus.

| EJ fictícia | Borda | Divergência |
|---|---|---|
| A Zerada | Zero em todos os meses disponíveis, distinto de ausência | 9.7/9.23 |
| B Sem cluster | Sem histórico do ano; distribuição e SDE tratam como C1 | 9.14 |
| C Parou reporte | Apenas meses 1 e 3, consulta até maio; ritmo congelado e projeção | 9.7/9.22 |
| D CSAT zero | Zero coletado entra na média; não substituir por NULL | 9.8 |
| E Acima meta | Acima da meta, cluster 4, colaboração e descida forçada no cenário 1 | 9.2/9.18 |
| F Abaixo verde | 41,65% da meta em maio, abaixo do limiar do evento | 9.5 |
| G Inativa | Incluída na rede e excluída dos resultados de evento | 9.20 |
| H Sem dados | Sem série; diferenças de fallback de Tracking e manutenção | 9.11/9.12 |
| Z Outro tenant | Recorte explícito dos services e perfil indistinguível de inexistente | isolamento |

As EJs com série têm máximo de 15 membros engajados e dez membros no último mês,
caracterizando engajamento de 1,5 (150%; 9.9). Acumulados oficiais diferem da soma
das linhas esparsas para detectar mudança da fonte de faturamento/colaboração.
A meta de engajamento é 50, na escala 0–100 já corrigida no adaptativo em 04/10.

Os valores do JSON foram capturados uma vez e inspecionados. São literais;
o pytest não gera ou atualiza o baseline nem recalcula o esperado por fórmulas.
A comparação usa igualdade exata do objeto JSON, sem tolerância ampla: todo
campo serializado participa. Ano 2026, mês 5 e tenant 991 são explícitos.

| Função | Saída fixada |
|---|---|
| `listar_empresas` | Todas as oito EJs do recorte, indicadores e paginação |
| `buscar_empresa` | Perfis completos de todas as oito EJs: série, metas, projeção, índices, crescimento |
| `calcular_indicadores_rede` | KPIs, distribuição, crescimento e contagens completas |
| `calcular_sde_cenarios` | Três cenários, SDE e cada movimento por EJ |
| `calcular_evento` | Quatro metas, participantes, percentuais, contagens, gaps e submeta |

## Comportamentos problemáticos preservados

- **9.14:** quatro EJs são contadas como C1 na distribuição, incluindo B Sem cluster.
  O selo da listagem continua nulo para essa EJ.
- **9.18:** E Acima meta passa de C4 a C3 no primeiro cenário por regra temporária,
  embora os demais cenários não a façam descer. SDEs atuais: **0,7; 1,3; 1,45**.
- **9.9:** engajamento real de **1,5** sem normalização.
- **9.12:** H Sem dados tem Tracking do perfil nulo, mas o indicador da listagem
  mantém `tracking_cluster_calculado = 2`.
- **9.22:** C Parou reporte tem duas linhas nos meses 1 e 3; o ritmo necessário
  usa contagem de linhas e retorna **R$ 9.000**, projeção anual **R$ 120.000**;
  Tracking anualiza pelo número do último mês e retorna **81.000.000 pontos/C4**.

CSAT zero coletado e faturamento zero não são tratados como bugs nesta evidência.
A rede sintética totaliza **R$ 1.209.980**, oito EJs e CSAT médio **3,5**; o evento
conta sete EJs, pois exclui a inativa. As saídas servem como referência de mudança,
não como validação independente da regra nacional.

## Verificação executada

1. `cd backend && ../.venv/bin/python -m pytest tests/test_caracterizacao.py -q -rs`:
   **7 passaram, 0 falharam, 0 pulados** (cinco casos parametrizados e dois testes de borda).
2. Prova de sensibilidade em processo separado: alterado **somente em memória**
   `SDE_WEIGHTS[3]` de 0,15 para 0,91 e executado o caso
   `calcular_sde_cenarios`. Resultado esperado: **1 falhou, 6 deselecionados**, código
   pytest 1. A lista foi restaurada em `finally`; nenhum arquivo de aplicação foi
   editado. Isso demonstra que o baseline identifica mudança de peso no SDE.
3. `make test` depois da mutação: **574 passaram, 0 falharam, 0 pulados**, sete
   avisos de dependências/cache. Banco PostgreSQL descartável com migrações 00–23.
   Foram observados avisos SQL de revogação de membership não concedida
   no executor das migrações 19/20; não houve ERROR/FATAL e testes de privilégios/isolamento passaram.

O fake aplica filtros, ordenação e paginação para que a sentinela de outro tenant
não seja ignorada artificialmente; ele **não simula RLS**. A bateria integrada de
banco verifica RLS separadamente. Não houve modelo pago, rede de produção nem
validação humana. Nenhum estado externo ou data de hoje é necessário para este
baseline: o mês/ano são explícitos e o evento recebe o ano como argumento.

## Critério de fechamento

O pacote de caracterização atual das cinco funções está implementado e verificado,
com baseline completo, corpus de bordas e quebra por mutação demonstrada. A afirmação
mais forte de que a transformação preservou a saída da produção exige obter uma
versão anterior identificável e repetir o mesmo corpus antes/depois. Essa lacuna
não é encerrada pelo total de testes ou por este snapshot posterior à transformação.
