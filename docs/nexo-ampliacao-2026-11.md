# Nexo — ampliação de novembro/2026: glossário, visualização da consulta e novas consultas

- Data: 07/11/2026 (America/Recife)
- Branch: `feat/nexo-ampliacao`, criada a partir de `84e0e40` (`feat/painel-admin`)
- Escopo: pedido de Heitor de 07/11/2026. Não altera fórmulas, migrações, monografia
  nem os módulos inativos de dashboards/créditos.
- Estado: implementado e verificado localmente por testes com provedor falso.
  **Avaliação com modelo real pendente** (não executada nesta tarefa).

## 1. Plano (escrito antes da implementação)

### 1.1 Contrato `PlanoConsulta` (`backend/app/models/ia.py`)

Todos os campos novos são opcionais com `default=None`, para que as 21 perguntas do
gabarito continuem válidas sem edição. `extra="forbid"` e `strict=True` permanecem.

| Campo | Mudança |
|---|---|
| `ferramenta` | `Literal` ganha `explicar`, `perfil_ej` e `metas` |
| `conceito` | novo: `Literal["fora_do_zero","ritmo","cluster","sde","taxa_colaboracao","faturamento_colaborativo","csat","engajamento","tracking_cluster","projecao_anual","ritmo_necessario","meta_atingida"] \| None` |
| `ordem` | novo: `Literal["desc","asc"] \| None` (None = desc) |
| `faixa` | novo: `Literal["acima_100","entre_50_100","abaixo_50","sem_meta"] \| None`, só com `metas` |
| `esclarecimento` | `Literal` ganha `ej` (EJ ambígua) |

Coerência verificada no backend, antes de qualquer leitura (`ferramentas.py`):
`conceito` só com `explicar`; `faixa` só com `metas`; `ordem="asc"` só com `ranking`;
`busca` só com `fora_do_zero` e `perfil_ej`. Combinação fora disso → `fora_do_catalogo`,
nunca descarte silencioso do requisito.

### 1.2 Contrato `RespostaRede`

- `serie: list[PontoSerie] | None = None`, com `PontoSerie(mes: int 1–12, valor: float)`.
  Preenchido só pelo backend em `perfil_ej` (faturamento do mês).
- Nenhum outro campo novo. `fonte="glossario"` para o glossário.

### 1.3 Guardas (`backend/app/ia/conversa.py` e `assistente.py`)

1. Nova guarda local `conceito_local(pergunta)`: reconhece só perguntas de definição
   inteiras ("o que é SDE?", "como é calculado o cluster?", "o que significa fora do
   zero?"). Responde com o glossário sem chamar o modelo e sem reservar no limitador.
   Roda depois de `referencia_externa` e antes de `ranking_ambiguo`. O que não casa por
   inteiro segue para o intérprete.
2. `busca_com_intencao_de_nome` passa a aceitar, **somente para `perfil_ej`**, o trecho
   normalizado que aparece literalmente na pergunta. Recusa mantida quando há
   cidade/município/universidade/localizada/sediada, e também quando o trecho vem logo
   depois de "EJ de/da/do/em/no/na" (forma de localidade, como "a EJ de Recife").
   Para as outras ferramentas, a regra do marcador ("nome/contendo/chamada") não muda.
3. `ranking_ambiguo` não muda ("piores EJs" sem métrica continua em `esclarecer`).
4. Contexto: `explicar` não substitui o contexto anterior (como `recusar`).

### 1.4 Arquivos

- Backend: `models/ia.py`, `ia/conversa.py`, `ia/assistente.py`, `ia/ferramentas.py`,
  `ia/glossario.py` (novo), `ia/adaptadores/compativel.py` (prompt),
  `services/rede_service.py` (`ordem` no ranking), `services/calculo_service.py`
  (função pura de faixa de meta), `utils/constants.py` (limiares das faixas de meta),
  `ia/avaliacao/perguntas.json` e `runner.py`.
- Correção de nome: "Saldo de Desenvolvimento Estratégico" → **Saldo de Evolução da Rede**
  em `routers/rede.py`, `calculo_service.py` e `frontend/.../IndicadoresPage.tsx`.
- Frontend: `assistenteService.ts`, `ResultadoConsulta.tsx`, `GraficoConsulta.tsx` e
  `visualizacao.ts` (novos), `openapi.json` regenerado, testes em `scripts/`.
- Testes: `tests/test_ia.py`, `tests/test_ia_glossario.py` (novo),
  `tests/test_ia_ampliacao.py` (novo), `tests/test_ia_rls.py`.

### 1.5 Ordem de execução

Itens 1 → 2 → 3b → 3a → 3c, cada um com `make check` verde e commit próprio.
O campo `serie` (item 2) é declarado no contrato no item 2 e preenchido no item 3a.
