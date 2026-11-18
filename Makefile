# Atalhos da stack do Portal das Federações.
# Requer Docker Desktop rodando. `make help` lista tudo.

.DEFAULT_GOAL := help

# Runtime PostgreSQL usa arquivo privado separado dos ambientes históricos.
COMPOSE = docker compose --env-file .env.docker

# Python do host para os scripts que rodam fora do Docker (a carga lê o .xlsx
# do disco e fala com o Postgres do lab em localhost:55432).
PYTHON ?= $(if $(wildcard .venv/bin/python),$(CURDIR)/.venv/bin/python,python3)
.PHONY: help up down dev dev-down test test-local check setup doctor build logs ps clean lab lab-down importar front-build front-lint front-test tools-build package demo-backend demo-frontend

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

docker-config: ## Gera .env.docker sem sobrescrever configuração existente
	$(PYTHON) scripts/configurar_docker.py

up: ## Sobe frontend, API e PostgreSQL (execute make docker-config antes)
	$(COMPOSE) up --build -d
	@echo "Portal: http://localhost:8080"

down: ## Derruba a stack
	$(COMPOSE) down

dev: up ## Sobe a aplicação PostgreSQL em Docker

dev-down: down ## Para a aplicação preservando o volume

test: ## Testa backend + RLS + migrações em banco descartável (exige Docker)
	@set -e; \
	trap 'docker compose --profile test rm -sf db-test >/dev/null' EXIT; \
	docker compose --profile test rm -sf db-test >/dev/null; \
	docker compose --profile test up -d --wait db-test; \
	docker compose --profile test logs --no-color db-test | awk '/ERROR|FATAL|WARNING/ {print; if ($$0 ~ /ERROR|FATAL/) falhou=1} END {exit falhou}'; \
	docker compose --profile test run --build --rm test

test-local: lab ## Testa no Python local contra o laboratório, sem aceitar testes pulados
	cd backend && $(PYTHON) -m pytest -q -rs --require-lab

ia-eval: ## Avalia modelo real (rede/custo): configure IA_* e IA_EVAL_TOKEN da demo
	cd backend && $(PYTHON) -m app.ia.avaliacao.runner $(if $(MODELO),--modelo "$(MODELO)",)

check: ## Verificação completa: backend/RLS, frontend e ferramenta auxiliar
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory front-test
	@$(MAKE) --no-print-directory front-build
	@$(MAKE) --no-print-directory front-lint
	@$(MAKE) --no-print-directory tools-build

setup: ## Instala dependências locais (Python 3.11+ e Node 22.12+)
	python3 -m venv .venv
	.venv/bin/python -m pip install -r backend/requirements-dev.lock
	cd frontend && npm ci
	cd tools/cluster-calculator && npm ci

doctor: ## Verifica ferramentas e ambiente sem mostrar credenciais
	$(PYTHON) scripts/doctor.py

build: ## Reconstrói as imagens sem subir
	$(COMPOSE) build

logs: ## Acompanha os logs da stack
	$(COMPOSE) logs -f

ps: ## Mostra o estado dos containers
	$(COMPOSE) ps

lab: ## Sobe só o Postgres do laboratório de dados do TCC
	docker compose --profile lab up -d --wait db
	@echo "Postgres do laboratório em localhost:$${POSTGRES_PORT:-55432}"

lab-down: ## Derruba o Postgres do laboratório (mantém o volume)
	docker compose --profile lab stop db

importar: ## Importa planilha do Portal BJ no lab: ARQUIVO=… ANO=2026 ESCOPO=--todas-federacoes|"--federacao fejepe" [DRY=1]
	@test -n "$(ARQUIVO)" || { echo "Informe ARQUIVO=caminho/da/exportacao.xlsx"; exit 2; }
	@test -n "$(ANO)" || { echo "Informe ANO=2026 (a planilha não traz o ano)"; exit 2; }
	@test -n "$(ESCOPO)" || { echo 'Informe ESCOPO=--todas-federacoes ou ESCOPO="--federacao <slug>" — não há default.'; exit 2; }
	cd backend && $(PYTHON) -m scripts.importar_planilha --arquivo "$(ARQUIVO)" --ano $(ANO) $(ESCOPO) $(if $(DRY),--dry-run,)

clean: ## Derruba tudo e apaga volumes (PERDE os dados do laboratório)
	docker compose --profile dev --profile lab --profile test down -v

front-build: ## Build do frontend fora do Docker (verificação rápida)
	cd frontend && npm run build

front-lint: ## Lint do frontend
	cd frontend && npm run lint

front-test: ## Testa onboarding por conta, paleta e URLs de fotos
	cd frontend && npm test

tools-build: ## Compila a calculadora auxiliar de cluster
	cd tools/cluster-calculator && npm run build

package: ## Empacota todo o código atual sem ambientes, builds ou dados reais
	$(PYTHON) scripts/preparar_entrega.py

