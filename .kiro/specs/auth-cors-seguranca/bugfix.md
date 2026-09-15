# Documento de Requisitos do Bugfix

## Introduction

O backend FastAPI do Portal FEJEPE (`portal_fejepe/`) apresenta duas falhas de
segurança conhecidas que expõem todos os dados da rede:

1. **JWT não validado.** O frontend envia `Authorization: Bearer <token>` do Supabase
   Auth, mas nenhum router em `/api/v1` verifica o token. Não existe a dependency
   `get_current_user`. Como consequência, qualquer requisição — com token inválido,
   expirado, ausente ou malformado — acessa livremente todos os endpoints de empresas,
   rede e eventos.

2. **CORS aberto.** Em `app/main.py`, o `CORSMiddleware` está configurado com
   `allow_origins=["*"]`, `allow_methods=["*"]` e `allow_headers=["*"]`, ignorando a
   propriedade `settings.cors_origin_list` (derivada da env `CORS_ORIGINS`) que já
   existe em `app/config.py`. Qualquer origem na web pode fazer requisições cross-origin
   à API.

Este bugfix é o primeiro passo do roadmap de migração para SaaS (ver `ROADMAP_SAAS.md`
e as "Pendências de segurança" em `portal_fejepe/AGENTS.md`). O objetivo é rejeitar
requisições sem JWT válido do Supabase (401) nos endpoints protegidos e restringir o
CORS às origens configuradas, preservando o funcionamento normal para requisições
legítimas.

## Bug Analysis

### Current Behavior (Defect)

O que acontece hoje quando o bug é acionado:

1.1 WHEN uma requisição chega a qualquer endpoint `/api/v1` (empresas, rede, eventos) sem o header `Authorization` THEN o sistema processa a requisição e retorna os dados normalmente, sem exigir autenticação.

1.2 WHEN uma requisição chega a um endpoint `/api/v1` com um header `Authorization` contendo um JWT inválido, expirado ou malformado THEN o sistema ignora o token e retorna os dados normalmente.

1.3 WHEN uma requisição cross-origin parte de uma origem que NÃO está listada em `CORS_ORIGINS` THEN o sistema responde com cabeçalhos CORS permissivos (`Access-Control-Allow-Origin: *`), autorizando a origem.

1.4 WHEN a env `CORS_ORIGINS` é definida com origens específicas THEN o sistema a ignora, pois o middleware usa `allow_origins=["*"]` fixo em vez de `settings.cors_origin_list`.

### Expected Behavior (Correct)

O que deve acontecer no lugar:

2.1 WHEN uma requisição chega a um endpoint protegido `/api/v1` sem o header `Authorization` THEN o sistema SHALL rejeitar a requisição com status HTTP 401 (não autenticado), sem acessar os dados.

2.2 WHEN uma requisição chega a um endpoint protegido `/api/v1` com um JWT inválido, expirado ou malformado THEN o sistema SHALL rejeitar a requisição com status HTTP 401, sem acessar os dados.

2.3 WHEN uma requisição cross-origin parte de uma origem que NÃO está listada em `CORS_ORIGINS` THEN o sistema SHALL NÃO autorizar a origem (não emitir `Access-Control-Allow-Origin` para ela).

2.4 WHEN a env `CORS_ORIGINS` está definida THEN o sistema SHALL usar `settings.cors_origin_list` como lista de origens permitidas no `CORSMiddleware`.

### Unchanged Behavior (Regression Prevention)

Comportamento existente que deve ser preservado:

3.1 WHEN uma requisição chega a um endpoint protegido `/api/v1` com um JWT válido do Supabase THEN o sistema SHALL CONTINUAR A processar a requisição e retornar os dados corretos, com os mesmos filtros, cálculos e formatos de resposta de hoje.

3.2 WHEN uma requisição cross-origin parte de uma origem listada em `CORS_ORIGINS` THEN o sistema SHALL CONTINUAR A autorizar a origem com os cabeçalhos CORS apropriados.

3.3 WHEN uma requisição acessa o endpoint público `/health` THEN o sistema SHALL CONTINUAR A responder normalmente sem exigir autenticação.

3.4 WHEN uma requisição autenticada aciona a lógica de negócio dos services (`empresa_service`, `rede_service`, `evento_service`) THEN o sistema SHALL CONTINUAR A produzir os mesmos indicadores e valores calculados de hoje (nenhuma fórmula ou cálculo é alterado).

## Derivação da Condição de Bug

### Bug 1 — JWT não validado

**Função de condição de bug** — identifica requisições que acionam o defeito:

```pascal
FUNCTION isBugCondition(req)
  INPUT: req of type HttpRequest para endpoint protegido /api/v1
  OUTPUT: boolean

  // Verdadeiro quando NÃO há um JWT válido do Supabase na requisição
  RETURN (req.authorization is missing)
      OR (NOT isValidSupabaseJwt(req.authorization.token))
END FUNCTION
```

**Especificação de propriedade** — comportamento correto para entradas com bug:

```pascal
// Propriedade: Fix Checking — rejeitar requisições sem JWT válido
FOR ALL req WHERE isBugCondition(req) DO
  result ← handleRequest'(req)
  ASSERT result.status = 401 AND NOT result.dados_expostos
END FOR
```

**Meta de preservação:**

```pascal
// Propriedade: Preservation Checking — requisições com JWT válido inalteradas
FOR ALL req WHERE NOT isBugCondition(req) DO
  ASSERT handleRequest(req) = handleRequest'(req)
END FOR
```

### Bug 2 — CORS aberto

**Função de condição de bug:**

```pascal
FUNCTION isBugCondition(origin)
  INPUT: origin of type string (header Origin da requisição cross-origin)
  OUTPUT: boolean

  // Verdadeiro quando a origem NÃO está na allowlist configurada
  RETURN origin NOT IN settings.cors_origin_list
END FUNCTION
```

**Especificação de propriedade:**

```pascal
// Propriedade: Fix Checking — não autorizar origens fora da allowlist
FOR ALL origin WHERE isBugCondition(origin) DO
  result ← corsResponse'(origin)
  ASSERT result.access_control_allow_origin != origin
     AND result.access_control_allow_origin != "*"
END FOR
```

**Meta de preservação:**

```pascal
// Propriedade: Preservation Checking — origens permitidas continuam autorizadas
FOR ALL origin WHERE NOT isBugCondition(origin) DO
  ASSERT corsResponse'(origin).access_control_allow_origin = origin
END FOR
```

**Definições:**
- **F**: código atual (main.py com CORS `*` e routers sem validação de JWT).
- **F'**: código corrigido (CORS restrito a `cors_origin_list` + dependency `get_current_user` protegendo os routers `/api/v1`).
