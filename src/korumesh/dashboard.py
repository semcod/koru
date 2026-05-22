"""Dashboard helpers for mesh frame grid."""

from __future__ import annotations

import base64

from korumesh.store import list_vision_frames


_GRID_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Koru mesh grid</title>
<style>
body{font-family:system-ui,sans-serif;margin:16px;background:#111;color:#eee}
nav.top{display:flex;gap:12px;align-items:center;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #2a2a2a}
nav.top a{color:#9ad;text-decoration:none}
nav.top a:hover{text-decoration:underline}
nav.top .sep{color:#555}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.tile{background:#1c1c1c;border:1px solid #333;border-radius:8px;padding:8px}
.tile img{width:100%;height:auto;border-radius:4px;background:#000}
.meta{font-size:12px;color:#aaa;margin-top:6px}
.empty{color:#888;font-style:italic;padding:24px;text-align:center}
</style></head><body>
<nav class="top">
  <a href="/">← Koru dashboard</a>
  <span class="sep">·</span>
  <strong>Observation grid</strong>
  <span class="sep">·</span>
  <a href="/api/mesh/frames">frames JSON</a>
  <span class="sep">·</span>
  <span class="meta">refresh every 60s</span>
</nav>
<div id="grid" class="grid"></div>
<script>
async function refresh() {
  const res = await fetch("/api/mesh/frames", { cache: "no-store" });
  const data = await res.json();
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  const frames = data.frames || [];
  if (frames.length === 0) {
    grid.innerHTML = '<div class="empty">No frames yet. Run <code>koru observe up</code> '
      + 'or <code>koru vision agent --publish-mesh</code> on a peer.</div>';
    return;
  }
  for (const frame of frames) {
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
