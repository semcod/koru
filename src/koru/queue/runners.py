"""Process execution runners for different executor types."""


import json
import os
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
    return {**os.environ, "COLUMNS": "10000", "TERM": "dumb", "PYTHONWARNINGS": "ignore"}


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
    return subprocess.run(
        command,
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
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
    return subprocess.run(
        command,
        cwd=project,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
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


def _build_llm_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    """Build messages list from request."""
    messages: list[dict[str, str]] = []
    system = request.get("system_prompt")
    if system:
        messages.append({"role": "system", "content": str(system)})
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


def run_llm_request(request: dict[str, Any], _project: Path) -> LlmRunResult:
    """Call an OpenAI-compatible chat-completion endpoint (default OpenRouter).

    Reads ``OPENROUTER_API_KEY`` from the environment when ``endpoint``
    points at openrouter.ai; falls back to ``OPENAI_API_KEY`` for the
    OpenAI endpoint. Honours ``KORU_LLM_ENDPOINT`` for self-hosted
    proxies (e.g. an Ollama OpenAI-compat shim).
    """
    model = str(request.get("model") or _DEFAULT_LLM_MODEL)
    endpoint, api_key, key_var = _resolve_llm_endpoint_and_key(request)

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
