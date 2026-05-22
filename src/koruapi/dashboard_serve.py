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

import contextlib
import errno
import importlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

yaml = cast(Any, importlib.import_module("yaml"))

from koru.configurator import CONFIG_REL_PATH, configure_project, load_project_config
from koru.context import build_context, render_markdown_handoff
from koru.events import emit_management_event
from koru.queue.runners import run_process
from koru.queue.ticket import planfile_command
from koru.wizard.project import propose_projects
from koruide.ide import autopilot_ide_choices, detect_running_ides, normalize_ide_id
from koruapi.runtime_insights import collect_runtime_insights
from koruapi.topology_post import apply_topology_post_update
from koru.topology import (
    load_topology,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

_SERVE_ENDPOINT_REL = Path(".planfile") / ".koru" / "serve-endpoint.json"


def _run_planfile(command: Sequence[str], project: Path) -> Any:
    return run_process(list(command), project)


def _list_tickets(project: Path) -> list[dict[str, Any]]:
    """Return all planfile tickets as JSON list (empty on errors)."""
    result = planfile_command(project, ["ticket", "list", "--format", "json"], runner=_run_planfile)
    if result.returncode != 0:
        return []
    try:
        payload = json.loads((result.stdout or "").strip() or "[]")
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return [payload] if isinstance(payload, dict) else []

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
                runner=_run_planfile,
            )
            if claim.returncode != 0:
                applied.append(
                    {"id": tid, "ok": False, "step": "claim", "stderr": claim.stderr[-500:]}
                )
                continue
            start = planfile_command(project, ["ticket", "start", tid], runner=_run_planfile)
            if start.returncode != 0:
                applied.append(
                    {"id": tid, "ok": False, "step": "start", "stderr": start.stderr[-500:]}
                )
                continue
            done = planfile_command(project, ["ticket", "done", tid], runner=_run_planfile)
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
            runner=_run_planfile,
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
  .app-shell {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 24px;
  }
  .controls {
    margin: 16px auto 0;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .controls label {
    display: flex;
    flex-direction: column;
    gap: 3px;
    color: var(--muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .controls select,
  .controls input,
  select.inline-select,
  input,
  textarea {
    padding: 4px 8px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--fg);
    font-size: 13px;
  }
  .controls select { min-width: 220px; }
  .controls .wide { min-width: 360px; max-width: min(70vw, 560px); }
  button {
    padding: 5px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: #1f2533;
    color: var(--fg);
    cursor: pointer;
    font-size: 12px;
  }
  button.primary { border: none; background: var(--accent); color: #0f1115; font-weight: 600; }
  button.icon { width: 28px; height: 28px; padding: 0; }
  .view-tabs {
    margin: 16px auto 0;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 2px;
  }
  .view-tab {
    white-space: nowrap;
    border-color: transparent;
    background: transparent;
    color: var(--muted);
  }
  .view-tab.active {
    background: #1f2533;
    border-color: var(--border);
    color: var(--fg);
  }
  .scope-line {
    margin: 10px auto 0;
    color: var(--muted);
    font-size: 12px;
    word-break: break-word;
  }
  main {
    margin: 0 auto;
    padding: 16px 0 24px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    overflow-x: auto;
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
  .tool-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .tool-icon {
    width: 1.2rem;
    text-align: center;
    opacity: 0.9;
    font-size: 13px;
  }
  table { width: 100%; border-collapse: collapse; }
  .table-wrap { width: 100%; overflow-x: auto; }
  .form-stack { display: flex; flex-direction: column; gap: 8px; }
  .form-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
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
  @media (max-width: 760px) {
    header {
      align-items: flex-start;
      flex-direction: column;
      gap: 4px;
      padding: 14px 16px;
    }
    .app-shell { padding: 0 12px; }
    .controls {
      align-items: stretch;
      flex-direction: column;
      gap: 10px;
    }
    .controls select,
    .controls input,
    .controls .wide,
    input,
    textarea,
    select.inline-select { width: 100%; min-width: 0; max-width: 100%; }
    main { grid-template-columns: 1fr; gap: 12px; padding-top: 12px; }
    .panel { padding: 12px; border-radius: 6px; }
    .kv { grid-template-columns: 1fr; gap: 2px 0; }
    th, td { padding: 7px 6px; }
  }
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
<div class="app-shell">
  <section class="controls panel full" id="dashboard-controls">
    <span class="muted">Loading dashboard controls…</span>
  </section>
  <nav class="view-tabs" id="view-tabs" aria-label="Dashboard views"></nav>
  <div class="scope-line" id="scope-line"></div>
  <main id="root">
    <div class="panel full"><span class="muted">Loading brief…</span></div>
  </main>
</div>
<footer>
  Auto-refresh 5 s · URL carries current <code>tab</code>, <code>project</code>, <code>ide</code>, and <code>change</code> ·
  <a href="/api/context">JSON</a> · <a href="/api/handoff">Markdown</a>
  · <a href="/api/topology">Topology JSON</a>
  · <a href="/api/runtime-context">Runtime context JSON</a>
</footer>
<script>
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const attr = (s) => esc(s).replace(/"/g, "&quot;");
const tabs = [
  ["overview", "Overview"],
  ["tickets", "Tickets"],
  ["runtime", "Runtime"],
  ["topology", "Topology"],
  ["policy", "Policy"],
  ["settings", "Settings"],
  ["all", "All"],
];
const urlState = new URL(window.location.href);
const state = {
  project: urlState.searchParams.get("project") || localStorage.getItem("koru.dashboard.project") || "",
  ide: urlState.searchParams.get("ide") || localStorage.getItem("koru.dashboard.ide") || "auto",
  tab: urlState.searchParams.get("tab") || localStorage.getItem("koru.dashboard.tab") || "overview",
  focus: urlState.searchParams.get("focus") || "",
  change: urlState.searchParams.get("change") || "",
};

if (!tabs.some(([id]) => id === state.tab)) state.tab = "overview";

function projectQuery() {
  return state.project ? `?project=${encodeURIComponent(state.project)}` : "";
}

function syncUrlState({ replace=false } = {}) {
  const url = new URL(window.location.href);
  const pairs = {
    tab: state.tab,
    project: state.project,
    ide: state.ide,
    focus: state.focus,
    change: state.change,
  };
  Object.entries(pairs).forEach(([key, value]) => {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  });
  const method = replace ? "replaceState" : "pushState";
  window.history[method]({}, "", url);
  const scope = $("scope-line");
  if (scope) {
    scope.innerHTML = `view <code>${esc(state.tab)}</code> · project <code>${esc(state.project || "default")}</code> · IDE <code>${esc(state.ide || "auto")}</code>${state.change ? ` · changing <code>${esc(state.change)}</code>` : ""}`;
  }
}

function noteChange(change, focus="") {
  state.change = change || "";
  state.focus = focus || "";
  syncUrlState();
}

function requestBody(extra) {
  return Object.assign({}, extra, {
    project: state.project || undefined,
    ide: state.ide || "auto",
  });
}

function renderDashboardControls(dash) {
  const projects = dash.projects || [];
  const ides = dash.ides || [];
  const projectPaths = projects.map(p => p.path);
  if (!state.project || !projectPaths.includes(state.project)) {
    state.project = dash.default_project || (projects[0] || {}).path || "";
    if (state.project) localStorage.setItem("koru.dashboard.project", state.project);
  }
  if (!state.ide) state.ide = "auto";
  const projectOptions = projects.map(p => `<option value="${attr(p.path)}" ${p.path === state.project ? "selected" : ""}>
    ${esc(p.name || p.path)}${p.planfile ? "" : " · no planfile"}
  </option>`).join("");
  const ideOptions = ides.map(ide => `<option value="${attr(ide.id)}" ${ide.id === state.ide ? "selected" : ""}>
    ${esc(ide.label || ide.id)}${ide.running ? " · running" : ""}
  </option>`).join("");
  const urls = (dash.urls || []).map(url => `<code>${esc(url)}</code>`).join(" ");
  const controls = $("dashboard-controls");
  if (!controls) return;
  controls.innerHTML = `
    <label>Project
      <select id="project-select" class="wide">${projectOptions}</select>
    </label>
    <label>IDE lane
      <select id="ide-select">${ideOptions}</select>
    </label>
    <span class="muted">${dash.lan ? "LAN" : "local"} · ${urls}</span>
  `;
}

function renderTabs() {
  const node = $("view-tabs");
  if (!node) return;
  node.innerHTML = tabs.map(([id, label]) => `
    <button type="button" class="view-tab ${id === state.tab ? "active" : ""}" data-tab="${attr(id)}">
      ${esc(label)}
    </button>
  `).join("");
}

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
  const agentIcons = {
    "antigravity": "🪂",
    "claude-code": "✳",
    "codex": "⌘",
    "gemini-cli": "♊",
    "cline": "🧩",
    "qwen-code": "◌",
    "opencode": "⌥",
    "cursor": "⌖",
    "windsurf": "〰",
    "aider": "🛠",
    "openrouter": "⇄",
  };
  const renderAgentId = (id) => {
    const icon = agentIcons[id] || "•";
    return `<span class="tool-label"><span class="tool-icon" aria-hidden="true">${icon}</span><code>${esc(id)}</code></span>`;
  };
  const rows = agents.map(a => `<tr>
    <td>${renderAgentId(a.id)}</td>
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
  const rawId = attr(t.id || "");
  const isActive = activeId && t.id === activeId;
  const star = isActive ? '<span class="pill ok">active</span> ' : "";
  const exec = esc(((t.executor) || {}).kind || "?");
  const name = esc(t.name || "");
  const priority = t.priority || "normal";
  const priorities = ["critical", "high", "normal", "low"];
  const prioritySelect = `<select class="inline-select" data-ticket-priority="${rawId}">
    ${priorities.map(p => `<option value="${p}" ${p === priority ? "selected" : ""}>${p}</option>`).join("")}
  </select>`;
  return `<tr>
    <td><code>${id}</code></td>
    <td>${star}${name}</td>
    <td>${prioritySelect}</td>
    <td>${statusPill(t.status)}</td>
    <td><code>${exec}</code></td>
    <td>
      <button class="icon" type="button" title="Move up" data-ticket-move="${rawId}" data-direction="up">&#8593;</button>
      <button class="icon" type="button" title="Move down" data-ticket-move="${rawId}" data-direction="down">&#8595;</button>
    </td>
  </tr>`;
}

function ticketsTable(tickets, activeId) {
  return `<div class="table-wrap"><table><thead><tr>
    <th>id</th><th>name</th><th>priority</th>
    <th>status</th><th>executor</th><th>order</th>
  </tr></thead><tbody>${
    tickets.map(t => ticketRow(t, activeId)).join("")
  }</tbody></table></div>`;
}

function renderCreateTicketForm() {
  return panel("Create ticket", `
    <form id="create-ticket-form" autocomplete="off">
      <div class="form-stack">
        <input id="ct-title" placeholder="Ticket title (optional)" />
        <textarea id="ct-description" rows="3" placeholder="Description / prompt (required)"></textarea>
        <div class="form-row">
          <select id="ct-priority">
            <option value="normal">normal</option>
            <option value="high">high</option>
            <option value="critical">critical</option>
            <option value="low">low</option>
          </select>
          <select id="ct-executor">
            <option value="human">human (LLM IDE)</option>
            <option value="shell">shell</option>
            <option value="api">api</option>
          </select>
          <input id="ct-queue" value="default" placeholder="Queue" />
          <button type="submit" class="primary">Create</button>
        </div>
      </div>
      <div id="ct-status" class="muted" style="margin-top:6px;min-height:1.2em"></div>
    </form>
  `, true);
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
  const insights = runtime.insights || {};
  const live = insights.summary || {};
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
  const activeTools = (insights.active_tools || []).slice(0, 8).map(t =>
    `<span class="pill ok">${esc(t.label || t.id || "?")} · pid ${esc(t.pid)} · cpu ${esc(t.cpu)}%</span>`
  ).join("");
  const topProcesses = (insights.top_processes || []).slice(0, 6).map(p =>
    `<tr>
      <td><code>${esc(p.name || "?")}</code></td>
      <td><code>${esc(p.pid)}</code></td>
      <td>${esc(p.category || "-")}</td>
      <td>${esc(p.cpu)}%</td>
      <td>${esc(p.rss_mb)} MB</td>
      <td>${esc(p.etime || "-")}</td>
    </tr>`
  ).join("");
  const runningIdes = (insights.running_ides || []).slice(0, 8).map(ide =>
    `<span class="pill">${esc(ide.label || ide.id || "?")} · pid ${esc(ide.pid)}</span>`
  ).join("");
  const body = `
    <div class="kv">
      <dt>project</dt><dd><code>${esc(summary.project || runtime.project_root || "?")}</code></dd>
      <dt>version</dt><dd>${esc(summary.version || "-")}</dd>
      <dt>services</dt><dd>${esc(summary.services || 0)}</dd>
      <dt>workspaces</dt><dd>${esc(summary.workspaces || 0)}</dd>
      <dt>pipelines</dt><dd>${esc(summary.pipelines || 0)}</dd>
      <dt>topology nodes</dt><dd>${esc(summary.topology_nodes || 0)}</dd>
      <dt>live IDEs</dt><dd>${esc(live.running_ides || 0)}</dd>
      <dt>active tools</dt><dd>${esc(live.active_tools || 0)}</dd>
      <dt>top processes</dt><dd>${esc(live.top_processes || 0)}</dd>
    </div>
    <div style="margin-top:12px">${checks}</div>
    <div class="muted" style="margin-top:8px">First services: ${systems || "none"}</div>
    <div class="muted" style="margin-top:10px">Running IDEs: ${runningIdes || "none"}</div>
    <div class="muted" style="margin-top:10px">Active tools now: ${activeTools || "none"}</div>
    <div style="margin-top:12px">
      <table><thead><tr>
        <th>process</th><th>pid</th><th>category</th><th>cpu</th><th>rss</th><th>etime</th>
      </tr></thead><tbody>${topProcesses || `<tr><td colspan="6" class="muted">no process data</td></tr>`}</tbody></table>
    </div>
    <div id="runtime-context-status" class="muted" style="margin-top:8px;min-height:1.2em"></div>
  `;
  return panel("Runtime context", body, true);
}

function renderSettings(configPayload) {
  const cfg = (configPayload && configPayload.config) || {};
  const serve = cfg.serve || {};
  const choices = (configPayload && configPayload.ide_choices) || ["auto"];
  const selectedIde = cfg.ide || state.ide || "auto";
  const ideOptions = choices.map(ide => `<option value="${attr(ide)}" ${ide === selectedIde ? "selected" : ""}>${esc(ide)}</option>`).join("");
  const body = `
    <form id="config-form" autocomplete="off">
      <div class="form-stack">
        <label>Workspace root
          <input id="cfg-workspace" value="${attr(cfg.workspace || "")}" />
        </label>
        <div class="form-row">
          <label>IDE lane
            <select id="cfg-ide">${ideOptions}</select>
          </label>
          <label>Default queue
            <input id="cfg-queue" value="${attr(cfg.queue_name || "default")}" />
          </label>
        </div>
        <div class="form-row">
          <label>Dashboard host
            <input id="cfg-host" value="${attr(serve.host || "127.0.0.1")}" />
          </label>
          <label>Dashboard port
            <input id="cfg-port" type="number" min="1" max="65535" value="${attr(serve.port || 8765)}" />
          </label>
        </div>
        <div class="form-row">
          <label><input id="cfg-lan" type="checkbox" ${serve.lan ? "checked" : ""} /> LAN</label>
          <label><input id="cfg-auto-port" type="checkbox" ${serve.auto_port ? "checked" : ""} /> auto port</label>
          <button type="submit" class="primary">Save settings</button>
        </div>
      </div>
      <div class="muted" style="margin-top:8px">Path: <code>${esc((configPayload && configPayload.path) || ".koru/config.json")}</code></div>
      <div id="config-status" class="muted" style="margin-top:6px;min-height:1.2em"></div>
    </form>
  `;
  return panel("Settings", body, true);
}

function renderViewContent(ctx, topo, runtime, configPayload) {
  const activeId = (ctx.ticket || {}).id || null;
  const views = {
    overview: [
      renderTicket(ctx.ticket, ctx.ticket_error),
      renderEnv(ctx.environment),
      renderAgents(ctx.environment),
    ],
    tickets: [
      renderCreateTicketForm(),
      renderWaitingInputActions(ctx.all_tickets),
      renderOpenTickets(ctx.open_tickets, ctx.all_tickets, activeId, ctx.ticket_error),
    ],
    runtime: [
      renderRuntimeContext(runtime),
      renderSemcodTools(ctx.environment),
      renderAgents(ctx.environment),
    ],
    topology: [
      renderTopology(topo),
    ],
    policy: [
      renderPolicy(ctx.policy),
      renderSelfService(ctx.self_service),
    ],
    settings: [
      renderSettings(configPayload),
    ],
    all: [
      renderSettings(configPayload),
      renderSelfService(ctx.self_service),
      renderTicket(ctx.ticket, ctx.ticket_error),
      renderEnv(ctx.environment),
      renderWaitingInputActions(ctx.all_tickets),
      renderOpenTickets(ctx.open_tickets, ctx.all_tickets, activeId, ctx.ticket_error),
      renderAgents(ctx.environment),
      renderSemcodTools(ctx.environment),
      renderRuntimeContext(runtime),
      renderTopology(topo),
      renderPolicy(ctx.policy),
    ],
  };
  return (views[state.tab] || views.overview).filter(Boolean).join("");
}

async function postTopologyToggle(kind, id, enabled) {
  const status = document.getElementById("topology-status");
  if (status) status.textContent = `saving ${kind} ${id}…`;
  noteChange(`topology:${kind}`, id);
  try {
    const body = kind === "component"
      ? { components: { [id]: enabled } }
      : { pipelines:  { [id]: enabled } };
    const res = await fetch("/api/topology", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody(body)),
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
  noteChange("runtime-context", section);
  try {
    const res = await fetch("/api/runtime-context/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody({ enabled: { [section]: enabled } })),
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
  noteChange(`waiting-input:${action}`, ticket_ids.join(","));
  try {
    const res = await fetch("/api/tickets/waiting-input/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody({ action, ticket_ids, reason })),
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

async function postTicketPriority(ticket_id, priority) {
  noteChange("ticket.priority", ticket_id);
  const res = await fetch("/api/tickets/update", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody({ ticket_id, priority })),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
  setTimeout(refresh, 150);
}

async function postTicketReorder(ticket_id, direction) {
  noteChange("ticket.order", ticket_id);
  const res = await fetch("/api/tickets/reorder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody({ ticket_id, direction })),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
  setTimeout(refresh, 150);
}

async function postDashboardConfig() {
  const status = $("config-status");
  if (status) { status.textContent = "saving settings…"; status.className = "muted"; }
  const port = Number($("cfg-port").value || 8765);
  noteChange("settings.save", "config");
  const body = requestBody({
    workspace: $("cfg-workspace").value.trim(),
    ide: $("cfg-ide").value,
    queue_name: $("cfg-queue").value.trim() || "default",
    serve: {
      host: $("cfg-host").value.trim() || "127.0.0.1",
      port,
      lan: $("cfg-lan").checked,
      auto_port: $("cfg-auto-port").checked,
    },
  });
  const res = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
  state.ide = data.config.ide || state.ide;
  localStorage.setItem("koru.dashboard.ide", state.ide);
  if (status) { status.textContent = `saved ${data.path}`; status.className = "muted ok"; }
  setTimeout(refresh, 200);
}

document.addEventListener("change", (ev) => {
  const t = ev.target;
  if (t instanceof HTMLSelectElement) {
    if (t.id === "project-select") {
      state.project = t.value;
      state.focus = "project";
      state.change = "scope.project";
      localStorage.setItem("koru.dashboard.project", state.project);
      syncUrlState();
      refresh();
      return;
    }
    if (t.id === "ide-select") {
      state.ide = t.value || "auto";
      state.focus = "ide";
      state.change = "scope.ide";
      localStorage.setItem("koru.dashboard.ide", state.ide);
      syncUrlState();
      return;
    }
    const ticketId = t.getAttribute("data-ticket-priority");
    if (ticketId) {
      postTicketPriority(ticketId, t.value).catch(e => window.alert(e.message));
      return;
    }
  }
  if (!(t instanceof HTMLInputElement) || t.type !== "checkbox") return;
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
  const tab = t.getAttribute("data-tab");
  if (tab) {
    state.tab = tab;
    state.focus = "view";
    state.change = "view.tab";
    localStorage.setItem("koru.dashboard.tab", state.tab);
    syncUrlState();
    renderTabs();
    refresh();
    return;
  }
  const ticketMove = t.getAttribute("data-ticket-move");
  if (ticketMove) {
    postTicketReorder(ticketMove, t.getAttribute("data-direction") || "down")
      .catch(e => window.alert(e.message));
    return;
  }
  if (t.id === "wi-approve") {
    postWaitingInputAction("approve");
  } else if (t.id === "wi-reject") {
    postWaitingInputAction("reject");
  }
});

async function refresh() {
  try {
    const dashRes = await fetch("/api/dashboard", { cache: "no-store" });
    if (!dashRes.ok) throw new Error("HTTP " + dashRes.status);
    const dash = await dashRes.json();
    renderDashboardControls(dash);
    renderTabs();
    syncUrlState({ replace: true });
    const [ctxRes, topoRes, runtimeRes, configRes] = await Promise.all([
      fetch("/api/context" + projectQuery(),  { cache: "no-store" }),
      fetch("/api/topology" + projectQuery(), { cache: "no-store" }),
      fetch("/api/runtime-context" + projectQuery(), { cache: "no-store" }),
      fetch("/api/config" + projectQuery(), { cache: "no-store" }),
    ]);
    if (!ctxRes.ok)  throw new Error("HTTP " + ctxRes.status);
    if (!topoRes.ok) throw new Error("HTTP " + topoRes.status);
    const ctx = await ctxRes.json();
    const topo = await topoRes.json();
    const runtime = runtimeRes.ok
      ? await runtimeRes.json()
      : { error: "runtime context unavailable" };
    const configPayload = configRes.ok
      ? await configRes.json()
      : { error: "configuration unavailable" };
    $("project").textContent = ctx.project || "?";
    $("ts").textContent = new Date().toLocaleTimeString();
    const root = $("root");
    const form = $("create-ticket-form");
    const editingTicket = form && ($("ct-title")?.value || $("ct-description")?.value);
    const configForm = $("config-form");
    const editingConfig = configForm && document.activeElement && configForm.contains(document.activeElement);
    if (!(state.tab === "tickets" && editingTicket) && !(state.tab === "settings" && editingConfig)) {
      root.innerHTML = renderViewContent(ctx, topo, runtime, configPayload);
    }
  } catch (e) {
    $("root").innerHTML = `<div class="panel full err">
      Failed to load brief: ${esc(e.message)}</div>`;
  }
}

refresh();
setInterval(refresh, 5000);

// --- Create Ticket form ---
document.addEventListener("submit", async (ev) => {
  if (!(ev.target instanceof HTMLFormElement)) return;
  ev.preventDefault();
  if (ev.target.id === "config-form") {
    postDashboardConfig().catch(e => {
      const status = $("config-status");
      if (status) { status.textContent = "save failed: " + e.message; status.className = "muted err"; }
    });
    return;
  }
  if (ev.target.id !== "create-ticket-form") return;
  const status = $("ct-status");
  const description = $("ct-description").value.trim();
  if (!description) {
    if (status) { status.textContent = "description is required"; status.className = "muted err"; }
    return;
  }
  const title = $("ct-title").value.trim();
  const priority = $("ct-priority").value;
  const executor = $("ct-executor").value;
  const queue = $("ct-queue").value.trim() || "default";
  if (status) { status.textContent = "creating…"; status.className = "muted"; }
  noteChange("ticket.create", title || "new-ticket");
  try {
    const res = await fetch("/api/tickets/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody({ title, description, priority, executor_kind: executor, queue_name: queue })),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    if (status) {
      status.textContent = `✓ created ${data.ticket_id} — ${data.name}`;
      status.className = "muted ok";
    }
    $("ct-title").value = "";
    $("ct-description").value = "";
    setTimeout(refresh, 300);
  } catch (e) {
    if (status) {
      status.textContent = "create failed: " + e.message;
      status.className = "muted err";
    }
  }
});
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
    lan: bool = False
    workspace: Path | None = None


def _local_lan_addresses() -> list[str]:
    """Return best-effort non-loopback IPv4 addresses for LAN dashboard URLs."""
    found: list[str] = []

    def add(addr: str) -> None:
        if not addr or addr.startswith("127.") or addr == "0.0.0.0":
            return
        if "." not in addr or addr in found:
            return
        found.append(addr)

    with contextlib.suppress(OSError):
        hostname = socket.gethostname()
        _name, _aliases, addrs = socket.gethostbyname_ex(hostname)
        for addr in addrs:
            add(addr)
    with contextlib.suppress(OSError):
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            add(str(probe.getsockname()[0]))
        finally:
            probe.close()
    return found


def _dashboard_urls(config: ServeConfig) -> list[str]:
  """Return URLs worth showing to the operator for this bind config."""
  hosts: list[str]
  if config.host in {"0.0.0.0", "::"}:
    hosts = ["localhost", *_local_lan_addresses()]
  else:
    hosts = [config.host]
  urls = [f"http://{host}:{config.port}/" for host in hosts]
  return list(dict.fromkeys(urls))


def _project_label(path: Path) -> str:
  return path.name or str(path)


def _dashboard_workspace(config: ServeConfig) -> Path:
  raw = os.environ.get("KORU_SERVE_WORKSPACE", "").strip()
  if raw:
    return Path(raw).expanduser().resolve()
  if config.workspace is not None:
    return config.workspace.expanduser().resolve()
  return config.project.resolve().parent


def _project_candidate_dict(path: Path, source: str) -> dict[str, Any]:
  path = path.expanduser().resolve()
  return {
    "path": str(path),
    "name": _project_label(path),
    "source": source,
    "planfile": (path / ".planfile" / "config.yaml").is_file(),
    "git": (path / ".git").exists(),
  }


def _looks_like_project(path: Path) -> bool:
  return any(
    (path / marker).exists()
    for marker in (
      ".git",
      ".planfile",
      "pyproject.toml",
      "package.json",
      "Cargo.toml",
      "go.mod",
      "Taskfile.yml",
      "Makefile",
    )
  )


def _workspace_project_candidates(workspace: Path, *, max_results: int) -> list[Path]:
  workspace = workspace.expanduser().resolve()
  rows: list[Path] = []
  if _looks_like_project(workspace):
    rows.append(workspace)
  try:
    children = sorted(workspace.iterdir(), key=lambda item: item.name.lower())
  except OSError:
    return rows
  for child in children:
    if len(rows) >= max_results:
      break
    if child.name.startswith(".") or not child.is_dir():
      continue
    if _looks_like_project(child):
      rows.append(child.resolve())
  return rows


def _discover_dashboard_projects(config: ServeConfig, *, max_results: int = 80) -> list[dict[str, Any]]:
  """Return projects the LAN dashboard may operate on."""
  rows: list[dict[str, Any]] = [_project_candidate_dict(config.project, "serve project")]
  with contextlib.suppress(Exception):
    for item in propose_projects(cast(Any, detect_running_ides()), max_results=16):
      rows.append(_project_candidate_dict(item.path, item.source))
  workspace = _dashboard_workspace(config)
  with contextlib.suppress(Exception):
    for project in _workspace_project_candidates(workspace, max_results=max_results):
      rows.append(_project_candidate_dict(project, f"workspace {workspace}"))

  seen: set[str] = set()
  out: list[dict[str, Any]] = []
  for row in rows:
    path = str(row["path"])
    if path in seen:
      continue
    seen.add(path)
    out.append(row)
    if len(out) >= max_results:
      break
  return out


def _resolve_dashboard_project(config: ServeConfig, raw: object | None) -> Path:
  if raw is None or not str(raw).strip():
    return config.project.resolve()
  candidate = Path(str(raw)).expanduser().resolve()
  allowed = {Path(str(row["path"])).resolve() for row in _discover_dashboard_projects(config)}
  if candidate in allowed:
    return candidate
  raise ValueError(f"project is not available in this dashboard: {candidate}")


def _dashboard_ide_rows() -> list[dict[str, Any]]:
  running = {row.id: row for row in detect_running_ides()}
  rows: list[dict[str, Any]] = [{"id": "auto", "label": "Auto", "running": False}]
  for ide_id in autopilot_ide_choices():
    if ide_id == "auto":
      continue
    detected = running.get(ide_id)
    rows.append(
      {
        "id": ide_id,
        "label": detected.label if detected else ide_id,
        "running": detected is not None,
        "pid": detected.pid if detected else None,
        "exe": detected.exe if detected else None,
      }
    )
  return rows


def _dashboard_state(config: ServeConfig) -> dict[str, Any]:
  return {
    "ok": True,
    "host": config.host,
    "port": config.port,
    "lan": bool(config.lan or config.host in {"0.0.0.0", "::"}),
    "urls": _dashboard_urls(config),
    "workspace": str(_dashboard_workspace(config)),
    "default_project": str(config.project.resolve()),
    "projects": _discover_dashboard_projects(config),
    "ides": _dashboard_ide_rows(),
    "queue_name": config.queue_name or "default",
  }


def _bool_from_dashboard(value: object, *, default: bool = False) -> bool:
  if value is None:
    return default
  if isinstance(value, bool):
    return value
  return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "tak"}


def _int_from_dashboard(value: object, *, default: int) -> int:
  if value is None or str(value).strip() == "":
    return default
  return int(str(value).strip())


def _dashboard_config_payload(config: ServeConfig, project: Path) -> dict[str, Any]:
  saved = load_project_config(project)
  serve = saved.get("serve") if isinstance(saved.get("serve"), dict) else {}
  effective = {
    "project": str(project.resolve()),
    "workspace": str(saved.get("workspace") or _dashboard_workspace(config)),
    "ide": str(saved.get("ide") or "auto"),
    "queue_name": str(saved.get("queue_name") or config.queue_name or "default"),
    "serve": {
      "host": str(serve.get("host") or config.host),
      "port": int(serve.get("port") or config.port),
      "lan": _bool_from_dashboard(
        serve.get("lan"),
        default=bool(config.lan or config.host in {"0.0.0.0", "::"}),
      ),
      "auto_port": _bool_from_dashboard(serve.get("auto_port"), default=bool(config.auto_port)),
    },
  }
  return {
    "ok": True,
    "path": str(project.resolve() / CONFIG_REL_PATH),
    "exists": bool((project.resolve() / CONFIG_REL_PATH).is_file()),
    "config": {**effective, **{k: v for k, v in saved.items() if k in {"schema", "created_at", "updated_at"}}},
    "ide_choices": list(autopilot_ide_choices()),
  }


def _load_sprint_file(path: Path) -> dict[str, Any]:
  data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
  return data if isinstance(data, dict) else {}


def _write_sprint_file(path: Path, data: dict[str, Any]) -> None:
  path.write_text(
    yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True),
    encoding="utf-8",
  )


def _find_ticket_in_sprints(project: Path, ticket_id: str) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
  sprints_dir = project / ".planfile" / "sprints"
  for path in sorted(sprints_dir.glob("*.yaml")):
    data = _load_sprint_file(path)
    sprint_raw = data.get("sprint")
    sprint = sprint_raw if isinstance(sprint_raw, dict) else {}
    tickets_raw = sprint.get("tickets")
    tickets = tickets_raw if isinstance(tickets_raw, dict) else {}
    ticket = tickets.get(ticket_id)
    if isinstance(ticket, dict):
      return path, data, tickets, ticket
  raise ValueError(f"ticket not found: {ticket_id}")


def _append_dashboard_history(ticket: dict[str, Any], action: str, message: str) -> None:
  history = ticket.setdefault("history", [])
  if isinstance(history, list):
    history.append(
      {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "source": "koru dashboard",
        "message": message,
      }
    )
  ticket["updated_at"] = datetime.now(UTC).isoformat()


def _update_ticket_from_dashboard(
  project: Path,
  *,
  ticket_id: str,
  priority: str | None = None,
  queue_name: str | None = None,
) -> dict[str, Any]:
  path, data, _tickets, ticket = _find_ticket_in_sprints(project, ticket_id)
  changes: list[str] = []
  if priority is not None:
    normalized = priority.strip().lower()
    if normalized not in {"critical", "high", "normal", "low"}:
      raise ValueError("priority must be critical|high|normal|low")
    if ticket.get("priority") != normalized:
      ticket["priority"] = normalized
      changes.append(f"priority={normalized}")
  if queue_name is not None:
    queue = queue_name.strip() or "default"
    execution = ticket.setdefault("execution", {})
    if not isinstance(execution, dict):
      execution = {}
      ticket["execution"] = execution
    if execution.get("queue") != queue:
      execution["queue"] = queue
      changes.append(f"queue={queue}")
  if changes:
    _append_dashboard_history(ticket, "dashboard_update", ", ".join(changes))
    _write_sprint_file(path, data)
  return {"ok": True, "ticket_id": ticket_id, "changed": bool(changes), "changes": changes}


def _reorder_ticket_from_dashboard(project: Path, *, ticket_id: str, direction: str) -> dict[str, Any]:
  path, data, tickets, _ticket = _find_ticket_in_sprints(project, ticket_id)
  items = list(tickets.items())
  index = next((idx for idx, (key, _value) in enumerate(items) if key == ticket_id), -1)
  if index < 0:
    raise ValueError(f"ticket not found: {ticket_id}")
  delta = -1 if direction == "up" else 1 if direction == "down" else 0
  if delta == 0:
    raise ValueError("direction must be up|down")
  new_index = max(0, min(len(items) - 1, index + delta))
  if new_index == index:
    return {"ok": True, "ticket_id": ticket_id, "changed": False, "position": index}
  item = items.pop(index)
  items.insert(new_index, item)
  sprint = data.setdefault("sprint", {})
  sprint["tickets"] = {key: value for key, value in items}
  _append_dashboard_history(item[1], "dashboard_reorder", f"position={new_index}")
  _write_sprint_file(path, data)
  return {"ok": True, "ticket_id": ticket_id, "changed": True, "position": new_index}


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

        def _query_params(self) -> dict[str, list[str]]:
          return parse_qs(urlparse(self.path).query)

        def _selected_project(self, body: dict[str, Any] | None = None) -> Path:
          raw: object | None = None
          if body is not None and "project" in body:
            raw = body.get("project")
          else:
            values = self._query_params().get("project") or []
            raw = values[0] if values else None
          return _resolve_dashboard_project(config, raw)

        def do_GET(self) -> None:  # noqa: N802 — stdlib API
          path = urlparse(self.path).path
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
          if path == "/api/dashboard":
            try:
              self._send_json(_dashboard_state(config))
            except Exception as exc:  # pragma: no cover — surface discovery errors
              self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
            return
          if path == "/api/config":
            try:
              project = self._selected_project()
              self._send_json(_dashboard_config_payload(config, project))
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:  # pragma: no cover — surface config errors
              self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
            return
          if path == "/api/context":
            try:
              project = self._selected_project()
              ctx = build_context(project=project, queue_name=config.queue_name)
              ctx["dashboard_project"] = str(project)
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
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
              project = self._selected_project()
              topo = load_topology(project)
              topo["dashboard_project"] = str(project)
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
            except Exception as exc:  # pragma: no cover — surface errors
              self._send_json(
                {"error": str(exc), "type": type(exc).__name__},
                status=500,
              )
              return
            self._send_json(topo)
            return
          if path == "/api/runtime-context":
            project = config.project
            runtime: dict[str, Any]
            try:
              runtime_context = importlib.import_module("planfile.runtime_context")
              project = self._selected_project()
              runtime = runtime_context.build_runtime_context(project)
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
            except Exception as exc:  # pragma: no cover — optional planfile integration
              runtime = {"error": str(exc), "type": type(exc).__name__}
            runtime["dashboard_project"] = str(project)
            runtime["insights"] = collect_runtime_insights(project)
            self._send_json(runtime)
            return
          if path == "/api/handoff":
            try:
              project = self._selected_project()
              ctx = build_context(project=project, queue_name=config.queue_name)
              md = render_markdown_handoff(ctx)
            except ValueError as exc:
              self._send(400, str(exc).encode("utf-8"))
              return
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
          path = urlparse(self.path).path
          try:
            body = self._read_json_body()
          except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

          if path == "/api/topology":
            try:
              project = self._selected_project(body)
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
            merged, err, status = apply_topology_post_update(project, body)
            if err is not None:
              self._send_json(err, status=status)
              return
            self._send_json(merged)
            return

          if path == "/api/runtime-context/config":
            try:
              runtime_context = importlib.import_module("planfile.runtime_context")
              project = self._selected_project(body)
              current = runtime_context.load_runtime_context_config(project)
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
              saved_config = runtime_context.save_runtime_context_config(project, merged)
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
            except Exception as exc:  # pragma: no cover — optional planfile integration
              self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
              return
            self._send_json(saved_config)
            return
          if path == "/api/config":
            try:
              project = self._selected_project(body)
              serve = body.get("serve") if isinstance(body.get("serve"), dict) else {}
              workspace_raw = str(body.get("workspace") or "").strip()
              result = configure_project(
                project=project,
                workspace=Path(workspace_raw) if workspace_raw else None,
                ide=str(body.get("ide") or "auto").strip() or "auto",
                queue_name=str(body.get("queue_name") or "default").strip() or "default",
                host=str(serve.get("host") or config.host).strip() or config.host,
                port=_int_from_dashboard(serve.get("port"), default=config.port),
                lan=_bool_from_dashboard(serve.get("lan"), default=bool(config.lan)),
                auto_port=_bool_from_dashboard(serve.get("auto_port"), default=bool(config.auto_port)),
                interactive=False,
              )
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
            except Exception as exc:
              self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
              return
            self._send_json({**_dashboard_config_payload(config, project), "saved": True, "path": str(result.path)})
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
            try:
              project = self._selected_project(body)
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
            result = _bulk_waiting_input_action(
              project,
              ticket_ids=ticket_ids,
              action=action,
              reason=reason,
            )
            if not result.get("ok"):
              self._send_json(result, status=400)
              return
            self._send_json(result)
            return
          if path == "/api/tickets/create":
            description = str(body.get("description") or "").strip()
            if not description:
              self._send_json({"error": "description is required"}, status=400)
              return
            title = str(body.get("title") or "").strip() or None
            priority = str(body.get("priority") or "normal").strip()
            executor_kind = str(body.get("executor_kind") or "human").strip()
            queue_name = str(body.get("queue_name") or "default").strip()
            ide = normalize_ide_id(str(body.get("ide") or "auto").strip() or "auto")
            try:
              from koru.tasks import create_nl_task

              project = self._selected_project(body)
              scaffold: dict[str, Any] = {
                "executor_kind": executor_kind,
                "executor_mode": "interactive",
                "labels": ["koru", "dashboard", "llm-ready"],
                "source_context": {"ide": ide},
                "source_tool": "koru-dashboard",
              }
              if title:
                scaffold["title"] = title
              created = create_nl_task(
                project,
                description,
                queue_name=queue_name,
                priority=priority,
                scaffold=scaffold,
              )
              self._send_json(
                {
                  "ok": True,
                  "ticket_id": created.ticket_id,
                  "name": created.name,
                  "sprint": created.sprint,
                  "path": str(created.path),
                  "project": str(project),
                  "ide": ide,
                }
              )
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:
              self._send_json(
                {"error": str(exc), "type": type(exc).__name__},
                status=500,
              )
            return
          if path == "/api/tickets/update":
            ticket_id = str(body.get("ticket_id") or "").strip()
            if not ticket_id:
              self._send_json({"error": "ticket_id is required"}, status=400)
              return
            try:
              project = self._selected_project(body)
              result = _update_ticket_from_dashboard(
                project,
                ticket_id=ticket_id,
                priority=str(body["priority"]).strip() if "priority" in body else None,
                queue_name=str(body["queue_name"]).strip() if "queue_name" in body else None,
              )
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
            except Exception as exc:
              self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
              return
            self._send_json(result)
            return
          if path == "/api/tickets/reorder":
            ticket_id = str(body.get("ticket_id") or "").strip()
            direction = str(body.get("direction") or "").strip().lower()
            if not ticket_id:
              self._send_json({"error": "ticket_id is required"}, status=400)
              return
            try:
              project = self._selected_project(body)
              result = _reorder_ticket_from_dashboard(project, ticket_id=ticket_id, direction=direction)
            except ValueError as exc:
              self._send_json({"error": str(exc)}, status=400)
              return
            except Exception as exc:
              self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
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
      "lan": bool(config.lan or config.host in {"0.0.0.0", "::"}),
      "urls": _dashboard_urls(config),
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
    urls = _dashboard_urls(config)
    if config.auto_port and actual != requested:
        print(
            f"koru serve: port {requested} busy — bound to {actual} instead",
            file=sys.stderr,
        )
    print(f"koru serve: dashboard at {url}")
    if len(urls) > 1:
      print("koru serve: LAN URLs:")
      for visible_url in urls:
        print(f"  {visible_url}")
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
            with contextlib.suppress(Exception):  # pragma: no cover — best-effort
                webbrowser.open(url, new=2)

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
            with contextlib.suppress(Exception):  # pragma: no cover — best-effort
                webbrowser.open(url, new=2)

        threading.Timer(0.3, _open_later).start()

    thread = threading.Thread(
        target=server.serve_forever,
        name="koru-serve-bg",
        daemon=True,
    )
    thread.start()
    time.sleep(0.05)
    return server, thread
