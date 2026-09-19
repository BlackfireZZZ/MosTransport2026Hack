.PHONY: setup sync-backend sync-ml up down logs dev dev-db dev-backend dev-frontend \
	dev-ml check backend-check frontend-check ml-check smoke migration migration-check

LOCAL_DATABASE_URL ?= postgresql+asyncpg://tramflow:tramflow_local@localhost:5432/tramflow

setup: sync-backend sync-ml
	cd frontend && npm ci

sync-backend:
	uv sync --package tramflow-backend --extra dev

sync-ml:
	uv sync --package tramflow-ml --extra dev

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

check: backend-check frontend-check
	$(MAKE) ml-check
	docker compose config --quiet

backend-check:
	uv run --package tramflow-backend ruff check backend
	uv run --package tramflow-backend mypy backend/app
	uv run --package tramflow-backend pytest backend/tests

frontend-check:
	cd frontend && npm run lint && npm run test -- --run && npm run build

ml-check:
	uv run --package tramflow-ml ruff check ml
	uv run --package tramflow-ml mypy ml/src

dev: dev-db
	$(MAKE) -j2 dev-backend-no-db dev-frontend

dev-db:
	docker compose up -d db

dev-backend: dev-db
	$(MAKE) dev-backend-no-db

dev-backend-no-db:
	DATABASE_URL=$(LOCAL_DATABASE_URL) uv run --package tramflow-backend alembic -c backend/alembic.ini upgrade head
	DATABASE_URL=$(LOCAL_DATABASE_URL) uv run --package tramflow-backend uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

dev-ml:
	uv run --package tramflow-ml tramflow-ml

smoke:
	./scripts/smoke.sh

migration:
	DATABASE_URL=$(LOCAL_DATABASE_URL) uv run --package tramflow-backend alembic -c backend/alembic.ini revision --autogenerate -m "$(NAME)"

migration-check:
	DATABASE_URL=$(LOCAL_DATABASE_URL) uv run --package tramflow-backend alembic -c backend/alembic.ini check
