# Implementation Plan: Autenticação JWT e CORS restrito

## Overview

Bugfix de segurança: validação de JWT do Supabase nos routers `/api/v1` e restrição do
CORS à allowlist configurada. As tarefas seguem o fluxo exploratório de bugfix — primeiro
os testes que **falham** no código não corrigido (exploração), depois os testes de
**preservação** que **passam** no código não corrigido, e só então a correção.

Referências:
- Requisitos: `bugfix.md` (2.1–2.4 comportamento esperado; 3.1–3.4 preservação).
- Correctness Properties do `design.md`: Property 1 (Bug Condition JWT), Property 2
  (Bug Condition CORS), Property 3 (Preservation JWT), Property 4 (Preservation CORS).
- Convenções: docstrings/comentários em português; routers finos; testes em
  `portal_fejepe/tests/`; Supabase Auth mockado via `dependency_overrides`/`monkeypatch`
  sobre `sb.auth.get_user` (sem rede real).

---

## Tasks

- [x] 1. Escrever testes de exploração da condição de bug (ANTES do fix)
  - **Property 1: Bug Condition** - Rejeitar requisições sem JWT válido (Bug 1 — JWT)
  - **Property 2: Bug Condition** - Não autorizar origens fora da allowlist (Bug 2 — CORS)
  - **CRÍTICO**: Estes testes DEVEM FALHAR no código não corrigido — a falha confirma que os bugs existem.
  - **NÃO tente corrigir o teste nem o código quando eles falharem.** Os testes codificam o comportamento esperado e validarão o fix quando passarem depois da implementação.
  - **META**: Surface counterexamples que demonstram os dois bugs.
  - **Abordagem PBT com escopo**: para o Bug 1, escopar a propriedade a casos concretos determinísticos (sem header, esquema não-Bearer, token malformado); para o Bug 2, gerar origens fora de `settings.cors_origin_list`.
  - Criar `portal_fejepe/tests/test_seguranca.py` usando `pytest` + `fastapi.testclient.TestClient`.
  - Bug 1 — casos que devem falhar no código não corrigido (retornam 200 em vez de 401):
    - `GET /api/v1/empresas` sem header `Authorization` (isBugCondition: header ausente) — esperado 401.
    - `GET /api/v1/rede/indicadores` com `Authorization: Bearer abc.invalido.xyz` (isBugCondition: token inválido) — esperado 401.
    - `GET /api/v1/eventos` sem header `Authorization` (cobre o endpoint sem `sb`) — esperado 401.
    - Propriedade escopada: para uma amostra de tokens malformados, todas as respostas devem ser 401.
  - Bug 2 — caso que deve falhar no código não corrigido (ecoa `*`):
    - Requisição com `Origin: https://atacante.example` estando `CORS_ORIGINS=http://localhost:5173` — esperado: sem `Access-Control-Allow-Origin` igual à origem nem igual a `*`.
  - Rodar os testes no código NÃO corrigido.
  - **RESULTADO ESPERADO**: os testes FALHAM (isto está correto — prova que os bugs existem).
  - Documentar os counterexamples encontrados (ex.: "`GET /api/v1/empresas` sem token retorna 200 com a lista completa de EJs"; "`Access-Control-Allow-Origin: *` presente para origem arbitrária").
  - Marcar a tarefa como concluída quando os testes estiverem escritos, executados e a falha documentada.
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2. Escrever testes de preservação (ANTES do fix)
  - **Property 3: Preservation** - Requisições autenticadas e `/health` inalterados (Bug 1)
  - **Property 4: Preservation** - Origens permitidas continuam autorizadas (Bug 2)
  - **IMPORTANTE**: seguir a metodologia observation-first — observar o comportamento no código NÃO corrigido para entradas onde `isBugCondition` é falso e capturá-lo em testes.
  - Adicionar os testes de preservação a `portal_fejepe/tests/test_seguranca.py`.
  - Observar/registrar no código não corrigido (¬C):
    - Endpoints protegidos retornam dados e `response_model` esperados (ex.: `GET /api/v1/empresas`, `GET /api/v1/rede/indicadores`, `GET /api/v1/rede/sde`, perfil de EJ).
    - `GET /health` retorna `200` sem token.
    - Requisição com `Origin` presente em `CORS_ORIGINS` recebe `Access-Control-Allow-Origin` igual à origem.
    - Valores calculados de `rede/indicadores`, `rede/sde` e perfil de EJ (para verificar que os services permanecem intocados).
  - Escrever testes property-based para preservação (recomendado — gera muitos casos e cobre edge cases):
    - Property 4: gerar origens dentro de `settings.cors_origin_list` e verificar que cada uma é ecoada em `Access-Control-Allow-Origin`.
    - Property 3: gerar variações de endpoints/parâmetros protegidos com token válido (mock) e verificar que o resultado é idêntico ao baseline.
  - Rodar os testes no código NÃO corrigido.
  - **RESULTADO ESPERADO**: os testes de preservação PASSAM (confirma o comportamento baseline a preservar).
  - Marcar a tarefa como concluída quando os testes estiverem escritos, executados e passando no código não corrigido.
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Corrigir os bugs de segurança (JWT não validado + CORS aberto)

  - [x] 3.1 Criar a dependency `get_current_user` em `app/dependencies.py`
    - Adicionar `get_current_user` que recebe `credentials: HTTPAuthorizationCredentials | None` via `HTTPBearer(auto_error=False)` e `sb: Client` via `Depends(get_supabase)`.
    - Levantar `HTTPException(401, "Não autenticado")` quando `credentials` é `None` ou `credentials.scheme != "Bearer"`.
    - Validar o token com `sb.auth.get_user(token)`; em qualquer exceção, ou resposta/usuário nulo, levantar `HTTPException(401, "Token inválido ou expirado")`.
    - Incluir o header `WWW-Authenticate: Bearer` nas respostas 401.
    - Retornar o usuário autenticado (objeto User do Supabase) no caso de sucesso.
    - Docstring/comentários em português.
    - _Bug_Condition: isBugCondition(req) = header ausente OR esquema != "Bearer" OR NOT isValidSupabaseJwt(token) (design)_
    - _Expected_Behavior: 401 sem expor dados quando C(req) vale (design — Property 1)_
    - _Preservation: usuário com JWT válido segue autenticado (design — Property 3)_
    - _Requirements: 2.1, 2.2_

  - [x] 3.2 Aplicar a dependency em nível de router nos routers protegidos
    - Em `app/routers/empresas.py`, `app/routers/rede.py` e `app/routers/eventos.py`, adicionar `dependencies=[Depends(get_current_user)]` ao `APIRouter(...)`.
    - Aplicar em nível de router garante que `GET /api/v1/eventos` (que não usa `get_supabase`) também fica protegido.
    - Manter os handlers finos: não alterar assinaturas nem referenciar o usuário nos handlers.
    - Não tocar em `/health` (definido em `main.py`) — permanece público.
    - _Bug_Condition: requisição a endpoint protegido /api/v1 sem JWT válido (design)_
    - _Expected_Behavior: gate de auth responde 401 antes do handler (design — Property 1)_
    - _Preservation: handlers e response_model inalterados para requisições autenticadas (design — Property 3)_
    - _Requirements: 2.1, 2.2, 3.1, 3.3_

  - [x] 3.3 Restringir o CORS em `app/main.py`
    - Trocar `allow_origins=["*"]` por `allow_origins=settings.cors_origin_list` no `CORSMiddleware`.
    - Manter `allow_credentials=False` (o frontend usa Bearer token, não cookies), compatível com allowlist explícita.
    - _Bug_Condition: isBugCondition(origin) = origin NOT IN settings.cors_origin_list (design)_
    - _Expected_Behavior: não emitir Access-Control-Allow-Origin para origem fora da allowlist (design — Property 2)_
    - _Preservation: origens em cors_origin_list continuam ecoadas (design — Property 4)_
    - _Requirements: 2.3, 2.4_

  - [x] 3.4 Verificar que os testes de exploração agora passam
    - **Property 1: Expected Behavior** - Requisições sem JWT válido rejeitadas com 401
    - **Property 2: Expected Behavior** - Origens fora da allowlist não autorizadas
    - **IMPORTANTE**: reexecutar os MESMOS testes da tarefa 1 — não escrever novos testes.
    - Com `sb.auth.get_user` mockado retornando usuário válido para token válido e erro/nulo para token inválido.
    - **RESULTADO ESPERADO**: os testes PASSAM (confirma que os bugs foram corrigidos — 401 sem token válido; CORS não ecoa origem fora da allowlist; `WWW-Authenticate: Bearer` presente).
    - _Requirements: Correctness Properties 1 e 2 do design; 2.1, 2.2, 2.3, 2.4_

  - [x] 3.5 Verificar que os testes de preservação continuam passando
    - **Property 3: Preservation** - Requisições autenticadas e `/health` inalterados
    - **Property 4: Preservation** - Origens permitidas continuam autorizadas
    - **IMPORTANTE**: reexecutar os MESMOS testes da tarefa 2 — não escrever novos testes.
    - Confirmar que, após o fix: endpoints protegidos com JWT válido retornam os mesmos dados/`response_model`; `/health` continua `200`; origens permitidas seguem ecoadas; valores calculados dos services inalterados.
    - **RESULTADO ESPERADO**: os testes PASSAM (sem regressões).
    - _Requirements: Correctness Properties 3 e 4 do design; 3.1, 3.2, 3.3, 3.4_

