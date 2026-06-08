"""NL intent models used by nlp2coru."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CoruIntent:
    action: str
    ide: str | None = None
    instance: str | None = None
    install: bool = False
    auto_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoruPlan:
    steps: list[CoruIntent] = field(default_factory=list)
    use_llm: bool = False


@dataclass(frozen=True)
class ApplyResult:
    ok: bool
    prompt: str
    lines: list[str]
    results: list[dict]
    error: str | None = None
