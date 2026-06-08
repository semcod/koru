"""Apply NL prompts through CORU DSL dispatch."""

from __future__ import annotations

from dsl2coru.bus import dispatch

from .control import dispatch_line, is_dsl2koru_line
from .heuristic import to_dsl_lines
from .models import ApplyResult


def _execute_line(line: str, *, default_file: str | None = None) -> dict:
    if is_dsl2koru_line(line):
        return dispatch_line(line, default_project=default_file)
    return dispatch(line, default_project=default_file).to_dict()


def apply_prompt(
    text: str,
    *,
    use_llm: bool = False,
    llm_model: str = "openrouter/qwen/qwen3-coder-next",
    default_file: str | None = None,
    single_action: bool = False,
) -> ApplyResult:
    lines = to_dsl_lines(text, use_llm=use_llm, llm_model=llm_model)
    if single_action and lines:
        lines = lines[:1]
    try:
        results = [_execute_line(line, default_file=default_file) for line in lines if line.strip()]
        ok = all(item.get("ok") for item in results)
        return ApplyResult(ok=ok, prompt=text, lines=lines, results=results)
    except Exception as exc:
        return ApplyResult(ok=False, prompt=text, lines=lines, results=[], error=f"nlp2coru apply failed: {exc}")
