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
| `faixa` | novo, só com `metas`. Planejado como `acima_100/entre_50_100/abaixo_50/sem_meta`; implementado como `Literal["meta_atingida","meta_parcial","meta_abaixo","sem_meta"] \| None` (ver decisão 6) |
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

## 2. O que mudou (resultado)

### 2.1 Contrato

| Contrato | Mudança implementada | Compatibilidade |
|---|---|---|
| `PlanoConsulta.ferramenta` | + `explicar`, `perfil_ej`, `metas` | as 21 perguntas anteriores validam sem edição |
| `PlanoConsulta.conceito` | `Literal` com 12 conceitos, default `None` | idem |
| `PlanoConsulta.ordem` | `Literal["desc","asc"] \| None`, default `None` (= desc) | idem |
| `PlanoConsulta.faixa` | `Literal["meta_atingida","meta_parcial","meta_abaixo","sem_meta"] \| None` | idem |
| `PlanoConsulta.esclarecimento` | + `ej` | idem |
| `RespostaRede.serie` | `list[PontoSerie] \| None`, `PontoSerie(mes 1–12, valor)`; só o perfil preenche | campo opcional; o cliente não consegue enviá-lo (`PerguntaRede` só aceita `contexto: PlanoConsulta`) |
| `rede_service.gerar_ranking` | parâmetro `ordem="desc"`; nova `gerar_ranking_com_exclusoes` devolve também a contagem de excluídas | chamadores atuais (`GET /rede/ranking`, testes) inalterados; o comportamento descendente é idêntico |
| `calculo_service` | nova função pura `classificar_faixa_meta(percentual)`; não recalcula o percentual | — |
| `constants.py` | `LIMIAR_META_ATINGIDA = 100.0`, `LIMIAR_META_PARCIAL = 50.0` | — |

`extra="forbid"` e `strict=True` continuam valendo. Nenhum campo representa SQL,
federação, papel ou identidade. Nenhuma migração SQL foi criada.

### 2.2 Ferramentas novas

- **`explicar`** (`app/ia/glossario.py`): 12 verbetes curados de 3 a 6 frases (o que é,
  como é calculado e por que importa), escritos a partir de `docs/regras-de-negocio.md`
  §4, §5 e §6.3 e de `backend/calculos.md`. Faixas de cluster, pesos do SDE, meses do
  ano, fator de escala e limiares de meta são lidos de `constants.py` na montagem do
  texto. O módulo não importa nada de banco e não recebe tenant. Resposta:
  `status="respondida"`, `fonte="glossario"`, sem linhas, com 1 ou 2 sugestões que
  levam ao dado (ex.: depois de SDE, "Qual o SDE da rede?").
- **`ranking` com `ordem="asc"`**: menores valores. Fica fora e é contada, no texto da
  resposta, a EJ sem coleta da métrica no período: sem monitoramento; acumulado de
  faturamento ou colab nulo; todos os `projetos_vendidos_mes` nulos; CSAT sem nenhuma
  nota. Faturamento zero informado entra normalmente.
- **`perfil_ej`**: resolve a `busca` só entre as EJs lidas com o tenant
  (`ler_todas` + `filtrar_por_tenant` + RLS). Nenhuma EJ resulta em "Não encontrei EJ
  com esse nome na sua federação", com o mesmo texto para EJ inexistente e EJ de outra
  federação, e sem repetir o nome digitado. Mais de uma resulta em `esclarecer`
  (motivo `ej`) com até 5 nomes em ordem alfabética; o nome exato desempata.
  Exatamente uma chama `empresa_service.buscar_empresa(sb, id_ej, ano, mes,
  federacao_id)`. As linhas da resposta são:
  - o link ao perfil completo (`id_ej`);
  - faturamento acumulado, % da meta de faturamento e projeção anual;
  - ritmo necessário por mês;
  - cluster oficial e cluster pelo tracking;
  - CSAT médio e projetos no ano;
  - a série mensal de faturamento (`serie`).

  CNPJ, contatos e cidade não saem.
- **`metas`**: distribuição da meta **anual de faturamento** em quatro faixas: ≥100%,
  de 50% a menos de 100%, <50% e sem meta cadastrada. O percentual vem de
  `calcular_percentual_meta`, já aplicado por `listar_empresas`. Com `faixa`, lista as
  EJs daquela faixa e o respectivo % (o filtro de acompanhamento foi implementado). A
  sugestão de acompanhamento é "Quais EJs … estão abaixo de 50% da meta de faturamento?".

