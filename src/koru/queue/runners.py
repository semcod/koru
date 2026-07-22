"""Process execution runners for different executor types."""


import codecs
import json
import locale
import os
import shutil
import subprocess
import time
import urllib.error
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from koru.control_commands import api_command, shell_command
from koru.queue.types import ApiRunResult, LlmRunResult


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


_DEFAULT_LLM_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"


def _resolve_llm_endpoint_and_key(
    request: dict[str, Any],
) -> tuple[str, str, str]:
    """Resolve endpoint, API key, and key variable name."""
    endpoint = str(
        request.get("endpoint") or os.getenv("KORU_LLM_ENDPOINT") or _DEFAULT_LLM_ENDPOINT,
    )
    if "openrouter.ai" in endpoint:
        api_key = os.getenv("OPENROUTER_API_KEY")
        key_var = "OPENROUTER_API_KEY"
    else:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        key_var = "OPENAI_API_KEY"
    return endpoint, api_key, key_var


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
    token = raw.strip().lower()
    if not token:
        return None
    if token in _SHELL_LLM_GENERIC_PROVIDERS:
        return (os.getenv("KORU_TILLM_CLIENT") or "claude-code").strip() or "claude-code"
    token = _SHELL_LLM_PROVIDER_ALIASES.get(token, token)
    return token if token in _SHELL_LLM_CLIENT_COMMANDS else None


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
    from koru.tillm_bridge import drive_shell_chat

    prompt, model, profile, timeout = _resolve_shell_llm_call_args(request)
    try:
        reply = drive_shell_chat(
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

    return _parse_shell_llm_reply(reply, model, client_id)


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
        context_block = (
            f"<project_context>{meta_note}\n\n{context_text}\n</project_context>"
        )
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
    if request.get("max_tokens") is not None:
        body["max_tokens"] = int(request["max_tokens"])
    schema = request.get("response_schema")
    if schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "koru_response", "schema": schema, "strict": True},
        }
    return body


def _build_llm_headers(endpoint: str, api_key: str) -> dict[str, str]:
    """Build request headers for LLM API."""
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
    return headers


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


def _handle_llm_error(
    exc: urllib.error.HTTPError | urllib.error.URLError, model: str
) -> LlmRunResult:
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
    """Run an LLM ticket, via a local vendor CLI or an HTTP chat-completion API.

    A vendor CLI (``claude-code``, ``aider``, …) is used when the ticket's
    ``inputs.provider`` or ``KORU_LLM_PROVIDER`` names one, and — because a
    logged-in CLI is a perfectly good executor — as an automatic fallback when
    no API key is configured. Otherwise this calls an OpenAI-compatible
    endpoint, reading ``OPENROUTER_API_KEY`` when ``endpoint`` points at
    openrouter.ai and ``OPENAI_API_KEY`` otherwise. Honours
    ``KORU_LLM_ENDPOINT`` for self-hosted proxies (e.g. an Ollama shim).
    """
    endpoint, api_key, key_var = _resolve_llm_endpoint_and_key(request)
    model = _normalize_llm_model(
        str(request.get("model") or os.getenv("LLM_MODEL") or _DEFAULT_LLM_MODEL),
        endpoint,
    )

    requested_client = _resolve_shell_llm_client(request)
    if requested_client:
        return run_shell_llm_request(request, project, requested_client)

    if not api_key:
        fallback_client = _autodetect_shell_llm_client()
        if fallback_client:
            return run_shell_llm_request(request, project, fallback_client)
        return LlmRunResult(
            returncode=1,
            stdout="",
            stderr=(
                f"{key_var} is not set — refusing to call {endpoint}, "
                "and no vendor agent CLI (claude, aider, codex, …) was found "
                "on PATH to run this ticket locally. Export the key (e.g. via "
                ".env), install/log in to an agent CLI, "
                "or use executor.kind=human for this ticket."
            ),
            status_code=0,
            model=model,
            usage={},
            raw={},
        )

    messages = _build_llm_messages(request)
    body = _build_llm_request_body(request, model, messages)
    headers = _build_llm_headers(endpoint, api_key)

    api_request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    timeout = float(request.get("timeout_seconds") or 60.0)

    try:
        with urllib.request.urlopen(api_request, timeout=timeout) as response:
            return _parse_llm_response(response, model)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        return _handle_llm_error(exc, model)
