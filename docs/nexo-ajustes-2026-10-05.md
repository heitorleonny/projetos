# Nexo: esclarecimento, identidade e contexto visível

Data: 05/10/2026. Mudanças solicitadas após a revisão de uso do assistente.

## Comportamento

Perguntas simples como “quais são as melhores EJs?” agora pedem o indicador, com quatro opções geradas pelo backend: maior faturamento, maior CSAT, mais projetos e maior colaboração. Não ocorre consulta ao modelo nem ao banco para esse caso simples. Se a frase tiver requisitos adicionais não reconhecidos pela guarda local, ela segue para o intérprete em vez de ignorá-los. O modelo também pode devolver a ferramenta tipada `esclarecer`; textos e opções permanecem definidos pelo backend.

O painel mostra o período, cluster oficial, busca por nome e critério usados na resposta. Acima da caixa de mensagem, mostra o contexto disponível para uma continuação. As sugestões de métricas repetem explicitamente cluster e período. Perguntas que usam busca por nome não recebem sugestões de agregados que perderiam esse filtro. A recusa mantém o contexto para o usuário retomar a consulta anterior.

Nome e sigla da própria federação passam a ser aceitos. O router lê o nome e slug da federação com o cliente autenticado e filtro pelo claim validado do JWT. Apenas esses aliases são normalizados para “minha federação” antes da interpretação. Siglas de outras federações e pedidos explícitos de várias federações são recusados localmente antes do modelo. O plano pode declarar um nome literal em `federacao_mencionada`; o backend compara esse nome com os aliases autenticados e recusa se forem diferentes. Esse campo não escolhe ID, altera o cliente ou concede autoridade. A identidade de execução continua vindo exclusivamente do JWT e as consultas seguem submetidas à RLS.

## Contrato

`PlanoConsulta.ferramenta` inclui `esclarecer`, com `esclarecimento` anulável (`metrica_ranking`, `periodo`, `escopo`) e `federacao_mencionada` anulável (nome literal, sem autoridade). `RespostaRede.status` inclui `esclarecimento`, e o campo de mesmo nome contém `{pergunta, opcoes: [{rotulo, pergunta}]}`. Clientes antigos continuam podendo enviar somente `{pergunta}`.

As opções produzem perguntas completas e repetem o recorte. O contexto segue efêmero no frontend; nenhum resultado anterior vai para o provedor e nenhuma nova tabela foi criada.

## Verificação e limites

Testes determinísticos cobrem esclarecimento com cluster/período explícitos, geração controlada de opções, nome e sigla próprios, metadados lidos com filtro do tenant na rota, recusa antecipada de outra federação, declaração externa hostil pelo modelo, sugestões com recorte e retomada após recusa. O corpus do modelo real passou de 19 para 21 casos; o gabarito da pergunta ambígua mudou para esclarecimento. A avaliação real permanece separada dos testes determinísticos. O runner reporta métricas de interpretação e catálogo separadas do fluxo com guardas backend, reaproveitando a mesma interpretação sem uma segunda chamada ao modelo; não equivale a testar a rota HTTP ou a autenticação.

Verificação desta rodada: 80 testes de IA/RLS passaram, nenhum pulado, usando PostgreSQL real do laboratório. `npm run build` e `npm run lint` também passaram. Não houve chamada ao provedor real nesta implementação.

A normalização aceita os nomes e slugs cadastrados da própria federação, sem adivinhar abreviações não cadastradas. As guardas semânticas complementam o catálogo; a garantia de isolamento dos dados continua sendo JWT, filtro explícito e RLS, independentemente de o modelo interpretar a intenção corretamente. O controle operacional compartilhado foi acrescentado em uma migração separada, sem créditos comerciais: ver [nexo-controle-operacional-2026-10-05.md](nexo-controle-operacional-2026-10-05.md).

## Correção após avaliação real: cidade não vira nome

A avaliação real revelou uma interpretação errada: “Quais EJs de Recife estão fora do zero?” produziu `busca=Recife`. O backend passou a exigir intenção explícita de nome (`nome`, `contendo`, `chamada`, `denominada` e variantes), além de verificar que o trecho buscado aparece literalmente depois desse marcador. Pedidos com cidade, município ou universidade explícitos não autorizam busca por nome. Uma continuação simples de mês/cluster pode reutilizar a mesma busca do contexto; uma busca diferente é recusada. O prompt também recebeu exemplos contrastando “de Recife” e “nome contendo Recife”.

A verificação da intenção ocorre antes de consultar os dados, independentemente do acerto do modelo. Novos testes usam um provedor hostil que devolve `busca=Recife` apesar da intenção geográfica, e comprovam que não há leitura do banco. Testes positivos preservam busca por nome e continuidade legítimas. Após esse ajuste, 86 testes IA/RLS passaram, sem pulados. Os parâmetros exatos da avaliação real continuam comparados sem normalização: divergências de metadados permanecem visíveis no relatório.
