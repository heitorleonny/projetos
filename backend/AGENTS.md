# AGENTS.md — Backend

API FastAPI/Python 3.12, Supabase Auth/PostgREST/PostgreSQL, Pydantic e ingestão
psycopg/pandas. Leia as regras da raiz e o contexto vigente.

Produção: `pip install -r requirements.lock`. Desenvolvimento/testes:
`pip install -r requirements-dev.lock`. Dependências diretas estão nos arquivos
`.txt`; atualizar os locks e repetir testes quando elas mudarem.

Na raiz: `make test` inicializa um banco descartável com toda a cadeia SQL e
exige testes sem skips. `make demo-smoke` verifica Auth/PostgREST da demo real
local; não substitui o teste remoto. Não apagar volumes para validar alterações.

Routers validam entradas e chamam services tipados. Fórmulas em
`app/services/calculo_service.py` e constantes em `app/utils/constants.py`.
Cliente Supabase por requisição com JWT. Tenant vem da autorização; papel não
amplia tenant. Escrita verifica papel ativo atual no banco. O operador plataforma
usa RPCs autorizadas; service key de requests só em `convite_service.py`.

`infra/db/init/` na raiz é fonte única do schema. Migração nova é aditiva e não
reescreve histórico aplicado. Toda leitura de tenant deve ter filtro independente
mais RLS. A ingestão recusa dono/BYPASSRLS e utiliza papel `ingestao`.

Não registrar segredo, credenciais nem linhas reais em logs/fixtures. Scripts
administrativos em `scripts/` rodam fora do caminho da API, exigem destino explícito
e não devem reutilizar conta/senha da demo em hospedagem. Não testar modelo pago
no pytest; avaliação com rede/custo é execução manual separada.
