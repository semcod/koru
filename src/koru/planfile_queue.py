"""Minimal planfile-backed queue runner for koru."""

from __future__ import annotations

import contextlib
import json
import os
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Protocol


class CommandResult(Protocol):
    """Protocol for subprocess-like command results."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class QueueRunResult:
    """Result of a single queue tick."""

    status: str
    ticket_id: str | None = None
    executor_kind: str | None = None
    message: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class QueueLoopResult:
    """Aggregate result of draining the planfile queue with run_planfile_queue_loop."""

    iterations: int
    completed: list[str]
    failed: list[str]
    waiting: list[str]
    last_status: str
    last_message: str = ""

    def summary(self) -> str:
        lines = [
            f"iterations={self.iterations}",
            f"completed={len(self.completed)}",
            f"failed={len(self.failed)}",
            f"waiting={len(self.waiting)}",
            f"last_status={self.last_status}",
        ]
        return " ".join(lines)


@dataclass(frozen=True)
class ApiRunResult:
    """Result of a direct HTTP API executor call."""

    returncode: int
    stdout: str
    stderr: str
    status_code: int
    headers: dict[str, str]


@dataclass(frozen=True)
class LlmRunResult:
    """Result of an OpenRouter (or compatible) chat-completion call.

    ``stdout`` carries the assistant's text content (extracted from
    ``choices[0].message.content``) so the rest of the queue runner can
    treat it like any other executor's stdout. ``model`` and ``usage``
    expose model/token info for cost tracking and ``raw`` carries the
    full JSON response in case downstream tooling wants it.
    """

    returncode: int
    stdout: str
    stderr: str
    status_code: int
    model: str
    usage: dict[str, int]
    raw: dict[str, Any]


def _planfile_env() -> dict[str, str]:
    """Force a wide, non-TTY console so planfile's Rich output stays one
    JSON object per line. Without this, long handler strings get wrapped
    by Rich and break json.loads on the koru side."""
    return {**os.environ, "COLUMNS": "10000", "TERM": "dumb", "PYTHONWARNINGS": "ignore"}


def _run_process(command: Sequence[str], project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        env=_planfile_env(),
    )


def _run_shell_command(command: str, project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=project,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_api_request(request: dict[str, Any], _project: Path) -> ApiRunResult:
    body = request.get("body")
    data: bytes | None = None
    headers = {str(k): str(v) for k, v in (request.get("headers") or {}).items()}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers.setdefault("content-type", "application/json")

    api_request = urllib.request.Request(
        str(request["endpoint"]),
        data=data,
        headers=headers,
        method=str(request.get("method") or "GET").upper(),
    )
    timeout = float(request.get("timeout_seconds") or 30.0)

    try:
        with urllib.request.urlopen(api_request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            return ApiRunResult(
                returncode=0,
                stdout=text,
                stderr="",
                status_code=int(response.status),
                headers=dict(response.headers.items()),
            )
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return ApiRunResult(
            returncode=1,
            stdout=text,
            stderr=f"HTTP {exc.code}",
            status_code=int(exc.code),
            headers=dict(exc.headers.items()),
        )
    except urllib.error.URLError as exc:
        return ApiRunResult(
            returncode=1,
            stdout="",
            stderr=str(exc.reason),
            status_code=0,
            headers={},
        )


_DEFAULT_LLM_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"


def _run_llm_request(request: dict[str, Any], _project: Path) -> LlmRunResult:
    """Call an OpenAI-compatible chat-completion endpoint (default OpenRouter).

    Reads ``OPENROUTER_API_KEY`` from the environment when ``endpoint``
    points at openrouter.ai; falls back to ``OPENAI_API_KEY`` for the
    OpenAI endpoint. Honours ``KORU_LLM_ENDPOINT`` for self-hosted
    proxies (e.g. an Ollama OpenAI-compat shim).
    """
    endpoint = str(
        request.get("endpoint")
        or os.getenv("KORU_LLM_ENDPOINT")
        or _DEFAULT_LLM_ENDPOINT
    )
    model = str(request.get("model") or _DEFAULT_LLM_MODEL)

    if "openrouter.ai" in endpoint:
        api_key = os.getenv("OPENROUTER_API_KEY")
        key_var = "OPENROUTER_API_KEY"
    else:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        key_var = "OPENAI_API_KEY"

    if not api_key:
        return LlmRunResult(
            returncode=1,
            stdout="",
            stderr=(
                f"{key_var} is not set — refusing to call {endpoint}. "
                "Export the key (e.g. via .env) and retry, "
                "or use executor.kind=human for this ticket."
            ),
            status_code=0,
            model=model,
            usage={},
            raw={},
        )

    messages: list[dict[str, str]] = []
    system = request.get("system_prompt")
    if system:
        messages.append({"role": "system", "content": str(system)})
    messages.append({"role": "user", "content": str(request["prompt"])})

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": float(request.get("temperature", 0.0)),
    }
    if request.get("max_tokens") is not None:
        body["max_tokens"] = int(request["max_tokens"])
    schema = request.get("response_schema")
    if schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "koru_response", "schema": schema, "strict": True},
        }

    headers = {
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json",
    }
    referer = os.getenv("KORU_LLM_HTTP_REFERER")
    title = os.getenv("KORU_LLM_X_TITLE", "koru")
    if "openrouter.ai" in endpoint:
        if referer:
            headers["http-referer"] = referer
        headers["x-title"] = title

    api_request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    timeout = float(request.get("timeout_seconds") or 60.0)

    try:
        with urllib.request.urlopen(api_request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
            content = ""
            choices = payload.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                content = str(msg.get("content") or "")
            return LlmRunResult(
                returncode=0 if content else 1,
                stdout=content,
                stderr="" if content else "LLM returned empty content",
                status_code=int(response.status),
                model=str(payload.get("model") or model),
                usage=dict(payload.get("usage") or {}),
                raw=payload,
            )
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return LlmRunResult(
            returncode=1,
            stdout="",
            stderr=f"HTTP {exc.code}: {text[:500]}",
            status_code=int(exc.code),
            model=model,
            usage={},
            raw={},
        )
    except urllib.error.URLError as exc:
        return LlmRunResult(
            returncode=1,
            stdout="",
            stderr=str(exc.reason),
            status_code=0,
            model=model,
            usage={},
            raw={},
        )


def _queue_lock_wanted() -> bool:
    v = os.environ.get("KORU_QUEUE_RUNNER_LOCK", "1").strip().lower()
    return v not in {"0", "false", "no", "off"}


@contextlib.contextmanager
def _queue_runner_lock(project: Path):
    """Serialize ``run_next_planfile_task`` per project (POSIX ``flock``).

    Prevents multiple IDE/terminal koru drains from picking the same open
    ticket. Set ``KORU_QUEUE_RUNNER_LOCK=0`` to disable (not recommended when
    several agents share one ``.planfile``).
    """
    if not _queue_lock_wanted() or os.name != "posix":
        yield
        return

    import fcntl

    lock_dir = project / ".planfile" / ".koru"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "queue-runner.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _claim_lease_seconds_str() -> str:
    raw = os.environ.get("KORU_TICKET_LEASE_SECONDS", "3600").strip()
    try:
        n = int(raw, 10)
    except ValueError:
        return "3600"
    return str(max(60, min(n, 86400 * 7)))


def _ticket_claim_or_error(
    project: Path,
    ticket_id: str,
    actor: str,
    *,
    planfile_runner: Callable[[Sequence[str], Path], CommandResult],
) -> QueueRunResult | None:
    """Run ``planfile ticket claim``; return ``QueueRunResult`` on CLI failure."""
    claim = _planfile_command(
        project,
        [
            "ticket",
            "claim",
            ticket_id,
            "--assigned-to",
            actor,
            "--lease-seconds",
            _claim_lease_seconds_str(),
        ],
        runner=planfile_runner,
    )
    if claim.returncode != 0:
        return QueueRunResult(
            status="claim_failed",
            ticket_id=ticket_id,
            message=(claim.stderr or claim.stdout or "ticket claim failed").strip(),
            exit_code=claim.returncode,
            stdout=claim.stdout,
            stderr=claim.stderr,
        )
    return None


def _planfile_command(
    project: Path,
    args: Sequence[str],
    runner: Callable[[Sequence[str], Path], CommandResult] = _run_process,
) -> CommandResult:
    configured = os.getenv("KORU_PLANFILE_CMD")
    if configured:
        base_command = shlex.split(configured)
    elif find_spec("planfile") is not None:
        base_command = [sys.executable, "-m", "planfile.cli"]
    else:
        base_command = ["planfile"]
    return runner([*base_command, *args], project)


def _parse_next_ticket(stdout: str) -> dict | None:
    """Pick the first runnable ticket from planfile output.

    Accepts both a single-object payload (legacy ``ticket next``) and
    an array (``ticket list --format json``). Returns ``None`` when the
    queue is idle.
    """
    stripped = stdout.strip()
    if not stripped or "No runnable ticket found" in stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = json.loads(stripped, strict=False)
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        # planfile ticket list returns oldest-first; treat the first
        # entry whose status is open / ready / todo as runnable.
        runnable_states = {None, "open", "ready", "todo"}
        for entry in payload:
            if isinstance(entry, dict) and entry.get("status") in runnable_states:
                return entry
        return None
    return None


def _ticket_command(ticket: dict) -> str | None:
    inputs = ticket.get("inputs") or {}
    executor = ticket.get("executor") or {}
    return inputs.get("script") or executor.get("handler")


def _ticket_llm_request(ticket: dict) -> dict[str, Any] | None:
    """Translate an executor.kind=llm ticket into an LLM HTTP call spec.

    Returns None when the ticket lacks the minimum signal (a prompt to
    send), so the caller can fall back to ``planfile ticket block``
    with a ``--reason`` describing the missing input.
    """
    inputs = ticket.get("inputs") or {}
    executor = ticket.get("executor") or {}
    prompt = (
        inputs.get("prompt")
        or ticket.get("description")
        or ticket.get("name")
    )
    if not prompt:
        return None
    return {
        "endpoint": inputs.get("llm_endpoint") or executor.get("handler"),
        "model": inputs.get("llm_model"),
        "prompt": str(prompt),
        "system_prompt": inputs.get("system_prompt"),
        "max_tokens": inputs.get("llm_max_tokens"),
        "temperature": inputs.get("llm_temperature", 0.0),
        "response_schema": inputs.get("response_schema"),
        "timeout_seconds": inputs.get("llm_timeout_seconds") or 60.0,
    }


def _ticket_api_request(ticket: dict) -> dict[str, Any] | None:
    inputs = ticket.get("inputs") or {}
    executor = ticket.get("executor") or {}
    endpoint = inputs.get("api_endpoint") or executor.get("handler")
    if not endpoint:
        return None

    return {
        "endpoint": endpoint,
        "method": inputs.get("api_method") or "GET",
        "headers": inputs.get("api_headers") or {},
        "body": inputs.get("api_body"),
        "timeout_seconds": inputs.get("api_timeout_seconds") or 30.0,
    }


def _default_human_prompt(prompt: str, ticket_id: str) -> str | None:
    """Read a multi-line human answer from stdin.

    Returns the trimmed answer, or ``None`` if the user cancelled
    (Ctrl-C) or submitted an empty response. Ctrl-D submits.
    """
    print()
    print(f"📝 {ticket_id} — human input needed")
    print("─" * 60)
    print(prompt)
    print("─" * 60)
    print("Type your answer (Ctrl-D to submit, Ctrl-C to cancel):")
    lines: list[str] = []
    try:
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            lines.append(line)
    except KeyboardInterrupt:
        print("\n[cancelled — ticket left untouched]")
        return None
    answer = "\n".join(lines).strip()
    if not answer:
        print("[empty answer — ticket left untouched]")
        return None
    return answer


def _result_json(result: CommandResult) -> str:
    payload: dict[str, Any] = {
        "exit_code": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }
    if hasattr(result, "status_code"):
        payload["status_code"] = result.status_code  # type: ignore[attr-defined]
    if hasattr(result, "model"):
        payload["llm_model"] = result.model  # type: ignore[attr-defined]
    if hasattr(result, "usage"):
        payload["llm_usage"] = result.usage  # type: ignore[attr-defined]
    return json.dumps(payload)


def run_next_planfile_task(
    *,
    project: Path,
    actor: str = "koru-shell",
    dry_run: bool = False,
    queue_name: str | None = None,
    interactive: bool = False,
    planfile_runner: Callable[[Sequence[str], Path], CommandResult] = _run_process,
    shell_runner: Callable[[str, Path], CommandResult] = _run_shell_command,
    api_runner: Callable[[dict[str, Any], Path], CommandResult] = _run_api_request,
    llm_runner: Callable[[dict[str, Any], Path], CommandResult] = _run_llm_request,
    prompt_runner: Callable[[str, str], str | None] = _default_human_prompt,
) -> QueueRunResult:
    """Execute one runnable planfile ticket, if any.

    When ``interactive`` is true and the next ticket is a ``human``
    executor, ``prompt_runner(prompt, ticket_id)`` is invoked to collect
    an answer. A non-empty answer triggers ``planfile ticket done``
    (the answer is appended to the run log under
    ``.planfile/.koru/runs/``); cancellation (``None``) leaves the
    ticket untouched and returns ``status=waiting_input`` as before.

    Concurrent drains (several IDE windows) are serialized per project
    via ``.planfile/.koru/queue-runner.lock`` (POSIX); disable with
    ``KORU_QUEUE_RUNNER_LOCK=0``. Before ``ticket start``, koru calls
    ``ticket claim --assigned-to <actor>`` for tracing / lease metadata.
    """
    project = project.resolve()

    with _queue_runner_lock(project):
        # planfile has no `ticket next` and no `--queue` filter on `list`.
        # `--status open` selects runnable tickets; koru filters by
        # ``queue_name`` in-process below (best-effort: planfile tickets
        # may carry an ``execution.queue`` field).
        next_args = ["ticket", "list", "--status", "open", "--format", "json"]
        next_result = _planfile_command(
            project,
            next_args,
            runner=planfile_runner,
        )
        if next_result.returncode != 0:
            return QueueRunResult(
                status="planfile_error",
                message="planfile ticket list failed",
                exit_code=next_result.returncode,
                stdout=next_result.stdout,
                stderr=next_result.stderr,
            )

        ticket = _parse_next_ticket(next_result.stdout)
        if ticket is None:
            return QueueRunResult(status="idle", message="No runnable ticket found")

        ticket_id = str(ticket["id"])
        executor = ticket.get("executor") or {}
        executor_kind = str(executor.get("kind") or "human")

        if executor_kind == "human":
            inputs = ticket.get("inputs") or {}
            prompt = str(
                inputs.get("prompt")
                or ticket.get("description")
                or ticket.get("name")
                or ticket_id
            )
            if not interactive or dry_run:
                return QueueRunResult(
                    status="waiting_input",
                    ticket_id=ticket_id,
                    executor_kind=executor_kind,
                    message=prompt,
                )
            answer = prompt_runner(prompt, ticket_id)
            if not answer:
                return QueueRunResult(
                    status="waiting_input",
                    ticket_id=ticket_id,
                    executor_kind=executor_kind,
                    message=prompt,
                )
            claimed = _ticket_claim_or_error(
                project, ticket_id, actor, planfile_runner=planfile_runner
            )
            if claimed:
                return claimed
            _planfile_command(
                project,
                ["ticket", "start", ticket_id],
                runner=planfile_runner,
            )
            _planfile_command(
                project,
                ["ticket", "done", ticket_id],
                runner=planfile_runner,
            )
            return QueueRunResult(
                status="completed",
                ticket_id=ticket_id,
                executor_kind=executor_kind,
                message=answer,
            )

        if executor_kind not in {"api", "shell", "llm"}:
            return QueueRunResult(
                status="unsupported_executor",
                ticket_id=ticket_id,
                executor_kind=executor_kind,
                message=f"Executor kind '{executor_kind}' is not implemented yet",
            )

        if executor_kind == "api":
            action = _ticket_api_request(ticket)
            missing_prompt = "API ticket is missing inputs.api_endpoint or executor.handler"
        elif executor_kind == "llm":
            action = _ticket_llm_request(ticket)
            missing_prompt = "LLM ticket is missing inputs.prompt (or description / name)"
        else:
            action = _ticket_command(ticket)
            missing_prompt = "Shell ticket is missing inputs.script or executor.handler"

        if not action:
            # `block --reason` is the planfile equivalent of the older
            # `input --prompt` surface koru used to call.
            _planfile_command(
                project,
                ["ticket", "block", ticket_id, "--reason", missing_prompt],
                runner=planfile_runner,
            )
            return QueueRunResult(
                status="waiting_input",
                ticket_id=ticket_id,
                executor_kind=executor_kind,
                message=missing_prompt,
            )

        if dry_run:
            message = json.dumps(action) if isinstance(action, dict) else action
            return QueueRunResult(
                status="dry_run",
                ticket_id=ticket_id,
                executor_kind=executor_kind,
                message=message,
            )

        claimed = _ticket_claim_or_error(
            project, ticket_id, actor, planfile_runner=planfile_runner
        )
        if claimed:
            return claimed
        _planfile_command(
            project,
            ["ticket", "start", ticket_id],
            runner=planfile_runner,
        )

        if executor_kind == "api":
            result = api_runner(action, project)
            action_label = f"{action['method']} {action['endpoint']}"
        elif executor_kind == "llm":
            result = llm_runner(action, project)
            action_label = f"llm {action.get('model') or _DEFAULT_LLM_MODEL}"
        else:
            result = shell_runner(str(action), project)
            action_label = str(action)

        if result.returncode == 0:
            # planfile's `done` has no `--note`/`--result-json`. The full
            # stdout/stderr is preserved in QueueRunResult and persisted to
            # `.planfile/.koru/runs/` by the run-log writer.
            _planfile_command(
                project,
                ["ticket", "done", ticket_id],
                runner=planfile_runner,
            )
            status = "completed"
        else:
            # Use `block --reason` for failures (planfile has no `fail`
            # verb). The full stderr stays in QueueRunResult / run log.
            reason = (
                result.stderr[-500:].strip()
                or f"Command exited with {result.returncode}"
            )
            _planfile_command(
                project,
                ["ticket", "block", ticket_id, "--reason", f"FAIL: {reason}"],
                runner=planfile_runner,
            )
            status = "failed"

        return QueueRunResult(
            status=status,
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            message=action_label,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )


# ---------------------------------------------------------------------------
# Loop driver — drain the queue ticket by ticket
# ---------------------------------------------------------------------------

# Statuses that should NOT terminate the loop (a transient outcome for the
# current ticket, but we can still try the next one).
_LOOP_CONTINUE_STATUSES: frozenset[str] = frozenset({"completed", "failed"})

# Statuses that DO terminate the loop. ``waiting_input`` requires human
# action; ``unsupported_executor`` and ``planfile_error`` indicate
# misconfiguration; ``idle`` means the queue is drained; ``dry_run`` is a
# preview that we do not advance past.
_LOOP_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        "idle",
        "waiting_input",
        "unsupported_executor",
        "planfile_error",
        "dry_run",
        "claim_failed",
    }
)


def run_planfile_queue_loop(
    *,
    project: Path,
    actor: str = "koru-shell",
    queue_name: str | None = None,
    interactive: bool = False,
    max_iterations: int = 100,
    progress_callback: Callable[[QueueRunResult, int], None] | None = None,
    planfile_runner: Callable[[Sequence[str], Path], CommandResult] = _run_process,
    shell_runner: Callable[[str, Path], CommandResult] = _run_shell_command,
    api_runner: Callable[[dict[str, Any], Path], CommandResult] = _run_api_request,
    llm_runner: Callable[[dict[str, Any], Path], CommandResult] = _run_llm_request,
    prompt_runner: Callable[[str, str], str | None] = _default_human_prompt,
) -> QueueLoopResult:
    """Drain the planfile queue by repeatedly calling run_next_planfile_task.

    The loop terminates when the queue is idle, a ticket needs human
    input we cannot satisfy, an executor kind is unsupported, planfile
    itself errors out, or ``max_iterations`` is reached. Successful
    (``completed``) and ``failed`` tickets do not stop the loop — the
    next ticket is fetched.

    ``progress_callback`` (when provided) is invoked after each iteration
    with ``(result, iteration_number_starting_at_1)`` for live progress
    reporting.
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    completed: list[str] = []
    failed: list[str] = []
    waiting: list[str] = []
    last_status = "idle"
    last_message = ""
    iterations = 0

    for i in range(max_iterations):
        iterations = i + 1
        result = run_next_planfile_task(
            project=project,
            actor=actor,
            queue_name=queue_name,
            interactive=interactive,
            planfile_runner=planfile_runner,
            shell_runner=shell_runner,
            api_runner=api_runner,
            llm_runner=llm_runner,
            prompt_runner=prompt_runner,
        )
        if progress_callback is not None:
            progress_callback(result, iterations)

        last_status = result.status
        last_message = result.message

        if result.status == "completed" and result.ticket_id:
            completed.append(result.ticket_id)
        elif result.status == "failed" and result.ticket_id:
            failed.append(result.ticket_id)
        elif result.status == "waiting_input" and result.ticket_id:
            waiting.append(result.ticket_id)

        if result.status in _LOOP_TERMINAL_STATUSES:
            break
        if result.status not in _LOOP_CONTINUE_STATUSES:
            # Unknown / future status — terminate to be safe.
            break

    return QueueLoopResult(
        iterations=iterations,
        completed=completed,
        failed=failed,
        waiting=waiting,
        last_status=last_status,
        last_message=last_message,
    )
