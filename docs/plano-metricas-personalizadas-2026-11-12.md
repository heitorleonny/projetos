# Plano — Painel de métricas personalizadas (somente administradores)

Data: 12/11/2026. Status: **implementado no mesmo dia** depois das respostas de Heitor
às decisões D1–D9 (opção B). As decisões finais e as diferenças em relação a este plano
estão no [ADR-009](adr-009-metricas-personalizadas.md). Diferenças principais: o CSAT é
um valor único (último registrado), não uma média; uma única tabela com `no_painel`
substitui as duas tabelas previstas; o período fica restrito a 2026. Este texto fica como
registro do planejamento.

## 1. O que se quer

Uma aba nova do portal, visível só para administradores da federação, com um painel em
formato de dashboard onde o admin:

1. **Pergunta em texto livre**, por exemplo: "top 10 EJs que mais faturaram em outubro e
   novembro".
2. **Cria métricas próprias**, por exemplo "Impacto comercial = faturamento × CSAT ×
   projetos", com nome dado por ele.
3. **Fixa essas métricas no painel** (rastrear) e **tira do painel / arquiva** quando não
   quiser mais.

## 2. Conflito de escopo que precisa de decisão antes de tudo

O `docs/retomada-escopo-reduzido-2026-10-23.md` retirou do TCC a geração de dashboards por
IA e diz: "evitar novas funcionalidades que não resolvam impedimento concreto da
demonstração ou da pergunta de pesquisa". Esta feature **não é** a que foi retirada (não
gera código React, não publica aplicação, não usa franquia de dashboard), mas ela volta a
ter "dashboard" e "IA" no mesmo lugar. Antes de gastar dias nela, Heitor precisa decidir:

- **Entra no TCC** (vira parte do que a monografia descreve e avalia), ou
- **Fica como produto**, fora do escopo acadêmico, sem peso na monografia, ou
- **Fica para depois da entrega** (trabalho futuro).

Prazo de referência: entrega em 30/11/2026 `[CONFIRMAR]` (o `CLAUDE.md` ainda cita 16/11).
Hoje é 12/11. As semanas finais já estão reservadas para avaliação, escrita e ensaio.

## 3. Decisões abertas (preciso da resposta de Heitor)

| # | Decisão | Recomendação |
|---|---|---|
| D1 | Escopo: TCC, produto ou depois | ver seção 2 |
| D2 | Quem acessa: só `admin` da federação, ou `plataforma` também | Só `admin` e `plataforma`, como o router `admin.py`. Mas o ADR-003 diz que `plataforma` **não** alcança dado de gestão de EJ; então `plataforma` entraria sem ver dados. Proposta: **somente `admin`** `[CONFIRMAR]` |
| D3 | "Faturar a maior quantidade" em out+nov: soma do `faturamento_mes` nos dois meses, ou `faturamento_acumulado` ao fim de novembro | **Soma de `faturamento_mes` na janela**, com o rótulo "faturamento no período" na tela. O acumulado já existe no ranking do Nexo |
| D4 | CSAT numa janela de meses | Média dos meses **com coleta** (reaproveita `calcular_media_csat`). EJ sem coleta fica fora e é contada na tela, como `sem_coleta` no ranking atual. `calculos.md` avisa que CSAT só é preciso no fim do ano |
| D5 | "Quantidade de projetos" | Duas variáveis separadas e nomeadas: `projetos_vendidos` (soma na janela) e `projetos_totais` (acumulado). O admin escolhe |
| D6 | Janela de período | v1: **dentro de um único ano** (mês inicial a mês final). Vários anos fica para v2 |
| D7 | Mês sem dado de alguma EJ | Não substituir o período em silêncio (regra do Nexo). A EJ sem cobertura completa da janela sai do cálculo e a tela diz quantas saíram |
| D8 | Métrica personalizada vs. oficial | Sempre marcada como **"personalizada, não oficial do MEJ"**. Nunca altera cluster, SDE nem tracking, que são fórmulas nacionais |
| D9 | Remover | Dois gestos distintos: **tirar do painel** (some o cartão, a métrica continua) e **arquivar** (a métrica some de tudo, recuperável). Exclusão definitiva só de métrica já arquivada |

