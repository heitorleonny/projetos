# CLAUDE.md — camada de TCC

**Leia o `AGENTS.md` primeiro.** Ele descreve o produto, o monorepo, a stack, as
convenções e as pendências de segurança, e continua valendo integralmente. Cada
subprojeto tem o seu (`portal_fejepe/AGENTS.md`, `front_portal_fejepe/AGENTS.md`).

Este arquivo acrescenta só o que o `AGENTS.md` não cobre: o trabalho acadêmico que
está sendo construído sobre este repositório, e as regras que vêm dele.

---

## O trabalho

Trabalho de Conclusão de Curso — Bacharelado em Sistemas de Informação, UFRPE,
**Trilha Graduação-Tecnologia**. Entrega em **16 de novembro de 2026**.

**Pergunta de pesquisa:** é possível antecipar, a partir da série histórica de
indicadores padronizados do MEJ, quais EJs entrarão em situação de risco no período
seguinte, com desempenho superior à regra de acompanhamento que a federação usa hoje?

Duas frentes, nesta ordem de prioridade:

1. **Detecção antecipada de risco** — o que responde à pergunta de pesquisa e é o que
   a banca avalia.
2. **Automação da ingestão e do cálculo dos indicadores** — engenharia habilitadora.
   Se o prazo apertar, esta pode ser entregue parcialmente; a primeira não.

> O roadmap de SaaS multi-tenant descrito no `AGENTS.md` **saiu do escopo do TCC** e
> passou a constar como trabalho futuro. Continua sendo a direção do produto — só não
> é mais o objeto da pesquisa. Não proponha trabalho de multi-tenancy como parte do
> TCC sem eu pedir.

---

## O que os dados permitem (verificado no schema, set/2026)

Isto restringe o desenho do modelo mais do que qualquer outra coisa. Antes de propor
qualquer abordagem, releia esta seção.

- **`monitoramento` é mensal** (`id_ej`, `ano`, `mes`). É a única série com
  granularidade fina — e portanto a base natural de observações.
- **`metas` é anual** por EJ.
- **O cluster é anual**, em colunas `cluster_2023`…`cluster_2026`
  (`app/utils/cluster.py`). São no máximo **3 transições ano-a-ano por EJ** em todo
  o histórico.

**Consequência para o rótulo de risco:** um rótulo baseado em queda de cluster produz
poucas dezenas de eventos no histórico inteiro — provavelmente pouco para treinar.
Um rótulo de horizonte mensal, derivável de `monitoramento` (por exemplo, ausência de
vendas ou faturamento acumulado descolado da meta ao longo dos próximos meses), gera
uma ordem de grandeza a mais de observações rotuladas.

Antes de escolher, **meça**: quantas EJs, quantos meses de série contínua, quantos
casos positivos cada definição candidata produz. Se as duas opções forem viáveis,
prefira a que tiver mais aderência às regras oficiais do movimento — mas não escolha
uma definição que não tenha eventos suficientes só porque ela é mais elegante.

---

## Regras de modelagem (não negociáveis)

Estas não são preferências de estilo. Violar qualquer uma invalida o resultado do
TCC, mesmo que o código rode.

- A divisão treino/teste é **temporal**, nunca aleatória: treino nos períodos mais
  antigos, teste nos mais recentes, sem embaralhar.
- **Nenhuma feature pode conter informação posterior** ao período da linha. Atenção
  redobrada com `faturamento_acumulado` e com a pontuação de cluster anualizada, que
  são cumulativos por construção.
- **Acurácia não é métrica de avaliação** — as classes são desbalanceadas. Use
  precisão, revocação, F1 e AUC-PR.
- Todo modelo é comparado contra a **regra-baseline que a federação usa hoje**,
  implementada em código e medida sobre exatamente os mesmos dados e métricas.
- O volume é pequeno. **Modelos simples e interpretáveis** — regressão logística,
  árvore, gradient boosting raso. Nada de deep learning.
- Todo alerta precisa vir com **explicação em linguagem de gestor** ("faturamento 40%
  abaixo da meta e sem vendas há 2 meses"), nunca em nome de variável.
- **Resultado negativo é resultado.** Se o modelo não superar o baseline, reporte.
  Não ajuste o rótulo nem o ponto de corte até a métrica ficar bonita.

---

## Regras de trabalho adicionais

- As fórmulas do movimento (cluster, SDE, ritmo, fórmula adaptativa) são **nacionais**,
  não da FEJEPE. Fonte de verdade: `portal_fejepe/calculos.md` e
  `app/utils/constants.py`. Não invente faixa nem peso — se a regra não estiver
  documentada, pare e pergunte.
- Reaproveite `app/services/calculo_service.py` em vez de reimplementar cálculo para
  a modelagem. Se precisar de uma variante, extraia uma função pura e teste as duas.
- Código novo de modelagem fica separado da API — não misture notebook e router.
- Não altere dados de produção. Qualquer migração destrutiva, pergunte antes.

## Como falar comigo

- Responda em **português do Brasil**.
- Marque com `[CONFIRMAR]` qualquer número, nome ou regra que você não verificou
  direto na fonte.
- Quando uma decisão tiver trade-off, apresente as opções com prós e contras em vez de
  escolher em silêncio.
- Não comece a implementar antes de eu confirmar o escopo da tarefa.

## Documentos do TCC

Ficam em `~/Documents/TCC`, fora deste repositório:

- `replanejamento/replanejamento-tcc.md` — plano atual, objetivos, riscos, cronograma
- `replanejamento/claude-code-bootstrap.md` — prompts de partida
- `validacao/roteiro-validacao.md` — instrumento de validação com usuários
- `monografia/` — o texto em LaTeX (ABNTeX2). **Não edite nada aí sem eu pedir.**
