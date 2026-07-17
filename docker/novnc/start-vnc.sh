#!/bin/bash
# Start TigerVNC + noVNC for the koru desktop smoke image.
# Install must tolerate a read-only bind-mount of the repo at /opt/koru.
set -uo pipefail

echo "=== koru noVNC desktop ==="
echo "User: $(whoami) | Home: $HOME | DISPLAY=${DISPLAY:-unset}"

export PATH="/home/koru/venv/bin:${PATH}"
export VIRTUAL_ENV=/home/koru/venv

# Install koru without writing into the (often :ro) source tree.
if [[ -f /opt/koru/pyproject.toml ]]; then
  echo "Installing koru from /opt/koru (non-editable copy into venv)..."
  if /home/koru/venv/bin/pip install --no-cache-dir \
      "/opt/koru[planfile,api]" 2>/tmp/koru-pip.log; then
    echo "OK: koru installed"
  else
    echo "WARN: full extras failed; trying minimal install..." >&2
    tail -20 /tmp/koru-pip.log >&2 || true
    /home/koru/venv/bin/pip install --no-cache-dir /opt/koru 2>>/tmp/koru-pip.log \
      || echo "WARN: koru pip install failed — PYTHONPATH fallback" >&2
  fi
  # Fallback so CLI still works if packaging fails
  if ! command -v koru >/dev/null 2>&1; then
    export PYTHONPATH="/opt/koru/src:/opt/koru/packages/coru/src${PYTHONPATH:+:$PYTHONPATH}"
    echo "PYTHONPATH=$PYTHONPATH"
  fi
fi

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
VNC_PASSWORD="${VNC_PASSWORD:-koru}"

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
echo ""

exec tail -f /dev/null
