# Design do Bugfix — Autenticação JWT e CORS restrito

## Overview

O backend FastAPI do Portal FEJEPE expõe todos os dados da rede porque (1) nenhum
endpoint `/api/v1` valida o JWT do Supabase enviado pelo frontend e (2) o
`CORSMiddleware` está fixo em `allow_origins=["*"]`, ignorando a allowlist já
configurada em `settings.cors_origin_list`.

A estratégia de correção é minimalista e cirúrgica, sem tocar em nenhuma regra de
negócio:

1. **Autenticação (Bug 1):** criar uma dependency `get_current_user` em
   `app/dependencies.py` que extrai o token do header `Authorization: Bearer <token>`,
   valida-o contra o Supabase Auth e retorna 401 quando o token está ausente, inválido,
   expirado ou malformado. Essa dependency é aplicada em nível de router (via
   `APIRouter(dependencies=[...])`) aos três routers protegidos (`empresas`, `rede`,
   `eventos`). O endpoint `/health` permanece público.
2. **CORS (Bug 2):** substituir `allow_origins=["*"]` por `settings.cors_origin_list`
   no `CORSMiddleware` em `app/main.py`.

Nenhum service, fórmula, filtro ou formato de resposta é alterado. A correção adiciona
um "portão" de autenticação antes dos handlers e restringe a lista de origens do CORS.

## Glossary

- **Bug_Condition (C)**: condição que aciona o defeito. Para o Bug 1: uma requisição a
  endpoint protegido `/api/v1` sem um JWT válido do Supabase. Para o Bug 2: uma origem
  cross-origin que não está em `settings.cors_origin_list`.
- **Property (P)**: comportamento desejado sob a condição de bug. Bug 1: responder 401
  sem expor dados. Bug 2: não emitir `Access-Control-Allow-Origin` para a origem.
- **Preservation**: comportamento existente que deve permanecer inalterado —
  requisições com JWT válido, origens permitidas, o endpoint público `/health` e todos
  os cálculos dos services.
- **JWT do Supabase**: token de acesso emitido pelo Supabase Auth no login por
  e-mail/senha, enviado pelo frontend no header `Authorization: Bearer <token>`.
- **get_current_user**: nova dependency em `app/dependencies.py` que valida o JWT e
  devolve o usuário autenticado (ou levanta `HTTPException(401)`).
- **get_supabase**: dependency existente que devolve o client Supabase singleton.
- **cors_origin_list**: propriedade em `app/config.py` (`settings.cors_origin_list`)
  que converte a env `CORS_ORIGINS` numa lista de origens permitidas.

## Bug Details

### Bug Condition

#### Bug 1 — JWT não validado

O bug se manifesta quando uma requisição chega a um endpoint protegido `/api/v1`
(empresas, rede, eventos) sem apresentar um JWT válido do Supabase. Hoje os routers não
declaram nenhuma dependency de autenticação; o handler é executado e os dados são
retornados independentemente de haver ou não um token. A causa é a **ausência da
dependency `get_current_user`** e da sua aplicação aos routers.

**Formal Specification:**
```
FUNCTION isBugCondition(req)
  INPUT: req of type HttpRequest para endpoint protegido /api/v1
  OUTPUT: boolean

  // Verdadeiro quando NÃO há um JWT válido do Supabase na requisição
  RETURN (req.authorization is missing)
      OR (req.authorization scheme != "Bearer")
      OR (NOT isValidSupabaseJwt(req.authorization.token))
END FUNCTION
```

#### Bug 2 — CORS aberto

O bug se manifesta quando uma requisição cross-origin parte de uma origem que não está
na allowlist configurada. Hoje o `CORSMiddleware` usa `allow_origins=["*"]`, então
qualquer origem é autorizada. A causa é o **valor fixo `["*"]`** em `app/main.py`, que
ignora `settings.cors_origin_list`.

**Formal Specification:**
```
FUNCTION isBugCondition(origin)
  INPUT: origin of type string (header Origin da requisição cross-origin)
  OUTPUT: boolean

  // Verdadeiro quando a origem NÃO está na allowlist configurada
  RETURN origin NOT IN settings.cors_origin_list
END FUNCTION
```

### Examples

- **Bug 1 — sem header:** `GET /api/v1/empresas` sem `Authorization`. Esperado: `401`.
  Atual: `200` com a lista completa de EJs.
- **Bug 1 — token inválido:** `GET /api/v1/rede/indicadores` com
  `Authorization: Bearer abc.invalido.xyz`. Esperado: `401`. Atual: `200` com os KPIs.
