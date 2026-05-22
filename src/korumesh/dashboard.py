"""Dashboard helpers for mesh frame grid."""

from __future__ import annotations

import base64

from korumesh.store import list_vision_frames


_GRID_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Koru mesh grid</title>
<style>
body{font-family:system-ui,sans-serif;margin:16px;background:#111;color:#eee}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.tile{background:#1c1c1c;border:1px solid #333;border-radius:8px;padding:8px}
.tile img{width:100%;height:auto;border-radius:4px;background:#000}
.meta{font-size:12px;color:#aaa;margin-top:6px}
</style></head><body>
<h1>Koru observation grid</h1>
<p class="meta">Refreshes every 60s from <code>/api/mesh/frames</code></p>
<div id="grid" class="grid"></div>
<script>
async function refresh() {
  const res = await fetch("/api/mesh/frames", { cache: "no-store" });
  const data = await res.json();
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  for (const frame of (data.frames || [])) {
    const tile = document.createElement("div");
    tile.className = "tile";
    tile.innerHTML = `<img alt="" src="data:${frame.mime};base64,${frame.image_b64}">`
      + `<div class="meta">${frame.peer_from} · ${frame.created_at}<br>${frame.bytes} bytes</div>`;
    grid.appendChild(tile);
  }
}
refresh();
setInterval(refresh, 60000);
</script></body></html>"""


def mesh_frames_payload() -> dict[str, object]:
    frames: list[dict[str, object]] = []
    for envelope in list_vision_frames():
        frames.append(
            {
                "envelope_id": envelope.envelope_id,
                "peer_from": envelope.peer_from,
                "created_at": envelope.created_at,
                "mime": envelope.mime,
                "image_b64": base64.b64encode(envelope.payload).decode("ascii"),
                "bytes": len(envelope.payload),
            }
        )
    return {"ok": True, "frames": frames}


def grid_html() -> str:
    return _GRID_HTML


def serve_mesh_http(handler: object, path: str) -> bool:
    """Serve ``/grid`` or ``/api/mesh/frames`` when *path* matches."""
    if path == "/grid":
        body = grid_html().encode("utf-8")
        getattr(handler, "_send")(200, body, "text/html; charset=utf-8")
        return True
    if path == "/api/mesh/frames":
        getattr(handler, "_send_json")(mesh_frames_payload())
        return True
    return False
