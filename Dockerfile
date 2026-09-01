# Koru - Closed-loop automation across semcod/* repositories
# Multi-stage build for production and testing
#
# Keep floors aligned with pyproject.toml extras (see docs/docker-e2e-testing.md).
# This image is a *queue/CLI* runtime, not a full desktop/noVNC stack.

FROM python@sha256:e5c9fa26ffb76e11e0f054f30dc2523a2f9693f0c36c0cf1e39b27e152d899fc AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    docker.io \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Cache bust arg — set to src/ hash by the test fixture to force rebuild on code change
ARG CACHE_BUST=none

# Copy source code first
COPY src/ ./src/
COPY packages/ ./packages/
COPY templates/ ./templates/
COPY docs/ ./docs/
COPY README.md .
COPY LICENSE* .
COPY VERSION .
COPY pyproject.toml .

# Install Python package + extras used by common container e2e (queue, API, desktop bridges).
# Optional quality gates (regix/redup/vallm) and vdisplay are installed as aligned floors;
# they are not a substitute for host Wayland / noVNC desktop validation.
RUN pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir -e ".[planfile,api,desktop]" \
    && pip install --no-cache-dir \
        "planfile>=0.1.117" \
        "testql>=1.2.64" \
        "wup>=0.2.60" \
        "regix>=0.1.0" \
        "redup>=0.4.28" \
        "vallm>=0.1.87"

# Create non-root user
RUN useradd -m -u 1000 koru && \
    chown -R koru:koru /app
USER koru

# Environment variables
ENV PYTHONPATH=/app/src
ENV KORU_AUTOPILOT_IDE=auto

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD koru --version || exit 1

ENTRYPOINT ["koru"]
CMD ["--help"]

# Development stage with test dependencies
FROM base AS development

USER root
RUN pip install --no-cache-dir -e ".[dev,watch,api,planfile,desktop]" && \
    chown -R koru:koru /app
USER koru

# Test stage
FROM development AS test

# Copy test files
COPY tests/ ./tests/

# Run tests
RUN python -m pytest tests/ -v -m "not slow and not e2e and not integration" --maxfail=20

# Production stage
FROM base AS production