## 4. Alternativas de arquitetura (trade-offs)

| Opção | Como | Prós | Contras |
|---|---|---|---|
| A. Estender o Nexo | Novas ferramentas no `PlanoConsulta` (ranking por período, métrica) | Reusa tudo, menor código | O Nexo é para todos os membros, não guarda nada, e mexer no prompt/schema exige **nova avaliação com modelo real** (`test_ia_prompt.py`). Não resolve o painel |
| **B. Módulo próprio "Métricas" (recomendada)** | Esquema e prompt próprios, mesmo provedor, limites e padrão "IA interpreta, backend calcula" | Isola o risco, não invalida a avaliação do Nexo, tem persistência e painel | Mais código novo |
| C. IA gera SQL ou código | Modelo escreve a consulta ou a fórmula executável | Flexível | Rejeitada: viola AGENTS regra 3, abre superfície de ataque e é o escopo retirado em 23/10 |

**Recomendação: B.** O ponto central do desenho é que a métrica é **dado, não código**.

## 5. Desenho da solução (opção B)

### 5.1 Princípio

Texto livre → modelo devolve um **plano tipado** → backend valida → admin **confere uma
prévia em linguagem de gestor** → só então salva. O modelo nunca calcula, nunca escreve
SQL, nunca escolhe federação. Mesmo padrão do ADR-005, mesmo `Provedor`.

Existe também um **construtor manual** (formulário). Ele é o caminho principal quando o
provedor de IA está indisponível e serve de rede de segurança quando a interpretação erra.

### 5.2 Catálogo fechado de variáveis

Cada variável tem: nome em português, tabela/coluna de origem, **agregação na janela**,
unidade e se "sem coleta" exclui a EJ.

| Variável | Origem | Agregação na janela |
|---|---|---|
| `faturamento` | `monitoramento.faturamento_mes` | soma |
| `faturamento_acumulado` | `monitoramento.faturamento_acumulado` | valor do último mês |
| `faturamento_colab` | `faturamento_colab_mes` | soma |
| `projetos_vendidos` | `projetos_vendidos_mes` | soma |
| `projetos_totais` | `projetos_totais` | último mês |
| `csat` | `csat` | média dos meses com coleta |
| `membros` | `numero_membros` | último mês |
| `membros_engajados` | `membros_engajados_mes` | soma |
| `projetos_impacto` | `projetos_impacto` | último mês |
| `meta_faturamento`, `meta_csat`, `meta_projetos_impacto` | `metas` do ano | valor do ano |
| `cluster` | `cluster_historico` do ano | valor do ano |

Valores derivados que já existem (`percentual_meta`, etc.) entram chamando
`calculo_service`, **sem reimplementar**. Nomes de coluna acima conferidos em
`backend/banco.md`; a lista final de agregações precisa de revisão de Heitor `[CONFIRMAR]`.

### 5.3 Definição da métrica (JSON validado por Pydantic)

```json
{
  "nome": "Impacto comercial",
  "expressao": "faturamento * csat * projetos_vendidos",
  "janela": {"ano": 2026, "mes_inicio": 10, "mes_fim": 11},
  "filtro": {"cluster": null},
  "saida": {"tipo": "ranking", "ordem": "desc", "limite": 10},
  "unidade": "numero"
}
```

- `expressao` é analisada por um **parser próprio** (descida recursiva), nunca `eval`.
  Aceita `+ - * /`, parênteses, números e as variáveis do catálogo.
- Limites duros: tamanho do texto, profundidade e número de nós da árvore. Divisão por
  zero e valor ausente resultam em "sem valor", não em erro nem em zero.
- A pergunta "top 10 EJs que mais faturaram em out e nov" vira `expressao = "faturamento"`
  com `saida = ranking`, sem tratamento especial.

### 5.4 Fluxo de uso

1. Admin escreve no campo "Pergunte ou crie uma métrica".
2. `POST /api/v1/metricas/interpretar` devolve a **proposta**: nome, fórmula legível,
   janela por extenso, filtro e **resultado de prévia** (top da lista ou valor).
