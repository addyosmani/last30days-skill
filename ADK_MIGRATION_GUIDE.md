# Migrating last30days to Google ADK — Step-by-Step Guide

This documents how we migrated the last30days research skill from a standalone Python CLI to a Google Agent Development Kit (ADK) agent, following the [agent-starter-pack](https://github.com/google/agent-starter-pack) best practices.

---

## Why ADK?

ADK gives us a standard agent runtime with built-in:
- Interactive web UI for testing (`adk web`)
- API server with SSE streaming
- Session management (in-memory, Cloud SQL, Agent Engine)
- OpenTelemetry observability
- Evaluation framework with rubric-based judges
- One-command Cloud Run deployment

## Architecture Overview

```
Before:                          After:
┌────────────────────┐           ┌────────────────────────────┐
│ scripts/            │           │ app/                        │
│   last30days.py    │           │   agent.py   ← ADK Agent   │
│   lib/             │           │   tools.py   ← wraps CLI   │
│     search.py      │           │   fast_api_app.py ← deploy │
│     render.py      │           │   telemetry.py    ← otel   │
│     ...            │           │   __init__.py               │
└────────────────────┘           ├────────────────────────────┤
                                 │ scripts/  (unchanged)       │
                                 │   last30days.py             │
                                 │   lib/                      │
                                 └────────────────────────────┘
```

The key insight: **the existing CLI stays untouched**. ADK tool functions in `app/tools.py` call the CLI via subprocess, so all existing search logic, caching, and rendering works as-is.

---

## Step 1: Project Setup

### Install dependencies

```bash
make install
# or: uv sync
```

### Configure authentication

Copy the example env and pick **one** auth approach:

```bash
cp .env.example .env
```

**Option A — Gemini API key** (simplest, good for development):
```bash
# Get a key at https://aistudio.google.com/apikey
GOOGLE_API_KEY=your-key-here
```

**Option B — Vertex AI** (production, uses Application Default Credentials):
```bash
gcloud auth application-default login
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=True
```

---

## Step 2: Agent Definition (`app/agent.py`)

This is the core migration. We define an ADK `Agent` with tools and wrap it in an `App`.

### Key patterns from agent-starter-pack:

**1. Use `Gemini()` model class with retry options** (not a plain string):

```python
from google.adk.models import Gemini
from google.genai import types

root_agent = Agent(
    name="last30days",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="...",
    tools=[...],
)
```

This gives you automatic retries on transient API errors.

**2. Wrap the agent in an `App`** for deployment:

```python
from google.adk.apps import App

app = App(root_agent=root_agent, name="last30days")
```

The `App` object is what `adk run`, `adk web`, and `get_fast_api_app()` consume.

**3. Dual auth with graceful fallback:**

```python
if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true":
    import google.auth
    _, project_id = google.auth.default()
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
```

**4. Optional BigQuery analytics plugin:**

```python
_plugins = []
if os.environ.get("BQ_ANALYTICS_DATASET_ID"):
    from google.adk.plugins.bigquery_agent_analytics_plugin import (
        BigQueryAgentAnalyticsPlugin,
    )
    _plugins.append(BigQueryAgentAnalyticsPlugin(...))
```

---

## Step 3: Tool Functions (`app/tools.py`)

Each ADK tool function **must have a full docstring** with Args and Returns sections — the LLM uses these to understand when and how to call the tool.

```python
def search_reddit(topic: str, days: int = 30, depth: str = "default") -> str:
    """Search Reddit for discussions about a topic.

    Args:
        topic: The topic to search for.
        days: Number of days to look back (default 30).
        depth: Search depth — "quick", "default", or "deep".

    Returns:
        Markdown-formatted Reddit discussion results.
    """
    return _run_research(topic, days=days, depth=depth, sources="reddit")
```

Our tools wrap the existing CLI via subprocess, so the migration was zero-risk to existing search logic.

---

## Step 4: FastAPI App for Cloud Run (`app/fast_api_app.py`)

The agent-starter-pack pattern is to **not use `adk api_server`** in production. Instead, use a proper FastAPI app:

```python
from google.adk.cli.fast_api import get_fast_api_app

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    session_service_uri=None,  # in-memory (swap for Cloud SQL URI)
)
```

### Required endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/health` | Cloud Run health checks |
| `/feedback` | User feedback collection |
| `/run`, `/run_sse` | Agent execution (provided by `get_fast_api_app`) |

---

## Step 5: Telemetry (`app/telemetry.py`)

The starter pack configures OpenTelemetry to log to GCS:

```python
def setup_telemetry() -> str | None:
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")
    bucket = os.environ.get("LOGS_BUCKET_NAME")
    if bucket:
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        # ...
```

Set `LOGS_BUCKET_NAME` in production to enable trace logging.

---

## Step 6: Dockerfile

Key differences from the old pattern:

| Before | After (starter-pack) |
|--------|---------------------|
| `CMD adk api_server` | `CMD uvicorn app.fast_api_app:app` |
| No build metadata | `ARG COMMIT_SHA`, `ARG AGENT_VERSION` |
| `WORKDIR /app` | `WORKDIR /code` (convention) |

The FastAPI approach gives us the `/health` endpoint that Cloud Run needs, plus full control over middleware and routes.

---

## Step 7: Testing

### Integration tests (`tests/integration/test_agent.py`)

Following the starter-pack pattern, use `Runner` + `InMemorySessionService`:

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

def test_runner_creates_session():
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    assert session.id is not None
```

Tests that need an API key are marked with `@pytest.mark.skipif` so CI doesn't fail without credentials.

### Evaluation framework (`tests/eval/`)

ADK's eval system uses rubric-based judges:

```json
{
  "criteria": {
    "rubric_based_final_response_quality_v1": {
      "rubrics": [
        { "rubricId": "relevance", "rubricContent": { "textProperty": "..." } },
        { "rubricId": "source_attribution", "rubricContent": { "textProperty": "..." } }
      ]
    }
  }
}
```

Run evaluations:
```bash
make eval
```

---

## Step 8: Makefile Targets

| Target | What it does |
|--------|-------------|
| `make install` | Install deps (auto-installs uv if missing) |
| `make setup` | Install + create .env from template |
| `make run` | Interactive terminal chat |
| `make web` | ADK dev UI in browser |
| `make playground` | ADK web with auto-reload |
| `make local-backend` | FastAPI with hot reload (Cloud Run parity) |
| `make test-agent` | Smoke test — verify agent loads |
| `make eval` | Run ADK evaluation suite |
| `make lint` | Ruff linting |
| `make docker-build` | Build container image |
| `make docker-run` | Run container locally |
| `make deploy` | Deploy to Cloud Run |

---

## Step 9: Deploy to Cloud Run

```bash
# One-command deploy
make deploy PROJECT=my-gcp-project REGION=us-central1

# Or with all env vars from .env
make deploy-env
```

This uses `gcloud run deploy --source .` which builds the Dockerfile in Cloud Build and deploys it.

---

## Checklist: agent-starter-pack Compliance

| Best Practice | Status |
|---------------|--------|
| `Agent` + `App` wrapper | ✅ |
| `Gemini()` model with retry options | ✅ |
| Full docstrings on all tool functions | ✅ |
| FastAPI app with `/health` endpoint | ✅ |
| OpenTelemetry setup with GCS bucket | ✅ |
| Optional BigQuery analytics plugin | ✅ |
| Dual auth (API key + Vertex AI) | ✅ |
| `pyproject.toml` with `[tool.agent-starter-pack]` | ✅ |
| Dockerfile using uvicorn (not `adk api_server`) | ✅ |
| Integration tests with Runner | ✅ |
| Evaluation config + evalsets | ✅ |
| Makefile with `playground` / `local-backend` | ✅ |
| `COMMIT_SHA` / `AGENT_VERSION` build args | ✅ |
| Graceful credential fallback | ✅ |
| `.env.example` with observability vars | ✅ |

---

## Quick Start (TL;DR)

```bash
# 1. Install
make install

# 2. Configure
cp .env.example .env
# Add your GOOGLE_API_KEY

# 3. Run
make web
# Open http://localhost:8765

# 4. Test
make test-agent
uv run pytest tests/integration/ -v

# 5. Deploy
make deploy PROJECT=my-project
```
