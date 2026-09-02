#!/bin/bash
# Start TigerVNC + noVNC for the koru desktop smoke image.
# /opt/koru is typically bind-mounted :ro — never write egg-info there.
set -uo pipefail

echo "=== koru noVNC desktop ==="
echo "User: $(whoami) | Home: $HOME | DISPLAY=${DISPLAY:-unset}"

export PATH="/home/koru/venv/bin:${PATH}"
export VIRTUAL_ENV=/home/koru/venv

install_koru_from_mount() {
  local src=/opt/koru
  [[ -f "$src/pyproject.toml" ]] || return 0

  echo "Synchronizing koru from $src (copy → writable build dir)..."
  local build
  build="$(mktemp -d /tmp/koru-build.XXXXXX)"
  # Minimal tree for setuptools; skip venv/node/build/egg-info
  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.venv' --exclude 'venv' --exclude 'node_modules' \
      --exclude 'build' --exclude 'dist' --exclude '.git' \
      --exclude '*.egg-info' --exclude '__pycache__' \
      --exclude 'publish-env' --exclude '.tox' \
      "$src/" "$build/"
  else
    # fallback: selective copy
    mkdir -p "$build"
    for item in src packages templates pyproject.toml README.md LICENSE VERSION MANIFEST.in; do
      [[ -e "$src/$item" ]] && cp -a "$src/$item" "$build/"
    done
    # LICENSE* optional
    cp -a "$src"/LICENSE* "$build/" 2>/dev/null || true
  fi

  if uv lock --project "$build" --check --no-sources \
    && UV_PROJECT_ENVIRONMENT=/home/koru/venv uv sync \
      --project "$build" \
      --frozen \
      --no-dev \
      --extra planfile \
      --extra api \
      --no-editable 2>/tmp/koru-uv.log; then
    echo "OK: koru installed from frozen lock (planfile,api)"
  else
    echo "WARN: frozen uv sync failed — using PYTHONPATH" >&2
    tail -15 /tmp/koru-uv.log >&2 || true
    export PYTHONPATH="/opt/koru/src:/opt/koru/packages/coru/src${PYTHONPATH:+:$PYTHONPATH}"
    # shim CLI
    cat > /home/koru/venv/bin/koru << 'SH'
#!/bin/bash
export PYTHONPATH="/opt/koru/src:/opt/koru/packages/coru/src${PYTHONPATH:+:$PYTHONPATH}"
exec /home/koru/venv/bin/python -m koru.cli "$@"
SH
    chmod +x /home/koru/venv/bin/koru
  fi
  rm -rf "$build"
}

install_koru_from_mount

mkdir -p "$HOME/.vnc"
cat > "$HOME/.vnc/xstartup" << 'XEOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export XKL_XMODMAP_DISABLE=1
exec startxfce4
XEOF
chmod +x "$HOME/.vnc/xstartup"

vncserver -kill :1 2>/dev/null || true
sleep 1

VNC_RESOLUTION="${VNC_RESOLUTION:-1280x800}"
VNC_PORT="${VNC_PORT:-5901}"
NOVNC_PORT="${NOVNC_PORT:-6080}"

echo "Starting VNC on :1 (${VNC_RESOLUTION})..."
if ! vncserver :1 \
  -geometry "$VNC_RESOLUTION" \
  -depth 24 \
  -SecurityTypes None \
  --I-KNOW-THIS-IS-INSECURE \
  -localhost no; then
  echo "ERROR: vncserver failed" >&2
  exit 1
fi

sleep 2

echo "Starting noVNC on ${NOVNC_PORT}..."
websockify --web=/usr/share/novnc/ \
  "$NOVNC_PORT" \
  "localhost:${VNC_PORT}" &

echo ""
echo "=== Ready ==="
echo "noVNC:  http://127.0.0.1:${NOVNC_PORT}/vnc.html?autoconnect=true"
echo "VNC:    localhost:${VNC_PORT}"
echo "Smoke:  docker exec -it koru-novnc bash /home/koru/smoke-desktop.sh"
if command -v koru >/dev/null 2>&1; then
  koru --version || true
fi
echo ""

exec tail -f /dev/null
