SHELL := /bin/sh

.PHONY: bootstrap setup doctor frontend-install sync-backend sync-ml \
	up down logs dev dev-db dev-backend dev-backend-no-db dev-frontend dev-ml \
	check verify-fast verify verify-full backend-check frontend-check ml-check \
	ml-eval architecture-check contract-generate contract-check e2e e2e-install \
	compose-check migration migration-check migration-verify stack-verify smoke \
	agent-create agent-up agent-smoke agent-down agent-remove

PYTHON_VERSION := $(shell tr -d '[:space:]' < .python-version)
NODE_VERSION := $(shell tr -d '[:space:]' < .node-version)
UV_VERSION ?= 0.12.13
POSTGRES_PORT ?= 5432
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 8080
LOCAL_DATABASE_URL ?= postgresql+asyncpg://tramflow:tramflow_local@localhost:$(POSTGRES_PORT)/tramflow

# Reproduce the dependency state from the committed lock files.
bootstrap: sync-backend sync-ml frontend-install

# Backward-compatible alias used by the README and existing workflows.
setup: bootstrap

doctor:
	@PYTHON_VERSION=$(PYTHON_VERSION) NODE_VERSION=$(NODE_VERSION) UV_VERSION=$(UV_VERSION) ./scripts/doctor.sh

sync-backend:
	uv sync --package tramflow-backend --extra dev --locked

sync-ml:
	uv sync --package tramflow-ml --extra dev --locked

frontend-install:
	cd frontend && npm ci

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

# Fast, deterministic checks that do not require a running database.
verify-fast: architecture-check backend-check ml-check ml-eval frontend-check contract-check compose-check

# Default proof gate: fast checks plus migrations on a disposable clean database.
verify: verify-fast migration-verify

# Backward-compatible alias required by AGENTS.md.
check: verify-fast

# Full proof gate additionally builds and exercises the production-like stack.
verify-full: verify stack-verify e2e

architecture-check:
	uv run --no-project python scripts/architecture_check.py

backend-check:
	uv run --package tramflow-backend ruff check backend
	uv run --package tramflow-backend mypy backend/app
	uv run --package tramflow-backend pytest backend/tests

frontend-check:
	cd frontend && npm run lint && npm run test -- --run && npm run build

ml-check:
	uv run --package tramflow-ml ruff check ml
	uv run --package tramflow-ml mypy ml/src
	uv run --package tramflow-ml pytest ml/tests

ml-eval:
	uv run --package tramflow-ml tramflow-ml evaluate

contract-generate:
	uv run --package tramflow-backend python scripts/export_openapi.py
	cd frontend && npm run api:generate

contract-check:
	cd frontend && npm run contract:check

e2e-install:
	cd frontend && npm run test:e2e:install

e2e:
	cd frontend && npm run test:e2e

compose-check:
	docker compose config --quiet

dev: dev-db
	$(MAKE) -j2 dev-backend-no-db dev-frontend

dev-db:
	POSTGRES_PORT=$(POSTGRES_PORT) docker compose up -d db

dev-backend: dev-db
	$(MAKE) dev-backend-no-db

dev-backend-no-db:
	DATABASE_URL=$(LOCAL_DATABASE_URL) uv run --package tramflow-backend alembic -c backend/alembic.ini upgrade head
	DATABASE_URL=$(LOCAL_DATABASE_URL) uv run --package tramflow-backend uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $(BACKEND_PORT) --reload

dev-frontend:
	cd frontend && npm run dev

dev-ml:
	uv run --package tramflow-ml tramflow-ml

smoke:
	BASE_URL=$${BASE_URL:-http://localhost:$(BACKEND_PORT)} \
	FRONTEND_URL=$${FRONTEND_URL:-http://localhost:$(FRONTEND_PORT)} \
	./scripts/smoke.sh

migration:
	DATABASE_URL=$(LOCAL_DATABASE_URL) uv run --package tramflow-backend alembic -c backend/alembic.ini revision --autogenerate -m "$(NAME)"

migration-check:
	DATABASE_URL=$(LOCAL_DATABASE_URL) uv run --package tramflow-backend alembic -c backend/alembic.ini check

# Runs upgrade and autogenerate drift detection against a newly-created volume.
migration-verify:
	@set -eu; \
	eval "$$(./scripts/agent-env.sh env migration-verify)"; \
	project="$$COMPOSE_PROJECT_NAME"; \
	cleanup() { docker compose --project-name "$$project" down -v --remove-orphans >/dev/null 2>&1 || true; }; \
	trap cleanup EXIT INT TERM; \
	cleanup; \
	docker compose --project-name "$$project" up -d --build db; \
	docker compose --project-name "$$project" run --rm migrate; \
	docker compose --project-name "$$project" run --rm migrate /workspace/.venv/bin/alembic check

# Uses an isolated Compose project so it cannot overwrite the developer's stack.
stack-verify:
	@set -eu; \
	eval "$$(./scripts/agent-env.sh env verify-full)"; \
	cleanup() { docker compose down -v --remove-orphans >/dev/null 2>&1 || true; }; \
	trap cleanup EXIT INT TERM; \
	cleanup; \
	docker compose up --build --wait; \
	BASE_URL="http://localhost:$$BACKEND_PORT" FRONTEND_URL="http://localhost:$$FRONTEND_PORT" ./scripts/smoke.sh

# Large tasks can get a dedicated branch/worktree plus an isolated Compose stack.
# Usage: make agent-create ID=forecast-contract REF=HEAD
agent-create:
	@test -n "$(ID)" || { echo "ID is required (example: make agent-create ID=forecast-contract)" >&2; exit 2; }
	@./scripts/agent-env.sh create "$(ID)" "$(or $(REF),HEAD)"

agent-up:
	@test -n "$(ID)" || { echo "ID is required" >&2; exit 2; }
	@set -eu; \
	worktree="$$(./scripts/agent-env.sh path "$(ID)")"; \
	eval "$$(./scripts/agent-env.sh env "$(ID)")"; \
	cd "$$worktree"; \
	docker compose up --build -d --wait; \
	printf 'Agent stack %s: UI http://localhost:%s, API http://localhost:%s\n' "$(ID)" "$$FRONTEND_PORT" "$$BACKEND_PORT"

agent-smoke:
	@test -n "$(ID)" || { echo "ID is required" >&2; exit 2; }
	@set -eu; \
	worktree="$$(./scripts/agent-env.sh path "$(ID)")"; \
	eval "$$(./scripts/agent-env.sh env "$(ID)")"; \
	cd "$$worktree"; \
	BASE_URL="http://localhost:$$BACKEND_PORT" FRONTEND_URL="http://localhost:$$FRONTEND_PORT" ./scripts/smoke.sh

agent-down:
	@test -n "$(ID)" || { echo "ID is required" >&2; exit 2; }
	@set -eu; \
	worktree="$$(./scripts/agent-env.sh path "$(ID)")"; \
	eval "$$(./scripts/agent-env.sh env "$(ID)")"; \
	cd "$$worktree"; \
	docker compose down -v --remove-orphans

# Refuses dirty worktrees and preserves the agent branch for recovery/review.
agent-remove: agent-down
	@test -n "$(ID)" || { echo "ID is required" >&2; exit 2; }
	@./scripts/agent-env.sh remove "$(ID)"
