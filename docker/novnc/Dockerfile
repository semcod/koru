# Lightweight desktop for koru GUI smoke (noVNC in browser).
# Python must be >=3.12 (koru requires-python). Base: bookworm + desktop/VNC.
#
# Build context: repository root
#   docker compose -f docker/novnc/docker-compose.yml up --build

FROM python:3.12-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    VNC_PORT=5901 \
    NOVNC_PORT=6080 \
    VNC_RESOLUTION=1280x800 \
    VNC_PASSWORD=koru \
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

RUN python -m venv /home/koru/venv \
    && /home/koru/venv/bin/pip install --no-cache-dir -U pip setuptools wheel

COPY --chown=koru:koru docker/novnc/start-vnc.sh /home/koru/start-vnc.sh
COPY --chown=koru:koru docker/novnc/smoke-desktop.sh /home/koru/smoke-desktop.sh
RUN chmod +x /home/koru/start-vnc.sh /home/koru/smoke-desktop.sh \
    && mkdir -p /home/koru/.vnc /home/koru/workspace

ENV PATH="/home/koru/venv/bin:${PATH}" \
    VIRTUAL_ENV=/home/koru/venv

EXPOSE 5901 6080

CMD ["/home/koru/start-vnc.sh"]
