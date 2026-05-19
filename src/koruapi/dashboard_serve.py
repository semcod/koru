"""Minimal local dashboard server for koru (canonical: :mod:`koruapi.dashboard_serve`).

Serves a small HTML page that calls back into ``build_context`` to show
the live LLM brief (active ticket, policy, agent lanes, gates). No
external dependencies — uses ``http.server`` from the stdlib.

TCP port defaults to ``8765``. Use ``--auto-port`` or set
``KORU_SERVE_AUTO_PORT=1`` to try the next ports (then an ephemeral
port) when the preferred port is busy. The resolved URL is written to
``.planfile/.koru/serve-endpoint.json`` for other tooling
(``read_serve_endpoint``).

When the preferred port is busy with a **previous** ``koru serve`` listener
(same host/port), a second ``koru serve`` sends **SIGTERM** to that PID and
retries the bind once (Linux: uses ``ss``). Other processes (e.g. planfile
on :8765) are left untouched. Set ``KORU_SERVE_NO_REPLACE=1`` to disable.

Endpoints:
    GET  /              -> HTML dashboard (auto-refreshing)
    GET  /api/context   -> JSON brief (``build_context`` output)
    GET  /api/handoff   -> raw markdown handoff (``render_markdown_handoff``)
    GET  /api/topology  -> merged topology JSON (defaults + persisted overrides)
    POST /api/topology  -> persist topology enable/disable edits
    GET  /health        -> ``{"ok": true}``

Bound to ``127.0.0.1`` by default — never exposed to the network unless
``--bind`` is explicitly set otherwise.
"""

from __future__ import annotations

