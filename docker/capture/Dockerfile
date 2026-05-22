# Cross-OS capture smoke harness for koruvision.
#
# Targets:
#   capture-headless  — no display server; expects providers to report blocked.
#   capture-x11       — Xvfb + scrot + mss; expects mss/cli_tools to capture.
#
# Wayland-in-docker (cage + grim + wlroots) is intentionally out of scope here
# because it triples build time. The plan covers it as Phase 6 future work.

# ---------- base stage ----------
FROM python:3.12-slim AS capture-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    KORU_VISION_SCALE=0.5 \
    KORU_VISION_INTERVAL_MIN=0

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/koru
COPY pyproject.toml ./
COPY src ./src
COPY docker/capture/smoke.py ./docker/capture/smoke.py

RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/opt/koru/src

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

# mss requires libxext, libxfixes (already pulled in by Xvfb deps), python-xlib.
RUN pip install --no-cache-dir "mss>=9.0,<11.0"

ENV DISPLAY=:99 \
    KORU_CAPTURE_MODE=x11

COPY docker/capture/entrypoint-x11.sh /opt/koru/docker/capture/entrypoint-x11.sh
RUN chmod +x /opt/koru/docker/capture/entrypoint-x11.sh

ENTRYPOINT ["/opt/koru/docker/capture/entrypoint-x11.sh"]
