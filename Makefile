# last30days ADK Agent — Development & Deployment
# ==================================================

.PHONY: install setup run web playground api local-backend test test-agent eval lint docker-build docker-run deploy deploy-env sync clean help

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

install: ## Install dependencies with uv
	@command -v uv >/dev/null || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv sync

setup: install ## First-time setup: install deps + create .env
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example — edit it to add your API keys."; \
	else \
		echo ".env already exists."; \
	fi

# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------

run: ## Run agent in terminal (interactive chat)
	uv run adk run app

web: ## Launch ADK dev UI (browser-based chat + traces)
	uv run adk web app

playground: ## Launch ADK playground with auto-reload
	uv run adk web app --port 8501 --reload_agents

api: ## Start ADK API server on port 8000
	uv run adk api_server app

local-backend: ## Start FastAPI backend (Cloud Run parity) on port 8000
	uv run uvicorn app.fast_api_app:app --host localhost --port 8000 --reload

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: ## Run existing test suite
	cd scripts && python3 -m pytest ../tests/ -x -q

test-agent: ## Quick smoke test of the ADK agent import
	uv run python -c "from app.agent import root_agent, app; print('Agent:', root_agent.name); print('App:', app.name); print('Tools:', [t.__name__ for t in root_agent.tools])"

eval: ## Run ADK evaluation suite
	uv run python -m google.adk.eval tests/eval/eval_config.json

lint: ## Lint with ruff
	uv run ruff check app/
	uv run ruff format --check app/

# ---------------------------------------------------------------------------
# Docker (local)
# ---------------------------------------------------------------------------

docker-build: ## Build container image
	docker build -t last30days-agent .

docker-run: docker-build ## Run container locally
	docker run --rm -p 8080:8080 --env-file .env last30days-agent

# ---------------------------------------------------------------------------
# Deploy to Google Cloud Run
# ---------------------------------------------------------------------------

PROJECT ?= $(shell gcloud config get-value project 2>/dev/null)
REGION  ?= us-central1
SERVICE ?= last30days-agent

deploy: ## Deploy to Cloud Run (set PROJECT and REGION if needed)
	@echo "Deploying to Cloud Run: $(PROJECT) / $(REGION)"
	gcloud run deploy $(SERVICE) \
		--project $(PROJECT) \
		--region $(REGION) \
		--source . \
		--allow-unauthenticated \
		--set-env-vars "GOOGLE_CLOUD_PROJECT=$(PROJECT),GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_LOCATION=$(REGION)"

deploy-env: ## Deploy with all keys from .env file
	@echo "Deploying to Cloud Run with env vars from .env"
	gcloud run deploy $(SERVICE) \
		--project $(PROJECT) \
		--region $(REGION) \
		--source . \
		--allow-unauthenticated \
		--env-vars-file .env

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

sync: ## Sync skill files to Claude/Codex/Agents directories
	bash scripts/sync.sh

clean: ## Remove build artifacts
	rm -rf __pycache__ app/__pycache__ .ruff_cache

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