### 2.3 Visualização da consulta (frontend)

O frontend não ganhou um "dashboard gerado por IA". O que mudou é a forma de mostrar
os mesmos valores que o backend devolveu. Arquivos novos:
`src/features/assistente/visualizacao.ts` (lógica pura) e `GraficoConsulta.tsx`
(Recharts).

| Resposta | Visualização |
|---|---|
| `ranking` | barras horizontais, no máximo 10 EJs |
| `ritmo_mensal` | barras das 3 categorias |
| `sde` | barras dos 3 cenários, com linha no zero quando há valor negativo |
| `perfil_ej` | linha da série mensal de faturamento; os cartões de indicadores ficam sempre visíveis |
| `metas` (distribuição) | barras das 4 faixas; a lista de uma faixa fica em tabela |
| `indicadores_rede`, `fora_do_zero`, glossário | sem gráfico, como antes |

- Alternância Gráfico/Tabela por botões com `aria-pressed`. A tabela ou os cartões
  anteriores ficam preservados como alternativa, e o gráfico tem `role="img"` com
  descrição textual de todos os valores.
- A cor vem de `var(--color-primary-400)`, a paleta da federação. Com
  `prefers-reduced-motion`, não há animação.
- **Verificação em largura de celular (390 px)** no Chrome sem interface, com página de
  teste e dados sintéticos fora do repositório. A primeira captura mostrou nomes de EJ
  com prefixo comum indistinguíveis e rótulos das faixas de meta sobrepostos. Por isso
  todas as barras passaram a ser horizontais, com o nome acima de cada barra, e a
  unidade (R$) foi para o título. A segunda captura ficou legível. Não foi feita
  navegação autenticada no portal real.

### 2.4 Correção de nome

"Saldo de Desenvolvimento Estratégico" virou **Saldo de Evolução da Rede** em três
lugares: `backend/app/routers/rede.py` (descrição da rota no OpenAPI),
`backend/app/services/calculo_service.py` (docstring) e
`frontend/src/features/indicadores/IndicadoresPage.tsx` (título exibido). Um teste
no backend e outro no frontend impedem a volta da expansão errada.
`CONTEXTO-TCC.md` §4 ainda traz a expansão antiga com `[CONFIRMAR]`; não foi editado
por ser o documento de contexto mantido por Heitor.

## 3. Guardas alteradas

| Guarda | Antes | Depois |
|---|---|---|
| `conceito_local` (nova, `conversa.py`) | — | Pergunta de definição **inteira** ("o que é SDE?", "como é calculado o cluster?", "o que significa fora do zero?") responde com o glossário sem chamar o modelo e sem `reservar_consulta_ia`. "Qual o SDE da rede?" e frases com mais pedidos seguem para o intérprete. Ordem: depois de `referencia_externa`, antes de `ranking_ambiguo`. |
| `busca_com_intencao_de_nome` | Busca só com marcador "nome/contendo/chamada…" ou continuação idêntica | Igual para todas as ferramentas, mais: **só em `perfil_ej`**, aceita o trecho normalizado que aparece como palavra(s) na pergunta, desde que a pergunta não tenha "EJ(s)/empresa(s) júnior(es) de/do/da/em/no/na …". A lista de palavras de localidade passou a cobrir também o singular ("localizada", "sediada"), o que só endurece a regra. |
| `executar_consulta` | `busca` só em `fora_do_zero` | `busca` em `fora_do_zero` e `perfil_ej`; `conceito` só em `explicar`; `faixa` só em `metas`; `ordem="asc"` só em `ranking`; `explicar` com `busca/cluster/criterio/limite` → recusa. Tudo antes de qualquer leitura. |
| `ranking_ambiguo` | — | inalterado ("piores EJs" sem métrica → esclarecer; teste novo) |
| Contexto | `recusar` preserva o contexto anterior | `explicar` também preserva; esclarecimento de EJ guarda o plano como contexto |
| Prompt (`compativel.py`) | proibia ranking de menores valores e perfil de EJ | frases removidas; acrescentados `explicar`, `ordem` (null = maiores), `perfil_ej`, `metas`, exemplos e "use null fora da ferramenta" para os campos novos |

Casos verificados: "Como está a EJ de Recife?" continua recusada, inclusive quando o
modelo hostil devolve `busca="Recife"` ou `busca="EJ de Recife"`. A injeção no
contexto também não muda tenant nem ferramenta: o plano é revalidado, ferramenta
inválida é rejeitada e uma busca diferente da anterior é recusada.

