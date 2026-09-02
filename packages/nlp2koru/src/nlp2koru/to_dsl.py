"""Canonical natural-language to dsl2koru translation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from uri2koru.nlp2uri import best_uri

from nlp2koru.llm_backend import LLMBackend, nl_to_dsl_line

_REFACTOR_MARKERS = ("refactor", "refaktoryz", "refakotryz")
_SETUP_ACTIONS = {
    "auto",
    "calibration",
    "chat",
    "doctor",
    "ensure",
    "lane",
    "manage",
    "status",
    "sync",
}


@dataclass(frozen=True)
class KoruIntent:
    """One deterministic Koru control intent."""

    action: str
    ide: str | None = None
    instance: str | None = None
    install: bool = False
    auto_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class KoruPlan:
    """A bounded sequence of Koru control intents."""

    steps: list[KoruIntent] = field(default_factory=list)
    use_llm: bool = False


def _refactor_intent(text: str) -> bool:
    lower = text.strip().lower()
    return any(marker in lower for marker in _REFACTOR_MARKERS) or bool(re.search(r"refak\w*ryz", lower))


def detect_setup_intent(text: str) -> bool:
    lower = text.strip().lower()
    return any(key in lower for key in ("setup", "prepare", "przygotuj", "start", "uruchom", "rund", "autopilot"))


def _parse_lane_mentions(text: str) -> tuple[str | None, str | None]:
    ide = None
    instance = None
    ide_match = re.search(r"\b(vscode|vscodium|cursor|windsurf|jetbrains|zed|antigravity)\b", text, re.IGNORECASE)
    if ide_match:
        ide = ide_match.group(1).lower()
    instance_match = re.search(r"\b([a-z0-9_-]+-(main|a|b|lane|prod|dev))\b", text, re.IGNORECASE)
    if instance_match:
        instance = instance_match.group(1).lower()
    return ide, instance


def _contains_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _resolve_heuristic_action(lower: str, text: str) -> tuple[str, bool]:
    if _contains_any(lower, "ensure", "zainstal", "install", "napraw", "sprawdz"):
        return "ensure", True
    if _contains_any(lower, "calibration") or "kalibrac" in lower:
        return "calibration", False
    if _contains_any(lower, "doctor", "diagnost"):
        return "doctor", False
    if _contains_any(lower, "lane", "instanc", "ustaw"):
        return "lane", False
    if _contains_any(lower, "sync", "synchroniz", "syncuj"):
        return "sync", False
    if _refactor_intent(text):
        return "auto", False
    if _contains_any(lower, "status", "stan"):
        return "status", False
    if _contains_any(lower, "chat", "wyslij", "wyślij"):
        return "chat", False
    if _contains_any(lower, "auto", "autonomous", "autopilot", "run", "execute"):
        return "auto", False
    return "status", False


def heuristic_plan(text: str) -> KoruPlan:
    lower = text.strip().lower()
    ide, instance = _parse_lane_mentions(lower)
    action, install = _resolve_heuristic_action(lower, text)
    return KoruPlan([KoruIntent(action=action, ide=ide, instance=instance, install=install)])


def _intent_line(intent: KoruIntent, text: str) -> str:
    action = intent.action.lower()
    if action == "ensure":
        return "ENSURE" + (" --install" if intent.install else "")
    if action == "lane":
        pieces = ["LANE"]
        if intent.ide:
            pieces.extend(["--ide", intent.ide])
        if intent.instance:
            pieces.extend(["--instance", intent.instance])
        return " ".join(pieces)
    if action in {"status", "doctor", "calibration", "sync"}:
        return action.upper()
    if action == "chat":
        return f"CHAT --text {text.strip()!r}".replace("\\'", "'")
    if action == "auto":
        return "AUTO"
    if action == "manage":
        return "DIAGNOSE"
    return f"TEXT {text!r}"


def to_dsl_lines(
    text: str,
    *,
    use_llm: bool = False,
    llm_model: str | None = None,
) -> list[str]:
    if use_llm:
        from nlp2koru.llm_backend import llm_plan

        plan = llm_plan(text, model=llm_model)
    else:
        plan = heuristic_plan(text)

    if not plan.steps:
        return ["STATUS"]

    first = plan.steps[0]
    wants_setup = _refactor_intent(text) or detect_setup_intent(text)
    if first.action in _SETUP_ACTIONS and wants_setup:
        lane = "LANE" + (f" --ide {first.ide}" if first.ide else "")
        lane += f" --instance {first.instance}" if first.instance else ""
        return ["ENSURE --install", lane, "DOCTOR", "DIAGNOSE", "AUTO"]

    lines: list[str] = []
    for step in plan.steps:
        lines.append(_intent_line(step, text))
        if step.action == "chat":
            break
    return lines or ["STATUS"]


def to_dsl(
    prompt: str,
    *,
    project: str | None = None,
    default_file: str | None = None,
    use_llm: bool = False,
    llm_backend: LLMBackend | None = None,
    llm_model: str | None = None,
) -> str:
    """Return one canonical DSL line without dispatching it."""
    context = default_file or project
    if use_llm:
        llm_line = nl_to_dsl_line(prompt, project=context, model=llm_model, backend=llm_backend)
        if llm_line:
            return llm_line

    hit = best_uri(prompt, project=context)
    if hit and hit.dsl:
        return hit.dsl

    normalized = prompt.strip()
    if normalized.lower().startswith(("query_repair", "repair_run", "validate_lane", "resolve")):
        return normalized

    lines = to_dsl_lines(prompt)
    if lines:
        return lines[0]
    raise ValueError(f"could not map NL to DSL: {prompt!r}")


def workflow_from_nl(prompt: str) -> dict[str, Any]:
    """Bridge to nlpshim for desktop workflow steps without dispatch."""
    from nlpshim.client import NLPBridgeClient, analyze_text_structure

    structure = analyze_text_structure(prompt, include_plan=True)
    steps = NLPBridgeClient().parse_intent(prompt, execute=False)
    payload: dict[str, Any] = {"steps": steps}
    if structure is not None:
        payload["structure"] = structure
    return payload
