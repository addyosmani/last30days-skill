"""FastAPI wrapper for Cloud Run deployment.

Provides:
- ADK agent served via get_fast_api_app()
- /health endpoint for Cloud Run health checks
- /feedback endpoint for user feedback collection
"""

import logging
import os
from pathlib import Path

import google.auth
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from app.telemetry import setup_telemetry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

setup_telemetry()

try:
    _, project_id = google.auth.default()
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
except google.auth.exceptions.DefaultCredentialsError:
    logger.info("No GCP credentials found — using Gemini API key mode")

logs_bucket = os.environ.get("LOGS_BUCKET_NAME")
artifact_service_uri = f"gs://{logs_bucket}" if logs_bucket else None

# ---------------------------------------------------------------------------
# FastAPI app (wraps ADK agent)
# ---------------------------------------------------------------------------

AGENT_DIR = str(Path(__file__).resolve().parent)

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    session_service_uri=None,  # in-memory sessions (swap for Cloud SQL URI)
)

app.title = "last30days Research Agent"


# ---------------------------------------------------------------------------
# Health check (required by Cloud Run)
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run / load balancers."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Feedback collection
# ---------------------------------------------------------------------------


@app.post("/feedback")
async def feedback(payload: dict):
    """Collect user feedback on agent responses."""
    logger.info("Feedback received: %s", payload)
    return {"status": "received"}
