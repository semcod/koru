# Reusable koru image for examples/*/*/docker-compose.yml builds.
# Build context must be the koru repository root.
#
# Example:
#   docker build -f examples/docker/koru-e2e.Dockerfile \
#     --build-arg E2E_SCRIPT=examples/ci/headless-autonomous-jsonl/e2e.sh \
#     -t koru:e2e-smoke .

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/koru

COPY pyproject.toml README.md LICENSE ./
COPY src ./src/
COPY templates ./templates/
COPY docs ./docs/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e . \
    && pip install --no-cache-dir \
        "planfile>=0.1.87" \
        "uvicorn[standard]>=0.27" \
        "fastapi>=0.110" \
        "wup>=0.2.60"

# Optional cache-bust when iterating on examples without touching src
ARG CACHE_BUST=0
RUN echo "$CACHE_BUST" > /tmp/.cache-bust

ARG E2E_SCRIPT=examples/ci/headless-autonomous-jsonl/e2e.sh
COPY ${E2E_SCRIPT} /opt/e2e-script.sh
RUN chmod +x /opt/e2e-script.sh

WORKDIR /workspace
ENV PYTHONUNBUFFERED=1
ENTRYPOINT []
CMD ["/bin/bash", "-euo", "pipefail", "/opt/e2e-script.sh"]
