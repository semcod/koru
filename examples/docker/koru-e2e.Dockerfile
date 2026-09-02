# Reusable koru image for examples/*/*/docker-compose.yml builds.
# Build context must be the koru repository root.
#
# Keep floors aligned with pyproject.toml (see docs/docker-e2e-testing.md).
#
# Example:
#   docker build -f examples/docker/koru-e2e.Dockerfile \
#     --build-arg E2E_SCRIPT=examples/ci/headless-autonomous-jsonl/e2e.sh \
#     -t koru:e2e-smoke .

FROM ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa AS uv
FROM python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254

COPY --from=uv /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/koru

ENV UV_PROJECT_ENVIRONMENT=/opt/koru/.venv \
    VIRTUAL_ENV=/opt/koru/.venv \
    PATH="/opt/koru/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock README.md LICENSE VERSION ./

# Validate the reviewed lock without local sibling overrides before copying
# frequently changed sources, then install exactly that frozen resolution.
RUN uv lock --check --no-sources \
    && uv sync --frozen --no-dev --no-editable \
        --extra planfile --extra api --extra browser --no-install-project

COPY src ./src/
COPY packages ./packages/
COPY templates ./templates/
COPY docs ./docs/

# Examples that ship helper scripts / scenario files need the tree in-image
COPY examples ./examples/

RUN uv sync --frozen --no-dev --no-editable \
        --extra planfile --extra api --extra browser

# Optional cache-bust when iterating on examples without touching src
ARG CACHE_BUST=0
RUN echo "$CACHE_BUST" > /tmp/.cache-bust

ARG E2E_SCRIPT=examples/ci/headless-autonomous-jsonl/e2e.sh
COPY ${E2E_SCRIPT} /opt/e2e-script.sh
RUN chmod +x /opt/e2e-script.sh

WORKDIR /workspace
ENTRYPOINT []
CMD ["/bin/bash", "-euo", "pipefail", "/opt/e2e-script.sh"]
