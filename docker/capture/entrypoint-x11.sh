#!/bin/sh
set -eu

# Background X server that mss / scrot can talk to.
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp -ac +extension RANDR &
XVFB_PID=$!

trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT INT TERM

# Wait for X to be ready (xdpyinfo loops up to 5 s).
i=0
while [ "$i" -lt 50 ]; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        break
    fi
    i=$((i + 1))
    sleep 0.1
done

# Paint the root window so capture providers see non-black pixels.
DISPLAY=:99 xsetroot -solid '#6ee7b7'
DISPLAY=:99 xsetroot -cursor_name left_ptr 2>/dev/null || true

# Give the X server a moment to commit the paint before mss / scrot read it.
sleep 0.2

# Sanity check (verbose-on-failure) — non-fatal, the python smoke test will
# also emit a clear diagnostic.
if command -v scrot >/dev/null 2>&1; then
    DISPLAY=:99 scrot --overwrite /tmp/x11-rootcheck.png 2>/dev/null \
        && echo "[entrypoint] scrot rootcheck: $(stat -c%s /tmp/x11-rootcheck.png) bytes" \
        || echo "[entrypoint] scrot rootcheck failed (continuing)" >&2
fi

exec python /opt/koru/docker/capture/smoke.py --mode=x11 "$@"
