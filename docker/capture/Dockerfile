# Cross-OS capture smoke harness for koruvision.
#
# Targets:
#   capture-headless  — no display server; expects providers to report blocked.
#   capture-x11       — Xvfb + scrot + mss; expects mss/cli_tools to capture.
#
# Wayland-in-docker (cage + grim + wlroots) is intentionally out of scope here
# because it triples build time. The plan covers it as Phase 6 future work.

# ---------- installer stage ----------
FROM ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa AS uv

# ---------- base stage ----------
FROM python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS capture-base

COPY --from=uv /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KORU_VISION_SCALE=0.5 \
    KORU_VISION_INTERVAL_MIN=0 \
    PATH="/opt/koru/.venv/bin:${PATH}" \
    VIRTUAL_ENV=/opt/koru/.venv

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/koru
COPY pyproject.toml uv.lock README.md VERSION ./
COPY LICENSE* ./

RUN uv lock --check --no-sources \
    && uv sync --frozen --no-dev --extra vision --no-editable --no-install-project

COPY src ./src
COPY packages ./packages
COPY docker/capture/smoke.py ./docker/capture/smoke.py

ENV PYTHONPATH=/opt/koru/src:/opt/koru/packages/coru/src:/opt/koru/packages/koruide/src

# ---------- headless target ----------
# No DISPLAY / WAYLAND_DISPLAY / DBUS — providers must surface a blocked status.
FROM capture-base AS capture-headless
ENV KORU_CAPTURE_MODE=headless
ENTRYPOINT ["python", "/opt/koru/docker/capture/smoke.py", "--mode=headless"]

# ---------- X11 target ----------
FROM capture-base AS capture-x11

RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb \
        x11-utils \
        x11-xserver-utils \
        scrot \
        imagemagick \
        xauth \
        dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

ENV DISPLAY=:99 \
    KORU_CAPTURE_MODE=x11

COPY docker/capture/entrypoint-x11.sh /opt/koru/docker/capture/entrypoint-x11.sh
RUN chmod +x /opt/koru/docker/capture/entrypoint-x11.sh

ENTRYPOINT ["/opt/koru/docker/capture/entrypoint-x11.sh"]
