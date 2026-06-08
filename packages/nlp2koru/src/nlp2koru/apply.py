"""Apply NL via to_dsl + dsl2koru.dispatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dsl2koru.bus import dispatch
from dsl2koru.result import DslResult
from nlp2koru.llm_backend import LLMBackend
from nlp2koru.to_dsl import to_dsl


@dataclass
class ApplyResult:
    ok: bool
    prompt: str
    dsl: str = ""
    result: DslResult | None = None
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "prompt": self.prompt,
            "dsl": self.dsl,
            "result": self.result.to_dict() if self.result else None,
            "data": self.data,
            "error": self.error,
        }


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
        return ApplyResult(ok=result.ok, prompt=prompt, dsl=line, result=result, error=result.error)
    except Exception as exc:
        return ApplyResult(ok=False, prompt=prompt, error=str(exc))
