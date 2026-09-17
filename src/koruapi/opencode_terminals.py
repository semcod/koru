"""OpenCode serve instance registry and HTTP client for the Terminals tab.

Koru supervises ``opencode serve`` instances through their documented HTTP API
instead of scraping TUIs: the server exposes sessions, messages, prompt input
and pending permission/question requests plus their reply endpoints.

Instance registry lives in ``.planfile/.koru/opencode-instances.json`` (runtime
data). Discovery combines the registry with a ``/proc`` scan for user-launched
``opencode serve`` processes so terminals started outside koru still appear in
the dashboard grid.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REGISTRY_NAME = "opencode-instances.json"
_REQUEST_TIMEOUT = 2.0
_LISTEN_RE = re.compile(r"opencode server listening on (https?://\S+)")
_TICKET_RE = re.compile(r"\b(PLF-\d+|STARTER-\d+)\b", re.IGNORECASE)
# Only sessions touched inside this window are scanned for a ticket id —
# reading full conversations for every session on each dashboard poll would be
# too expensive.
_TICKET_SCAN_WINDOW_MS = 3 * 24 * 3600 * 1000
_TICKET_SCAN_SESSIONS = 8
_session_ticket_cache: dict[tuple[str, str], tuple[int, str | None]] = {}

DEFAULT_FAILOVER_TTL_SECONDS = 3600.0  # 1 hour default if reset time unknown
_EXHAUSTION_LOCK = threading.Lock()
_EXHAUSTED_PROVIDERS: dict[str, dict[str, Any]] = {}

# Patterns that indicate provider rate limit / quota exhaustion
_EXHAUSTION_ERROR_PATTERNS = [
    re.compile(r"usage limit reached", re.IGNORECASE),
    re.compile(r"rate limit", re.IGNORECASE),
    re.compile(r"quota exceeded", re.IGNORECASE),
    re.compile(r"resource has been exhausted", re.IGNORECASE),
    re.compile(r"credit limit", re.IGNORECASE),
    re.compile(r"insufficient_quota", re.IGNORECASE),
    re.compile(r"AI_APICallError", re.IGNORECASE),
    re.compile(r"\b429\b"),
]
_RESET_TIME_RE = re.compile(
    r"reset at\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", re.IGNORECASE
)
_LOG_STREAM_ERROR_RE = re.compile(
    r'level=ERROR\s+run=(\w+)\s+message="stream error"\s+'
    r'providerID=([a-zA-Z0-9_-]+)\s+modelID=([a-zA-Z0-9_.-]+)\s+'
    r'(?:session\.id=([^\s]+)\s+)?'
    r'.*?error\.error="([^"]+)"'
)


def _koru_dir(project: Path) -> Path:
    return Path(project) / ".planfile" / ".koru"


def registry_path(project: Path) -> Path:
    return _koru_dir(project) / REGISTRY_NAME


def load_registry(project: Path) -> list[dict[str, Any]]:
    path = registry_path(project)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [entry for entry in data if isinstance(entry, dict) and entry.get("url")]


def save_registry(project: Path, entries: list[dict[str, Any]]) -> Path:
    path = registry_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def register_instance(
    project: Path,
    *,
    url: str,
    label: str = "",
    pid: int | None = None,
    managed: bool = False,
    auto_answer: bool = True,
) -> dict[str, Any]:
    entries = load_registry(project)
    for entry in entries:
        if entry.get("url") == url:
            entry.update(
                {"label": label or entry.get("label", ""), "pid": pid,
                 "managed": managed, "auto_answer": auto_answer}
            )
            save_registry(project, entries)
            return entry
    entry = {
        "id": f"oc{int(time.time() * 1000) % 10**8:x}",
        "url": url.rstrip("/"),
        "label": label or url,
        "pid": pid,
        "managed": managed,
        "auto_answer": auto_answer,
        "project": str(project),
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    entries.append(entry)
    save_registry(project, entries)
    return entry


def unregister_instance(project: Path, instance_id: str) -> bool:
    entries = load_registry(project)
    kept = [e for e in entries if e.get("id") != instance_id]
    if len(kept) == len(entries):
        return False
    save_registry(project, kept)
    return True


def set_auto_answer(project: Path, instance_id: str, enabled: bool) -> dict[str, Any] | None:
    entries = load_registry(project)
    for entry in entries:
        if entry.get("id") == instance_id:
            entry["auto_answer"] = bool(enabled)
            save_registry(project, entries)
            return entry
    for found in _scan_serve_processes():
        if found.get("id") == instance_id:
            return register_instance(
                project,
                url=str(found["url"]),
                label=str(found.get("label", "")),
                pid=found.get("pid"),
                managed=False,
                auto_answer=bool(enabled),
            )
    return None


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _scan_serve_processes() -> list[dict[str, Any]]:
    """Find ``opencode serve --port N`` processes the user started manually."""
    found: list[dict[str, Any]] = []
    proc = Path("/proc")
    if not proc.is_dir():
        return found
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        argv = [a for a in raw.split(b"\0") if a]
        names = [a.decode("utf-8", "ignore") for a in argv]
        if len(names) < 2 or not any("opencode" in n for n in names[:2]):
            continue
        if "serve" not in names[1:4]:
            continue
        port = None
        host = "127.0.0.1"
        for i, name in enumerate(names):
            if name == "--port" and i + 1 < len(names):
                try:
                    port = int(names[i + 1])
                except ValueError:
                    port = None
            elif name.startswith("--port="):
                try:
                    port = int(name.split("=", 1)[1])
                except ValueError:
                    port = None
            elif name == "--hostname" and i + 1 < len(names):
                host = names[i + 1]
            elif name.startswith("--hostname="):
                host = name.split("=", 1)[1]
        if not port:
            continue
        found.append(
            {"id": f"proc-{port}", "url": f"http://{host}:{port}",
             "pid": int(entry.name),
             "label": f"opencode serve :{port}", "managed": False,
             "auto_answer": False}
        )
    return found


def _api_request(
    url: str,
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = _REQUEST_TIMEOUT,
) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url.rstrip("/") + path, data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8", "ignore"))


def instance_health(url: str) -> bool:
    try:
        data = _api_request(url, "/api/health", timeout=1.0)
    except Exception:
        return False
    if isinstance(data, dict) and data.get("healthy") is False:
        return False
    return True


def list_sessions(url: str) -> list[dict[str, Any]]:
    data = _api_request(url, "/api/session")
    items = data.get("data", data) if isinstance(data, dict) else data
    return items if isinstance(items, list) else []


def list_providers(url: str) -> list[dict[str, Any]]:
    """Sanitized provider catalog — never exposes request bodies or keys."""
    try:
        data = _api_request(url, "/api/provider", timeout=1.5)
    except Exception:
        return []
    items = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        api = item.get("api") if isinstance(item.get("api"), dict) else {}
        out.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "api_type": api.get("type"),
                "api_url": api.get("url"),
            }
        )
    return out


def parse_exhaustion_from_error(
    error_text: str, *, default_ttl: float = DEFAULT_FAILOVER_TTL_SECONDS
) -> tuple[bool, float, str]:
    """Parse error text for quota/rate limit signals.

    Returns (is_exhausted, ttl_seconds, reason).
    If a reset time like 'reset at 2026-09-17 18:48:17' is found,
    ttl_seconds is calculated until that time.
    """
    if not error_text:
        return False, 0.0, ""
    matched = False
    for pat in _EXHAUSTION_ERROR_PATTERNS:
        if pat.search(error_text):
            matched = True
            break
    if not matched:
        return False, 0.0, ""

    ttl = default_ttl
    match = _RESET_TIME_RE.search(error_text)
    if match:
        raw_ts = match.group(1)
        try:
            dt = datetime.datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=datetime.timezone.utc
            )
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            delta = (dt - now_dt).total_seconds()
            if delta > 0:
                ttl = delta
        except Exception:
            pass
    return True, max(1.0, ttl), error_text.strip()


def mark_provider_exhausted(
    provider_id: str,
    ttl_seconds: float = DEFAULT_FAILOVER_TTL_SECONDS,
    *,
    reason: str = "",
    reset_at: float | None = None,
) -> dict[str, Any]:
    """Mark a provider ID as exhausted until reset_at or now + ttl_seconds."""
    provider = str(provider_id).strip().lower()
    if not provider:
        return {}
    now = time.time()
    if reset_at is None:
        reset_at = now + ttl_seconds
    record = {
        "providerID": provider,
        "reason": reason or "Quota/rate limit reached",
        "marked_at": now,
        "reset_at": reset_at,
    }
    with _EXHAUSTION_LOCK:
        _EXHAUSTED_PROVIDERS[provider] = record
    return record


def is_provider_exhausted(provider_id: str) -> bool:
    """Return True if the provider is currently marked exhausted and not expired."""
    provider = str(provider_id).strip().lower()
    if not provider:
        return False
    now = time.time()
    with _EXHAUSTION_LOCK:
        record = _EXHAUSTED_PROVIDERS.get(provider)
        if not record:
            return False
        if now >= record["reset_at"]:
            del _EXHAUSTED_PROVIDERS[provider]
            return False
        return True


def get_exhausted_providers() -> dict[str, dict[str, Any]]:
    """Return a dictionary of currently exhausted providers with remaining seconds."""
    now = time.time()
    out = {}
    with _EXHAUSTION_LOCK:
        expired = []
        for pid, record in _EXHAUSTED_PROVIDERS.items():
            rem = record["reset_at"] - now
            if rem <= 0:
                expired.append(pid)
            else:
                out[pid] = {
                    "providerID": record["providerID"],
                    "reason": record["reason"],
                    "marked_at": record["marked_at"],
                    "reset_at": record["reset_at"],
                    "remaining_seconds": round(rem, 1),
                }
        for pid in expired:
            del _EXHAUSTED_PROVIDERS[pid]
    return out


def clear_provider_exhaustion(provider_id: str | None = None) -> None:
    """Clear exhaustion status for one provider or all."""
    with _EXHAUSTION_LOCK:
        if provider_id is None:
            _EXHAUSTED_PROVIDERS.clear()
        else:
            _EXHAUSTED_PROVIDERS.pop(str(provider_id).strip().lower(), None)


def scan_opencode_log_for_exhaustion(
    log_path: Path | None = None,
    max_bytes: int = 128 * 1024,
) -> list[dict[str, Any]]:
    """Scan the tail of opencode.log for stream errors and rate limits.

    Automatically marks detected failing providers as exhausted.
    Returns list of parsed error events.
    """
    if log_path is None:
        log_path = Path.home() / ".local" / "share" / "opencode" / "log" / "opencode.log"
    if not log_path.is_file():
        return []
    try:
        size = log_path.stat().st_size
        offset = max(0, size - max_bytes)
        with log_path.open("rb") as f:
            if offset > 0:
                f.seek(offset)
            raw = f.read().decode("utf-8", "ignore")
    except OSError:
        return []

    detected: list[dict[str, Any]] = []
    for match in _LOG_STREAM_ERROR_RE.finditer(raw):
        run_id, provider_id, model_id, session_id, error_msg = match.groups()
        is_ex, ttl, _ = parse_exhaustion_from_error(error_msg)
        if is_ex:
            record = mark_provider_exhausted(provider_id, ttl_seconds=ttl, reason=error_msg)
            detected.append({
                "run": run_id,
                "providerID": provider_id,
                "modelID": model_id,
                "sessionID": session_id or "",
                "error": error_msg,
                "reset_at": record.get("reset_at"),
            })
    return detected


def get_instance_config(url: str) -> dict[str, Any]:
    """Fetch instance /config without raising exceptions."""
    try:
        data = _api_request(url, "/config", timeout=1.5)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_available_models(url: str) -> list[dict[str, str]]:
    """Return available models on the instance in preference order:
    [{"providerID": ..., "modelID": ...}]
    """
    models: list[dict[str, str]] = []
    cfg = get_instance_config(url)
    default_model_str = cfg.get("model")
    default_entry: dict[str, str] | None = None
    if isinstance(default_model_str, str) and "/" in default_model_str:
        p, m = default_model_str.split("/", 1)
        default_entry = {"providerID": p.strip(), "modelID": m.strip()}

    providers = cfg.get("provider") if isinstance(cfg.get("provider"), dict) else {}
    for pid, pdata in providers.items():
        if not isinstance(pdata, dict):
            continue
        pmodels = pdata.get("models") if isinstance(pdata.get("models"), dict) else {}
        for mid in pmodels.keys():
            entry = {"providerID": str(pid), "modelID": str(mid)}
            if default_entry and entry == default_entry:
                continue
            models.append(entry)

    if default_entry:
        models.insert(0, default_entry)

    if not models:
        for p in list_providers(url):
            pid = p.get("id")
            if pid:
                models.append({"providerID": str(pid), "modelID": "default"})
    return models


def resolve_active_terminal_model(
    url: str,
    requested_model: dict[str, str] | None = None,
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    """Resolve active model with automatic failover if provider is exhausted.

    Returns (resolved_model, failover_info):
    - resolved_model: {"providerID": ..., "modelID": ...} or None
    - failover_info: {"from": failed_provider, "to": resolved_provider, "model": model_id} or None
    """
    req_provider = None
    if isinstance(requested_model, dict):
        req_provider = requested_model.get("providerID") or requested_model.get("providerId")

    if req_provider and not is_provider_exhausted(str(req_provider)):
        return _normalize_model(requested_model, style="prompt"), None

    available = get_available_models(url)
    unexhausted = [m for m in available if not is_provider_exhausted(m["providerID"])]

    if unexhausted:
        chosen = unexhausted[0]
        failover = None
        if req_provider and req_provider != chosen["providerID"]:
            failover = {
                "from": str(req_provider),
                "to": chosen["providerID"],
                "model": chosen["modelID"],
            }
        return chosen, failover

    fallback = (
        _normalize_model(requested_model, style="prompt")
        if requested_model
        else (available[0] if available else None)
    )
    return fallback, None


def _normalize_model(
    model: dict[str, str] | None, *, style: str = "create"
) -> dict[str, str] | None:
    """Normalize a caller model dict to the route-specific server schema.

    The opencode API is inconsistent: session create wants
    ``{"id", "providerID"}`` while ``prompt_async`` wants
    ``{"providerID", "modelID"}``.
    """
    if not isinstance(model, dict):
        return None
    model_id = model.get("id") or model.get("modelID")
    provider = model.get("providerID") or model.get("providerId")
    if not model_id or not provider:
        return None
    if style == "prompt":
        return {"providerID": str(provider), "modelID": str(model_id)}
    return {"id": str(model_id), "providerID": str(provider)}


def create_session(
    url: str,
    *,
    title: str = "",
    agent: str | None = None,
    model: dict[str, str] | None = None,
    directory: str | None = None,
) -> dict[str, Any] | None:
    body: dict[str, Any] = {}
    if title:
        body["title"] = title
    if agent:
        body["agent"] = agent
    normalized = _normalize_model(model)
    if normalized:
        body["model"] = normalized
    if directory:
        body["location"] = {"directory": directory}
    data = _api_request(url, "/api/session", method="POST", body=body)
    item = data.get("data", data) if isinstance(data, dict) else data
    return item if isinstance(item, dict) else None


def session_messages(url: str, session_id: str, *, limit: int = 60) -> list[dict[str, Any]]:
    # The unprefixed route returns conversation messages (info+parts); the
    # /api variant serves a different event projection (e.g. agent-switched).
    data = _api_request(url, f"/session/{session_id}/message")
    items = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return items[-limit:]


def normalize_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Flatten an opencode ``{info, parts}`` message for the dashboard.

    The conversation route returns ``info.role`` plus typed ``parts``
    (``text``, ``reasoning``, ``tool``, ``step-start``, ``file`` …). The
    renderer expects ``{role, text}``; normalization happens here so the
    dashboard API stays stable if the server shape drifts again. Legacy flat
    shapes (``text``/``content``/``command``) are accepted too.
    """
    if not isinstance(msg, dict):
        return {"role": "?", "text": str(msg)}
    info = msg.get("info") if isinstance(msg.get("info"), dict) else msg
    role = info.get("role") or msg.get("type") or "?"
    chunks: list[str] = []
    parts = msg.get("parts")
    if isinstance(parts, list):
        for part in parts:
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")
            text = part.get("text")
            if ptype == "text" and text:
                chunks.append(str(text))
            elif ptype == "reasoning" and text:
                chunks.append("[reasoning]\n" + str(text))
            elif ptype == "tool":
                name = part.get("tool") or part.get("name") or "?"
                state = part.get("state")
                title = state.get("title") if isinstance(state, dict) else None
                chunks.append(f"[tool: {name}]" + (f" {title}" if title else ""))
            elif ptype == "file":
                chunks.append(
                    f"[file: {part.get('filename') or part.get('url') or ''}]"
                )
            elif ptype in ("step-start", "step-finish", "snapshot", "patch"):
                continue
            elif text:
                chunks.append(str(text))
    if not chunks:
        if isinstance(msg.get("text"), str):
            chunks.append(msg["text"])
        elif isinstance(msg.get("content"), list):
            for c in msg["content"]:
                if isinstance(c, dict):
                    if c.get("text"):
                        chunks.append(str(c["text"]))
                    elif c.get("name"):
                        chunks.append(f"[tool: {c['name']}]")
        elif msg.get("command"):
            out = msg.get("output")
            chunks.append("$ " + str(msg["command"]) + (f"\n{out}" if out else ""))
    model = info.get("model") if isinstance(info.get("model"), dict) else {}
    ts = info.get("time") if isinstance(info.get("time"), dict) else {}
    return {
        "role": role,
        "text": "\n".join(c for c in chunks if c).strip(),
        "agent": info.get("agent"),
        "model": info.get("modelID") or model.get("modelID") or model.get("id"),
        "provider": info.get("providerID") or model.get("providerID"),
        "created": ts.get("created"),
    }


