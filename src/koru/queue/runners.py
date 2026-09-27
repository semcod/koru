"""Process execution runners for different executor types."""

import codecs
import json
import locale
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import parse_qs, urlparse

from koru.control_commands import api_command, shell_command
from koru.queue.types import ApiRunResult, LlmRunResult, TaskandRunResult
from korullm import probe_subllm_route, run_subllm_messages


def _planfile_env() -> dict[str, str]:
    """Force a wide, non-TTY console so planfile's Rich output stays one
    JSON object per line. Without this, long handler strings get wrapped
    by Rich and break json.loads on the koru side."""
    return {
        **os.environ,
        "COLUMNS": "10000",
        "TERM": "dumb",
        "PYTHONWARNINGS": "ignore",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }


def _decode_subprocess_output(data: bytes | str | None) -> str:
    """Decode subprocess output without crashing on mixed Windows code pages."""
    if data is None:
        return ""
    if isinstance(data, str):
        return data

    seen: set[str] = set()
    candidates: list[str] = []
    for encoding in ("utf-8", locale.getpreferredencoding(False)):
        try:
            normalized = codecs.lookup(encoding).name
        except LookupError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(normalized)
        try:
            return data.decode(normalized)
        except UnicodeDecodeError:
            continue
    fallback = candidates[-1] if candidates else "utf-8"
    return data.decode(fallback, errors="replace")


