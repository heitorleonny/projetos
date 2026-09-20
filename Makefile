# Atalhos da stack do Portal FEJEPE.
# Requer Docker Desktop rodando. `make help` lista tudo.

.DEFAULT_GOAL := help
.PHONY: help up down dev test build logs ps clean lab lab-down front-build front-lint

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

clean: ## Derruba tudo e apaga volumes (PERDE os dados do laboratório)
	docker compose --profile dev --profile lab --profile test down -v

front-build: ## Build do frontend fora do Docker (verificação rápida)
	cd front_portal_fejepe && npm run build

front-lint: ## Lint do frontend
	cd front_portal_fejepe && npm run lint
