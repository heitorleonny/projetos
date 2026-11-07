# Verificação técnica — backend, frontend, banco e execução

Atualização após a auditoria de métricas de 04/10: a suíte completa passou com
**383 testes e 5 avisos**; o build, o lint e a verificação integrada da demo
também passaram. Os números de 377 testes abaixo registram a etapa operacional
anterior. As correções e pendências dos dados estão em
`docs/auditoria-estatica-metricas-2026-10-04.md`; a conferência do segundo
tenant está em `docs/auditoria-segundo-tenant-2026-10-04.md`.

- Início: 03/10/2026. Conclusão: 04/10/2026.
- Ambiente: macOS, Python 3.13 no host e 3.12 no container, Node 24,
  PostgreSQL 16 no laboratório/testes e stack Supabase local de demonstração.
- Branch: `feat/painel-admin`, HEAD `e84fa5b`, com alterações anteriores à revisão
  e as correções desta tarefa ainda não commitadas.
- Escopo: verificar a aplicação existente e tornar sua execução/testes repetíveis.
  Produção, publicação, correções de regras de negócio e implementação de IA
  não fizeram parte desta verificação.

## Resultado reproduzível

| Verificação | Comando | Resultado |
|---|---|---|
| Backend e migrações em banco novo | `make test` | **377 passados, 0 falhos, 0 pulados** |
| TypeScript e bundle | `make front-build` | aprovado |
| ESLint | `make front-lint` | aprovado, sem erros ou avisos |
| Fluxo integrado | `make check` | aprovado de ponta a ponta na execução final, com 377 testes |
| Dependências e Docker | `make doctor` | ferramentas e ambiente encontrados |
| Configuração Compose | `docker compose config --quiet` | válida |
| Demo preservando banco existente | `make demo` | aprovado, sem reaplicar migrações históricas |
| Login/API com Supabase real | `make demo-smoke` | aprovado para FEJEPE, FEJEMG e operador |
| Qualidade do diff | `git diff --check` | aprovado |

A primeira execução, com Docker desligado, teve 262 passados e **113 pulados**.
Depois de iniciar o laboratório, os 375 testes então existentes passaram sem
pulos. Os dois testes acrescentados cobrem convite sem configuração: não pode
criar cadastro órfão e deve devolver HTTP 503.

No container, os 377 testes emitiram cinco avisos de depreciação de dependências
(Starlette/AnyIO e Supabase/PostgREST). Não houve ERROR/FATAL na inicialização do banco descartável. Houve um
WARNING do initdb da imagem Alpine (`no usable system locales were found`),
sem impedir as migrações. O log foi conferido antes de executar os testes.
Esses resultados não substituem os testes de caracterização das fórmulas (A3).

O modo estrito foi verificado apontando o teste de RLS para uma porta local
inacessível: pytest pulou os testes, mas `--require-lab` fez o processo terminar
com código **1**. Assim, banco indisponível não produz uma verificação completa
aparentemente bem-sucedida.

## Correções realizadas

1. **Execução de testes:** `make test` agora usa um serviço `db-test` independente,
   com armazenamento temporário e todas as migrações desde `00`. Aguarda o banco
   saudável, confere o log da inicialização, conecta os testes pelos três papéis
   corretos e remove apenas esse serviço ao terminar. Não apaga lab ou demo.
2. **Desenvolvimento:** `make dev` seleciona explicitamente `backend-dev` e
   `frontend-dev`, evitando subir simultaneamente os serviços padrão que ocupam
   a mesma porta. Passa também as configurações necessárias ao painel admin.
   A configuração foi validada; a navegação desta revisão usou os comandos no host.
3. **Demo:** `scripts/demo_local.py` descobre URL/chaves na CLI, configura os
   processos sem gravar `.env`, e oferece `demo-backend`/`demo-frontend`.
   `demo` reutiliza um banco existente e verifica objetos das migrações 13–15,
   em vez de reaplicar a migração 04. Não é um gerenciador de migrações pendentes.
4. **Frontend:** Eventos deriva a seleção inicial dos dados e limpa a expansão
   na troca de evento. Simulação deriva os totais da API, mantendo edições
   manuais em estado próprio. Foram removidos os três erros de setState em
   effects encontrados pelo lint, sem alterar as fórmulas de cálculo.
5. **Convite:** ausência de chave de serviço é detectada antes da inserção do
   usuário. A API responde 503; não deixa um cadastro que impediria nova tentativa
   por conflito de e-mail. O cliente privilegiado continua sendo criado somente
   depois da inserção autorizada pela RLS.
6. **Roteiro:** README, guia de execução e documentação operacional foram
   atualizados; `doctor`, `setup`, `check`, `test-local` e `demo-smoke` estão
   disponíveis na raiz. `.venv/` e `__pycache__/` da raiz ficam ignorados.

## Backend e frontend na demo

`demo-smoke` autentica as 27 contas das federações e o operador no GoTrue e usa o FastAPI
TestClient com PostgREST real. Verifica:

