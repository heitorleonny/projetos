# 📖 Documentação da API — Portal FEJEPE

## Visão Geral

A API do Portal FEJEPE segue a arquitetura REST e é construída com FastAPI.
Todos os cálculos estratégicos são centralizados no backend (Python),
conforme diretriz documentada em `estrutura.md`.

**Base URL:** `http://localhost:8000`

## Autenticação

> ⚠️ Fase atual: sem autenticação. Preparado para receber middleware de API Key.

## Versionamento

Todos os endpoints usam o prefixo `/api/v1/` para permitir evolução sem quebrar o frontend.

---

## Endpoints

### 🏢 Empresas

#### `GET /api/v1/empresas`

Lista EJs com filtros, ordenação e paginação.

**Query Parameters:**

| Param | Tipo | Default | Descrição |
|---|---|---|---|
| `ano` | int | 2026 | Ano de referência |
| `mes` | int (1-12) | null | Mês de referência |
| `cluster` | int (1-5) | null | Filtro por cluster |
| `status` | string | null | Filtro por status |
| `search` | string | null | Busca por nome |
| `ordem_por` | enum | "nome" | nome, faturamento, faturamento_colab, cluster, csat, percentual_meta, projetos |
| `direcao` | enum | "asc" | asc ou desc |
| `page` | int | 1 | Página atual |
| `page_size` | int (1-100) | 20 | Itens por página |

**Exemplo:**

```bash
curl "http://localhost:8000/api/v1/empresas?ano=2026&mes=2&cluster=3&ordem_por=faturamento&direcao=desc"
```

**Resposta:**

