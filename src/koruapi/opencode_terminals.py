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

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REGISTRY_NAME = "opencode-instances.json"
_REQUEST_TIMEOUT = 2.0
_LISTEN_RE = re.compile(r"opencode server listening on (https?://\S+)")


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


def _normalize_model(model: dict[str, str] | None) -> dict[str, str] | None:
    """Translate to the server schema ``{"id": ..., "providerID": ...}``."""
    if not isinstance(model, dict):
        return None
    model_id = model.get("id") or model.get("modelID")
    provider = model.get("providerID") or model.get("providerId")
    if not model_id or not provider:
        return None
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
    data = _api_request(url, f"/api/session/{session_id}/message")
    items = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return items[-limit:]


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
    normalized = _normalize_model(model)
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
    }
    if not row["healthy"]:
        return row
    try:
        sessions = list_sessions(url)
    except Exception:
        row["healthy"] = False
        return row
    for sess in sessions:
        row["sessions"].append(
            {
                "id": sess.get("id"),
                "slug": sess.get("slug"),
                "title": sess.get("title") or sess.get("slug") or sess.get("id"),
                "directory": sess.get("directory"),
                "cost": sess.get("cost"),
            }
        )
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
    return {"messages": messages, "session_id": session_id}


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
    if not session_id:
        try:
            sess = create_session(
                url,
                title=text[:60],
                agent=agent,
                model=model,
                directory=str(project),
            )
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return {"error": f"failed to create session: {exc}"}
        if not sess or not sess.get("id"):
            return {"error": "failed to create session"}
        session_id = str(sess["id"])
    try:
        result = send_prompt(url, session_id, text, model=model, agent=agent)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"error": str(exc)}
    return {"ok": True, "session_id": session_id, "result": result}


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
    "discover_instances",
    "instance_health",
    "list_sessions",
    "load_registry",
    "pending_requests",
    "register_instance",
    "registry_path",
    "reply_permission",
    "reply_question",
    "save_registry",
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
