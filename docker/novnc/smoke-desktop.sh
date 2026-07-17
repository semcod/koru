#!/bin/bash
# Minimal in-desktop smoke: DISPLAY set, koru CLI present, optional xdotool.
set -euo pipefail
export DISPLAY="${DISPLAY:-:1}"
export PATH="/home/koru/venv/bin:${PATH}"

echo "==> DISPLAY=$DISPLAY"

# Wait for VNC/X to come up (container start-vnc is async)
ok_x=0
for _ in $(seq 1 30); do
  if command -v xdpyinfo >/dev/null 2>&1; then
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
      ok_x=1
      break
    fi
  elif command -v xdotool >/dev/null 2>&1; then
    if xdotool getmouselocation >/dev/null 2>&1; then
      ok_x=1
      break
    fi
  elif [[ -S "/tmp/.X11-unix/X${DISPLAY#:}" ]]; then
    ok_x=1
    break
  fi
  sleep 1
done
if [[ "$ok_x" -ne 1 ]]; then
  echo "FAIL: X display $DISPLAY not ready" >&2
  exit 1
fi
echo "OK: X display"

if command -v koru >/dev/null 2>&1; then
  koru --version
  koru doctor --help >/dev/null
  echo "OK: koru CLI"
else
  echo "WARN: koru not on PATH yet (pip install from /opt/koru may still be running)" >&2
  if [[ -x /home/koru/venv/bin/pip && -f /opt/koru/pyproject.toml ]]; then
    /home/koru/venv/bin/pip install --no-cache-dir -e "/opt/koru[planfile,api]" -q || true
  fi
  if command -v koru >/dev/null 2>&1; then
    koru --version
    echo "OK: koru CLI (after install)"
  fi
fi

if command -v xdotool >/dev/null 2>&1; then
  xdotool getmouselocation >/dev/null
  echo "OK: xdotool"
fi

echo "==> desktop smoke passed"