```json
{
  "data": [
    {
      "id": 2,
      "id_ej": 102,
      "nome": "EJ Beta",
      "cluster": 3,
      "status": "ativa",
      "foto_url": null,
      "faturamento_acumulado": 50000.0,
      "faturamento_colab_acumulado": 10000.0,
      "projetos_totais": 5,
      "csat_medio": 4.9,
      "percentual_meta": 8.33,
      "ritmo": "significativo",
      "taxa_colaboracao": 0.2,
      "cluster_calculado": null,
      "tendencia_cluster": null
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

---

#### `GET /api/v1/empresas/{id_ej}`

Perfil completo de uma EJ individual.

**Path Parameters:**
- `id_ej` (int) — Identificador da EJ

**Query Parameters:**
- `ano` (int, default: 2026)
- `mes` (int, opcional)

**Exemplo:**

```bash
curl "http://localhost:8000/api/v1/empresas/101?ano=2026&mes=2"
```

**Resposta inclui:**
- Dados cadastrais completos
- Indicadores calculados (faturamento, CSAT, ritmo, etc.)
- Série mensal de faturamento (para gráficos)
- Metas vs realizado
- Projeção anual (regressão linear)
- Ritmo necessário para bater meta
- Crescimento mensal e anual

---

#### `GET /api/v1/empresas/comparar`

Compara múltiplas EJs lado a lado.

**Query Parameters:**
- `ids` (list[int], obrigatório, 2-10 ids) — IDs das EJs (id_ej)
- `ano` (int, default: 2026)
- `mes` (int, opcional)

**Exemplo:**

```bash
curl "http://localhost:8000/api/v1/empresas/comparar?ids=101&ids=102&ano=2026"
```

---

### 📊 Rede

#### `GET /api/v1/rede/indicadores`

KPIs consolidados da rede FEJEPE.

**Query Parameters:**
- `ano` (int, default: 2026)
- `mes` (int, opcional)
- `cluster` (int, opcional)

**Resposta inclui:**
- Faturamento total e colab
- Total de projetos
- Média de CSAT
- Nº de EJs fora do zero
- Nº de EJs em ritmo mínimo e significativo
- Crescimento vs ano anterior
- Distribuição por cluster

---

#### `GET /api/v1/rede/ranking`

Ranking dinâmico de EJs.

**Query Parameters:**
- `ano`, `mes` (referência temporal)
- `criterio` — faturamento | csat | projetos | colab
- `cluster` (filtro)
- `limit` (int, default: 20)

---

### ❤️ Sistema

#### `GET /health`

Health check simples.

```json
{"status": "ok", "version": "0.1.0"}
```

---

## Cálculos Estratégicos

Todos centralizados em `app/services/calculo_service.py`. Referência: `calculos.md`.

| Cálculo | Função | Fórmula |
|---|---|---|
| % Meta | `calcular_percentual_meta()` | `(fat_acum / meta) * 100` |
| Ritmo | `classificar_ritmo()` | sem_vendas / mínimo / significativo |
| Taxa Colab | `calcular_taxa_colaboracao()` | `fat_colab / fat_total` |
| Pontos Cluster | `calcular_pontos_cluster()` | `Fat * CSAT * (1+Eng) * (1+Colab) * 100` |
| Cluster | `classificar_cluster()` | Lookup na tabela de faixas |
| SDE | `calcular_sde()` | `Σ peso_i * (S_i - D_i)` |
| Crescimento | `calcular_crescimento()` | `((atual - anterior) / anterior) * 100` |
| Projeção | `projetar_faturamento_anual()` | Regressão linear simples |
| Ritmo Necessário | `calcular_ritmo_necessario()` | `(meta - acum) / meses_restantes` |

---

## Decisões de Arquitetura

1. **supabase-py**: acesso direto ao Supabase sem ORM intermediário
2. **Cálculos no backend**: regra de negócio não vai para o frontend
3. **Paginação desde o início**: preparado para rede com muitas EJs
4. **Versionamento `/api/v1/`**: evolução sem breaking changes
5. **Singleton do Supabase**: cliente instanciado uma vez via dependency injection
6. **Constantes centralizadas**: faixas de cluster e pesos SDE em `utils/constants.py`

## Nexo — Pergunte à sua rede

`POST /api/v1/ia/perguntar`, autenticado, papel mínimo `membro`, tenant obrigatório.

```json
{"pergunta":"Quais EJs estão fora do zero em outubro de 2026?"}
```

A resposta inclui `status` (`respondida`, `fora_do_catalogo`, `sem_dados` ou `esclarecimento`),
`resposta`, `fonte`, `ano`, `mes`, `total`, `linhas`, `unidade`, `modelo`, `contexto` e `sugestoes`.
Cada linha pode indicar sua própria `unidade`, para agregados que misturam moeda e contagens.
Um mês ausente ou com cobertura incompleta gera `sem_dados`; não usa o mês anterior.
O corpo aceita somente `pergunta` e `contexto` opcional. O contexto é o último plano
tipado devolvido pela API: ferramenta, ano, mês, critério, limite, cluster e busca.
Permite continuações como “e em agosto?”, sem transportar resultados nem identidade.
Federação, SQL e papel são proibidos em ambos os objetos.

O catálogo oferece EJs fora do zero, indicadores, ranking, SDE e ritmo mensal.
Cluster oficial do ano (1–5) funciona em todas as consultas; busca literal por nome
funciona apenas nas EJs fora do zero. Falta de cobertura informa meses completos
disponíveis, sem substituir o período solicitado.

Perguntas ambíguas podem retornar `status=esclarecimento`, `contexto` e
`esclarecimento={pergunta,opcoes:[{rotulo,pergunta}]}`. O frontend envia a pergunta
concreta da opção escolhida; o backend mantém o recorte explícito. O plano tipado
inclui `esclarecimento` e `federacao_mencionada`, que é somente uma declaração textual
revalidada contra o nome/slug da federação autenticada. Esse campo jamais seleciona
o tenant ou substitui a autorização.

Erros: 401 sem login; 403 sem federação; 422 entrada inválida; 503 sem configuração
de IA, indisponibilidade do provedor ou erro de leitura; 502 interpretação inválida
por um adaptador que não respeitou o contrato. Limite de uso do fornecedor (429)
é apresentado como indisponibilidade 503, com orientação segura de recuperação.

O portal também reserva chamadas no PostgreSQL antes de acessar o fornecedor:
por padrão 6 por usuário e 30 por federação em janela fixa de um minuto. A configuração
operacional fica protegida no banco, sem parâmetros de tenant/limite no RPC.
Seu esgotamento responde 429 com `Retry-After: 60`; respostas locais de recusa ou
esclarecimento não fazem reserva. Isso não implementa créditos mensais do plano.

Configure no backend `IA_PROVEDOR=openrouter`, `IA_MODELO`, `IA_API_KEY` e opcionalmente
`IA_TIMEOUT_SEGUNDOS=20` e `IA_MAX_TOKENS_SAIDA=1024`. O endpoint do OpenRouter é
resolvido automaticamente. Para API direta use `IA_PROVEDOR=openai`; para outro
endpoint use `IA_PROVEDOR=compativel` e `IA_BASE_URL`. Endpoint compatível deve
suportar Chat Completions e JSON
Schema estrito. Sem configuração, o portal continua funcionando e o painel explica
que o assistente ainda não foi configurado. O frontend usa o interceptor de JWT já
existente. Não configure nenhuma chave de IA em variável `VITE_*`.

Avaliação manual (rede e custo), com um JWT de usuário da demo na variável de
ambiente `IA_EVAL_TOKEN`: `make ia-eval MODELO=<modelo>`. Não coloque o token no
comando, no Git ou em logs. O runner autentica esse token antes de consultar.
Consulte `docs/adr-004-pergunte-a-rede.md` e `docs/adr-005-nexo.md` para arquitetura e limitações.

No OpenRouter, o limite de geração usa `max_tokens`. Opcionalmente, configure
`IA_RACIOCINIO=desativado` para modelos que permitem desligar raciocínio explícito;
o padrão `padrao` preserva a configuração do modelo. Essa opção só é enviada ao
OpenRouter. A ativação local e a avaliação estão em
`docs/ativacao-pergunte-a-rede-2026-10-04.md`.

### Paleta da própria federação

`GET /api/v1/federacao/minha` e o branding público incluem `cor_primaria`,
`cor_secundaria` e `cor_acento`. `PUT /api/v1/federacao/minha/paleta` exige login,
papel mínimo admin e vínculo ativo atual no banco. Aceita somente os três campos,
cada um em `#RRGGBB` ou null para restaurar o padrão. Não recebe id/slug/status.
A RPC da migração17 limita a escrita às cores da própria federação e não concede
ao administrador UPDATE geral do cadastro. Um membro recebe403; falta de login401;
formato/campos inválidos422. A paleta salva é compartilhada, com atualização da UI
ao entrar, focar a página ou em até um minuto nas sessões abertas.

### Administração master (07/10/2026)

Todas as rotas abaixo exigem JWT válido e papel ativo `plataforma` no banco:

| Método | Caminho (`/api/v1`) | Operação |
|---|---|---|
| GET | `/admin/master/federacoes` | Agregados de cadastros e vínculo de plano por federação |
| GET | `/admin/master/planos` | Catálogo de planos |
| POST | `/admin/master/planos` | Cria plano |
| PUT | `/admin/master/planos/{plano_id}` | Substitui os campos editáveis do plano |
| PUT | `/admin/master/federacoes/{federacao_id}/plano` | Atribui plano; `plano_id: null` remove vínculo (204) |

Plano: `nome`, `limite_usuarios`, `limite_creditos_ia_mes`, `preco_mensal`.
Campos numéricos opcionais aceitam nulo e zero, com teto de 1.000.000.
Preço não gera cobrança e limite de usuários ainda é informativo. Créditos de
IA são de dashboards; cotas específicas por federação prevalecem, e mês já
iniciado conserva sua cota. Ver `docs/adr-007-administracao-master.md`.
