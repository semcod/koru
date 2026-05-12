# Koru - Closed-loop automation across semcod/* repositories
# Multi-stage build for production and testing

FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    docker.io \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy source code first
COPY src/ ./src/
COPY templates/ ./templates/
COPY docs/ ./docs/
COPY README.md .
COPY LICENSE* .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Install external tools (planfile, regix, testql, etc.)
RUN pip install --no-cache-dir \
    planfile>=0.1.87 \
    regix>=0.1.0 \
    redup>=0.4.15 \
    testql>=0.1.0 \
    vallm>=0.1.87 \
    wup>=0.1.0

# Create non-root user
RUN useradd -m -u 1000 koru && \
    chown -R koru:koru /app
USER koru

# Environment variables
ENV PYTHONPATH=/app/src
ENV KORU_AUTOPILOT_IDE=auto

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD koru --doctor || exit 1

ENTRYPOINT ["koru"]
CMD ["--help"]

# Development stage with test dependencies
FROM base as development

USER root
RUN pip install --no-cache-dir -e ".[dev,watch]" && \
    chown -R koru:koru /app
USER koru

# Test stage
FROM development as test

# Copy test files
COPY tests/ ./tests/

# Run tests
RUN python -m pytest tests/ -v

# Production stage
FROM base as production
