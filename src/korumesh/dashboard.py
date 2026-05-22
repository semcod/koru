"""Dashboard helpers for mesh frame grid."""

from __future__ import annotations

from korumesh.dashboard_parse import envelope_to_frame_entry
from korumesh.store import list_vision_frames


_GRID_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Koru mesh grid</title>
<style>
body{font-family:system-ui,sans-serif;margin:16px;background:#111;color:#eee}
nav.top{display:flex;gap:12px;align-items:center;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #2a2a2a;flex-wrap:wrap}
nav.top a{color:#9ad;text-decoration:none}
nav.top a:hover{text-decoration:underline}
nav.top .sep{color:#555}
.peer-section{margin-bottom:24px}
.peer-section h2{margin:8px 0 10px;font-size:14px;color:#cde;text-transform:uppercase;letter-spacing:0.05em}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.tile{background:#1c1c1c;border:1px solid #333;border-radius:8px;padding:8px;display:flex;flex-direction:column}
.tile img{width:100%;height:auto;border-radius:4px;background:#000;image-rendering:auto}
.tile .badge{display:inline-block;background:#243149;color:#9ad;padding:1px 6px;border-radius:99px;font-size:11px;margin-right:4px}
.tile .meta{font-size:12px;color:#aaa;margin-top:6px;line-height:1.4}
.tile .meta strong{color:#cde}
.empty{color:#888;font-style:italic;padding:24px;text-align:center}
</style></head><body>
<nav class="top">
  <a href="/">\u2190 Koru dashboard</a>
  <span class="sep">\u00b7</span>
  <strong>Observation grid</strong>
  <span class="sep">\u00b7</span>
  <a href="/api/mesh/frames">frames JSON</a>
  <span class="sep">\u00b7</span>
  <span id="summary" class="meta"></span>
</nav>
<div id="content"></div>
<script>
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");

function groupFramesByPeer(frames) {
  const map = new Map();
  for (const frame of frames) {
    if (!map.has(frame.peer_from)) map.set(frame.peer_from, []);
    map.get(frame.peer_from).push(frame);
  }
  for (const list of map.values()) {
    list.sort((a, b) => (a.monitor ?? 0) - (b.monitor ?? 0));
  }
  return map;
}

function renderTile(frame) {
  const monitor = frame.monitor ?? -1;
  const output = frame.output || "";
  const labelParts = [];
  if (monitor >= 0) labelParts.push(`monitor ${monitor}`);
  if (output) labelParts.push(output);
  const label = labelParts.join(" \u00b7 ") || "screen";
  const nativeRes = (frame.native_width && frame.native_height)
    ? `${frame.native_width}\u00d7${frame.native_height}` : "?";
  const thumbRes = (frame.width && frame.height)
    ? `${frame.width}\u00d7${frame.height}` : "?";
  const scale = (frame.native_width && frame.width)
    ? Math.round((frame.width / frame.native_width) * 100) : null;
  return `<div class="tile">
    <img alt="${esc(label)}" src="data:${esc(frame.mime)};base64,${frame.image_b64}">
    <div class="meta">
      <span class="badge">${esc(label)}</span>
      <strong>${esc(nativeRes)}</strong> native
      \u2192 ${esc(thumbRes)} ${scale != null ? `(${scale}%)` : ""}
      <br>${esc(frame.created_at)}
      <br>${frame.bytes.toLocaleString()} bytes
    </div>
  </div>`;
}

function renderPeer(peer, frames) {
  const tiles = frames.map(renderTile).join("");
  return `<section class="peer-section">
    <h2>${esc(peer)} \u00b7 ${frames.length} monitor${frames.length === 1 ? "" : "s"}</h2>
    <div class="grid">${tiles}</div>
  </section>`;
}

async function refresh() {
  const res = await fetch("/api/mesh/frames", { cache: "no-store" });
  const data = await res.json();
  const content = document.getElementById("content");
  const summary = document.getElementById("summary");
  const frames = data.frames || [];
  if (frames.length === 0) {
    content.innerHTML = '<div class="empty">No frames yet. Run <code>koru observe up</code> '
      + 'or <code>koru vision agent --publish-mesh</code> on a peer.</div>';
    summary.textContent = "no frames";
    return;
  }
  const peers = groupFramesByPeer(frames);
  const html = Array.from(peers.entries())
    .map(([peer, list]) => renderPeer(peer, list)).join("");
  content.innerHTML = html;
  const totalMonitors = frames.length;
  summary.textContent = `${peers.size} peer${peers.size === 1 ? "" : "s"} \u00b7 `
    + `${totalMonitors} monitor${totalMonitors === 1 ? "" : "s"} \u00b7 refresh every 30s`;
}

refresh();
setInterval(refresh, 30000);
</script></body></html>"""


def mesh_frames_payload() -> dict[str, object]:
    """Return ``/api/mesh/frames`` JSON with parsed monitor metadata per frame."""
    frames = [envelope_to_frame_entry(envelope) for envelope in list_vision_frames()]
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