- [x] 4. Checkpoint — Garantir que toda a suíte passa
  - Rodar `pytest` em `portal_fejepe/` e confirmar que os testes novos (`test_seguranca.py`) e os existentes (`test_empresas.py`, `test_eventos.py`, `test_calculos.py`) passam.
  - Confirmar que nenhuma fórmula/cálculo dos services foi alterado (preservação 3.4).
  - Se surgirem dúvidas ou falhas inesperadas, perguntar ao usuário antes de prosseguir.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

---

## Task Dependency Graph

```
1. Testes de exploração (Bug Condition — falham em F)   ─┐
                                                          ├─► 3.1 get_current_user ─► 3.2 gate nos routers ─┐
2. Testes de preservação (observados em F — passam)     ─┘                                                  │
                                                            3.3 CORS restrito (independente) ───────────────┤
                                                                                                            ▼
                                                                                          3.4 exploração passa (F')
                                                                                          3.5 preservação passa (F')
                                                                                                            │
                                                                                                            ▼
                                                                                             4. Checkpoint (pytest full)
```

Definições de waves (ondas de execução paralela). Cada wave lista os IDs de tarefa que
podem rodar em paralelo, respeitando as dependências acima:

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["1", "2"],
      "descricao": "Testes de exploração e de preservação, independentes entre si, antes de qualquer código de fix."
    },
    {
      "wave": 2,
      "tasks": ["3.1", "3.3"],
      "descricao": "Criar a dependency get_current_user e restringir o CORS; 3.3 é independente de 3.1."
    },
    {
      "wave": 3,
      "tasks": ["3.2"],
      "descricao": "Aplicar o gate nos routers; depende de 3.1."
    },
    {
      "wave": 4,
      "tasks": ["3.4", "3.5"],
      "descricao": "Verificar exploração e preservação após o fix; dependem de todo o bloco 3 (3.1, 3.2, 3.3)."
    },
    {
      "wave": 5,
      "tasks": ["4"],
      "descricao": "Checkpoint final (pytest completo); depende de 3.4 e 3.5."
    }
  ]
}
```

Notas de dependência:
- **1** e **2** são independentes entre si e devem vir ANTES de qualquer código de fix.
- **3.1 → 3.2**: o gate de router depende da dependency `get_current_user`.
- **3.3** (CORS) é independente de 3.1/3.2 e pode ser feito em paralelo.
- **3.4/3.5** dependem de todo o bloco 3 (3.1, 3.2, 3.3) estar aplicado.
- **4** depende de 3.4 e 3.5.

## Notes

- Escreva e rode os testes das tarefas 1 e 2 **antes** de qualquer correção: os testes de
  exploração devem **falhar** no código não corrigido (confirmando os bugs) e os de
  preservação devem **passar** (fixando o comportamento baseline a proteger).
- Não altere fórmulas nem cálculos dos services (`calculo_service.py` e afins): o escopo é
  apenas autenticação e CORS. A preservação 3.4 valida essa garantia.
- Mocke o Supabase Auth via `dependency_overrides`/`monkeypatch` sobre `sb.auth.get_user`;
  os testes não devem depender de rede real.
- Mantenha os routers finos: aplique a autenticação em nível de `APIRouter` e não altere as
  assinaturas dos handlers.
- `/health` permanece público e não recebe o gate de autenticação.
- Rode `pytest` a partir de `portal_fejepe/` para validar; não inicie dev servers de forma
  bloqueante em automações.
