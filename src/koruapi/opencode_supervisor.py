"""Supervisor loop for koru-managed ``opencode serve`` instances.

Polls pending permission and question requests on each instance that has
``auto_answer`` enabled and resolves them through the documented opencode HTTP
API:

- permission requests → replied ``once`` (per-request grant, never persisted
  as ``always`` so the audit trail stays per action);
- question requests → answered by SubLLM, which picks the option labels that
  best match the autonomous task context; when the LLM is unavailable the
  request stays pending for the human in the dashboard.

The loop runs as a daemon thread next to the dashboard server so ``koru serve``
and ``koru auto --web`` both get supervision for free.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koruapi.opencode_terminals import (
    discover_instances,
    list_sessions,
    pending_requests,
    reply_permission,
    reply_question,
    resolve_active_terminal_model,
    scan_opencode_log_for_exhaustion,
    send_prompt,
)

DEFAULT_INTERVAL = 3.0

LogFn = Callable[[str], None]
_steered_sessions: dict[str, float] = {}


def _default_log(message: str) -> None:
    print(f"[koru-supervisor] {message}", file=sys.stderr)


def supervisor_enabled() -> bool:
    raw = os.environ.get("KORU_TERMINALS_SUPERVISOR", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _load_subllm(log: LogFn) -> tuple[bool, Callable[..., Any] | None]:
    """Resolve the optional SubLLM runner; ``(False, None)`` (after logging) if absent."""
    try:
        from korullm import run_subllm
    except Exception:  # pragma: no cover — subllm optional
        log("subllm unavailable; question left pending")
        return False, None
    return True, run_subllm


def _question_spec(questions: list[Any]) -> list[dict[str, Any]] | None:
    """Build the SubLLM question spec; ``None`` when a question has no options."""
    spec: list[dict[str, Any]] = []
    for index, q in enumerate(questions):
        options = q.get("options") or []
        labels = [str(o.get("label", "")) for o in options if isinstance(o, dict)]
        if not labels:
            return None
        spec.append(
            {
                "index": index,
                "header": q.get("header", ""),
                "question": q.get("question", ""),
                "options": labels,
                "multiple": bool(q.get("multiple")),
            }
        )
    return spec


def _subllm_answer_stdout(
    run_subllm: Callable[..., Any] | None,
    project: Path,
    spec: list[dict[str, Any]],
    log: LogFn,
) -> tuple[bool, str | None]:
    """Run SubLLM over the spec; ``(True, stdout)`` on success, ``(False, None)`` on failure."""
    prompt = (
        "An opencode agent in an autonomous koru run is asking for a decision. "
        "Pick the best option for each question, preferring the choice that "
        "keeps autonomous work unblocked. Reply with ONLY a JSON array of "
        "arrays of chosen option labels, in question order.\n\n" + json.dumps(spec, indent=2)
    )
    try:
        result = run_subllm(
            prompt,
            project,
            route_function="supervisor-answer",
            system_prompt="You are the koru supervisor. Answer with strict JSON only.",
            timeout_seconds=30.0,
        )
    except Exception as exc:  # pragma: no cover — transport failure
        log(f"subllm call failed: {exc}")
        return False, None
    if result.returncode != 0:
        log(f"subllm returned {result.returncode}: {result.stderr[:120]}")
        return False, None
    return True, result.stdout


def _parse_answer_payload(stdout: str | None, log: LogFn) -> tuple[bool, Any]:
    """Parse the SubLLM reply; ``(False, None)`` when no JSON array can be salvaged."""
    try:
        return True, json.loads(stdout.strip())
    except json.JSONDecodeError:
        # Try to salvage a JSON array embedded in prose.
        start, end = stdout.find("["), stdout.rfind("]")
        if start != -1 and end > start:
            try:
                return True, json.loads(stdout[start : end + 1])
            except json.JSONDecodeError:
                pass
    log("subllm answer not JSON; question left pending")
    return False, None


def _normalize_answer_set(parsed: list[Any], spec: list[dict[str, Any]], log: LogFn) -> list[list[str]] | None:
    """Map parsed picks onto real option labels; ``None`` on an invalid entry."""
    answers: list[list[str]] = []
    for i, chosen in enumerate(parsed):
        allowed = set(spec[i]["options"])
        if isinstance(chosen, str):
            chosen = [chosen]
        if not isinstance(chosen, list) or not chosen:
            log("subllm answer invalid; question left pending")
            return None
        picked = [str(c) for c in chosen if str(c) in allowed]
        if not picked:
            # LLM invented a label — fall back to the first real option.
            picked = [spec[i]["options"][0]]
        if not spec[i]["multiple"]:
            picked = picked[:1]
        answers.append(picked)
    return answers


def _question_answers_via_llm(project: Path, request: dict[str, Any], log: LogFn) -> list[list[str]] | None:
    """Ask SubLLM to pick option labels for each pending question."""
    questions = request.get("questions") or []
    if not questions:
        return None
    subllm_ready, run_subllm = _load_subllm(log)
    if not subllm_ready:
        return None
    spec = _question_spec(questions)
    if spec is None:
        return None
    call_ok, stdout = _subllm_answer_stdout(run_subllm, project, spec, log)
    if not call_ok:
        return None
    parse_ok, parsed = _parse_answer_payload(stdout, log)
    if not parse_ok:
        return None
    if not isinstance(parsed, list) or len(parsed) != len(spec):
        log("subllm answer shape mismatch; question left pending")
        return None
    return _normalize_answer_set(parsed, spec, log)


def _prune_steered_sessions(now: float) -> None:
    if len(_steered_sessions) > 500:
        cutoff = now - 3600.0
        for sid, t in list(_steered_sessions.items()):
            if t < cutoff:
                del _steered_sessions[sid]


def _resolve_instance_target(entry: dict[str, Any]) -> str | None:
    if not entry.get("auto_answer"):
        return None
    url = str(entry.get("url") or "")
    if not url or not entry.get("healthy"):
        return None
    return url


def _steer_session_to_fallback(
    url: str,
    sid: str,
    failing_pid: str,
    fallback_model: dict[str, Any],
    now: float,
    stats: dict[str, int],
    log: LogFn,
) -> None:
    try:
        steer_text = (
            f"Supervisor failover: provider '{failing_pid}' exhausted. "
            "Continuing autonomous execution with "
            f"{fallback_model['providerID']}/{fallback_model['modelID']}."
        )
        send_prompt(url, sid, steer_text, model=fallback_model)
        _steered_sessions[sid] = now
        stats["failovers"] += 1
        log(
            f"{url}: session {sid} auto-steered to fallback "
            f"{fallback_model['providerID']}/{fallback_model['modelID']}"
        )
    except Exception as exc:
        stats["errors"] += 1
        log(f"{url}: failover steering failed for {sid}: {exc}")


def _handle_instance_failovers(
    url: str,
    log_events: list[dict[str, Any]],
    now: float,
    stats: dict[str, int],
    log: LogFn,
) -> None:
    if not log_events:
        return
    try:
        active_sessions = {
            str(s.get("id")): s for s in list_sessions(url) if isinstance(s, dict) and s.get("id")
        }
    except Exception:
        active_sessions = {}

    for ev in log_events:
        sid = ev.get("sessionID")
        failing_pid = ev.get("providerID")
        if not sid or not failing_pid or sid not in active_sessions:
            continue
        last_steered = _steered_sessions.get(sid, 0.0)
        if now - last_steered < 120.0:
            continue
        fallback_model, _ = resolve_active_terminal_model(url)
        if fallback_model and fallback_model.get("providerID") != failing_pid:
            _steer_session_to_fallback(url, sid, failing_pid, fallback_model, now, stats, log)


def _handle_pending_permissions(
    url: str,
    permissions: list[dict[str, Any]],
    stats: dict[str, int],
    log: LogFn,
) -> None:
    for req in permissions:
        session_id = str(req.get("sessionID") or "")
        request_id = str(req.get("id") or "")
        if not session_id or not request_id:
            continue
        try:
            reply_permission(url, session_id, request_id, "once")
            stats["permissions"] += 1
            log(f"{url}: permission {request_id} ({req.get('action', '?')}) -> once")
        except Exception as exc:
            stats["errors"] += 1
            log(f"{url}: permission {request_id} reply failed: {exc}")


def _handle_pending_questions(
    project: Path,
    url: str,
    questions: list[dict[str, Any]],
    stats: dict[str, int],
    log: LogFn,
) -> None:
    for req in questions:
        session_id = str(req.get("sessionID") or "")
        request_id = str(req.get("id") or "")
        if not session_id or not request_id:
            continue
        answers = _question_answers_via_llm(project, req, log)
        if answers is None:
            continue
        try:
            reply_question(url, session_id, request_id, answers)
            stats["questions"] += 1
            log(f"{url}: question {request_id} answered {answers}")
        except Exception as exc:
            stats["errors"] += 1
            log(f"{url}: question {request_id} reply failed: {exc}")


def _supervise_instance(
    project: Path,
    url: str,
    log_events: list[dict[str, Any]],
    now: float,
    stats: dict[str, int],
    log: LogFn,
) -> None:
    _handle_instance_failovers(url, log_events, now, stats, log)
    try:
        pending = pending_requests(url)
    except Exception as exc:
        stats["errors"] += 1
        log(f"{url}: pending poll failed: {exc}")
        return
    _handle_pending_permissions(url, pending.get("permissions") or [], stats, log)
    _handle_pending_questions(project, url, pending.get("questions") or [], stats, log)


def supervise_once(project: Path, *, log: LogFn = _default_log) -> dict[str, int]:
    """One supervisor pass over every auto-answer instance. Returns counts."""
    stats = {
        "permissions": 0,
        "questions": 0,
        "failovers": 0,
        "errors": 0,
        "instances": 0,
    }
    log_events = scan_opencode_log_for_exhaustion()
    for ev in log_events:
        log(f"provider {ev['providerID']} exhausted: {ev['error'][:80]}")

    now = time.time()
    _prune_steered_sessions(now)

    for entry in discover_instances(project):
        url = _resolve_instance_target(entry)
        if url is None:
            continue
        stats["instances"] += 1
        _supervise_instance(project, url, log_events, now, stats, log)

    return stats


def _supervisor_loop(project: Path, interval: float, stop: threading.Event, log: LogFn) -> None:
    while not stop.is_set():
        try:
            supervise_once(project, log=log)
        except Exception as exc:  # pragma: no cover — keep the loop alive
            log(f"supervisor pass failed: {exc}")
        stop.wait(interval)


def start_supervisor(
    project: Path,
    *,
    interval: float = DEFAULT_INTERVAL,
    log: LogFn = _default_log,
) -> tuple[threading.Thread, threading.Event] | None:
    """Start the supervisor daemon thread; returns ``(thread, stop_event)``.

    Returns ``None`` when disabled via ``KORU_TERMINALS_SUPERVISOR=0``.
    """
    if not supervisor_enabled():
        return None
    stop = threading.Event()
    thread = threading.Thread(
        target=_supervisor_loop,
        args=(Path(project), interval, stop, log),
        name="koru-opencode-supervisor",
        daemon=True,
    )
    thread.start()
    log("opencode supervisor started")
    return thread, stop


__all__ = [
    "DEFAULT_INTERVAL",
    "start_supervisor",
    "supervise_once",
    "supervisor_enabled",
]
