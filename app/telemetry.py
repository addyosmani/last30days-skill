"""Telemetry and observability setup for the last30days ADK agent."""

import os


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry for Google Cloud.

    Returns the GCS bucket name if telemetry logging is enabled, else None.
    """
    os.environ.setdefault(
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true"
    )

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    if bucket:
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "NO_CONTENT"
        )
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl"
        )
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload"
        )
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )

        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )

    return bucket
