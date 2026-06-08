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


def heuristic_plan(text: str) -> CoruPlan:
    lower = text.strip().lower()
    ide, instance = _parse_lane_mentions(lower)

    if any(key in lower for key in ("ensure", "zainstal", "install", "napraw", "sprawdz")):
        return CoruPlan([CoruIntent(action="ensure", ide=ide, instance=instance, install=True)], use_llm=False)

    if "calibration" in lower or "kalibrac" in lower:
        return CoruPlan([CoruIntent(action="calibration", ide=ide, instance=instance)], use_llm=False)

    if "doctor" in lower or "diagnost" in lower:
        return CoruPlan([CoruIntent(action="doctor", ide=ide, instance=instance)], use_llm=False)

    if any(key in lower for key in ("lane", "instanc", "ustaw")):
        return CoruPlan([CoruIntent(action="lane", ide=ide, instance=instance)], use_llm=False)

    if any(key in lower for key in ("sync", "synchroniz", "syncuj")):
        return CoruPlan([CoruIntent(action="sync", ide=ide, instance=instance)], use_llm=False)

    if _refactor_intent(text):
        return CoruPlan([CoruIntent(action="auto", ide=ide, instance=instance)], use_llm=False)

    if any(key in lower for key in ("status", "stan")):
        return CoruPlan([CoruIntent(action="status", ide=ide, instance=instance)], use_llm=False)

    if any(key in lower for key in ("chat", "wyslij", "wyślij")):
        return CoruPlan([CoruIntent(action="chat", ide=ide, instance=instance)], use_llm=False)

    if any(key in lower for key in ("auto", "autonomous", "autopilot", "run", "execute")):
        return CoruPlan([CoruIntent(action="auto", ide=ide, instance=instance)], use_llm=False)

    return CoruPlan([CoruIntent(action="status", ide=ide, instance=instance)], use_llm=False)


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