import errno
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from koru.context import build_context, render_markdown_handoff
from koru.events import emit_management_event
from koru.queue.runners import run_process
from koru.queue.ticket import planfile_command
from koru.topology import (
    load_topology,
    save_topology,
    set_component_enabled,
    set_pipeline_enabled,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

_SERVE_ENDPOINT_REL = Path(".planfile") / ".koru" / "serve-endpoint.json"


def _list_tickets(project: Path) -> list[dict[str, Any]]:
    """Return all planfile tickets as JSON list (empty on errors)."""
    result = planfile_command(project, ["ticket", "list", "--format", "json"], runner=run_process)
    if result.returncode != 0:
        return []
    try:
        payload = json.loads((result.stdout or "").strip() or "[]")
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return [payload] if isinstance(payload, dict) else []


def apply_topology_post_update(
    project: Path,
    body: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int]:
    """Apply topology enable/disable edits from a POST body."""
    components = body.get("components") or {}
    pipelines = body.get("pipelines") or {}
    if not isinstance(components, dict) or not isinstance(pipelines, dict):
        return None, {"error": "`components` and `pipelines` must be objects"}, 400
    if not components and not pipelines:
        return (
            None,
            {"error": "empty update; provide `components` and/or `pipelines`"},
            400,
        )

    topo = load_topology(project)
    errors: list[str] = []
    applied: list[dict[str, Any]] = []

    for component_id, enabled in components.items():
        if not isinstance(enabled, bool):
            errors.append(f"component {component_id!r}: value must be boolean")
            continue
        result = set_component_enabled(topo, str(component_id), enabled)
        if not result.found:
            errors.append(f"unknown component: {component_id!r}")
            continue
        applied.append(
            {"kind": "component", "id": result.id, "enabled": result.current},
        )

    for pipeline_id, enabled in pipelines.items():
        if not isinstance(enabled, bool):
            errors.append(f"pipeline {pipeline_id!r}: value must be boolean")
            continue
        result = set_pipeline_enabled(topo, str(pipeline_id), enabled)
        if not result.found:
            errors.append(f"unknown pipeline: {pipeline_id!r}")
            continue
        applied.append(
            {"kind": "pipeline", "id": result.id, "enabled": result.current},
        )

    if errors:
        return None, {"error": "invalid topology update", "details": errors}, 400

    saved = save_topology(project, topo)
    merged = load_topology(project)
    merged["path"] = str(saved)
    merged["saved"] = applied
    return merged, None, 200


def _bulk_waiting_input_action(
    project: Path,
    *,
    ticket_ids: list[str],
    action: str,
    reason: str,
) -> dict[str, Any]:
    tickets = _list_tickets(project)
    waiting = {
        str(t.get("id"))
        for t in tickets
        if isinstance(t, dict) and str(t.get("status") or "") == "waiting_input"
    }
    selected = [tid for tid in ticket_ids if tid in waiting]
    if not selected:
        return {"ok": False, "error": "no waiting_input tickets selected", "applied": []}

    applied: list[dict[str, Any]] = []
    for tid in selected:
        if action == "approve":
            claim = planfile_command(
                project,
                ["ticket", "claim", tid, "--assigned-to", "koru-web"],
                runner=run_process,
            )
            if claim.returncode != 0:
                applied.append({"id": tid, "ok": False, "step": "claim", "stderr": claim.stderr[-500:]})
                continue
            start = planfile_command(project, ["ticket", "start", tid], runner=run_process)
            if start.returncode != 0:
                applied.append({"id": tid, "ok": False, "step": "start", "stderr": start.stderr[-500:]})
                continue
            done = planfile_command(project, ["ticket", "done", tid], runner=run_process)
            applied.append(
                {
                    "id": tid,
                    "ok": done.returncode == 0,
                    "action": "approve",
                    "stderr": done.stderr[-500:],
                },
            )
            continue

        block = planfile_command(
            project,
            ["ticket", "block", tid, "--reason", reason or "Rejected in koru web dashboard"],
            runner=run_process,
        )
        applied.append(
            {
                "id": tid,
                "ok": block.returncode == 0,
                "action": "reject",
                "stderr": block.stderr[-500:],
            },
        )

    return {"ok": True, "action": action, "requested": ticket_ids, "applied": applied}


def _address_in_use(exc: BaseException) -> bool:
    if isinstance(exc, OSError):
        if exc.errno in (errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", -1)):
            return True
        winerr = getattr(exc, "winerror", None)
        if winerr == 10048:  # WSAEADDRINUSE
            return True
    return "Address already in use" in str(exc)


def _listener_pids_for_tcp_port(port: int) -> list[int]:
    """Return PIDs listening on *port* (Linux ``ss``); empty if unknown."""
    if sys.platform == "win32":
        return []
    try:
        proc = subprocess.run(
            ["ss", "-H", "-ltnp", f"sport = :{port}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    pids: list[int] = []
    for m in re.finditer(r"pid=(\d+)", text):
        try:
            pids.append(int(m.group(1)))
        except ValueError:
            continue
    return list(dict.fromkeys(pids))


def _cmdline_suggests_koru_serve_from_bytes(raw: bytes) -> bool:
    """True if *raw* is a ``/proc/*/cmdline`` blob for ``koru … serve`` (not ``mcp-serve``)."""
    s = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").lower()
    if re.search(r"\bmcp-serve\b", s):
        return False
    if re.search(r"-m\s+koru\.cli\s+serve\b", s):
        return True
    return bool(re.search(r"(^|[\s/])koru(\.cli)?\s+serve\b", s))


def _cmdline_suggests_koru_serve(pid: int) -> bool:
    if sys.platform == "win32":
        return False
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False
    return _cmdline_suggests_koru_serve_from_bytes(raw)


def _try_stop_prior_koru_serve_listener(host: str, port: int) -> bool:
    """SIGTERM prior ``koru serve`` on *port*; return True if we sent a signal."""
    del host  # ss filter is port-centric; 127.0.0.1 vs 0.0.0.0 both match sport
    if os.environ.get("KORU_SERVE_NO_REPLACE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return False
    killed = False
    for pid in _listener_pids_for_tcp_port(port):
        if pid == os.getpid():
            continue
        if not _cmdline_suggests_koru_serve(pid):
            continue
        try:
            print(
                f"koru serve: port {port} busy — stopping prior listener pid={pid}",
                file=sys.stderr,
            )
            os.kill(pid, signal.SIGTERM)
            killed = True
        except ProcessLookupError:
            continue
    if not killed:
        return False
    for _ in range(40):
        remaining = [
            p
            for p in _listener_pids_for_tcp_port(port)
            if p != os.getpid() and _cmdline_suggests_koru_serve(p)
        ]
        if not remaining:
            break
        time.sleep(0.1)
    return True


def serve_endpoint_path(project: Path) -> Path:
    """JSON path where the last successful ``koru serve`` bind is recorded."""
    return project.resolve() / _SERVE_ENDPOINT_REL


def read_serve_endpoint(project: Path) -> dict[str, Any] | None:
    """Load ``serve-endpoint.json`` if present; return ``None`` on missing/invalid."""
    path = serve_endpoint_path(project)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


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
  · <a href="/api/topology">Topology JSON</a>
  · <a href="/api/runtime-context">Runtime context JSON</a>
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

function renderWaitingInputActions(allTickets) {
  const waiting = (allTickets || []).filter(t => (t.status || "") === "waiting_input");
  if (!waiting.length) return "";
  const rows = waiting.map(t => `
    <tr>
      <td><input type="checkbox" class="wi-ticket" value="${esc(t.id || "")}" checked></td>
      <td><code>${esc(t.id || "")}</code></td>
      <td>${esc(t.name || "")}</td>
      <td><code>${esc(((t.executor) || {}).kind || "?")}</code></td>
    </tr>
  `).join("");
  const body = `
    <div class="muted" style="margin-bottom:8px">
      Queue is blocked on <code>waiting_input</code>. Select tickets and approve or reject in bulk.
    </div>
    <table><thead><tr>
      <th>select</th><th>id</th><th>name</th><th>executor</th>
    </tr></thead><tbody>${rows}</tbody></table>
    <div style="margin-top:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <button id="wi-approve">Approve selected</button>
      <button id="wi-reject">Reject selected</button>
      <input id="wi-reason" placeholder="Reject reason (optional)" style="min-width:320px" />
    </div>
    <div id="wi-status" class="muted" style="margin-top:8px;min-height:1.2em"></div>
  `;
  return panel("Waiting Input Actions", body, true);
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

function renderTopology(topo) {
  if (!topo) return "";
  const components = topo.components || {};
  const pipelines = topo.pipelines || {};
  const compRows = Object.entries(components).map(([id, c]) => {
    const checked = c.enabled ? "checked" : "";
    const avail = c.available
      ? '<span class="pill ok">installed</span>'
      : '<span class="pill">missing</span>';
    const via = c.via && c.via !== "missing"
      ? `<code>${esc(c.via)}</code>` : '<span class="muted">—</span>';
    return `<tr>
      <td><label><input type="checkbox" data-kind="component"
        data-id="${esc(id)}" ${checked}/> <code>${esc(id)}</code></label></td>
      <td>${avail}</td>
      <td>${via}</td>
      <td class="muted">${esc(c.role || "")}</td>
    </tr>`;
  }).join("");
  const pipeRows = Object.entries(pipelines).map(([id, p]) => {
    const checked = p.enabled ? "checked" : "";
    const comps = (p.components || []).map(c =>
      `<code>${esc(c)}</code>`).join(", ") || '<span class="muted">—</span>';
    return `<tr>
      <td><label><input type="checkbox" data-kind="pipeline"
        data-id="${esc(id)}" ${checked}/> <code>${esc(id)}</code></label></td>
      <td><span class="pill">${esc(p.trigger || "manual")}</span></td>
      <td>${comps}</td>
      <td class="muted">${esc(p.description || "")}</td>
    </tr>`;
  }).join("");
  const savedNote = topo.exists
    ? `<span class="pill ok">persisted</span>`
    : `<span class="pill">defaults only — first edit creates ${
        esc(topo.path || ".koru/topology.yaml")
      }</span>`;
  const body = `
    <div style="margin-bottom:12px">${savedNote}
      <span class="muted" style="margin-left:8px">
        Toggle a checkbox to update <code>.koru/topology.yaml</code>.
        Pipelines (gates, autoloop, idle-diagnostics) honour these flags.
      </span>
    </div>
    <h3 style="margin:8px 0 4px;font-size:12px;color:var(--muted);
               text-transform:uppercase;letter-spacing:0.05em">Components</h3>
    <table><thead><tr>
      <th>component</th><th>availability</th><th>via</th><th>role</th>
    </tr></thead><tbody>${compRows}</tbody></table>
    <h3 style="margin:16px 0 4px;font-size:12px;color:var(--muted);
               text-transform:uppercase;letter-spacing:0.05em">Pipelines</h3>
    <table><thead><tr>
      <th>pipeline</th><th>trigger</th><th>components</th><th>description</th>
    </tr></thead><tbody>${pipeRows}</tbody></table>
    <div id="topology-status" class="muted"
         style="margin-top:8px;min-height:1.2em"></div>
  `;
  return panel("Topology & pipelines", body, true);
}

function renderRuntimeContext(runtime) {
  if (!runtime || runtime.error) {
    return panel(
      "Runtime context",
      `<div class="muted">${esc((runtime && runtime.error) || "not available")}</div>`,
      true,
    );
  }
  const summary = runtime.summary || {};
  const enabled = ((runtime.config || {}).enabled) || {};
  const labels = {
    systems: "systems", libraries: "libraries", algorithms: "algorithms",
    apis: "apis", applications: "applications", pipelines: "pipelines", topology: "topology"
  };
  const checks = Object.entries(labels).map(([key, label]) => `
    <label style="display:inline-block;margin:2px 12px 6px 0">
      <input type="checkbox" data-runtime-section="${esc(key)}" ${enabled[key] ? "checked" : ""}/>
      <code>${esc(label)}</code>
    </label>
  `).join("");
  const systems = (runtime.systems || []).slice(0, 12).map(s =>
    `<span class="pill">${esc(s.name || "?")}</span>`
  ).join("");
  const body = `
    <div class="kv">
      <dt>project</dt><dd><code>${esc(summary.project || runtime.project_root || "?")}</code></dd>
      <dt>version</dt><dd>${esc(summary.version || "-")}</dd>
      <dt>services</dt><dd>${esc(summary.services || 0)}</dd>
      <dt>workspaces</dt><dd>${esc(summary.workspaces || 0)}</dd>
      <dt>pipelines</dt><dd>${esc(summary.pipelines || 0)}</dd>
      <dt>topology nodes</dt><dd>${esc(summary.topology_nodes || 0)}</dd>
    </div>
    <div style="margin-top:12px">${checks}</div>
    <div class="muted" style="margin-top:8px">First services: ${systems || "none"}</div>
    <div id="runtime-context-status" class="muted" style="margin-top:8px;min-height:1.2em"></div>
  `;
  return panel("Runtime context", body, true);
}

async function postTopologyToggle(kind, id, enabled) {
  const status = document.getElementById("topology-status");
  if (status) status.textContent = `saving ${kind} ${id}…`;
  try {
    const body = kind === "component"
      ? { components: { [id]: enabled } }
      : { pipelines:  { [id]: enabled } };
    const res = await fetch("/api/topology", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error("HTTP " + res.status + ": " + text);
    }
    const data = await res.json();
    if (status) {
      status.textContent = `saved ${kind} ${id} = ${enabled} `
        + `(path: ${data.path || ".koru/topology.yaml"})`;
      status.classList.remove("err");
      status.classList.add("ok");
    }
  } catch (e) {
    if (status) {
      status.textContent = "save failed: " + e.message;
      status.classList.remove("ok");
      status.classList.add("err");
    }
  }
}

async function postRuntimeContextToggle(section, enabled) {
  const status = document.getElementById("runtime-context-status");
  if (status) status.textContent = `saving ${section}…`;
  try {
    const res = await fetch("/api/runtime-context/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: { [section]: enabled } }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error("HTTP " + res.status + ": " + text);
    }
    if (status) {
      status.textContent = `saved ${section} = ${enabled}`;
      status.classList.remove("err");
      status.classList.add("ok");
    }
    setTimeout(refresh, 150);
  } catch (e) {
    if (status) {
      status.textContent = "save failed: " + e.message;
      status.classList.remove("ok");
      status.classList.add("err");
    }
  }
}

function selectedWaitingTickets() {
  return Array.from(document.querySelectorAll(".wi-ticket"))
    .filter(el => el.checked)
    .map(el => el.value)
    .filter(Boolean);
}

async function postWaitingInputAction(action) {
  const status = $("wi-status");
  const ticket_ids = selectedWaitingTickets();
  if (!ticket_ids.length) {
    if (status) status.textContent = "select at least one ticket";
    return;
  }
  const reasonEl = $("wi-reason");
  const reason = reasonEl ? reasonEl.value : "";
  if (status) status.textContent = `${action} ${ticket_ids.length} ticket(s)…`;
  try {
    const res = await fetch("/api/tickets/waiting-input/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ticket_ids, reason }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    const okCount = (data.applied || []).filter(x => x.ok).length;
    if (status) {
      status.textContent = `${action}: ${okCount}/${(data.applied || []).length} succeeded`;
      status.classList.remove("err");
      status.classList.add("ok");
    }
    setTimeout(refresh, 150);
  } catch (e) {
    if (status) {
      status.textContent = "action failed: " + e.message;
      status.classList.remove("ok");
      status.classList.add("err");
    }
  }
}

document.addEventListener("change", (ev) => {
  const t = ev.target;
  if (!(t instanceof HTMLInputElement)) return;
  if (t.type !== "checkbox") return;
  const runtimeSection = t.getAttribute("data-runtime-section");
  if (runtimeSection) {
    postRuntimeContextToggle(runtimeSection, t.checked);
    return;
  }
  const kind = t.getAttribute("data-kind");
  const id = t.getAttribute("data-id");
  if (!kind || !id) return;
  postTopologyToggle(kind, id, t.checked);
});

document.addEventListener("click", (ev) => {
  const t = ev.target;
  if (!(t instanceof HTMLElement)) return;
  if (t.id === "wi-approve") {
    postWaitingInputAction("approve");
  } else if (t.id === "wi-reject") {
    postWaitingInputAction("reject");
  }
});

async function refresh() {
  try {
    const [ctxRes, topoRes, runtimeRes] = await Promise.all([
      fetch("/api/context",  { cache: "no-store" }),
      fetch("/api/topology", { cache: "no-store" }),
      fetch("/api/runtime-context", { cache: "no-store" }),
    ]);
    if (!ctxRes.ok)  throw new Error("HTTP " + ctxRes.status);
    if (!topoRes.ok) throw new Error("HTTP " + topoRes.status);
    const ctx = await ctxRes.json();
    const topo = await topoRes.json();
    const runtime = runtimeRes.ok
      ? await runtimeRes.json()
      : { error: "runtime context unavailable" };
    $("project").textContent = ctx.project || "?";
    $("ts").textContent = new Date().toLocaleTimeString();
    const root = $("root");
    const activeId = (ctx.ticket || {}).id || null;
    root.innerHTML = [
      renderSelfService(ctx.self_service),
      renderTicket(ctx.ticket, ctx.ticket_error),
      renderEnv(ctx.environment),
      renderWaitingInputActions(ctx.all_tickets),
      renderOpenTickets(
        ctx.open_tickets, ctx.all_tickets, activeId, ctx.ticket_error
      ),
      renderAgents(ctx.environment),
      renderSemcodTools(ctx.environment),
      renderRuntimeContext(runtime),
      renderTopology(topo),
      renderPolicy(ctx.policy),
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
    auto_port: bool = False


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

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}

        def do_GET(self) -> None:  # noqa: N802 — stdlib API
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send(
                    200,
                    _DASHBOARD_HTML.encode("utf-8"),
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
            if path == "/api/topology":
                try:
                    topo = load_topology(config.project)
                except Exception as exc:  # pragma: no cover — surface errors
                    self._send_json(
                        {"error": str(exc), "type": type(exc).__name__},
                        status=500,
                    )
                    return
                self._send_json(topo)
                return
            if path == "/api/runtime-context":
                try:
                    from planfile.runtime_context import build_runtime_context

                    runtime = build_runtime_context(config.project)
                except Exception as exc:  # pragma: no cover — optional planfile integration
                    runtime = {"error": str(exc), "type": type(exc).__name__}
                self._send_json(runtime)
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
                    200,
                    md.encode("utf-8"),
                    "text/markdown; charset=utf-8",
                )
                return
            self._send(404, b"not found")

        def do_POST(self) -> None:  # noqa: N802 — stdlib API
            path = self.path.split("?", 1)[0]
            try:
                body = self._read_json_body()
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            if path == "/api/topology":
                merged, err, status = apply_topology_post_update(config.project, body)
                if err is not None:
                    self._send_json(err, status=status)
                    return
                self._send_json(merged)
                return

            if path == "/api/runtime-context/config":
                try:
                    from planfile.runtime_context import (
                        load_runtime_context_config,
                        save_runtime_context_config,
                    )

                    current = load_runtime_context_config(config.project)
                    merged = {
                        "enabled": {
                            **(current.get("enabled") or {}),
                            **(body.get("enabled") or {}),
                        },
                        "overrides": {
                            **(current.get("overrides") or {}),
                            **(body.get("overrides") or {}),
                        },
                    }
                    saved_config = save_runtime_context_config(config.project, merged)
                except Exception as exc:  # pragma: no cover — optional planfile integration
                    self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
                    return
                self._send_json(saved_config)
                return
            if path == "/api/tickets/waiting-input/bulk":
                action = str(body.get("action") or "").strip().lower()
                if action not in {"approve", "reject"}:
                    self._send_json({"error": "action must be approve|reject"}, status=400)
                    return
                ticket_ids_raw = body.get("ticket_ids")
                if not isinstance(ticket_ids_raw, list):
                    self._send_json({"error": "ticket_ids must be an array"}, status=400)
                    return
                ticket_ids = [str(x).strip() for x in ticket_ids_raw if str(x).strip()]
                reason = str(body.get("reason") or "").strip()
                result = _bulk_waiting_input_action(
                    config.project,
                    ticket_ids=ticket_ids,
                    action=action,
                    reason=reason,
                )
                if not result.get("ok"):
                    self._send_json(result, status=400)
                    return
                self._send_json(result)
                return
            self._send(404, b"not found")

    return _Handler


def build_server(config: ServeConfig) -> ThreadingHTTPServer:
    """Construct (but do not start) the dashboard HTTP server."""
    handler = _build_handler(config)
    return ThreadingHTTPServer((config.host, config.port), handler)


def write_serve_endpoint_file(config: ServeConfig) -> None:
    """Persist dashboard base URL and port for other tools (``read_serve_endpoint``)."""
    koru_dir = config.project.resolve() / ".planfile" / ".koru"
    koru_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "http_base": f"http://{config.host}:{config.port}",
        "host": config.host,
        "port": config.port,
        "pid": os.getpid(),
    }
    (koru_dir / "serve-endpoint.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def bind_serve_server(config: ServeConfig) -> tuple[ThreadingHTTPServer, int, int]:
    """Bind a server; set ``config.port`` to the listening port.

    Returns ``(server, actual_port, requested_port)``.
    """
    requested = config.port
    if not config.auto_port:
        try:
            server = build_server(config)
            return server, config.port, requested
        except OSError as exc:
            if not _address_in_use(exc):
                raise
            if _try_stop_prior_koru_serve_listener(config.host, config.port):
                server = build_server(config)
                return server, config.port, requested
            raise

    ceiling = min(requested + 33, 65536)
    candidates = [requested] + [p for p in range(requested + 1, ceiling) if p != requested]
    last_err: OSError | None = None
    for p in candidates:
        config.port = p
        try:
            server = build_server(config)
            return server, p, requested
        except OSError as exc:
            last_err = exc
            continue

    config.port = 0
    try:
        server = build_server(config)
    except OSError as exc:
        msg = f"koru serve: cannot bind {config.host} starting from port {requested}"
        if last_err is not None:
            msg += f" — {last_err}"
        raise OSError(msg) from exc
    actual = int(server.server_address[1])
    config.port = actual
    return server, actual, requested


def serve(config: ServeConfig) -> int:
    """Start the dashboard server and block until Ctrl-C.

    Returns the process exit code (0 on clean shutdown).
    """
    try:
        server, actual, requested = bind_serve_server(config)
    except OSError as exc:
        if not config.auto_port:
            print(
                f"koru serve: cannot bind {config.host}:{config.port} — {exc}",
                file=sys.stderr,
            )
        else:
            print(str(exc), file=sys.stderr)
        return 1

    write_serve_endpoint_file(config)
    url = f"http://{config.host}:{config.port}/"
    if config.auto_port and actual != requested:
        print(
            f"koru serve: port {requested} busy — bound to {actual} instead",
            file=sys.stderr,
        )
    print(f"koru serve: dashboard at {url}")
    print(f"koru serve: project = {config.project}")
    print("koru serve: Ctrl-C to stop")

    emit_management_event(
        tool="koru.serve",
        action="started",
        status="running",
        message=url,
        queue=config.queue_name,
        details={
            "project": str(config.project),
            "open_browser": config.open_browser,
            "port": config.port,
            "requested_port": requested,
        },
    )

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


def start_serve_background(
    config: ServeConfig,
    *,
    log: Callable[[str], None] = print,
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Bind the dashboard, write ``serve-endpoint.json``, and run ``serve_forever`` on a thread.

    The caller should ``shutdown()`` the server, ``server_close()``, and
    ``join()`` the returned thread when tearing down (e.g. ``koru autonomous``).
    """
    server, actual, requested = bind_serve_server(config)
    write_serve_endpoint_file(config)
    url = f"http://{config.host}:{config.port}/"
    if config.auto_port and actual != requested:
        log(f"koru serve: port {requested} busy — bound to {actual} instead")
    log(f"koru serve: dashboard at {url}")
    log(f"koru serve: project = {config.project}")
    emit_management_event(
        tool="koru.serve",
        action="started",
        status="running",
        message=url,
        queue=config.queue_name,
        details={
            "project": str(config.project),
            "open_browser": config.open_browser,
            "port": config.port,
            "requested_port": requested,
            "background": True,
        },
    )
    if config.open_browser:

        def _open_later() -> None:
            try:
                webbrowser.open(url, new=2)
            except Exception:  # pragma: no cover — best-effort
                pass

        threading.Timer(0.3, _open_later).start()

    thread = threading.Thread(
        target=server.serve_forever,
        name="koru-serve-bg",
        daemon=True,
    )
    thread.start()
    time.sleep(0.05)
    return server, thread
