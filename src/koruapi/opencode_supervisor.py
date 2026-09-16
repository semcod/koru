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
from pathlib import Path
from typing import Any, Callable

from koruapi.opencode_terminals import (
    discover_instances,
    pending_requests,
    reply_permission,
    reply_question,
)

DEFAULT_INTERVAL = 3.0

LogFn = Callable[[str], None]


def _default_log(message: str) -> None:
    print(f"[koru-supervisor] {message}", file=sys.stderr)


def supervisor_enabled() -> bool:
    raw = os.environ.get("KORU_TERMINALS_SUPERVISOR", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _question_answers_via_llm(
    project: Path, request: dict[str, Any], log: LogFn
) -> list[list[str]] | None:
    """Ask SubLLM to pick option labels for each pending question."""
    questions = request.get("questions") or []
    if not questions:
        return None
    try:
        from korullm import run_subllm
    except Exception:  # pragma: no cover — subllm optional
        log("subllm unavailable; question left pending")
        return None
    spec = []
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
    prompt = (
        "An opencode agent in an autonomous koru run is asking for a decision. "
        "Pick the best option for each question, preferring the choice that "
        "keeps autonomous work unblocked. Reply with ONLY a JSON array of "
        "arrays of chosen option labels, in question order.\n\n"
        + json.dumps(spec, indent=2)
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
        return None
    if result.returncode != 0:
        log(f"subllm returned {result.returncode}: {result.stderr[:120]}")
        return None
    try:
        parsed = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        # Try to salvage a JSON array embedded in prose.
        text = result.stdout
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end <= start:
            log("subllm answer not JSON; question left pending")
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            log("subllm answer not JSON; question left pending")
            return None
    if not isinstance(parsed, list) or len(parsed) != len(spec):
        log("subllm answer shape mismatch; question left pending")
        return None
    answers: list[list[str]] = []
    valid = True
    for i, chosen in enumerate(parsed):
        allowed = set(spec[i]["options"])
        if isinstance(chosen, str):
            chosen = [chosen]
        if not isinstance(chosen, list) or not chosen:
            valid = False
            break
        picked = [str(c) for c in chosen if str(c) in allowed]
        if not picked:
            # LLM invented a label — fall back to the first real option.
            picked = [spec[i]["options"][0]]
        if not spec[i]["multiple"]:
            picked = picked[:1]
        answers.append(picked)
    if not valid:
        log("subllm answer invalid; question left pending")
        return None
    return answers


def supervise_once(project: Path, *, log: LogFn = _default_log) -> dict[str, int]:
    """One supervisor pass over every auto-answer instance. Returns counts."""
    stats = {"permissions": 0, "questions": 0, "errors": 0, "instances": 0}
    for entry in discover_instances(project):
        if not entry.get("auto_answer"):
            continue
        url = str(entry.get("url") or "")
        if not url or not entry.get("healthy"):
            continue
        stats["instances"] += 1
        try:
            pending = pending_requests(url)
        except Exception as exc:
            stats["errors"] += 1
            log(f"{url}: pending poll failed: {exc}")
            continue
        for req in pending["permissions"]:
            session_id = str(req.get("sessionID") or "")
            request_id = str(req.get("id") or "")
            if not session_id or not request_id:
                continue
            try:
                reply_permission(url, session_id, request_id, "once")
                stats["permissions"] += 1
                log(
                    f"{url}: permission {request_id} "
                    f"({req.get('action', '?')}) -> once"
                )
            except Exception as exc:
                stats["errors"] += 1
                log(f"{url}: permission {request_id} reply failed: {exc}")
        for req in pending["questions"]:
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
    return stats


def _supervisor_loop(
    project: Path, interval: float, stop: threading.Event, log: LogFn
) -> None:
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