- **Bug 1 — token expirado:** `GET /api/v1/eventos` com um JWT do Supabase já expirado.
  Esperado: `401`. Atual: `200` com os eventos.
- **Bug 2 — origem estranha:** requisição de `https://atacante.example` com
  `CORS_ORIGINS=http://localhost:5173`. Esperado: sem `Access-Control-Allow-Origin`
  para essa origem. Atual: `Access-Control-Allow-Origin: *`.
- **Edge — `/health`:** `GET /health` sem token deve continuar retornando `200`
  (endpoint público, não protegido).

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Requisições a endpoints protegidos `/api/v1` com um JWT válido do Supabase continuam
  processando e retornando os mesmos dados, com os mesmos filtros, cálculos e formatos.
- Requisições cross-origin de origens listadas em `CORS_ORIGINS` continuam autorizadas
  com os cabeçalhos CORS apropriados.
- O endpoint público `/health` continua respondendo `200` sem exigir autenticação.
- Todas as fórmulas e valores calculados nos services (`empresa_service`,
  `rede_service`, `evento_service`, `calculo_service`) permanecem idênticos.
- Os `response_model`, códigos 404/503 e mensagens de erro de negócio existentes nos
  routers permanecem inalterados para requisições autenticadas.

**Scope:**
Todas as entradas que NÃO satisfazem a condição de bug devem permanecer completamente
inalteradas por esta correção. Isso inclui:
- Requisições autenticadas com JWT válido (Bug 1).
- Origens dentro da allowlist (Bug 2).
- O endpoint público `/health`.
- A lógica interna de services e utils (nenhum cálculo é tocado).

## Hypothesized Root Cause

### Bug 1 — JWT não validado

1. **Ausência da dependency de autenticação**: não existe `get_current_user` em
   `app/dependencies.py`; só há `get_supabase`. Nenhum router declara uma dependency que
   verifique o token, então o FastAPI executa os handlers sem qualquer checagem.
2. **Routers sem `dependencies`**: `APIRouter(prefix="/api/v1/...")` é criado sem o
   parâmetro `dependencies=[...]`, logo não há gate global por router.
3. **Endpoint sem `sb` também exposto**: `GET /api/v1/eventos` (listar) sequer recebe o
   client Supabase, então proteger apenas via `get_supabase` seria insuficiente — a
   proteção precisa ser aplicada no nível do router.

### Bug 2 — CORS aberto

1. **Valor hardcoded**: `allow_origins=["*"]` em `app/main.py` ignora
   `settings.cors_origin_list`, que já existe e é derivada de `CORS_ORIGINS`.
2. **`allow_credentials=False` com `*`**: combinação que hoje reflete `*` para qualquer
   origem; ao trocar por uma allowlist, o Starlette passa a ecoar apenas as origens
   permitidas.

## Correctness Properties

Property 1: Bug Condition (JWT) — Rejeitar requisições sem JWT válido

_For any_ requisição a endpoint protegido `/api/v1` onde a condição de bug do JWT vale
(isBugCondition retorna true: header ausente, esquema não-Bearer, ou token
inválido/expirado/malformado), a função corrigida SHALL responder com status HTTP 401 e
NÃO expor nenhum dado da rede.

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition (CORS) — Não autorizar origens fora da allowlist

_For any_ origem cross-origin onde a condição de bug do CORS vale (isBugCondition
retorna true: origem não está em `settings.cors_origin_list`), a resposta corrigida
SHALL NÃO emitir `Access-Control-Allow-Origin` igual a essa origem nem igual a `*`.

**Validates: Requirements 2.3, 2.4**

Property 3: Preservation (JWT) — Requisições autenticadas inalteradas

_For any_ requisição a endpoint protegido `/api/v1` onde a condição de bug do JWT NÃO
vale (JWT válido do Supabase), a função corrigida SHALL produzir o mesmo resultado que a
função original, preservando dados, filtros, cálculos e formato de resposta. O endpoint
público `/health` também permanece acessível sem autenticação.

**Validates: Requirements 3.1, 3.3, 3.4**

Property 4: Preservation (CORS) — Origens permitidas continuam autorizadas

_For any_ origem cross-origin onde a condição de bug do CORS NÃO vale (origem está em
`settings.cors_origin_list`), a resposta corrigida SHALL emitir
`Access-Control-Allow-Origin` igual a essa origem, preservando o acesso cross-origin
legítimo do frontend.

