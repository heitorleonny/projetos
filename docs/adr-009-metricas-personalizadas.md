# ADR-009 — Painel de métricas personalizadas

Data: 12/11/2026. Status: implementado e verificado localmente. A avaliação da
interpretação com modelo real está pendente.

Plano de origem: [plano-metricas-personalizadas-2026-11-12.md](plano-metricas-personalizadas-2026-11-12.md).

## Problema

Administradores querem acompanhar recortes que o portal não oferece, como "top 10
EJs que mais faturaram em outubro e novembro" ou uma métrica própria, por exemplo
"faturamento × CSAT × projetos". Precisam criá-las digitando, ver tudo num painel e
retirar o que não serve mais. A retomada de 23/10 tirou do escopo a geração de
dashboards por IA, isto é, código React gerado, publicação e fila. Este pedido não
pode reabrir aquela superfície.

## Decisões de Heitor (12/11/2026)

| # | Decisão |
|---|---|
| D1 | A feature entra no TCC. |
| D2 | Todos os usuários da federação veem o painel; só `admin` cria, altera e remove. **Ampliado em 13/11:** o admin master (`plataforma`) também gere, só na federação vinculada à própria conta (migração 28). |
| D3 | Os exemplos do pedido são só exemplos: o motor é genérico. |
| D4 | CSAT é um **valor único** da EJ, nunca média de meses. Implementado como "último CSAT registrado até o fim do período" `[CONFIRMAR]`. |
| D5 | Projetos em duas variáveis: `projetos_vendidos` (soma no período) e `projetos_totais` (acumulado). |
| D6 | Só 2026 (`settings.ANO_DEFAULT`), com período dentro de um único ano. |
| D7 | Mês sem dado não é trocado em silêncio. A EJ sem todos os meses do período sai do cálculo e é contada. |
| D8 | Métrica personalizada é marcada como tal e nunca altera cluster, SDE ou tracking. |
| D9 | "Tirar do painel" é diferente de "arquivar". Excluir de vez só vale para métrica arquivada. |
| Arq. | Opção B: módulo próprio, sem mexer no contrato nem no prompt do Lamps. |

## Decisão técnica

**A métrica é dado, não código.** A definição é JSON: expressão, período,
cluster, visual, ordem, limite e agregação. A expressão usa só as variáveis de
um catálogo fechado (`app/metricas/catalogo.py`) e é analisada por um parser
próprio de descida recursiva (`app/metricas/expressao.py`), sem `eval` e sem SQL
dinâmico. A gramática tem só `+ − × ÷`, parênteses, números e variáveis, com
limites de 300 caracteres, 60 elementos e 12 níveis de parênteses. Divisão por
zero e valor ausente deixam a EJ "sem valor", nunca zero.

**O cálculo é puro.** `app/metricas/avaliacao.py` e
`app/services/metricas_service.py` leem `empresa_junior` (com filtro de tenant),
`monitoramento`, `metas` e `cluster_historico` com o cliente da requisição, e
calculam em memória. O volume é pequeno: cerca de 16,5 mil linhas de
monitoramento em 2026 na base local inteira.

**O texto livre segue o padrão do Lamps** (ADR-005), com contrato e prompt
próprios (`app/ia/metricas_interprete.py`):

1. O backend recusa uma referência a outra federação antes de chamar o modelo.
2. A reserva por minuto é a mesma do Lamps (`reservar_consulta_ia`) e falha fechada.
3. O modelo devolve um `PlanoMetrica` fechado (JSON Schema estrito). Ele não
   escolhe tenant e não escreve texto exibido ao usuário. O ano citado é
   conferido pelo backend.
4. A expressão proposta passa pelo mesmo parser. Se falhar, a resposta é uma
   recusa com texto fixo.
5. A resposta é uma **proposta com prévia calculada pelo portal**. Nada é salvo
   sem o clique do admin, que pode ajustar a proposta no construtor manual.

O construtor manual funciona sem provedor de IA configurado.

## Persistência e isolamento

A migração `27-metricas-personalizadas.sql` é aditiva e cria
`metrica_personalizada` com RLS forçada:

- leitura: `federacao_id` do claim, para qualquer papel;
- escrita: tenant do claim **e** `pode_gerir_metricas()` (migração 28), que lê do
  banco se quem chama é `admin` ou `plataforma` ativo vinculado àquela federação;
  a autoria é igual a `auth.uid()`;
- exclusão: apenas de métrica com `arquivada_em` preenchido;
- GRANT por coluna: tenant, autoria, versão e datas não são editáveis pelo
  cliente; um trigger define a versão (sobe quando a definição muda), as datas e
  o teto de 50 métricas ativas;
- o nome é único entre as métricas ativas da federação.

O router (`app/routers/metricas.py`) confere o papel no banco
(`usuario_atual()`) antes de cada escrita. A política repete a regra.

## Alternativas rejeitadas

- **Estender o Lamps**: obrigaria a refazer a avaliação com modelo real, não
  persiste nada e atende todos os membros, não só admins.
- **IA gerando SQL ou código**: contraria a regra 3 do AGENTS e é o escopo retirado em 23/10.
- **Média dos meses para o CSAT**: rejeitada por Heitor (D4).

## Limites conhecidos

- A qualidade da interpretação em texto livre não foi medida com modelo real.
  Use `python -m app.ia.avaliacao.metricas` (20 casos, 6 adversariais). Uma
  execução contra um endpoint local de regras escritas à mão só mostrou que o
  avaliador funciona; não é resultado de modelo.
- A janela por minuto é compartilhada com o Lamps e não existe orçamento mensal.
- Período só dentro de 2026. Não há janela entre anos, fórmula condicional, filtro
  por cidade ou universidade, alertas ou exportação.
- A série mensal soma ou faz a média das EJs com dado em cada mês. O número de
  EJs pode variar de um mês para outro e aparece na dica do gráfico.
- A interpretação do D4 ("último CSAT registrado") precisa ser confirmada contra a
  regra do movimento `[CONFIRMAR]`. Na base local, CSAT varia mês a mês para várias EJs.
