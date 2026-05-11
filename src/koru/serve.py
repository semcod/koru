"""Minimal local dashboard server for koru.

Serves a small HTML page that calls back into ``build_context`` to show
the live LLM brief (active ticket, policy, agent lanes, gates). No
external dependencies — uses ``http.server`` from the stdlib.

Endpoints:
    GET  /              -> HTML dashboard (auto-refreshing)
    GET  /api/context   -> JSON brief (``build_context`` output)
    GET  /api/handoff   -> raw markdown handoff (``render_markdown_handoff``)
    GET  /health        -> ``{"ok": true}``

Bound to ``127.0.0.1`` by default — never exposed to the network unless
``--bind`` is explicitly set otherwise.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .context import build_context, render_markdown_handoff

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>koru dashboard</title>
<style>
  :root {
    --bg: #0f1115;
    --panel: #161922;
    --muted: #8a93a6;
    --fg: #e6e8ee;
    --accent: #6ee7b7;
    --warn: #fbbf24;
    --err: #f87171;
    --border: #232838;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--fg);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Helvetica Neue", Arial, sans-serif;
  }
  header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  header h1 { margin: 0; font-size: 18px; font-weight: 600; }
  header .meta { color: var(--muted); font-size: 12px; }
  main {
    max-width: 1100px;
    margin: 0 auto;
    padding: 24px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
  }
  .panel h2 {
    margin: 0 0 12px;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
  }
  .panel.full { grid-column: 1 / -1; }
  .kv { display: grid; grid-template-columns: 140px 1fr; gap: 4px 12px; }
  .kv dt { color: var(--muted); }
  .kv dd { margin: 0; word-break: break-word; }
  code, pre {
    font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo,
                 Consolas, monospace;
    font-size: 12px;
  }
  pre {
    background: #0a0c11;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    border: 1px solid var(--border);
  }
  .pill {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 99px;
    background: #1f2533;
    color: var(--fg);
    font-size: 11px;
    margin-right: 4px;
  }
  .pill.ok { background: rgba(110, 231, 183, 0.15); color: var(--accent); }
  .pill.warn { background: rgba(251, 191, 36, 0.15); color: var(--warn); }
  .pill.err { background: rgba(248, 113, 113, 0.15); color: var(--err); }
  table { width: 100%; border-collapse: collapse; }
  th, td {
    text-align: left;
    padding: 6px 8px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
  }
  th { color: var(--muted); font-weight: 500; }
  .muted { color: var(--muted); }
  .err { color: var(--err); }
  .ok { color: var(--accent); }
  footer {
    padding: 16px 24px;
    color: var(--muted);
    font-size: 12px;
    text-align: center;
  }
  a { color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1>koru dashboard</h1>
  <div class="meta">
    <span id="project">loading…</span>
    <span class="muted"> · refreshed </span>
    <span id="ts">-</span>
  </div>
</header>
<main id="root">
  <div class="panel full"><span class="muted">Loading brief…</span></div>
</main>
<footer>
  Local-only · <code>127.0.0.1</code> · auto-refresh 5 s ·
  <a href="/api/context">JSON</a> · <a href="/api/handoff">Markdown</a>
</footer>
<script>
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function panel(title, body, full=false) {
  return `<section class="panel${full ? " full" : ""}">
    <h2>${esc(title)}</h2>${body}</section>`;
}

function kv(pairs) {
  return `<dl class="kv">${pairs.map(([k, v]) =>
    `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>`;
}

function renderTicket(ticket, err) {
  if (!ticket) {
    return panel("Active ticket",
      `<div class="muted">${esc(err || "no ticket")}</div>`);
  }
  const inputs = ticket.inputs || {};
  const files = (ticket.files || []).map(f => `<code>${esc(f)}</code>`).join(", ");
  return panel("Active ticket", kv([
    ["id", `<code>${esc(ticket.id)}</code>`],
    ["name", esc(ticket.name || "")],
    ["status", `<span class="pill">${esc(ticket.status || "?")}</span>`],
    ["executor", `<code>${esc((ticket.executor || {}).kind || "?")}</code>`],
    ["files", files || `<span class="muted">none</span>`],
    ["prompt", inputs.prompt
      ? `<pre>${esc(inputs.prompt)}</pre>`
      : `<span class="muted">—</span>`],
  ]));
}

function renderEnv(env) {
  const pe = (env && env.project) || {};
  const markers = (pe.markers) || {};
  const present = Object.entries(markers).filter(([_, v]) => v)
    .map(([k]) => `<span class="pill ok">${esc(k)}</span>`).join("");
  const absent = Object.entries(markers).filter(([_, v]) => !v)
    .map(([k]) => `<span class="pill">${esc(k)}</span>`).join("");
  const rec = (env && env.recommended_agent) || null;
  return panel("Environment", kv([
    ["project", `<code>${esc(pe.name || "?")}</code>`],
    ["cwd", `<code>${esc(pe.cwd || "?")}</code>`],
    ["python", `<code>${esc(pe.python || "?")}</code>`],
    ["recommended", rec
      ? `<code>${esc(rec.label)}</code>`
      : `<span class="muted">none</span>`],
    ["present", present || `<span class="muted">none</span>`],
    ["absent", absent || `<span class="muted">—</span>`],
  ]));
}

function renderAgents(env) {
  const agents = (env && env.llm_agents) || [];
  if (!agents.length) {
    return panel("LLM / IDE lanes",
      `<div class="muted">No lanes detected.</div>`);
  }
  const rows = agents.map(a => `<tr>
    <td><code>${esc(a.id)}</code></td>
    <td>${a.available
      ? '<span class="pill ok">yes</span>'
      : '<span class="pill">no</span>'}</td>
    <td>${a.launchable
      ? '<span class="pill ok">yes</span>'
      : '<span class="pill">no</span>'}</td>
    <td class="muted">${esc(a.reason || "")}</td>
  </tr>`).join("");
  return panel("LLM / IDE lanes",
    `<table><thead><tr><th>id</th><th>available</th>
      <th>launchable</th><th>reason</th></tr></thead>
      <tbody>${rows}</tbody></table>`);
}

function renderPolicy(policy) {
  policy = policy || {};
  const keys = [
    "allow_commit", "allow_push", "allow_branch_create",
    "allow_branch_switch", "allow_tag", "allow_destructive_shell",
    "require_planfile_lifecycle", "require_ci_pass_before_complete",
  ];
  const rows = keys.map(k => {
    const v = policy[k];
    const pill = v === true
      ? '<span class="pill ok">true</span>'
      : v === false
        ? '<span class="pill">false</span>'
        : `<span class="pill">${esc(v)}</span>`;
    return `<tr><td><code>${esc(k)}</code></td><td>${pill}</td></tr>`;
  }).join("");
  const ci = policy.ci_command
    ? `<tr><td><code>ci_command</code></td>
       <td><code>${esc(policy.ci_command)}</code></td></tr>`
    : "";
  return panel("Policy", `<table><tbody>${rows}${ci}</tbody></table>`);
}

function renderSelfService(ss) {
  ss = ss || {};
  const rows = Object.entries(ss).map(([k, v]) =>
    `<tr><td><code>${esc(k)}</code></td>
     <td><code>${esc(v)}</code></td></tr>`).join("");
  return panel("Self-service commands",
    `<table><tbody>${rows}</tbody></table>`);
}

function priorityPill(prio) {
  const cls = prio === "critical" ? "err"
            : prio === "high" ? "warn"
            : prio === "low" ? "" : "ok";
  return `<span class="pill ${cls}">${esc(prio || "normal")}</span>`;
}

function statusPill(status) {
  const cls = status === "done" ? "ok"
            : status === "in_progress" ? "warn"
            : status === "blocked" ? "err"
            : "";
  return `<span class="pill ${cls}">${esc(status || "open")}</span>`;
}

function ticketRow(t, activeId) {
  const id = esc(t.id || "?");
  const isActive = activeId && t.id === activeId;
  const star = isActive ? '<span class="pill ok">active</span> ' : "";
  const exec = esc(((t.executor) || {}).kind || "?");
  const name = esc(t.name || "");
  return `<tr>
    <td><code>${id}</code></td>
    <td>${star}${name}</td>
    <td>${priorityPill(t.priority)}</td>
    <td>${statusPill(t.status)}</td>
    <td><code>${exec}</code></td>
  </tr>`;
}

function ticketsTable(tickets, activeId) {
  return `<table><thead><tr>
    <th>id</th><th>name</th><th>priority</th>
    <th>status</th><th>executor</th>
  </tr></thead><tbody>${
    tickets.map(t => ticketRow(t, activeId)).join("")
  }</tbody></table>`;
}

function renderOpenTickets(openTickets, allTickets, activeId, ticketError) {
  openTickets = openTickets || [];
  allTickets = allTickets || [];

  // Happy path: open queue has work in it.
  if (openTickets.length) {
    return panel("Open tickets",
      ticketsTable(openTickets, activeId), true);
  }

  // Idle queue, but we have history — show it.
  if (allTickets.length) {
    const counts = allTickets.reduce((acc, t) => {
      const s = t.status || "open";
      acc[s] = (acc[s] || 0) + 1;
      return acc;
    }, {});
    const summary = Object.entries(counts).map(
      ([s, n]) => `${statusPill(s)} <strong>${n}</strong>`
    ).join(" · ");
    const hint = `<div class="muted" style="margin-bottom:8px">
      <strong>queue is idle</strong> — ${esc(ticketError || "no open tickets")}.
      ${summary} ·
      run <code>koru scan --apply</code> to generate new tickets
      from real repo signals (pytest collect errors, TODO/FIXME,
      missing gates).
    </div>`;
    return panel("Recent tickets",
      hint + ticketsTable(allTickets, activeId), true);
  }

  // Truly empty.
  return panel("Tickets",
    `<div class="muted">queue is idle — no tickets recorded.
     Try <code>koru scan --apply</code> or <code>koru task "&lt;desc&gt;"</code>.</div>`,
    true);
}

function renderSemcodTools(env) {
  const tools = (env && env.semcod_tools) || [];
  if (!tools.length) return "";
  const installed = tools.filter(t => t.available);
  const missing = tools.filter(t => !t.available);
  const rows = installed.map(t => `<tr>
    <td><code>${esc(t.id)}</code></td>
    <td><code>${esc(t.via)}</code>${
      t.config_present ? ' <span class="pill ok">configured</span>' : ''
    }</td>
    <td class="muted">${esc(t.role || "")}</td>
    <td><code>${esc(t.command_hint || "")}</code></td>
  </tr>`).join("");
  const missingNote = missing.length
    ? `<div class="muted" style="margin-top:8px">Not installed: ${
        missing.map(t => `<code>${esc(t.id)}</code>`).join(", ")
      }</div>`
    : "";
  const body = installed.length
    ? `<table><thead><tr>
        <th>tool</th><th>via</th><th>role</th><th>command</th>
       </tr></thead><tbody>${rows}</tbody></table>${missingNote}`
    : `<div class="muted">No semcod tools detected.</div>${missingNote}`;
  return panel("Available semcod tools", body, true);
}

async function refresh() {
  try {
    const res = await fetch("/api/context", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const ctx = await res.json();
    $("project").textContent = ctx.project || "?";
    $("ts").textContent = new Date().toLocaleTimeString();
    const root = $("root");
    const activeId = (ctx.ticket || {}).id || null;
    root.innerHTML = [
      renderTicket(ctx.ticket, ctx.ticket_error),
      renderEnv(ctx.environment),
      renderOpenTickets(
        ctx.open_tickets, ctx.all_tickets, activeId, ctx.ticket_error
      ),
      renderAgents(ctx.environment),
      renderSemcodTools(ctx.environment),
      renderPolicy(ctx.policy),
      renderSelfService(ctx.self_service),
    ].join("");
  } catch (e) {
    $("root").innerHTML = `<div class="panel full err">
      Failed to load brief: ${esc(e.message)}</div>`;
  }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


@dataclass
class ServeConfig:
    project: Path
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    open_browser: bool = True
    queue_name: str | None = None


def _build_handler(config: ServeConfig) -> type[BaseHTTPRequestHandler]:
    """Create a request handler closure bound to ``config``."""

    class _Handler(BaseHTTPRequestHandler):
        # Silence default access log; we print one summary line on start.
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def _send(
            self,
            status: int,
            body: bytes,
            content_type: str = "text/plain; charset=utf-8",
        ) -> None:
            try:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                # Aggressive no-cache: the dashboard ships embedded HTML
                # and koru releases may change its structure. Stale
                # browser cache otherwise shows tabs from old koru
                # versions (e.g. self-service commands that no longer
                # exist on the new planfile CLI surface).
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # Client closed the connection mid-write. Auto-refresh
                # navigations and tab closures trigger this routinely;
                # it's not an error worth a traceback.
                return

        def _send_json(self, payload: Any, status: int = 200) -> None:
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self._send(status, body, "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802 — stdlib API
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send(
                    200, _DASHBOARD_HTML.encode("utf-8"),
                    "text/html; charset=utf-8",
                )
                return
            if path == "/health":
                self._send_json({"ok": True})
                return
            if path == "/api/context":
                try:
                    ctx = build_context(
                        project=config.project,
                        queue_name=config.queue_name,
                    )
                except Exception as exc:  # pragma: no cover — surface errors
                    self._send_json(
                        {"error": str(exc), "type": type(exc).__name__},
                        status=500,
                    )
                    return
                self._send_json(ctx)
                return
            if path == "/api/handoff":
                try:
                    ctx = build_context(
                        project=config.project,
                        queue_name=config.queue_name,
                    )
                    md = render_markdown_handoff(ctx)
                except Exception as exc:  # pragma: no cover
                    self._send(500, str(exc).encode("utf-8"))
                    return
                self._send(
                    200, md.encode("utf-8"),
                    "text/markdown; charset=utf-8",
                )
                return
            self._send(404, b"not found")

    return _Handler


def build_server(config: ServeConfig) -> ThreadingHTTPServer:
    """Construct (but do not start) the dashboard HTTP server."""
    handler = _build_handler(config)
    return ThreadingHTTPServer((config.host, config.port), handler)


def serve(config: ServeConfig) -> int:
    """Start the dashboard server and block until Ctrl-C.

    Returns the process exit code (0 on clean shutdown).
    """
    try:
        server = build_server(config)
    except OSError as exc:
        print(f"koru serve: cannot bind {config.host}:{config.port} — {exc}")
        return 1

    url = f"http://{config.host}:{config.port}/"
    print(f"koru serve: dashboard at {url}")
    print(f"koru serve: project = {config.project}")
    print("koru serve: Ctrl-C to stop")

    if config.open_browser:
        # Open browser after server is listening, on a background thread,
        # so the open() call doesn't race with serve_forever().
        def _open_later() -> None:
            try:
                webbrowser.open(url, new=2)
            except Exception:  # pragma: no cover — best-effort
                pass

        threading.Timer(0.3, _open_later).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("koru serve: stopping")
    finally:
        server.server_close()
    return 0
