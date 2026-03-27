FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22 (needed for vendored Bird CLI — X/Twitter search)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install yt-dlp (YouTube transcript extraction)
RUN pip install --no-cache-dir yt-dlp

WORKDIR /code

# Copy dependency files first (cache layer)
COPY pyproject.toml README.md ./
COPY uv.lock* ./
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY fixtures/ ./fixtures/

# Install the project
RUN uv sync --no-dev

# Build metadata
ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

# Runtime
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Run via FastAPI (matches starter-pack pattern — includes /health endpoint)
CMD ["uv", "run", "uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
