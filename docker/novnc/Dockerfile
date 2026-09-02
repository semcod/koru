# Lightweight desktop for koru GUI smoke (noVNC in browser).
# Python must be >=3.12 (koru requires-python). Base: bookworm + desktop/VNC.
#
# Build context: repository root
#   docker compose -f docker/novnc/docker-compose.yml up --build

FROM ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa AS uv
FROM python:3.12.14-bookworm@sha256:581429e3df12d76e6af4be5ab7d0e7fc2013eb57dc23d2de691411c8efdbb970

COPY --from=uv /uv /uvx /bin/

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    VNC_PORT=5901 \
    NOVNC_PORT=6080 \
    VNC_RESOLUTION=1280x800 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        xfce4 xfce4-terminal dbus-x11 \
        tigervnc-standalone-server tigervnc-common \
        novnc websockify \
        xterm scrot imagemagick xdotool xclip x11-utils \
        curl wget git sudo procps net-tools ca-certificates rsync \
        fonts-liberation fonts-dejavu-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash koru \
    && echo "koru ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER koru
WORKDIR /home/koru

RUN uv venv /home/koru/venv

COPY --chown=koru:koru docker/novnc/start-vnc.sh /home/koru/start-vnc.sh
COPY --chown=koru:koru docker/novnc/smoke-desktop.sh /home/koru/smoke-desktop.sh
RUN chmod +x /home/koru/start-vnc.sh /home/koru/smoke-desktop.sh \
    && mkdir -p /home/koru/.vnc /home/koru/workspace

ENV PATH="/home/koru/venv/bin:${PATH}" \
    VIRTUAL_ENV=/home/koru/venv

EXPOSE 5901 6080

CMD ["/home/koru/start-vnc.sh"]