def send_prompt(
    url: str,
    session_id: str,
    text: str,
    *,
    model: dict[str, str] | None = None,
    agent: str | None = None,
) -> dict[str, Any]:
    """Fire-and-execute a prompt via ``prompt_async``.

    ``POST /session/{id}/prompt`` only *queues* text for a running loop
    (``delivery: "steer"``); an idle session never executes it. The
    ``prompt_async`` route starts the agent loop and returns ``204``.
    It is mounted without the ``/api`` prefix — that prefix falls through
    to the SPA handler.
    """
    body: dict[str, Any] = {"parts": [{"type": "text", "text": text}]}
    normalized = _normalize_model(model, style="prompt")
    if normalized:
        body["model"] = normalized
    if agent:
        body["agent"] = agent
    _api_request(
        url,
        f"/session/{session_id}/prompt_async",
        method="POST",
        body=body,
        timeout=10.0,
    )
    return {"ok": True, "session_id": session_id, "delivery": "async"}


def pending_requests(url: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"permissions": [], "questions": []}
    for kind, path in (
        ("permissions", "/api/permission/request"),
        ("questions", "/api/question/request"),
    ):
        try:
            data = _api_request(url, path, timeout=1.5)
        except Exception:
            continue
        items = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(items, list):
            out[kind] = [i for i in items if isinstance(i, dict)]
    return out