def _run_captured_subprocess(
    command: list[str] | str,
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    shell: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and decode captured streams robustly.

    ``command`` is usually ``list[str]`` for direct execution and ``str`` for
    ``shell=True`` calls.
    """
    result = subprocess.run(
        command,
        cwd=cwd,
        text=False,
        capture_output=True,
        check=False,
        env=env,
        shell=shell,
    )
    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        _decode_subprocess_output(result.stdout),
        _decode_subprocess_output(result.stderr),
    )


def _control_corr(prefix: str) -> str:
    return f"{prefix}-{time.monotonic_ns():x}"


def run_process(command: list[str], project: Path) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with planfile-friendly environment."""
    shell_command(
        project,
        corr=_control_corr("process"),
        argv=command,
        actor="planfile-runner",
    )
    return _run_captured_subprocess(
        command,
        cwd=project,
        env=_planfile_env(),
    )


def run_shell_command(command: str, project: Path) -> subprocess.CompletedProcess[str]:
    """Run a shell command."""
    shell_command(
        project,
        corr=_control_corr("shell"),
        argv=["sh", "-lc", command],
        actor="planfile-runner",
    )
    return _run_captured_subprocess(
        command,
        cwd=project,
        shell=True,
    )


def run_api_request(request: dict[str, Any], _project: Path) -> ApiRunResult:
    """Execute an HTTP API request."""
    body = request.get("body")
    data: bytes | None = None
    headers = {str(k): str(v) for k, v in (request.get("headers") or {}).items()}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers.setdefault("content-type", "application/json")

    endpoint = str(request["endpoint"])
    parsed = urlparse(endpoint)
    query = {
        key: values[-1] if len(values) == 1 else values
        for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
    }
    api_command(
        _project,
        corr=_control_corr("api"),
        method=str(request.get("method") or "GET"),
        path=endpoint,
        query=query,
        body=body if isinstance(body, dict) else None,
        headers=headers,
        actor="planfile-runner",
        interface_id="queue_api_request",
    )

    api_request = urllib.request.Request(
        endpoint,
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


_DEFAULT_LLM_MODEL = "cursor/grok-4.6"


# Vendor CLIs koru can drive headlessly through tillm, mapped to the binary
# that must be on PATH. These run against the operator's existing CLI login
# (e.g. ~/.claude/.credentials.json), so they need no API key.
_SHELL_LLM_CLIENT_COMMANDS: dict[str, str] = {
    "claude-code": "claude",
    "aider": "aider",
    "codex": "codex",
    "cline": "cline",
    "gemini-cli": "gemini",
    "opencode": "opencode",
    "qwen-code": "qwen",
}

# "Use a vendor CLI, pick it from KORU_TILLM_CLIENT" rather than naming one.
_SHELL_LLM_GENERIC_PROVIDERS = frozenset(
    {"shell", "tillm", "vendor_cli", "vendor_agent_cli"},
)

_SHELL_LLM_PROVIDER_ALIASES: dict[str, str] = {
    "claude": "claude-code",
    "anthropic": "claude-code",
    "gemini": "gemini-cli",
    "qwen": "qwen-code",
}


def _shell_llm_truthy(raw: str | None, *, default: bool) -> bool:
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_shell_llm_client(raw: str) -> str | None:
    """Map a provider token onto a tillm shell-client id."""
    provider_id = raw.strip().lower()
    if not provider_id:
        return None
    if provider_id in _SHELL_LLM_GENERIC_PROVIDERS:
        return (os.getenv("KORU_TILLM_CLIENT") or "claude-code").strip() or "claude-code"
    provider_id = _SHELL_LLM_PROVIDER_ALIASES.get(provider_id, provider_id)
    return provider_id if provider_id in _SHELL_LLM_CLIENT_COMMANDS else None


def _resolve_shell_llm_client(request: dict[str, Any]) -> str | None:
    """Resolve an explicitly requested vendor CLI for this ticket, if any.

    Ticket-level ``inputs.provider`` wins over the ``KORU_LLM_PROVIDER``
    environment default. Returns ``None`` when neither selects a vendor CLI,
    which leaves the HTTP chat-completion path in charge.
    """
    for candidate in (request.get("provider"), os.getenv("KORU_LLM_PROVIDER")):
        if not candidate:
            continue
        client_id = _normalize_shell_llm_client(str(candidate))
        if client_id:
            return client_id
    return None


def _autodetect_shell_llm_client() -> str | None:
    """Find an installed vendor CLI to use when no API key is configured.

    This is what keeps ``executor.kind=llm`` tickets runnable on a workstation
    that has a logged-in agent CLI but no OpenRouter/OpenAI key. Set
    ``KORU_LLM_SHELL_FALLBACK=0`` to keep the hard failure instead.
    """
    if not _shell_llm_truthy(os.getenv("KORU_LLM_SHELL_FALLBACK"), default=True):
        return None
    preferred = (os.getenv("KORU_TILLM_CLIENT") or "").strip().lower()
    ordered = [preferred] if preferred in _SHELL_LLM_CLIENT_COMMANDS else []
    ordered += [c for c in _SHELL_LLM_CLIENT_COMMANDS if c not in ordered]
    for client_id in ordered:
        if shutil.which(_SHELL_LLM_CLIENT_COMMANDS[client_id]):
            return client_id
    return None


def _as_text(value: object) -> str:
    """Decode a vendor CLI stream to text.

    tillm may hand back raw bytes; ``str()`` on those yields a ``b'...'`` repr
    that ends up verbatim in the ticket's block reason, so decode explicitly.
    """
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def _flatten_llm_messages(messages: list[dict[str, str]]) -> str:
    """Collapse chat messages into the single prompt a vendor CLI accepts."""
    parts: list[str] = []
    for message in messages:
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        role = str(message.get("role") or "user")
        parts.append(content if role == "user" else f"[{role}]\n{content}")
    return "\n\n".join(parts)


def _resolve_shell_llm_call_args(request: dict[str, Any]) -> tuple[str, str, str, float]:
    """Resolve the prompt, model, execute profile, and timeout for a vendor CLI call."""
    prompt = _flatten_llm_messages(_build_llm_messages(request))
    model = str(request.get("model") or os.getenv("KORU_TILLM_MODEL") or "").strip()
    profile = (os.getenv("KORU_TILLM_EXECUTE_PROFILE") or "default").strip() or "default"
    # An agent CLI editing real code routinely runs for many minutes, so the
    # HTTP-scale default does not apply here. Explicit per-ticket timeouts win.
    timeout = request.get("timeout_seconds") or os.getenv("KORU_LLM_SHELL_TIMEOUT_SECONDS") or 1800.0
    return prompt, model, profile, float(timeout)


def _shell_llm_error_result(client_id: str, model: str, exc: Exception) -> LlmRunResult:
    """Build the blocked-ticket result for a failed vendor CLI invocation."""
    return LlmRunResult(
        returncode=1,
        stdout="",
        stderr=f"vendor CLI '{client_id}' failed: {exc}",
        status_code=0,
        model=model or client_id,
        usage={},
        raw={},
    )


def _parse_shell_llm_reply(reply: dict[str, Any], model: str, client_id: str) -> LlmRunResult:
    """Translate a tillm bridge reply into an LlmRunResult."""
    exit_code = int(reply.get("exit_code") or 0)
    succeeded = bool(reply.get("ok")) and exit_code == 0
    return LlmRunResult(
        returncode=0 if succeeded else (exit_code or 1),
        stdout=_as_text(reply.get("stdout")),
        stderr=_as_text(reply.get("stderr")),
        status_code=0,
        model=model or client_id,
        usage={},
        raw=dict(reply),
    )


def run_shell_llm_request(
    request: dict[str, Any],
    project: Path,
    client_id: str,
) -> LlmRunResult:
    """Run an LLM ticket through a local vendor CLI instead of an HTTP API.

    Reuses the same tillm bridge as the autopilot drive lane, so the ticket
    executes headlessly against the operator's existing CLI login.
    """
    from koru.task_model_policy import drive_with_model_policy
    from koru.tillm_bridge import drive_shell_chat

    prompt, model, profile, timeout = _resolve_shell_llm_call_args(request)
    try:
        reply = drive_with_model_policy(
            drive_shell_chat,
            task=request.get("task"),
            explicit_model=str(request.get("model") or ""),
            client_id=client_id,
            project=project,
            prompt=prompt,
            execute=True,
            model=model or None,
            execute_profile=profile,
            timeout_seconds=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - surface any bridge failure as a blocked ticket
        return _shell_llm_error_result(client_id, model, exc)

    selected_model = (reply.get("model_routing") or {}).get("requested_model", model)
    return _parse_shell_llm_reply(reply, selected_model, client_id)


def _build_llm_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    """Build messages list from request."""
    messages: list[dict[str, str]] = []
    system = request.get("system_prompt")
    if system:
        messages.append({"role": "system", "content": str(system)})

    context_text = request.get("context_text")
    if context_text:
        context_metadata = request.get("context_metadata") or {}
        included = context_metadata.get("included_files") or []
        truncated = context_metadata.get("truncated", False)
        meta_lines = []
        if included:
            meta_lines.append(f"Included files: {', '.join(included)}")
        if truncated:
            total = context_metadata.get("total_chars", 0)
            shown_chars = len(context_text)
            meta_lines.append(f"[Context truncated: showing {shown_chars} of {total} chars]")
        meta_note = ("\n" + "\n".join(meta_lines)) if meta_lines else ""
        context_block = f"<project_context>{meta_note}\n\n{context_text}\n</project_context>"
        messages.append({"role": "user", "content": context_block})

    messages.append({"role": "user", "content": str(request["prompt"])})
    return messages


def _build_llm_request_body(
    request: dict[str, Any],
    model: str,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """Build request body for LLM API."""
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": float(request.get("temperature", 0.0)),
    }
    schema = request.get("response_schema")
    if schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "koru_response", "schema": schema, "strict": True},
        }
    return body


def _parse_llm_response(
    response: Any,
    model: str,
) -> LlmRunResult:
    """Parse successful LLM response."""
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


def _handle_llm_error(exc: urllib.error.HTTPError | urllib.error.URLError, model: str) -> LlmRunResult:
    """Handle LLM API errors."""
    if isinstance(exc, urllib.error.HTTPError):
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
    else:
        return LlmRunResult(
            returncode=1,
            stdout="",
            stderr=str(exc.reason),
            status_code=0,
            model=model,
            usage={},
            raw={},
        )


def _normalize_llm_model(model: str, endpoint: str) -> str:
    """Strip registry prefixes before calling OpenRouter-compatible endpoints."""
    normalized = model.strip()
    if "openrouter.ai" in endpoint and normalized.startswith("openrouter/"):
        return normalized.split("/", 1)[1]
    return normalized


def run_llm_request(request: dict[str, Any], project: Path) -> LlmRunResult:
    """Run an LLM ticket through the centrally configured SubLLM route."""
    messages = _build_llm_messages(request)
    timeout = request.get("timeout_seconds")
    result = run_subllm_messages(
        messages,
        project,
        route_function="queue-executor",
        timeout_seconds=float(timeout) if timeout is not None else 1800.0,
    )
    return LlmRunResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        status_code=0,
        model=result.model,
        usage=result.usage,
        raw=result.raw,
    )


