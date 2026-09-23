# Atalhos da stack do Portal FEJEPE.
# Requer Docker Desktop rodando. `make help` lista tudo.

.DEFAULT_GOAL := help

# Python do host para os scripts que rodam fora do Docker (a carga lê o .xlsx
# do disco e fala com o Postgres do lab em localhost:55432).
PYTHON ?= $(if $(wildcard .venv/bin/python),$(CURDIR)/.venv/bin/python,python3)
.PHONY: help up down dev test build logs ps clean lab lab-down importar front-build front-lint

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

up: ## Sobe a stack (frontend :8080, backend :8000)
	docker compose up --build -d
	@echo "Frontend: http://localhost:8080   API: http://localhost:8000/docs"

down: ## Derruba a stack
	docker compose down

dev: ## Sobe em modo desenvolvimento com hot reload (Vite :5173)
	docker compose --profile dev up --build

test: ## Roda a suíte de testes do backend dentro do container
	docker compose --profile test run --rm test

build: ## Reconstrói as imagens sem subir
	docker compose build

logs: ## Acompanha os logs da stack
	docker compose logs -f

ps: ## Mostra o estado dos containers
	docker compose ps

lab: ## Sobe só o Postgres do laboratório de dados do TCC
	docker compose --profile lab up -d db
	@echo "Postgres do laboratório em localhost:$${POSTGRES_PORT:-55432}"

lab-down: ## Derruba o Postgres do laboratório (mantém o volume)
	docker compose --profile lab stop db

importar: ## Importa planilha do Portal BJ no lab: ARQUIVO=… ANO=2026 ESCOPO=--todas-federacoes|"--federacao fejepe" [DRY=1]
	@test -n "$(ARQUIVO)" || { echo "Informe ARQUIVO=caminho/da/exportacao.xlsx"; exit 2; }
	@test -n "$(ANO)" || { echo "Informe ANO=2026 (a planilha não traz o ano)"; exit 2; }
	@test -n "$(ESCOPO)" || { echo 'Informe ESCOPO=--todas-federacoes ou ESCOPO="--federacao <slug>" — não há default.'; exit 2; }
	cd portal_fejepe && $(PYTHON) -m scripts.importar_planilha --arquivo "$(ARQUIVO)" --ano $(ANO) $(ESCOPO) $(if $(DRY),--dry-run,)

clean: ## Derruba tudo e apaga volumes (PERDE os dados do laboratório)
	docker compose --profile dev --profile lab --profile test down -v

front-build: ## Build do frontend fora do Docker (verificação rápida)
	cd front_portal_fejepe && npm run build

front-lint: ## Lint do frontend
	cd front_portal_fejepe && npm run lint

# ── Ambiente de DEMONSTRAÇÃO (stack Supabase completa) ─────────────────────
#
# Outro ambiente, outra finalidade — não substitui o `make lab`:
#
#   make lab   → 1 container, Postgres puro na 55432, shim de auth.jwt().
#                É onde `pytest -q` roda os testes de RLS, rápido.
#   make demo  → a stack inteira (Postgres + PostgREST + GoTrue + Studio).
#                É onde se ABRE A TELA e se olha, com login de verdade.
#
# O shim não serve para o segundo caso: ele replica `auth.jwt()`, não o GoTrue
# que emite o token. Ver docs/adr-002-rls-local-sem-stack-completa.md.
#
# As migrações NÃO são copiadas para supabase/migrations/: `infra/db/init/` é
# fonte única, e duas cópias divergiriam na primeira migração nova. Por isso o
# schema entra por psql, e não por `supabase db reset`.

DEMO_PROJETO  := portal-fejepe-demo
DEMO_DB_PORT  ?= 54422
DEMO_DSN      ?= postgresql://postgres:postgres@127.0.0.1:$(DEMO_DB_PORT)/postgres
# Senha do papel de carga. Valor padrão de DESENVOLVIMENTO, sobrescrevível por
# ambiente — nunca escrita em SQL versionado.
INGESTAO_SENHA ?= app_ingestao
INGESTAO_DSN_DEMO := postgresql://app_ingestao:$(INGESTAO_SENHA)@127.0.0.1:$(DEMO_DB_PORT)/postgres

.PHONY: demo demo-schema demo-reset demo-stop demo-dados demo-seed demo-tudo demo-status

demo: ## Sobe a stack Supabase de demonstração e aplica o schema (01..12)
	supabase start
	@$(MAKE) --no-print-directory demo-schema

demo-schema: ## Aplica infra/db/init/01..12 na stack de demonstração (pula o 00)
	@set -e; \
	for arquivo in $$(ls infra/db/init/*.sql | grep -v '/00-'); do \
		echo "→ $$arquivo"; \
		psql "$(DEMO_DSN)" -v ON_ERROR_STOP=1 -q -f "$$arquivo"; \
	done
	@# O papel `ingestao` (NOLOGIN) nasce na migração 10. O login dele NÃO:
	@# a 10 só cria `app_ingestao` quando `supabase_auth_admin` não existe —
	@# isto é, só no laboratório. Aqui esse role existe, então o login é
	@# criado pelo operador, que é exatamente o que este bloco faz.
	@set -e; \
	if [ -z "$$(psql "$(DEMO_DSN)" -tAc "SELECT 1 FROM pg_roles WHERE rolname='app_ingestao'")" ]; then \
		psql "$(DEMO_DSN)" -v ON_ERROR_STOP=1 -q -v senha="$(INGESTAO_SENHA)" \
			-c "CREATE ROLE app_ingestao LOGIN PASSWORD :'senha' IN ROLE ingestao"; \
		echo "→ papel app_ingestao criado"; \
	else \
		psql "$(DEMO_DSN)" -v ON_ERROR_STOP=1 -q -v senha="$(INGESTAO_SENHA)" \
			-c "ALTER ROLE app_ingestao LOGIN PASSWORD :'senha'"; \
		echo "→ papel app_ingestao já existia; senha atualizada"; \
	fi
	@echo "Schema aplicado. Studio: http://localhost:54423"

demo-dados: ## Carrega a planilha nacional na demo: ARQUIVO=… ANO=2026 [DRY=1]
	@test -n "$(ARQUIVO)" || { echo "Informe ARQUIVO=caminho/da/exportacao.xlsx"; exit 2; }
	@test -n "$(ANO)" || { echo "Informe ANO=2026 (a planilha não traz o ano)"; exit 2; }
	cd portal_fejepe && $(PYTHON) -m scripts.importar_planilha --arquivo "$(ARQUIVO)" \
		--ano $(ANO) --todas-federacoes --dsn "$(INGESTAO_DSN_DEMO)" $(if $(DRY),--dry-run,)

demo-seed: ## Cria os usuários de teste (Auth + tabela usuario) na demo
	cd portal_fejepe && $(PYTHON) -m scripts.seed_demo

demo-tudo: ## Do zero até o portal navegável: stack + schema + dados + usuários
	@$(MAKE) --no-print-directory demo
	@$(MAKE) --no-print-directory demo-dados ARQUIVO="$(ARQUIVO)" ANO="$(ANO)"
	@$(MAKE) --no-print-directory demo-seed

demo-status: ## Mostra URLs e chaves da stack de demonstração
	supabase status

demo-stop: ## Para a stack de demonstração, preservando os dados
	supabase stop --project-id $(DEMO_PROJETO)

demo-reset: ## Derruba a demo APAGANDO os volumes e recria do zero (stack + schema)
	supabase stop --project-id $(DEMO_PROJETO) --no-backup
	@$(MAKE) --no-print-directory demo
