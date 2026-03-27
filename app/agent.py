"""last30days ADK agent — multi-source research across Reddit, X, YouTube & more."""

import logging
import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import (
    research_topic,
    search_hackernews,
    search_reddit,
    search_web,
    search_x,
    search_youtube,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth: support both Gemini API key and Vertex AI
# ---------------------------------------------------------------------------
# Option A — Gemini API key (set GOOGLE_API_KEY in .env)
# Option B — Vertex AI  (set GOOGLE_CLOUD_PROJECT + GOOGLE_GENAI_USE_VERTEXAI=True)

_use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"

if _use_vertex:
    import google.auth

    _, project_id = google.auth.default()
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

root_agent = Agent(
    name="last30days",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a research assistant that finds what people are saying about "
        "any topic across Reddit, X/Twitter, YouTube, Hacker News, and the web "
        "over the last 30 days.\n\n"
        "When the user asks about a topic:\n"
        "1. Use `research_topic` for a comprehensive multi-source search.\n"
        "2. Use individual source tools (search_reddit, search_x, etc.) when "
        "the user wants results from a specific platform.\n"
        "3. Summarise the findings clearly, highlighting key themes, sentiment, "
        "and notable discussions.\n"
        "4. Always cite the source platform and link when available.\n\n"
        "You can adjust the time window with the `days` parameter (default 30) "
        "and search depth with `depth` (quick/default/deep)."
    ),
    tools=[
        research_topic,
        search_reddit,
        search_x,
        search_youtube,
        search_web,
        search_hackernews,
    ],
)

# ---------------------------------------------------------------------------
# Plugins (optional — BigQuery analytics)
# ---------------------------------------------------------------------------

_plugins = []
if os.environ.get("BQ_ANALYTICS_DATASET_ID"):
    try:
        from google.adk.plugins.bigquery_agent_analytics_plugin import (
            BigQueryAgentAnalyticsPlugin,
        )

        _plugins.append(
            BigQueryAgentAnalyticsPlugin(
                project=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
                bq_dataset_id=os.environ.get("BQ_ANALYTICS_DATASET_ID", ""),
                gcs_bucket_name=os.environ.get("BQ_ANALYTICS_GCS_BUCKET", ""),
            )
        )
    except Exception as e:
        logger.warning("Failed to initialize BigQuery Analytics: %s", e)

# ---------------------------------------------------------------------------
# App (wraps agent for deployment — used by FastAPI, adk web, adk run)
# ---------------------------------------------------------------------------

_app_kwargs = {
    "root_agent": root_agent,
    "name": "last30days",
}
if _plugins:
    _app_kwargs["plugins"] = _plugins

app = App(**_app_kwargs)