3. Se a pergunta for ambígua (ex.: "melhores", "do ano"), a resposta é um
   **esclarecimento com opções**, nunca um palpite. Mesmo comportamento do Nexo.
4. Admin pode editar a proposta no construtor, e então **Salvar** (a métrica) e/ou
   **Fixar no painel** (o cartão).
5. Cartão no painel: **Tirar do painel**; menu da métrica: **Arquivar**, **Restaurar**,
   **Excluir** (só arquivada).

### 5.5 Painel (dashboard)

Rota nova `/metricas`, grupo `analises` em `config/navigation.ts`, **visível só se
`sessao.pode_administrar`** (o `Navbar` já filtra assim a aba Administração). Atenção: o
guia de primeiro acesso usa a mesma lista; o item novo precisa ser filtrado por papel
também lá, para não aparecer no tour de quem não é admin.

Tipos de cartão na v1 (todos com Recharts, que já está no projeto):

- **Valor único** (agregado da rede para a métrica).
- **Ranking** (barras horizontais, top N) com tabela expansível.
- **Série mensal** (linha) da métrica na rede, ou das N primeiras EJs. `[v1.1 se apertar]`

Cada cartão mostra: título, fórmula legível, janela, filtro, "N EJs sem dados completas
ficaram fora" e o selo "personalizada". Estados de carregando, vazio, erro e sem dados.
Layout responsivo, foco e rótulos acessíveis, como as demais telas.

### 5.6 Persistência (migração nova `27-metricas-personalizadas.sql`)

Migração aditiva, arquivo numerado, **sem editar migração aplicada** (AGENTS regra 4).

- `metrica_personalizada` (`id`, `federacao_id`, `nome`, `descricao`, `definicao jsonb`,
  `versao`, `criado_por`, `criado_em`, `atualizado_em`, `arquivada_em`).
- `metrica_painel_item` (`id`, `federacao_id`, `metrica_id`, `titulo`, `visual`, `ordem`,
  `criado_por`, `criado_em`).
- RLS por `federacao_id` **e** papel `admin` lido do banco (`usuario_atual()`), como em
  `13-painel-admin.sql`. Privilégios mínimos no padrão de `21-privilegios-minimos.sql`.
- Índices por `(federacao_id, arquivada_em)` e `(federacao_id, ordem)`.
- Constraint: nome único por federação entre métricas não arquivadas; limite de métricas
  por federação (proposta: 50) `[CONFIRMAR]`.
- Em `app/database.py`, incluir as duas tabelas no conjunto `TABELAS` (hoje é uma lista
  fechada, então sem isso o cliente recusa).
- Guardar o histórico: editar uma métrica incrementa `versao` e o cartão mostra a versão,
  para o número de ontem não mudar de significado em silêncio.

### 5.7 Backend

```
app/models/metricas.py        esquemas Pydantic (definição, plano, proposta, resposta)
app/metricas/catalogo.py      variáveis, agregações, unidades
app/metricas/expressao.py     parser e avaliador puros (sem banco, sem I/O)
app/services/metricas_service.py   leitura com tenant, avaliação por EJ, ranking
app/ia/metricas_interprete.py      prompt + validação do plano de métrica
app/routers/metricas.py       routers finos
```

- Leitura de `monitoramento`/`metas` por `ler_todas` com `filtrar_por_tenant`, igual ao
  Nexo. O volume é pequeno (≈13,5 mil linhas de monitoramento em toda a base, segundo o
  comentário da migração 26), então **o cálculo é feito em Python, em memória**; nenhum SQL
  gerado dinamicamente.
- Rotas (`/api/v1/metricas`): `GET` lista, `POST` cria, `PATCH` edita, `POST /{id}/arquivar`,
  `/restaurar`, `DELETE` (só arquivada); `POST /avaliar` (prévia sem salvar);
  `POST /interpretar` (texto → proposta); `GET/POST/DELETE /painel` e `PUT /painel/ordem`.