.PHONY: deploy-check
deploy-check: ## Verifica contratos de deploy VPS e regressão, sem publicar
	$(PYTHON) infra/deploy/test-check-env.py
	$(PYTHON) -m unittest discover -s scripts -p test_regressao_api.py -v
	docker compose --env-file infra/deploy/aws.env.example -f infra/deploy/compose.aws.yml config --quiet
	docker compose -p portal-federacoes -f docker-compose.yml -f infra/deploy/vps-fejepe/compose.prod.yml --env-file infra/deploy/vps-fejepe/env.prod.example config --quiet
	for s in infra/deploy/vps-fejepe/*.sh; do bash -n "$$s" || exit 1; done

# ── HISTÓRICO: demonstração Supabase (não usar na entrega PostgreSQL) ─────────────────────
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
DEMO_CONTAINER_DB := supabase_db_$(DEMO_PROJETO)
DEMO_DSN      ?= postgresql://postgres:postgres@127.0.0.1:$(DEMO_DB_PORT)/postgres
# Senha do papel de carga. Valor padrão de DESENVOLVIMENTO, sobrescrevível por
# ambiente — nunca escrita em SQL versionado.
INGESTAO_SENHA ?= app_ingestao
INGESTAO_DSN_DEMO := postgresql://app_ingestao:$(INGESTAO_SENHA)@127.0.0.1:$(DEMO_DB_PORT)/postgres

.PHONY: demo demo-schema demo-reset demo-stop demo-dados demo-seed demo-tudo demo-status demo-smoke

demo: ## Sobe a stack Supabase de demonstração e aplica o schema (01..NN)
	$(PYTHON) scripts/demo_local.py preparar

demo-schema: ## Aplica migrações em demo nova com ledger; recusa banco legado
	$(PYTHON) scripts/demo_local.py esquema
	@# O papel `ingestao` (NOLOGIN) nasce na migração 10. O login dele NÃO:
	@# a 10 só cria `app_ingestao` quando `supabase_auth_admin` não existe —
	@# isto é, só no laboratório. Aqui esse role existe, então o login é
	@# criado pelo operador, que é exatamente o que este bloco faz.
	@set -e; \
	if [ -z "$$(psql "$(DEMO_DSN)" -tAc "SELECT 1 FROM pg_roles WHERE rolname='app_ingestao'")" ]; then \
		echo "CREATE ROLE app_ingestao LOGIN PASSWORD :'senha' IN ROLE ingestao" \
			| psql "$(DEMO_DSN)" -v ON_ERROR_STOP=1 -q -v senha="$(INGESTAO_SENHA)"; \
		echo "→ papel app_ingestao criado"; \
	else \
		echo "ALTER ROLE app_ingestao LOGIN PASSWORD :'senha'" \
			| psql "$(DEMO_DSN)" -v ON_ERROR_STOP=1 -q -v senha="$(INGESTAO_SENHA)"; \
		echo "→ papel app_ingestao já existia; senha atualizada"; \
	fi
	@# GRANT USAGE ON SCHEMA auth: a migração 10 tenta, e aqui ela FALHA EM
	@# SILÊNCIO ("WARNING: no privileges were granted for auth"). O schema `auth`
	@# pertence a `supabase_admin`, e o `postgres` da CLI não é membro dele nem
	@# superusuário — então não tem o que conceder. Sem esta linha, `ingestao`
	@# leva "permission denied for schema auth" ao avaliar QUALQUER política de
	@# RLS, porque todas chamam auth.jwt(), e a carga inteira morre.
	@# No laboratório isso nunca apareceu: lá o shim cria o schema `auth` como
	@# dono do banco, e o GRANT da 10 funciona. Ver o resumo da sessão de 22/09.
	docker exec $(DEMO_CONTAINER_DB) psql -U supabase_admin -d postgres -q \
		-v ON_ERROR_STOP=1 -c "GRANT USAGE ON SCHEMA auth TO ingestao;"
	@echo "→ USAGE em schema auth concedido a ingestao (via supabase_admin)"
	@echo "Schema aplicado. Studio: http://localhost:54423"

demo-dados: ## Carrega a planilha nacional na demo: ARQUIVO=… ANO=2026 [DRY=1]
	@test -n "$(ARQUIVO)" || { echo "Informe ARQUIVO=caminho/da/exportacao.xlsx"; exit 2; }
	@test -n "$(ANO)" || { echo "Informe ANO=2026 (a planilha não traz o ano)"; exit 2; }
	cd backend && $(PYTHON) -m scripts.importar_planilha --arquivo "$(ARQUIVO)" \
		--ano $(ANO) --todas-federacoes --dsn "$(INGESTAO_DSN_DEMO)" $(if $(DRY),--dry-run,)

demo-seed: ## Cria os usuários de teste (Auth + tabela usuario) na demo
	cd backend && $(PYTHON) -m scripts.seed_demo

demo-tudo: ## Do zero até o portal navegável: stack + schema + dados + usuários
	@test -n "$(ARQUIVO)" -a -n "$(ANO)" || { echo "Informe ARQUIVO=... ANO=2026"; exit 2; }
	@$(MAKE) --no-print-directory demo
	@$(MAKE) --no-print-directory demo-dados ARQUIVO="$(ARQUIVO)" ANO="$(ANO)"
	@$(MAKE) --no-print-directory demo-seed

demo-status: ## Mostra URLs e chaves da stack de demonstração
	supabase status

demo-stop: ## Para a stack de demonstração, preservando os dados
	supabase stop --project-id $(DEMO_PROJETO)

demo-backend: ## Inicia a API no host contra a demo, configurando as chaves automaticamente
	$(PYTHON) scripts/demo_local.py backend

demo-frontend: ## Inicia o Vite no host contra a demo, configurando a chave pública
	$(PYTHON) scripts/demo_local.py frontend

demo-smoke: ## Verifica login, endpoints e isolamento na demo (requer dados e usuários)
	$(PYTHON) scripts/demo_local.py verificar

demo-reset: ## Derruba a demo APAGANDO os volumes e recria do zero (stack + schema)
	supabase stop --project-id $(DEMO_PROJETO) --no-backup
	@$(MAKE) --no-print-directory demo