**Validates: Requirements 3.2**

## Fix Implementation

### Changes Required

#### Mudança 1 — Dependency de autenticação

**File**: `app/dependencies.py`

**Function**: nova `get_current_user`

**Abordagem de validação do JWT — escolha e trade-offs:**

Optamos por validar o token via **`supabase.auth.get_user(token)`** (o SDK do Supabase
já disponível), em vez de verificar a assinatura JWT localmente.

- **`auth.get_user(token)` (escolhido):**
  - _Prós:_ usa o SDK já instalado (`supabase 2.*`); o Supabase valida assinatura,
    expiração e revogação; não exige gerenciar o JWT secret nem baixar JWKS; alinhado
    com a convenção "auth via Supabase". Erro ou usuário ausente ⇒ 401.
  - _Contras:_ faz uma chamada de rede ao Supabase por requisição (latência e
    dependência de disponibilidade do Auth). Mitigável no futuro com cache curto, fora
    do escopo deste bugfix.
- **Verificação local da assinatura (alternativa não escolhida):**
  - _Prós:_ sem round-trip por requisição.
  - _Contras:_ exige o JWT secret/JWKS no backend, mais superfície de configuração e
    risco; não detecta revogação. Adia decisões de tenant/claims que virão no roadmap.

**Especificação (pseudocódigo, não é o código final):**
```
FUNCTION get_current_user(credentials, sb)
  INPUT:
    credentials: HTTPAuthorizationCredentials | None  (via HTTPBearer(auto_error=False))
    sb: Client                                         (via Depends(get_supabase))
  OUTPUT: usuário autenticado (objeto User do Supabase)

  IF credentials is None OR credentials.scheme != "Bearer" THEN
    RAISE HTTPException(401, "Não autenticado")
  END IF

  token ← credentials.credentials
  TRY
    resposta ← sb.auth.get_user(token)
  CATCH qualquer_erro
    RAISE HTTPException(401, "Token inválido ou expirado")
  END TRY

  IF resposta is None OR resposta.user is None THEN
    RAISE HTTPException(401, "Token inválido ou expirado")
  END IF

  RETURN resposta.user
END FUNCTION
```
Notas de implementação:
- Usar `HTTPBearer(auto_error=False)` para controlar a mensagem 401 (com `auto_error=True`
  o esquema retornaria 403 em header ausente; queremos 401 uniforme).
- A resposta 401 SHALL incluir o header `WWW-Authenticate: Bearer`.
- A dependency recebe o client via `Depends(get_supabase)`, mantendo a convenção de
  injeção.

#### Mudança 2 — Aplicar autenticação aos routers protegidos

**Files**: `app/routers/empresas.py`, `app/routers/rede.py`, `app/routers/eventos.py`

Aplicar a dependency em nível de router para cobrir todos os endpoints (inclusive
`GET /api/v1/eventos`, que não usa `get_supabase`):
```
router = APIRouter(
    prefix="/api/v1/empresas",
    tags=["Empresas"],
    dependencies=[Depends(get_current_user)],
)
```
Repetir para `rede` e `eventos`. Como é gate em nível de router, os handlers não mudam
de assinatura e não precisam referenciar o usuário. `/health` (em `main.py`) fica fora
e permanece público.

#### Mudança 3 — Restringir CORS

**File**: `app/main.py`