def reply_permission(
    url: str, session_id: str, request_id: str, reply: str
) -> dict[str, Any]:
    if reply not in {"once", "always", "reject"}:
        raise ValueError("reply must be once|always|reject")
    return _api_request(
        url,
        f"/api/session/{session_id}/permission/{request_id}/reply",
        method="POST",
        body={"reply": reply},
    )


def reply_question(
    url: str, session_id: str, request_id: str, answers: list[list[str]]
) -> dict[str, Any]:
    return _api_request(
        url,
        f"/api/session/{session_id}/question/{request_id}/reply",
        method="POST",
        body={"answers": answers},
    )


def discover_instances(project: Path, *, probe: bool = True) -> list[dict[str, Any]]:
    """Registry entries merged with ``opencode serve`` processes from /proc."""
    merged: dict[str, dict[str, Any]] = {}
    for entry in _scan_serve_processes():
        merged[entry["url"]] = entry
    for entry in load_registry(project):
        url = str(entry.get("url", "")).rstrip("/")
        if not url:
            continue
        base = merged.pop(url, None)
        if base:
            base.update(entry)
            entry = base
        if entry.get("managed") and not _pid_alive(entry.get("pid")):
            # Managed but the pid is gone — drop instead of showing dead rows.
            continue
        merged[url] = entry
    instances = list(merged.values())
    if probe:
        for entry in instances:
            entry["healthy"] = instance_health(str(entry["url"]))
    return instances