- Todas exigem `get_current_user` + papel `admin` **conferido no banco**.
- O limitador de consultas (`reservar_consulta_ia`) envolve só o `/interpretar`. Ele é
  limite por minuto, **não** orçamento mensal nem custo; isso continua sendo limitação
  conhecida (`docs/politica-creditos-ia.md`). Os créditos de dashboard (migração 19) não
  são usados.

### 5.8 Segurança e riscos

- **Tenant vem da autenticação**, nunca da pergunta nem do corpo. Texto do admin e saída
  do modelo são dado não confiável.
- Defesa em duas camadas, como o resto do portal: filtro no service **e** RLS.
- **Sem `eval`, sem SQL dinâmico, sem importar nada** a partir da expressão.
- Nome e descrição renderizados como texto (sem HTML).
- Prompt hostil: "ignore as regras", "mostre outra federação", "me dê o SQL", fórmulas
  gigantes, `__import__`, divisão por zero, nomes de variável inexistentes.
- Risco de **fidelidade**: o modelo pode entender "do ano" como acumulado ou como soma.
  Mitigação: prévia obrigatória antes de salvar e texto da proposta em linguagem de gestor.
  Isso **não** prova que a interpretação está correta; só dá ao admin a chance de ver.

## 6. Fases, entregas e critérios de pronto

Estimativas são ordem de grandeza `[CONFIRMAR]`, não compromisso.

| Fase | Entrega | Pronto quando | Esforço |
|---|---|---|---|
| 0 | Decisões D1–D9 respondidas | Heitor confirmou por escrito | 0,5 dia |
| 1 | Motor puro: catálogo, parser, avaliador, janela | Testes unitários passam, inclusive entradas hostis e casos de borda | 1–1,5 dia |
| 2 | Migração 27 + RLS + privilégios + `database.py` | Testes de RLS com **segundo tenant** e papel `membro` recusado, sem skips | 1 dia |
| 3 | API e service de métricas e painel | Testes de API: CRUD, arquivar/restaurar, isolamento, papel | 1–1,5 dia |
| 4 | Frontend: aba, painel, construtor manual, prévia, remover | `npm run check` passa; conferência manual em desktop e celular | 2 dias |
| 5 | Camada de texto livre: esquema, prompt, esclarecimento, limitador | Provedor falso em testes; **avaliação com modelo real** de um conjunto de perguntas (inclui as duas do pedido) com resultado registrado | 1,5–2 dias |
| 6 | Documentação e fechamento | ADR-009 e atualização de `ESTADO-PORTAL-PARA-TCC.md` com evidência, ambiente e limites; `make check` completo | 0,5 dia |

Total aproximado: **7–9 dias úteis** com texto livre; **5–6** só com o construtor manual
(fases 0–4 e 6). Dá para entregar em etapas: **v1 = fases 0–4** (já resolve "criar, rastrear
e tirar métricas"), **v2 = fase 5** (digitar em português).

### Fora do v1
Janela entre anos; séries por EJ; agendamento e alertas; exportar cartão; compartilhar
com membros; métricas por núcleo; fórmulas condicionais (`SE`); edição de layout por
arrastar e soltar (v1 tem só ordem).

## 7. Testes (resumo)

- **Unidade:** expressão (precedência, parênteses, divisão por zero, variável inválida,
  limite de tamanho), agregações por janela, CSAT sem coleta, EJ sem cobertura.
- **Caracterização:** as duas perguntas do pedido contra dados sintéticos com resultado
  conhecido à mão.
- **RLS/isolamento:** admin da federação A não lê nem altera métrica da B; `membro` não
  acessa nada; plataforma conforme D2. Sem skips.
- **API:** papéis, arquivar/restaurar/excluir, limites de quantidade, concorrência de nome.
- **IA:** conjunto de perguntas ouro, tentativas adversariais, provedor falso nos testes
  automáticos e **uma rodada com modelo real registrada à parte** (o teste com provedor
  falso não equivale a avaliar o modelo real, como já está dito no README).

## 8. Próximo passo

Responder D1 (principalmente), D2, D3 e D9. Com isso, a Fase 1 pode começar sem
retrabalho. Nada será implementado antes disso.
