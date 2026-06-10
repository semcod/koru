"""Heuristic prompt routing for CORU intents."""

from __future__ import annotations

import re

from .models import CoruIntent, CoruPlan


_REFACTOR_MARKERS = (
    "refactor",
    "refaktoryz",
    "refakotryz",
)


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


def _heuristic_intent(
    *,
    action: str,
    ide: str | None,
    instance: str | None,
    install: bool = False,
) -> CoruPlan:
    return CoruPlan(
        [CoruIntent(action=action, ide=ide, instance=instance, install=install)],
        use_llm=False,
    )


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


def heuristic_plan(text: str) -> CoruPlan:
    lower = text.strip().lower()
    ide, instance = _parse_lane_mentions(lower)
    action, install = _resolve_heuristic_action(lower, text)
    return _heuristic_intent(action=action, ide=ide, instance=instance, install=install)


def to_dsl_lines(text: str, *, use_llm: bool = False, llm_model: str = "openrouter/qwen/qwen3-coder-next") -> list[str]:
    from .llm import llm_plan

    if use_llm:
        plan = llm_plan(text, model=llm_model)
    else:
        plan = heuristic_plan(text)

    if not plan.steps:
        return ["STATUS"]

    first = plan.steps[0]
    tokens: list[str] = []

    def _line(intent: CoruIntent) -> str:
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
        if action == "status":
            return "STATUS"
        if action == "doctor":
            return "DOCTOR"
        if action == "calibration":
            return "CALIBRATION"
        if action == "sync":
            return "SYNC"
        if action == "chat":
            return f"CHAT --text {first_text!r}".replace("\\\'", "'")
        if action == "auto":
            pieces = ["AUTO"]
            return " ".join(pieces)
        if action == "manage":
            return "DIAGNOSE"
        return f"TEXT {text!r}"

    first_text = text.strip()
    wants_setup = _refactor_intent(text) or detect_setup_intent(text)
    if first.action in {"auto", "ensure", "lane", "status", "doctor", "calibration", "sync", "chat", "manage"} and wants_setup:
        tokens.extend([
            "ENSURE --install",
            "LANE" + (f" --ide {first.ide}" if first.ide else "") + (f" --instance {first.instance}" if first.instance else ""),
            "DOCTOR",
            "DIAGNOSE",
            "AUTO",
        ])
        if first.action == "auto":
            return tokens

    if not wants_setup:
        for step in plan.steps:
            step_line = _line(step)
            tokens.append(step_line)
            if step.action == "chat":
                break
        return tokens

    return tokens or ["STATUS"]