def preflight_llm_request(project: Path) -> tuple[bool, str]:
    """Probe Koru's central queue route without invoking a model."""
    return probe_subllm_route(project, route_function="queue-executor")


def _find_taskand_cli(project: Path) -> Path | None:
    """Find a usable taskand CLI binary."""
    env_bin = os.getenv("TASKAND_BIN")
    if env_bin:
        p = Path(env_bin)
        if p.is_file() and os.access(p, os.X_OK):
            return p
    which_bin = shutil.which("taskand")
    if which_bin:
        return Path(which_bin)
    candidates = [
        Path("/home/tom/github/paxlet-com/taskand/bin/taskand"),
        project.parent / "paxlet-com" / "taskand" / "bin" / "taskand",
        project.parent / "taskand" / "bin" / "taskand",
        project / "bin" / "taskand",
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _find_twinerd_cli() -> Path | None:
    """Find a usable twinerd CLI binary."""
    env_bin = os.getenv("TWINERD_BIN")
    if env_bin:
        p = Path(env_bin)
        if p.is_file() and os.access(p, os.X_OK):
            return p
    which_bin = shutil.which("twinerd")
    if which_bin:
        return Path(which_bin)
    candidate = Path("/home/tom/.local/bin/twinerd")
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate
    return None


def create_twinerd_sandbox(
    source_project: Path,
    name: str = "twin-sandbox",
    target_base: Path | None = None,
    cli_bin: Path | None = None,
) -> dict[str, Any] | None:
    """Create a zero-copy digital twin sandbox via Twinerd."""
    binary = cli_bin or _find_twinerd_cli()
    if not binary:
        return None
    target_dir = target_base or Path("/tmp/twinerd-sandboxes")
    cmd = [
        str(binary),
        "create",
        "--name",
        name,
        "--source",
        str(source_project),
        "--target",
        str(target_dir),
        "--driver",
        "auto",
        "--json",
    ]
    proc = _run_captured_subprocess(cmd, cwd=source_project)
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
        return data if isinstance(data, dict) and data.get("status") == "ok" else None
    except json.JSONDecodeError:
        return None


class _TaskandGatewayConfig(NamedTuple):
    """Resolved gateway endpoint settings for a Taskand call."""

    url: str
    timeout_seconds: float
    headers: dict[str, str]


class _TaskandReplyContext(NamedTuple):
    """Gateway reply fields shared by the Taskand result mappers."""

    payload: Any
    result_field: Any
    text: str
    status_code: int
    uri: Any


class _TaskandGatewayTarget(NamedTuple):
    """Resolved gateway endpoint and request body for one Taskand call."""

    endpoint: str
    body: dict[str, Any]


def _taskand_gateway_config(request: dict[str, Any]) -> _TaskandGatewayConfig:
    """Resolve gateway URL, timeout and auth headers for a Taskand call."""
    gateway_url = str(
        request.get("gateway_url")
        or os.getenv("TASKAND_GATEWAY_URL")
        or os.getenv("TASKAND_GATEWAY")
        or "http://127.0.0.1:8077"
    ).rstrip("/")
    timeout_seconds = float(request.get("timeout_seconds") or 60.0)
    auth_token = os.getenv("TASKAND_AUTH_TOKEN") or "taskand-admin-key"
    return _TaskandGatewayConfig(
        url=gateway_url,
        timeout_seconds=timeout_seconds,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )


def _probe_taskand_gateway(gateway_url: str) -> bool:
    """Return True when the Taskand gateway answers its health probe."""
    try:
        health_req = urllib.request.Request(f"{gateway_url}/healthz", method="GET")
        with urllib.request.urlopen(health_req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _normalize_step_id(s: dict[str, Any], idx: int) -> int:
    val = s.get("id")
    if isinstance(val, int):
        return val
    try:
        return int(val if val is not None else idx)
    except (ValueError, TypeError):
        return idx


def _normalize_step_name(s: dict[str, Any], step_id: int) -> str:
    name = s.get("name")
    return str(name) if name else f"step_{step_id}"


def _resolve_step_process(s: dict[str, Any]) -> str | None:
    if "process" not in s and "uri" in s:
        return str(s["uri"])
    if "process" in s and s["process"]:
        return str(s["process"])
    return None


def _normalize_step_deps(s: dict[str, Any]) -> list[Any]:
    if "deps" in s and isinstance(s["deps"], list):
        return s["deps"]
    raw_deps = s.get("deps")
    if isinstance(raw_deps, (list, tuple)):
        return [str(d) for d in raw_deps]
    if raw_deps:
        return [str(raw_deps)]
    return []


def _normalize_step_params(s: dict[str, Any]) -> dict[str, Any]:
    if "params" in s:
        return s["params"]
    for key in ("input", "inputs", "data"):
        val = s.get(key)
        if isinstance(val, dict):
            return val
    return {}


def _normalize_step(step: Any, idx: int) -> dict[str, Any] | None:
    """Normalize a single DAG step dictionary to Taskand orchestrator contract."""
    if not isinstance(step, dict):
        return None
    s = dict(step)
    step_id = _normalize_step_id(s, idx)
    s["id"] = step_id
    s["name"] = _normalize_step_name(s, step_id)
    proc = _resolve_step_process(s)
    if proc is not None:
        s["process"] = proc
    s["deps"] = _normalize_step_deps(s)
    s["params"] = _normalize_step_params(s)
    return s


def normalize_taskand_plan(plan: Any) -> dict[str, Any]:
    """Normalize a DAG plan to match Taskand orchestrator/validator expectations."""
    if not isinstance(plan, dict):
        return {"steps": []}
    steps = plan.get("steps")
    if not isinstance(steps, list):
        return plan
    normalized_steps: list[dict[str, Any]] = []
    for idx, raw_step in enumerate(steps, start=1):
        norm = _normalize_step(raw_step, idx)
        if norm is not None:
            normalized_steps.append(norm)
    res = dict(plan)
    res["steps"] = normalized_steps
    return res


def _taskand_gateway_target(
    request: dict[str, Any],
    gateway_url: str,
    timeout_seconds: float,
    uri: Any,
    data: dict[str, Any],
) -> _TaskandGatewayTarget | None:
    """Resolve the gateway endpoint and request body for plan/proc-call modes.

    Returns ``None`` when the request carries neither a plan nor a uri.
    """
    plan = request.get("plan")
    if plan:
        body: dict[str, Any] = {"plan": normalize_taskand_plan(plan)}
        if request.get("run_id"):
            body["runId"] = request["run_id"]
        return _TaskandGatewayTarget(f"{gateway_url}/api/orchestrator", body)
    if uri:
        return _TaskandGatewayTarget(
            f"{gateway_url}/api/proc/call",
            {"uri": uri, "data": data, "timeout": int(timeout_seconds)},
        )
    return None


def _orchestrator_taskand_result(reply: _TaskandReplyContext) -> TaskandRunResult:
    """Map an orchestrator reply whose result carries a run status."""
    result = reply.result_field
    orch_status = str(result.get("status") or "")
    succeeded = orch_status == "SUCCEEDED"
    return TaskandRunResult(
        returncode=0 if succeeded else 1,
        stdout=reply.text,
        stderr="" if succeeded else f"Orchestrator finished with status: {orch_status}",
        status_code=reply.status_code,
        uri=reply.uri or "proc://taskand.dev/orchestrator/execute/v1",
        run_id=result.get("runId"),
        data=result,
        raw=reply.payload,
    )


def _proc_call_taskand_result(reply: _TaskandReplyContext) -> TaskandRunResult:
    """Map a plain proc-call reply without an orchestrator run status."""
    payload = reply.payload
    result = reply.result_field
    ok = payload.get("ok") if isinstance(payload, dict) else True
    succeeded = bool(ok) and (not isinstance(result, dict) or result.get("ok") is not False)
    return TaskandRunResult(
        returncode=0 if succeeded else 1,
        stdout=reply.text,
        stderr="" if succeeded else str(payload.get("error") or "Process failed"),
        status_code=reply.status_code,
        uri=reply.uri or "",
        run_id=payload.get("requestId") if isinstance(payload, dict) else None,
        data=result if isinstance(result, dict) else None,
        raw=payload,
    )


def _parse_taskand_gateway_payload(
    payload: Any,
    text: str,
    status_code: int,
    uri: Any,
) -> TaskandRunResult:
    """Parse a gateway JSON payload into a TaskandRunResult."""
    result_field = payload.get("result") if isinstance(payload, dict) else payload
    reply = _TaskandReplyContext(payload, result_field, text, status_code, uri)
    if isinstance(result_field, dict) and "status" in result_field:
        return _orchestrator_taskand_result(reply)
    return _proc_call_taskand_result(reply)


def _read_taskand_reply(response: Any, uri: Any) -> TaskandRunResult:
    """Read a gateway response body and map the JSON payload to a result."""
    text = response.read().decode("utf-8", errors="replace")
    payload = json.loads(text) if text else {}
    return _parse_taskand_gateway_payload(payload, text, int(response.status), uri)


def _taskand_http_error_result(exc: urllib.error.HTTPError, uri: Any) -> TaskandRunResult:
    """Map an HTTP error response from the gateway to a failed result."""
    text = exc.read().decode("utf-8", errors="replace")
    return TaskandRunResult(
        returncode=1,
        stdout=text,
        stderr=f"HTTP {exc.code}: {text[:500]}",
        status_code=int(exc.code),
        uri=uri or "",
    )


def _taskand_url_error_result(exc: urllib.error.URLError, uri: Any) -> TaskandRunResult:
    """Map a transport-level failure to reach the gateway to a failed result."""
    return TaskandRunResult(
        returncode=1,
        stdout="",
        stderr=f"Taskand request failed: {exc.reason}",
        status_code=0,
        uri=uri or "",
    )


def _post_taskand_gateway(
    endpoint: str,
    body: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
    uri: Any,
) -> TaskandRunResult:
    """POST to the Taskand gateway and map the reply or error to a result."""
    post_data = json.dumps(body).encode("utf-8")
    api_req = urllib.request.Request(endpoint, data=post_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(api_req, timeout=timeout_seconds) as response:
            return _read_taskand_reply(response, uri)
    except urllib.error.HTTPError as exc:
        return _taskand_http_error_result(exc, uri)
    except urllib.error.URLError as exc:
        return _taskand_url_error_result(exc, uri)


def _run_taskand_cli_call(
    cli_bin: Path,
    uri: str,
    data: dict[str, Any],
    project: Path,
) -> TaskandRunResult:
    """Invoke the local Taskand CLI for a proc call."""
    cmd = [str(cli_bin), "call", uri, json.dumps(data), "--json"]
    proc = _run_captured_subprocess(cmd, cwd=project)
    try:
        parsed = json.loads(proc.stdout) if proc.stdout else {}
        succeeded = proc.returncode == 0 and parsed.get("ok") is not False
        return TaskandRunResult(
            returncode=0 if succeeded else (proc.returncode or 1),
            stdout=proc.stdout,
            stderr=proc.stderr if proc.returncode != 0 else str(parsed.get("error") or ""),
            status_code=200 if succeeded else 500,
            uri=uri,
            run_id=parsed.get("requestId"),
            data=parsed,
            raw=parsed,
        )
    except json.JSONDecodeError:
        return TaskandRunResult(
            returncode=proc.returncode or 1,
            stdout=proc.stdout,
            stderr=proc.stderr or "Invalid JSON output from taskand CLI",
            status_code=500,
            uri=uri,
        )


def _resolve_sandbox_project(
    project: Path,
    request: dict[str, Any],
) -> tuple[Path, dict[str, Any] | None]:
    """Resolve project directory inside a Twinerd sandbox if requested."""
    sandbox_kind = str(request.get("sandbox") or "").strip().lower()
    if sandbox_kind != "twinerd":
        return project, None
    twin_name = str(request.get("twin_name") or f"twin-{project.name}")
    twin_info = create_twinerd_sandbox(project, name=twin_name)
    if twin_info and twin_info.get("mount_point"):
        return Path(str(twin_info["mount_point"])), twin_info
    return project, twin_info


def run_taskand_request(request: dict[str, Any], project: Path) -> TaskandRunResult:
    """Execute a task using Taskand process framework (via Gateway HTTP or local CLI)."""
    target_project, _twin_info = _resolve_sandbox_project(project, request)
    config = _taskand_gateway_config(request)
    uri = request.get("uri")
    data = request.get("data") or {}

    if _probe_taskand_gateway(config.url):
        target = _taskand_gateway_target(request, config.url, config.timeout_seconds, uri, data)
        if target is None:
            return TaskandRunResult(
                returncode=1,
                stdout="",
                stderr="Missing uri or plan in taskand request",
                status_code=400,
                uri="",
            )
        return _post_taskand_gateway(target.endpoint, target.body, config.headers, config.timeout_seconds, uri)

    # Fallback to local CLI invocation
    cli_bin = _find_taskand_cli(target_project)
    if cli_bin and uri:
        return _run_taskand_cli_call(cli_bin, uri, data, target_project)

    return TaskandRunResult(
        returncode=1,
        stdout="",
        stderr=f"Taskand gateway unavailable at {config.url} and no local taskand CLI found",
        status_code=503,
        uri=uri or "",
    )
