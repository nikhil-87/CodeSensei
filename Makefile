# ============================================================================
# CodeSensei — developer convenience targets
# ============================================================================
# Works on Linux, macOS, and Windows (with `make` via Git Bash / WSL / choco).
# All targets are thin wrappers around docker compose / npm / pytest so they
# remain debuggable individually.
# ============================================================================

SHELL          := /bin/bash
COMPOSE        := docker compose -f docker/docker-compose.yml --env-file .env
COMPOSE_DEV    := docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml --env-file .env
COMPOSE_OBS    := docker compose -f docker/docker-compose.observability.yml --env-file .env
PY             := python
PIP            := pip
NPM            := npm

.DEFAULT_GOAL  := help

# ----- meta -----------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n\nTargets:\n"} \
	      /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ----- stack lifecycle ------------------------------------------------------
.PHONY: up
up: ## Start the full stack in detached mode
	$(COMPOSE) up -d --build

.PHONY: up-dev
up-dev: ## Start stack with dev overrides (hot reload, volume mounts)
	$(COMPOSE_DEV) up -d --build

.PHONY: down
down: ## Stop and remove containers (preserves volumes)
	$(COMPOSE) down

.PHONY: nuke
nuke: ## Stop containers AND delete all volumes (DESTRUCTIVE)
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

.PHONY: ps
ps: ## List running services
	$(COMPOSE) ps

.PHONY: restart
restart: ## Restart all services
	$(COMPOSE) restart

# ----- observability --------------------------------------------------------
.PHONY: obs-up
obs-up: ## Start Prometheus + Grafana
	$(COMPOSE_OBS) up -d

.PHONY: obs-down
obs-down: ## Stop Prometheus + Grafana
	$(COMPOSE_OBS) down

# ----- AI models ------------------------------------------------------------
.PHONY: pull-models
pull-models: ## Pull DeepSeek + nomic-embed-text via Ollama
	bash scripts/pull-models.sh

# ----- backend --------------------------------------------------------------
.PHONY: backend-install
backend-install: ## Install backend deps in local venv
	cd backend && $(PIP) install -e ".[dev]"

.PHONY: backend-run
backend-run: ## Run backend locally (no Docker)
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: backend-test
backend-test: ## Run backend unit + integration tests
	cd backend && pytest -v --cov=app --cov-report=term-missing

.PHONY: backend-lint
backend-lint: ## Lint backend with Ruff + mypy
	cd backend && ruff check app tests && mypy app

.PHONY: backend-format
backend-format: ## Format backend with Ruff
	cd backend && ruff format app tests

# ----- worker ---------------------------------------------------------------
.PHONY: worker-run
worker-run: ## Run worker locally
	cd worker && $(PY) -m app.worker

# ----- analysis engine ------------------------------------------------------
.PHONY: engine-test
engine-test: ## Run analysis-engine unit tests
	cd analysis-engine && pytest -v --cov=engine

# ----- frontend -------------------------------------------------------------
.PHONY: frontend-install
frontend-install: ## Install frontend deps
	cd frontend && $(NPM) ci

.PHONY: frontend-run
frontend-run: ## Run Vite dev server
	cd frontend && $(NPM) run dev

.PHONY: frontend-build
frontend-build: ## Production build
	cd frontend && $(NPM) run build

.PHONY: frontend-test
frontend-test: ## Run React Testing Library tests
	cd frontend && $(NPM) test

.PHONY: frontend-e2e
frontend-e2e: ## Run Playwright E2E tests
	cd frontend && $(NPM) run test:e2e

.PHONY: frontend-lint
frontend-lint: ## Lint frontend with ESLint
	cd frontend && $(NPM) run lint

# ----- database -------------------------------------------------------------
.PHONY: db-migrate
db-migrate: ## Apply Alembic migrations
	$(COMPOSE) exec backend alembic upgrade head

.PHONY: db-revision
db-revision: ## Generate a new Alembic revision (use MSG="...")
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(MSG)"

.PHONY: db-shell
db-shell: ## Open psql in the postgres container
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

# ----- testing (all) --------------------------------------------------------
.PHONY: test
test: backend-test engine-test frontend-test ## Run every test suite

# ----- linting (all) --------------------------------------------------------
.PHONY: lint
lint: backend-lint frontend-lint ## Run every linter

# ----- health ---------------------------------------------------------------
.PHONY: health
health: ## Hit health endpoints on every service
	bash scripts/health-check.sh
