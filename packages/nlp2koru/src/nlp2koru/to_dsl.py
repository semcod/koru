"""Canonical natural-language to dsl2koru translation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from uri2koru.nlp2uri import best_uri

if TYPE_CHECKING:
    from nlp2koru.llm_backend import LLMBackend

_REFACTOR_PATTERN = r"refactor|refak\w*ryz"
_ACTION_RULES = (
    (r"ensure|zainstal|install|napraw|sprawdz", "ensure", True),
    (r"calibration|kalibrac", "calibration", False),
    (r"doctor|diagnost", "doctor", False),
    (r"lane|instanc|ustaw", "lane", False),
    (r"sync|synchroniz|syncuj", "sync", False),
    (_REFACTOR_PATTERN, "auto", False),
    (r"status|stan", "status", False),
    (r"chat|wyslij|wyślij", "chat", False),
    (r"auto|autonomous|autopilot|run|execute", "auto", False),
)
_VALID_ACTIONS = frozenset((*{action for _, action, _ in _ACTION_RULES}, "repair"))
_SETUP_ACTIONS = (_VALID_ACTIONS - {"repair"}) | {"manage"}
_FIXED_LINES = {
    "status": "STATUS",
    "doctor": "DOCTOR",
    "calibration": "CALIBRATION",
    "sync": "SYNC",
    "auto": "AUTO",
    "manage": "DIAGNOSE",
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
    return bool(re.search(_REFACTOR_PATTERN, text.strip().lower()))


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


def _resolve_heuristic_action(lower: str) -> tuple[str, bool]:
    return next(
        ((action, install) for pattern, action, install in _ACTION_RULES if re.search(pattern, lower)),
        ("status", False),
    )


def heuristic_plan(text: str) -> KoruPlan:
    lower = text.strip().lower()
    ide, instance = _parse_lane_mentions(lower)
    action, install = _resolve_heuristic_action(lower)
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
    if action == "chat":
        return f"CHAT --text {text.strip()!r}".replace("\\'", "'")
    return _FIXED_LINES.get(action, f"TEXT {text!r}")


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
        from nlp2koru.llm_backend import nl_to_dsl_line

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
