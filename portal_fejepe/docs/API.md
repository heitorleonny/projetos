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
| `comunidade` | string | null | Filtro por comunidade |
| `status` | string | null | Filtro por status |
| `search` | string | null | Busca por nome |
| `ordem_por` | enum | "nome" | nome, faturamento, faturamento_colab, cluster, comunidade, csat, percentual_meta, projetos |
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
      "comunidade": "Comunidade B",
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
- `comunidade` (string, opcional)

**Resposta inclui:**
- Faturamento total e colab
- Total de projetos
- Média de CSAT
- Nº de EJs fora do zero
- Nº de EJs em ritmo mínimo e significativo
- Crescimento vs ano anterior
- Distribuição por cluster
- Participação por comunidade (%)

---

#### `GET /api/v1/rede/ranking`

Ranking dinâmico de EJs.

**Query Parameters:**
- `ano`, `mes` (referência temporal)
- `criterio` — faturamento | csat | projetos | colab
- `cluster`, `comunidade` (filtros)
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