## 4. Decisões tomadas sem consulta

Critério: a opção que menos afrouxa as guardas e menos muda o contrato.

1. **Commits do trabalho pendente.** Foram 3 commits em `feat/painel-admin`. A
   reorganização de pastas e as funcionalidades novas (autenticação própria, Nexo,
   administração) chegaram juntas nos mesmos arquivos novos de `backend/`, então não
   dava para separá-las sem reconstruir estados intermediários.
2. **Arquivos deixados fora do commit**, todos agora no `.gitignore`:
   - `docs/evidencias-nexo/painel-desktop.jpg` e `limite-provedor.jpg`, porque mostram
     ao fundo o perfil de uma EJ com faturamento e CSAT (o AGENTS.md proíbe capturas
     com desempenho individual); `docs/verificacao-nexo-2026-10-04.md` mantém os links;
   - `front_portal_fejepe/.vite/` (cache);
   - `tools/cluster-calculator/tsconfig.app.tsbuildinfo` (artefato de build; a cópia
     antiga, já rastreada, saiu com o renome);
   - `supabase/snippets/` (consulta salva pelo Studio).

   Também foram acrescentados `node_modules/`, `dist/`, caches, `*.log` e `*.tar.gz`.
3. **CNPJ já rastreado.** O comentário em `backend/app/ingestao/contrato.py:80` traz um
   CNPJ de exemplo (`10.279.902/0001-62`) que está no histórico desde `b307dbb`. Não
   reescrevi o histórico; fica o registro.
4. **`frontend/openapi.json` regenerado** a partir da app em cada item. A versão
   versionada estava defasada: faltavam as rotas `/api/v1/auth/*` e os schemas
   `Login`/`Senha`, que entram junto.
5. **Limiares de meta em `constants.py`.** Os valores 100 e 50 vieram do seu pedido;
   não existiam constantes para eles. O glossário e o prompt leem os dois de lá.
6. **Nomes neutros para `faixa`.** Usei `meta_atingida`, `meta_parcial`, `meta_abaixo`
   e `sem_meta` em vez de `acima_100` etc., para o contrato não fixar números que moram
   em `constants.py`.
7. **`explicar` com filtro de dado é recusado.** `busca`, `cluster`, `criterio` e
   `limite` levam a recusa, porque seriam descartados em silêncio. `ano` e `mes` são
   tolerados: não mudam uma definição e costumam vir do contexto.
8. **`explicar` sem `conceito`** leva a `fora_do_catalogo`, com a lista do que o Nexo
   explica, e não a um novo tipo de esclarecimento.
9. **Perfil: casamento sem acento nem caixa**, via `normalizar`, só no `perfil_ej`
   (o `fora_do_zero` mantém `casefold`), e por palavra inteira.
10. **Perfil: qualquer "EJ de/da/em …" sem marcador é recusado**, mesmo que exista EJ
    com esse nome ("EJ de Computação"). Nesses casos o usuário precisa escrever "a EJ
    chamada …". É mais restritivo, mas impede que localidade vire nome.
11. **Perfil: mês omitido** = último mês com monitoramento **daquela EJ** no ano. O
    fluxo de cobertura existente roda com a EJ resolvida.
12. **Perfil sem nome** leva a `esclarecer` (motivo `ej`) **sem opções**. Listar EJs ali
    seria uma consulta nova sem pedido.
13. **"% da meta" com `unidade="numero"`.** Não criei a unidade `percentual`, que
    mudaria o contrato; o símbolo vai no nome da linha.
14. **Ranking ascendente:** EJ sem nenhum monitoramento também conta como excluída. Em
    `desc` nada muda, nem a contagem. A rota `GET /rede/ranking` não ganhou o parâmetro.
15. **Gráfico como modo inicial**, com a tabela a um clique.
16. **Todas as barras horizontais** depois da captura em 390 px. O pedido falava em
    "barras" para ritmo, SDE e metas; horizontais continuam sendo barras e cabem os
    rótulos.
17. **Teste de componente por renderização no servidor.** O frontend não tem jsdom nem
    testing-library, e não acrescentei dependência. O empacotamento usa o esbuild que
    já vem com o Vite e `react-dom/server`. Isso verifica os dois estados da alternância
    (`modoInicial`) e a ausência de gráfico, mas **não executa o clique** num DOM.
