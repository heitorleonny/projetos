# AGENTS.md — Portal das Federações

> Decisão de Heitor em 05/11/2026: substituir Supabase por PostgreSQL próprio
> e executar a aplicação em Docker. Regras abaixo que exigem SDK/serviço Supabase
> descrevem a arquitetura anterior; preservar seus invariantes de isolamento na
> autenticação própria e no cliente psycopg. O mapa vigente está em
> `docs/entrega-tcc-2026-11-05.md`; a decisão, em `docs/adr-008-postgresql-docker.md`.
> Credencial de dono só no migrador/bootstrap administrativo; nunca na API.
> Não alterar a monografia enquanto Heitor a revisa.

Leia `CONTEXTO-TCC.md` para método/escopo/invariantes e
`ESTADO-PORTAL-PARA-TCC.md` para estado e evidências atuais. A instrução direta de
Heitor tem precedência. Em 07/10/2026 Heitor autorizou a reorganização das pastas
para entrega e preparação de deploy; os nomes antigos dos relatórios são históricos.

## Estrutura e comandos

- `backend/`: FastAPI, cálculo, ingestão, IA e scripts administrativos.
- `frontend/`: React/Vite, autenticação e branding por federação.
- `tools/cluster-calculator/`: aplicação auxiliar; não integra o deploy principal.
- `infra/db/init/`: fonte única das migrações SQL.
- `infra/deploy/`: configurações de homologação e guias de operação.
- `scripts/`: ferramentas de execução local; `docs/`: ADRs e evidências.

`make setup` instala dependências travadas. `make check` verifica backend/RLS em
banco descartável, testes/build/lint do frontend e build da ferramenta auxiliar.
`make demo-smoke` verifica Auth/PostgREST reais da demo local. Não rode os dois
comandos de banco em paralelo. Não execute `make clean` ou `make demo-reset` para
verificar mudanças: apagam volumes. Servidores/watchers não devem bloquear automações.

## Regras

1. O projeto já é multi-tenant. Tenant vem da autorização, nunca do corpo, pergunta
   de IA ou coluna de arquivo. RLS e filtros do backend são camadas independentes.
2. Requests usam cliente Supabase por requisição com chave pública e JWT do usuário.
   Service key só em `app/services/convite_service.py`, após autorização/RLS.
   Scripts administrativos fora de request podem ter privilégio nominal explícito.
3. Cálculos estratégicos ficam no backend, com constantes em `app/utils/constants.py`.
   Leia `backend/calculos.md` antes de mudar fórmulas. IA escolhe planos validados;
   não calcula indicadores nem escolhe identidade/papel/federação.
4. Toda tabela de tenant tem RLS, índice apropriado e testes de isolamento. Migração
   nova = novo arquivo numerado. Nunca editar migração aplicada ou duplicar schema
   em `supabase/migrations/`. Defaults SQL dependem do criador do objeto.
5. Nunca versionar segredos, `.env`, dados reais de EJ, planilhas ou capturas com
   desempenho individual. Variáveis publicadas no frontend são públicas.
6. Testes de isolamento não podem aprovar com skips. Reporte passes/falhas/skips e
   separe laboratório, Supabase local, destino remoto e avaliação de usuários.
7. Preservar alterações existentes. Sem pedido explícito, não fazer commit, push,
   merge, stash, reset, rebase ou descarte. Não escrever em produção nem criar
   recursos pagos durante preparação de código.
8. Ao concluir mudança substantiva, atualizar `ESTADO-PORTAL-PARA-TCC.md` com
   evidência, ambiente e limites. Não editar a monografia.

Português no domínio e documentação. Routers finos, services tipados; leitura de
múltiplas linhas via `leitura.py`. No frontend, features verticais, configuração
via `src/config/env.ts` e branding via tenant autenticado. Fonte de referência para
deploy: `infra/deploy/README.md`; a comparação de provedores não é publicação.
