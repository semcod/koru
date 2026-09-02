# healing-webhook — receives alerts from Alertmanager + probe failures from
# testql-watchdog, decides whether to run redsl gate / redsl improve / rebuild
# restore. Delegates the actual dispatch to the host docker.sock so it can
# spin up short-lived `semcod/redsl:local` / `semcod/rebuild:local` containers
# on demand.

FROM ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa AS uv
FROM python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md VERSION ./
COPY LICENSE* ./

# The repository lock owns every transitive dependency. vallm and redup are
# exact, hash-bound tools installed without dependency resolution because they
# are not Koru runtime dependencies and therefore do not belong in pyproject.
RUN uv lock --check --no-sources \
    && uv sync --frozen --all-extras --no-dev --no-editable --no-install-project \
    && printf '%s\n' \
       'redup==0.4.28 --hash=sha256:a9114c5bc9cde91b1e8c0506c2f7bf81a799b2076e00ac9838509f383d8e97f7 --hash=sha256:e7765dc7ab1833a10f0218d3477033b07f85658fc1343c48c9efb9dcffa6d401' \
       'vallm==0.1.87 --hash=sha256:1bfc0aad027821f12c8014e16f840420dc69550e5aeafc6d1f57feef2353c2e0 --hash=sha256:98a9058013051da9a3d6166e6ced5594d6a5b474d1b7f31bfd24b448b232bd41' \
       > /tmp/healing-tools.txt \
    && uv pip install --python /app/.venv/bin/python --no-deps --require-hashes -r /tmp/healing-tools.txt \
    && rm /tmp/healing-tools.txt

COPY services/healing-webhook/*.py /app/

ENV PATH="/app/.venv/bin:${PATH}" \
    VIRTUAL_ENV=/app/.venv \
    REPO_PATH=/repo \
    REDSL_IMAGE=semcod/redsl:local \
    REBUILD_IMAGE=semcod/rebuild:local \
    DRY_RUN=true \
    PORT=8810

EXPOSE 8810

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8810"]