18. **Runner.**
    - `parametros_corretos` passa a tratar `ordem=null` e `"desc"` como iguais, e o
      prompt pede `null` para maiores valores, para não penalizar as perguntas antigas.
    - As perguntas de perfil usam o marcador `{EJ EXEMPLO}`, substituído na hora por
      uma EJ do próprio tenant cujo nome é único e passa pelas guardas. O nome real não
      é versionado nem gravado no relatório; só entra na pergunta enviada ao modelo,
      como faria um usuário.
19. **Sugestões padrão** ("faturamento total / ritmo / SDE") não aparecem em `metas`,
    que tem sugestões próprias, nem no glossário.

## 5. Corpus de avaliação

- **As 21 perguntas existentes não foram alteradas.** Nenhuma esperava `recusar` para
  perfil de EJ. "Quais EJs de Recife estão fora do zero?" continua `recusar` e é
  coberta pelos testes. O `git diff` do arquivo só tem inserções.
- **12 perguntas de desenvolvimento novas**, 3 por ferramenta:
  - `explicar`: `explicar-sde`, `explicar-tracking` (as duas atendidas pela guarda
    local) e `explicar-livre` (vai ao modelo);
  - ranking ascendente: `ranking-asc-faturamento`, `ranking-asc-csat` e
    `ranking-asc-projetos`;
  - `perfil_ej`: `perfil-ej`, `perfil-inexistente` e `perfil-continuacao`;
  - `metas`: `metas-distribuicao`, `metas-abaixo` e `metas-sem-meta-cluster`.
- O runner ganhou as métricas `conceito_correto`, `ordem_correta` e `faixa_correta`,
  cada uma calculada sobre os casos da ferramenta correspondente. Elas entram no
  critério de falha.
- **Holdout não criado**, conforme pedido.
- O prompt mudou. As 21 perguntas antigas precisam ser reavaliadas junto com as novas;
  um resultado anterior não vale para o prompt atual.

### Comando para a avaliação real (rede e custo; não executado nesta tarefa)

Com a stack local de pé (`make up`) e `IA_PROVEDOR`, `IA_MODELO` e `IA_API_KEY`
preenchidos em `.env.docker`:

```sh
docker compose --env-file .env.docker up -d backend      # recarrega as variáveis IA_*
read -rs SENHA                                            # senha da conta da federação avaliada
TOKEN=$(SENHA="$SENHA" python3 -c 'import json,os,urllib.request as u;r=u.Request("http://localhost:8080/api/v1/auth/login",json.dumps({"email":"SEU-EMAIL","password":os.environ["SENHA"]}).encode(),{"Content-Type":"application/json"});print(json.load(u.urlopen(r))["access_token"])'); unset SENHA
docker compose --env-file .env.docker exec -e IA_EVAL_TOKEN="$TOKEN" backend \
  python -m app.ia.avaliacao.runner --modelo "ID-DO-MODELO" --saida /tmp/ia-avaliacao.json
docker compose --env-file .env.docker cp backend:/tmp/ia-avaliacao.json "docs/ia-avaliacao-nexo-$(date +%F).json"
unset TOKEN
```

O runner sai com código 1 quando qualquer métrica fica abaixo de 100% ou há erro; o
JSON é salvo mesmo assim. `make ia-eval MODELO=…` continua existindo para rodar no host,
mas exige `DATABASE_DSN`/`AUTH_DATABASE_DSN` apontando para o banco, que o compose não
publica no host.

## 6. Testes e totais

| Execução | Backend (`make test`, PostgreSQL 16 descartável) | Frontend (`node --test`) | Lint, build, calculadora |
|---|---|---|---|
| Linha de base, depois dos commits do trabalho pendente | **584 passaram, 0 falhas, 0 pulados**, 3 avisos | **21 passaram, 0 falhas, 0 pulados** | aprovados |
| Item 1 (glossário) | 633 / 0 / 0 | 22 / 0 / 0 | aprovados |
| Item 2 (visualização) | 638 / 0 / 0 | 30 / 0 / 0 | aprovados |
| Item 3b (ranking asc) | 663 / 0 / 0 | 30 / 0 / 0 | aprovados |
| Item 3a (perfil) | 693 / 0 / 0 | 32 / 0 / 0 | aprovados |
| Item 3c (metas) | 722 / 0 / 0 | 33 / 0 / 0 | aprovados |
| **Final** (corpus e runner) | **726 passaram, 0 falhas, 0 pulados**, 3 avisos | **33 passaram, 0 falhas, 0 pulados** | aprovados |

Os 3 avisos são os mesmos da linha de base (SDK de teste antigo e cache do pytest sem
permissão de escrita no container).