- autenticação obrigatória nas rotas protegidas;
- branding da federação do usuário;
- todas as páginas de EJs, sem duplicatas ou perda frente a `meta.total`;
- total dos indicadores consistente com a listagem;
- indicadores, ritmo, SDE, ranking e eventos;
- perfil de EJ, comparação e endpoints de leitura do painel;
- listagens disjuntas entre FEJEPE e FEJEMG;
- HTTP 404 para consulta direta à EJ de outro tenant;
- operador limitado à FEJEPE nos dados de EJ, apesar do alcance administrativo.
- uma conta admin ativa e vinculada por federação e 1.507 EJs distribuídas entre os tenants.

Conferência manual no navegador local:

- FEJEPE: login, Dashboard, evento Ciranda, Simulação e painel administrativo.
- Simulação: editar total, incrementar subida e Resetar; resultado responde às
  entradas e Resetar limpa os movimentos, mantendo os totais editados.
- FEJEMG: branding e Dashboard, Cluster Track, Indicadores, Comparação e estado
  vazio de Eventos. Sem erros de execução no console nas páginas conferidas.
- Operador: acesso às abas Importar planilha, Federações e Usuários; listas
  carregadas sem erros de execução no console.

Esta navegação foi uma verificação de funcionamento, não uma avaliação completa
com usuários. Não foram enviados convites, alterados cadastros ou importados
arquivos reais durante a navegação. As regras de escrita/RLS e ingestão são
exercitadas pela suíte com dados sintéticos.

## Estrutura do banco

Consulta versionada, somente leitura e sem exposição de dados individuais:
`infra/db/queries/verificar-estrutura.sql`.

```bash
psql postgresql://portal:portal@127.0.0.1:55432/portal_lab \
  -X -v ON_ERROR_STOP=1 -f infra/db/queries/verificar-estrutura.sql
psql postgresql://postgres:postgres@127.0.0.1:54422/postgres \
  -X -v ON_ERROR_STOP=1 -f infra/db/queries/verificar-estrutura.sql
```

Verificado no lab e na demo:

- dez tabelas de domínio, todas com RLS ativa;
- FKs, chaves naturais, políticas e índices presentes, incluindo índices por
  federação e os caminhos de EJ/núcleo/federação em metas e monitoramento;
- restrição `num_nonnulls(...) = 1` nos donos de metas e monitoramento;
- papéis `anon`, `authenticated`, `ingestao` e `app_ingestao` sem superusuário
  nem BYPASSRLS; no lab, `app_authenticated` também sem esses privilégios;
- zero EJs vinculadas a núcleo de outra federação na consulta de consistência.

As migrações 00–15 foram aplicadas do zero no banco descartável. A demo existente
foi inspecionada e usada nos testes HTTP; **não foi resetada**. Nenhuma migração
histórica foi editada, e `infra/db/init/` continua sendo a fonte do schema.

### Pendência de segurança confirmada — A2

Na demo, `anon` e `authenticated` ainda recebem privilégios amplos nas tabelas
que não tiveram revogação explícita pela migração 13. A consulta de privilégios
mostra `TRUNCATE` em oito tabelas para cada papel e SELECT de tabela inteira
para `anon` em `federacao`.

Isso confirma o achado já registrado no ADR-003. RLS protege as consultas de
linhas testadas, mas não controla TRUNCATE. O PostgREST não expõe TRUNCATE
pela API; portanto, esse privilégio não significa que a rota HTTP de leitura
permita truncar tabelas. Ainda assim, os privilégios precisam ser revogados
pela migração nova planejada (A2), com validação na stack Supabase.

A decisão sobre `ALTER DEFAULT PRIVILEGES` permanece aberta no contexto do
projeto. Esta revisão registrou a evidência; não alterou esses privilégios nem
considera o banco pronto para publicação multi-tenant em produção.

## Branches

```bash
git rev-list --left-right --count main...HEAD
# 0 37
git rev-list --left-right --count feat/multi-tenant-fases-1-3...HEAD
# 0 0
git worktree list
# um checkout, em feat/painel-admin
```

A branch atual contém toda a `main` local. A antiga branch multi-tenant aponta
para o mesmo commit. Não há trabalho divergente a incorporar por merge.
As referências antigas foram preservadas e o desenvolvimento segue na branch
atual. Nenhum commit, push, merge ou descarte de alterações foi necessário.

## Pendências para as próximas tarefas

- **A2:** revogar privilégios amplos e decidir o tratamento dos privilégios padrão.
- **A3/A4:** caracterizar cálculos antes de corrigir a escala do cluster adaptativo.
- **Regras no frontend:** o simulador ainda contém a fórmula de SDE, já inventariada
  em `docs/regras-de-negocio.md` §8.4; retirar essas fórmulas é uma mudança própria.
- **A0:** revisar e organizar commits do trabalho acumulado, quando solicitados;
  a árvore permanece com alterações locais e não foi enviada ao GitHub.
- **A1:** atualizar os demais documentos históricos, incluindo `banco.md` a partir
  de dump de schema; a revisão operacional não reescreveu toda a documentação.

Nenhum dado real de EJ foi adicionado a fixture, documento ou commit. Logs
locais de diagnóstico ficaram em `/tmp`, sem chaves ou valores individuais.