**Change**: trocar a origem fixa pela allowlist configurada:
```
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,   # antes: ["*"]
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Manter `allow_credentials=False` (o frontend usa Bearer token, não cookies), o que é
compatível com uma allowlist explícita.

## Testing Strategy

### Validation Approach

A estratégia segue duas fases: primeiro, surface counterexamples que demonstram os dois
bugs no código não corrigido (fix checking sobre C); depois, verificar que a correção
funciona e preserva o comportamento legítimo (preservation checking sobre ¬C). Os testes
usam `pytest` + `fastapi.testclient.TestClient`, com o Supabase Auth mockado (sem rede
real) via `app.dependency_overrides`/`monkeypatch` sobre `sb.auth.get_user`.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples que demonstram os bugs ANTES do fix e confirmam a
análise de causa raiz. Se refutados, re-hipotetizar.

**Test Plan**: Disparar requisições aos endpoints protegidos sem token e com token
inválido, e requisições cross-origin de origem não permitida, observando no código
não corrigido que os dados vazam (200) e que o CORS ecoa `*`.

**Test Cases**:
1. **Sem token → empresas**: `GET /api/v1/empresas` sem `Authorization` (falha no código não corrigido: retorna 200 em vez de 401).
2. **Token inválido → rede**: `GET /api/v1/rede/indicadores` com Bearer inválido (falha no código não corrigido: 200).
3. **Sem token → eventos (listar)**: `GET /api/v1/eventos` sem `Authorization` — cobre o endpoint sem `sb` (falha no código não corrigido: 200).
4. **CORS origem não permitida**: preflight/`Origin` de origem fora de `CORS_ORIGINS` (falha no código não corrigido: responde `Access-Control-Allow-Origin: *`).

**Expected Counterexamples**:
- Endpoints protegidos retornam 200 com dados sem token válido.
- Cabeçalho `Access-Control-Allow-Origin: *` presente para origem arbitrária.
- Causas prováveis: ausência de `get_current_user` aplicada aos routers; `allow_origins=["*"]` fixo.

### Fix Checking

**Goal**: Verificar que, para toda entrada onde a condição de bug vale, a função
corrigida produz o comportamento esperado.

**Pseudocode:**
```
// Bug 1
FOR ALL req WHERE isBugCondition(req) DO
  result := handleRequest_fixed(req)
  ASSERT result.status = 401 AND NOT result.dados_expostos
END FOR

// Bug 2
FOR ALL origin WHERE isBugCondition(origin) DO
  result := corsResponse_fixed(origin)
  ASSERT result.access_control_allow_origin NOT IN { origin, "*" }
END FOR
```

### Preservation Checking

**Goal**: Verificar que, para toda entrada onde a condição de bug NÃO vale, a função
corrigida produz o mesmo resultado que a função original.

**Pseudocode:**
```
// Bug 1 — JWT válido inalterado
FOR ALL req WHERE NOT isBugCondition(req) DO
  ASSERT handleRequest_original(req) = handleRequest_fixed(req)
END FOR

// Bug 2 — origem permitida inalterada
FOR ALL origin WHERE NOT isBugCondition(origin) DO
  ASSERT corsResponse_fixed(origin).access_control_allow_origin = origin
END FOR
```

**Testing Approach**: Property-based testing é recomendado para preservation checking
porque gera muitos casos automaticamente no domínio de entrada, cobre edge cases que
testes unitários manuais poderiam perder e dá garantia forte de que o comportamento é
inalterado para entradas não-bug. Aqui o domínio a variar é o conjunto de origens
permitidas e a variedade de endpoints/parâmetros com token válido.

**Test Plan**: Observar o comportamento no código não corrigido para JWT válido, origens
permitidas e `/health`, então escrever testes que capturem esse comportamento e o
verifiquem após o fix (com `sb.auth.get_user` mockado retornando um usuário para token
válido).

**Test Cases**:
1. **JWT válido preservado**: com `get_current_user` mockado como usuário válido, os endpoints retornam os mesmos dados/`response_model` de antes.
2. **`/health` público**: `GET /health` sem token continua `200` após o fix.
3. **Origem permitida preservada**: requisição de origem em `CORS_ORIGINS` recebe `Access-Control-Allow-Origin` igual à origem.
4. **Cálculos preservados**: respostas de `rede/indicadores`, `rede/sde` e perfil de EJ com token válido mantêm os mesmos valores calculados (services intocados).

### Unit Tests

- `get_current_user`: 401 sem header; 401 com esquema não-Bearer; 401 quando `sb.auth.get_user` lança erro; 401 quando retorna usuário nulo; sucesso quando retorna usuário válido.
- Header `WWW-Authenticate: Bearer` presente nas respostas 401.
- CORS: origem permitida ecoada; origem não permitida não autorizada.

### Property-Based Tests

- Gerar origens aleatórias (dentro e fora da allowlist) e verificar: permitidas ⇒ ecoadas; não permitidas ⇒ nunca ecoadas nem `*` (fix + preservation do Bug 2).
- Gerar variações de endpoints/parâmetros protegidos com token válido e verificar que o gate de auth não altera o resultado (preservation do Bug 1).
- Gerar tokens malformados aleatórios e verificar que todos resultam em 401 (fix do Bug 1).

### Integration Tests

- Fluxo completo com `TestClient`: login mockado → chamada autenticada aos três routers → 200 com dados; sem token → 401.
- Troca de configuração de `CORS_ORIGINS` e verificação do comportamento cross-origin correspondente.
- Confirmar que `/health` permanece público enquanto os routers `/api/v1` exigem autenticação.