Arquivos de teste do Nexo hoje: `test_ia.py` 72, `test_ia_ampliacao.py` 77 (novo),
`test_ia_glossario.py` 49 (novo), `test_ia_rls.py` 31 (antes 15 casos),
`test_ia_limites.py` 26. No frontend, `scripts/test-nexo.mjs` tem 12 testes (novo).

Cobertura dos testes pedidos:

- **Contrato:** cada ferramenta nova tem teste com provedor falso. Valores fora do
  `Literal` (`conceito`, `ordem`, `faixa`, `esclarecimento`) e campos extras são
  rejeitados.
- **Isolamento em PostgreSQL real, com e sem o filtro Python:**
  - perfil de EJ de outra federação pelo nome responde igual ao de EJ inexistente;
  - um nome que só existe em MG não aparece nas opções de esclarecimento;
  - o perfil do próprio tenant resolve uma EJ só, embora o trecho também esteja no
    nome da EJ de MG;
  - ranking `asc` só lista e só conta como excluídas EJs do tenant;
  - `metas` só conta EJs do tenant; a EJ de MG não tem meta e apareceria em "sem meta"
    se vazasse.
- **Glossário:** `explicar` não abre consulta ao banco (`Mock` sem `table`/`rpc`), não
  chama o modelo e não reserva no limitador. Todo número do texto pertence às
  constantes, e trocar as constantes muda o texto. O módulo só importa
  `collections.abc`, `app.models.ia` e `app.utils`.
- **Guardas:** "Como está a EJ de Recife?" é recusada, e a injeção no contexto não
  muda tenant nem ferramenta.
- **Frontend:** a alternância gráfico/tabela é testada nos dois modos, e não há gráfico
  em `indicadores_rede` nem em `fora_do_zero`; o perfil e as metas também têm teste.

## 7. Limitações e o que ficou de fora

- **Sem avaliação com modelo real.** Acerto de interpretação das ferramentas novas e
  efeito do prompt novo nas perguntas antigas são desconhecidos.
- Só **meta de faturamento** em `metas`; CSAT, engajamento, taxa de colaboração e
  projetos de impacto ficam fora, e o prompt manda recusar.
- No perfil, uma pergunta como "como está a Fulano de Recife?" pode virar
  `busca="Fulano"` e descartar "de Recife", porque a guarda só detecta localidade
  quando ela vem depois de "EJ". Resolver isso exigiria interpretar nomes próprios com
  "de", que são comuns.
- Se o nome completo de uma EJ estiver contido no de outra, o nome exato desempata.
  Sem nome exato, a opção de esclarecimento pode levar de novo à mesma lista.
- O clique da alternância não é exercitado num DOM real (decisão 17). A largura de
  celular foi conferida em página de teste com dados sintéticos, não no portal com
  login.
- A série do perfil é fixa (faturamento do mês no ano consultado). O ADR-005 continua
  correto ao dizer que não há "série temporal livre".
- As perguntas de perfil do corpus dependem da EJ escolhida na hora; resultados só são
  comparáveis no mesmo banco.
- Dashboards gerados por IA e créditos continuam inativos; nada foi reativado.
- Não houve push, deploy, migração, alteração da monografia ou de `relatorio-tcc-empresa/`.

## 8. Commits

Trabalho pendente em `feat/painel-admin`, sem push:

| Hash | Mensagem |
|---|---|
| `c8da3d1` | refactor: reorganiza pastas backend/frontend/tools e consolida código de out–nov/2026 |
| `24b562b` | feat(infra): execução em Docker com PostgreSQL próprio |
| `84e0e40` | docs: relatórios, ADRs 003–008 e estado de outubro–novembro/2026 |

Branch `feat/nexo-ampliacao`, criada a partir de `84e0e40`:

| Hash | Mensagem |
|---|---|
| `bf46f27` | feat(ia): Nexo explica os indicadores com glossário curado |
| `5ce7596` | feat(ia): visualização da consulta no Nexo com alternância gráfico/tabela |
| `e3eae1e` | feat(ia): ranking dos menores valores no Nexo |
| `8d4c48f` | feat(ia): perfil de uma EJ no Nexo (ferramenta perfil_ej) |
| `3a66c03` | feat(ia): atingimento da meta de faturamento da rede no Nexo (ferramenta metas) |
| `c6dad98` | test(ia): perguntas de desenvolvimento das ferramentas novas e runner |
| (este relatório) | docs(ia): relatório da ampliação do Nexo e estado do portal |