def _prune_dead_managed(project: Path, instances: list[dict[str, Any]]) -> None:
    live_urls = {e.get("url") for e in instances}
    registry = load_registry(project)
    kept = [
        e for e in registry
        if not e.get("managed") or e.get("url") in live_urls
    ]
    if len(kept) != len(registry):
        save_registry(project, kept)


def spawn_instance(
    project: Path,
    *,
    label: str = "",
    directory: str | None = None,
    auto_answer: bool = True,
    wait_seconds: float = 10.0,
) -> dict[str, Any]:
    """Start ``opencode serve --port 0`` and register the bound URL."""
    cwd = Path(directory).expanduser() if directory else Path(project)
    proc = subprocess.Popen(
        ["opencode", "serve", "--port", "0", "--hostname", "127.0.0.1"],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    url = None
    deadline = time.monotonic() + wait_seconds
    try:
        assert proc.stdout is not None
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            match = _LISTEN_RE.search(line)
            if match:
                url = match.group(1)
                break
    finally:
        if url is None:
            proc.terminate()
    if url is None:
        code = proc.poll()
        raise RuntimeError(
            f"opencode serve did not report a listening URL (exit={code})"
        )
    return register_instance(
        project,
        url=url,
        label=label or f"opencode {url.rsplit(':', 1)[-1]}",
        pid=proc.pid,
        managed=True,
        auto_answer=auto_answer,
    )


def stop_instance(project: Path, instance_id: str) -> dict[str, Any]:
    entries = load_registry(project)
    target = next((e for e in entries if e.get("id") == instance_id), None)
    if target is None:
        # Adopted-but-unpersisted ``opencode serve`` processes are still
        # addressable: refuse rather than reporting them as unknown.
        target = _find_instance(project, instance_id)
    if target is None:
        return {"ok": False, "error": f"unknown instance {instance_id!r}"}
    if not target.get("managed"):
        return {"ok": False, "error": "instance is not koru-managed; stop refused"}
    pid = target.get("pid")
    stopped = False
    if _pid_alive(pid):
        try:
            os.kill(int(pid), 15)
            stopped = True
        except OSError:
            stopped = False
    unregister_instance(project, instance_id)
    return {"ok": True, "stopped": stopped, "pid": pid}


def _session_updated_ms(sess: dict[str, Any]) -> int:
    ts = sess.get("time")
    if isinstance(ts, dict):
        try:
            return int(ts.get("updated") or ts.get("created") or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def _session_directory(sess: dict[str, Any]) -> str | None:
    loc = sess.get("location")
    if isinstance(loc, dict) and loc.get("directory"):
        return str(loc["directory"])
    return sess.get("directory")


def _extract_ticket_id(text: str) -> str | None:
    match = _TICKET_RE.search(text or "")
    return match.group(1).upper() if match else None


def _session_ticket(url: str, sess: dict[str, Any]) -> str | None:
    """Most recent planfile ticket id mentioned in user prompts, cached."""
    sid = sess.get("id")
    if not sid:
        return None
    updated = _session_updated_ms(sess)
    if not updated or updated < (time.time() * 1000) - _TICKET_SCAN_WINDOW_MS:
        return None
    key = (url, str(sid))
    cached = _session_ticket_cache.get(key)
    if cached is not None and cached[0] == updated:
        return cached[1]
    ticket = None
    try:
        messages = session_messages(url, str(sid), limit=100)
        for msg in reversed(messages):
            info = msg.get("info") if isinstance(msg.get("info"), dict) else {}
            if info.get("role") != "user":
                continue
            for part in msg.get("parts") or []:
                if isinstance(part, dict) and part.get("type") == "text":
                    ticket = _extract_ticket_id(str(part.get("text") or ""))
                    if ticket:
                        break
            if ticket:
                break
    except Exception:
        ticket = None
    if len(_session_ticket_cache) > 500:
        _session_ticket_cache.clear()
    _session_ticket_cache[key] = (updated, ticket)
    return ticket


def instance_status(entry: dict[str, Any]) -> dict[str, Any]:
    """Aggregate one instance row for the grid: sessions + pending counts."""
    url = str(entry.get("url", ""))
    row: dict[str, Any] = {
        "id": entry.get("id"),
        "url": url,
        "label": entry.get("label") or url,
        "pid": entry.get("pid"),
        "managed": bool(entry.get("managed")),
        "auto_answer": bool(entry.get("auto_answer")),
        "healthy": bool(entry.get("healthy")),
        "sessions": [],
        "pending": {"permissions": 0, "questions": 0},
        "providers": [],
        "active_ticket": None,
        "project_dirs": [],
        "models": [],
    }
    if not row["healthy"]:
        return row
    try:
        sessions = list_sessions(url)
    except Exception:
        row["healthy"] = False
        return row
    srow_by_id: dict[str, dict[str, Any]] = {}
    for sess in sessions:
        model = sess.get("model") if isinstance(sess.get("model"), dict) else {}
        srow = {
            "id": sess.get("id"),
            "slug": sess.get("slug"),
            "title": sess.get("title") or sess.get("slug") or sess.get("id"),
            "directory": _session_directory(sess),
            "cost": sess.get("cost"),
            "agent": sess.get("agent"),
            "model": model.get("id") or model.get("modelID"),
            "provider": model.get("providerID"),
            "updated": _session_updated_ms(sess) or None,
            "ticket": None,
        }
        row["sessions"].append(srow)
        if sess.get("id"):
            srow_by_id[str(sess["id"])] = srow
    recent = sorted(sessions, key=_session_updated_ms, reverse=True)[
        :_TICKET_SCAN_SESSIONS
    ]
    for sess in recent:
        srow = srow_by_id.get(str(sess.get("id") or ""))
        if srow is None:
            continue
        srow["ticket"] = _session_ticket(url, sess)
        if row["active_ticket"] is None and srow["ticket"]:
            row["active_ticket"] = srow["ticket"]
    row["project_dirs"] = sorted(
        {s["directory"] for s in row["sessions"] if s.get("directory")}
    )
    row["models"] = sorted(
        {
            f"{s['provider']}/{s['model']}" if s.get("provider") else s["model"]
            for s in row["sessions"]
            if s.get("model")
        }
    )
    row["providers"] = list_providers(url)
    row["exhausted_providers"] = get_exhausted_providers()
    try:
        pending = pending_requests(url)
        row["pending"] = {
            "permissions": len(pending["permissions"]),
            "questions": len(pending["questions"]),
        }
    except Exception:
        pass
    return row


def terminals_payload(project: Path) -> dict[str, Any]:
    instances = discover_instances(project)
    _prune_dead_managed(project, instances)
    rows = [instance_status(entry) for entry in instances]
    return {
        "project": str(project),
        "instances": rows,
        "total": len(rows),
        "healthy": sum(1 for r in rows if r["healthy"]),
        "exhausted_providers": get_exhausted_providers(),
    }


def terminal_detail(project: Path, instance_id: str) -> dict[str, Any]:
    entry = _find_instance(project, instance_id)
    if entry is None:
        return {"error": f"unknown instance {instance_id!r}"}
    url = str(entry["url"])
    detail = instance_status({**entry, "healthy": instance_health(url)})
    if detail["healthy"]:
        pending = pending_requests(url)
        detail["pending_requests"] = pending
    detail["exhausted_providers"] = get_exhausted_providers()
    return detail


def terminal_messages(
    project: Path, instance_id: str, session_id: str, *, limit: int = 60
) -> dict[str, Any]:
    entry = _find_instance(project, instance_id)
    if entry is None:
        return {"error": f"unknown instance {instance_id!r}"}
    try:
        messages = session_messages(str(entry["url"]), session_id, limit=limit)
    except Exception as exc:
        return {"error": str(exc), "messages": []}
    return {
        "messages": [normalize_message(m) for m in messages],
        "session_id": session_id,
    }


def _find_instance(project: Path, instance_id: str) -> dict[str, Any] | None:
    for entry in discover_instances(project, probe=False):
        if entry.get("id") == instance_id:
            return entry
    return None


def terminal_prompt(project: Path, body: dict[str, Any]) -> dict[str, Any]:
    instance_id = str(body.get("iid") or "").strip()
    text = str(body.get("text") or "").strip()
    if not instance_id or not text:
        return {"error": "iid and text are required"}
    entry = _find_instance(project, instance_id)
    if entry is None:
        return {"error": f"unknown instance {instance_id!r}"}
    url = str(entry["url"])
    session_id = str(body.get("session_id") or "").strip()
    model = body.get("model")
    model = model if isinstance(model, dict) else None
    agent = str(body.get("agent") or "").strip() or None

    # Refresh provider exhaustion from recent log
    scan_opencode_log_for_exhaustion()

    # Resolve active model with automatic failover if provider is exhausted
    active_model, failover_meta = resolve_active_terminal_model(url, requested_model=model)

    if not session_id:
        sess = None
        try:
            sess = create_session(
                url,
                title=text[:60],
                agent=agent,
                model=active_model,
                directory=str(project),
            )
        except (urllib.error.URLError, OSError, ValueError) as exc:
            is_ex, ttl, reason = parse_exhaustion_from_error(str(exc))
            if is_ex and active_model:
                mark_provider_exhausted(active_model["providerID"], ttl_seconds=ttl, reason=reason)
                retry_model, _ = resolve_active_terminal_model(url)
                if retry_model and retry_model.get("providerID") != active_model.get("providerID"):
                    failover_meta = {
                        "from": active_model["providerID"],
                        "to": retry_model["providerID"],
                        "model": retry_model["modelID"],
                    }
                    active_model = retry_model
                    try:
                        sess = create_session(
                            url,
                            title=text[:60],
                            agent=agent,
                            model=active_model,
                            directory=str(project),
                        )
                    except Exception:
                        sess = None
            if not sess or not sess.get("id"):
                return {"error": f"failed to create session: {exc}"}
        if not sess or not sess.get("id"):
            return {"error": "failed to create session"}
        session_id = str(sess["id"])

    try:
        result = send_prompt(url, session_id, text, model=active_model, agent=agent)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        is_ex, ttl, reason = parse_exhaustion_from_error(str(exc))
        if is_ex and active_model:
            mark_provider_exhausted(active_model["providerID"], ttl_seconds=ttl, reason=reason)
            retry_model, _ = resolve_active_terminal_model(url)
            if retry_model and retry_model.get("providerID") != active_model.get("providerID"):
                try:
                    result = send_prompt(url, session_id, text, model=retry_model, agent=agent)
                    failover_meta = {
                        "from": active_model["providerID"],
                        "to": retry_model["providerID"],
                        "model": retry_model["modelID"],
                    }
                    out = {"ok": True, "session_id": session_id, "result": result}
                    if failover_meta:
                        out["failover"] = failover_meta
                    return out
                except Exception as retry_exc:
                    return {"error": f"prompt failed after failover retry: {retry_exc}"}
        return {"error": str(exc)}

    out = {"ok": True, "session_id": session_id, "result": result}
    if failover_meta:
        out["failover"] = failover_meta
    return out


def terminal_reply(project: Path, body: dict[str, Any]) -> dict[str, Any]:
    instance_id = str(body.get("iid") or "").strip()
    session_id = str(body.get("session_id") or "").strip()
    request_id = str(body.get("request_id") or "").strip()
    kind = str(body.get("kind") or "").strip()
    if not all([instance_id, session_id, request_id, kind]):
        return {"error": "iid, session_id, request_id and kind are required"}
    entry = _find_instance(project, instance_id)
    if entry is None:
        return {"error": f"unknown instance {instance_id!r}"}
    url = str(entry["url"])
    try:
        if kind == "permission":
            result = reply_permission(
                url, session_id, request_id, str(body.get("reply") or "once")
            )
        elif kind == "question":
            answers = body.get("answers")
            if not isinstance(answers, list):
                return {"error": "answers must be an array of label arrays"}
            result = reply_question(url, session_id, request_id, answers)
        else:
            return {"error": "kind must be permission|question"}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"error": str(exc)}
    return {"ok": True, "result": result}


__all__ = [
    "clear_provider_exhaustion",
    "discover_instances",
    "get_available_models",
    "get_exhausted_providers",
    "get_instance_config",
    "instance_health",
    "is_provider_exhausted",
    "list_providers",
    "list_sessions",
    "load_registry",
    "mark_provider_exhausted",
    "normalize_message",
    "parse_exhaustion_from_error",
    "pending_requests",
    "register_instance",
    "registry_path",
    "reply_permission",
    "reply_question",
    "resolve_active_terminal_model",
    "save_registry",
    "scan_opencode_log_for_exhaustion",
    "session_messages",
    "send_prompt",
    "set_auto_answer",
    "spawn_instance",
    "stop_instance",
    "terminal_detail",
    "terminal_messages",
    "terminal_prompt",
    "terminal_reply",
    "terminals_payload",
    "unregister_instance",
]
