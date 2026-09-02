"""Canonical dispatch boundary for natural-language Koru requests."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from dsl2koru.bus import dispatch
from dsl2koru.result import DslResult

from nlp2koru.llm_backend import LLMBackend
from nlp2koru.to_dsl import to_dsl, to_dsl_lines

_DSL2KORU_VERBS = frozenset(
    {"QUERY_REPAIR_HISTORY", "QUERY_LANE_STATUS", "VALIDATE_LANE", "RESOLVE", "REPAIR_RUN"}
)


@dataclass
class ApplyResult:
    ok: bool
    prompt: str
    dsl: str = ""
    result: DslResult | None = None
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    lines: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "prompt": self.prompt,
            "dsl": self.dsl,
            "result": self.result.to_dict() if self.result else None,
            "data": self.data,
            "error": self.error,
            "lines": self.lines,
            "results": self.results,
        }


def is_dsl2koru_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and stripped.split()[0].upper() in _DSL2KORU_VERBS


def dispatch_line(line: str, *, default_project: str | None = None) -> dict[str, Any]:
    return dispatch(line, default_project=default_project).to_dict()


def _execute_line(line: str, *, default_file: str | None = None) -> dict[str, Any]:
    if is_dsl2koru_line(line):
        return dispatch_line(line, default_project=default_file)
    from dsl2coru.bus import dispatch as dispatch_compat

    return dispatch_compat(line, default_project=default_file).to_dict()


def _compat_executor() -> Callable[..., dict[str, Any]]:
    """Honor an injected legacy executor without restoring legacy behavior."""
    module = sys.modules.get("nlp2coru.apply")
    candidate = getattr(module, "_execute_line", None) if module else None
    return candidate if callable(candidate) else _execute_line


def apply_nl(
    prompt: str,
    *,
    project: str | None = None,
    use_llm: bool = False,
    llm_backend: LLMBackend | None = None,
) -> ApplyResult:
    try:
        line = to_dsl(prompt, project=project, use_llm=use_llm, llm_backend=llm_backend)
        result = dispatch(line, default_project=project)
        payload = result.to_dict()
        return ApplyResult(
            ok=result.ok,
            prompt=prompt,
            dsl=line,
            result=result,
            error=result.error,
            lines=[line],
            results=[payload],
        )
    except Exception as exc:
        return ApplyResult(ok=False, prompt=prompt, error=str(exc))


def apply_prompt(
    text: str,
    *,
    use_llm: bool = False,
    llm_model: str | None = None,
    default_file: str | None = None,
    single_action: bool = False,
) -> ApplyResult:
    """Compatibility multi-line application owned by canonical nlp2koru."""
    lines = to_dsl_lines(text, use_llm=use_llm, llm_model=llm_model)
    if single_action:
        lines = lines[:1]
    try:
        execute = _compat_executor()
        results = [execute(line, default_file=default_file) for line in lines if line.strip()]
        return ApplyResult(
            ok=all(item.get("ok") for item in results),
            prompt=text,
            dsl=lines[0] if lines else "",
            lines=lines,
            results=results,
        )
    except Exception as exc:
        return ApplyResult(
            ok=False,
            prompt=text,
            dsl=lines[0] if lines else "",
            error=f"nlp2koru apply failed: {exc}",
            lines=lines,
        )
