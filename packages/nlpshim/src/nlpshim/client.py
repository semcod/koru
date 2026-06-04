"""NLP to DSL translation client using nlp2dsl_sdk with graceful fallbacks."""

from __future__ import annotations

import os
from typing import Any

try:
    from nlp2dsl_sdk import NLP2DSLClient as ExternalNLP2DSLClient
except ImportError:
    ExternalNLP2DSLClient = None  # type: ignore


class FallbackNLP2DSLClient:
    """Mock / local translation for test stability when nlp2dsl service is not running."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    def from_env(cls) -> "FallbackNLP2DSLClient":
        return cls()

    def workflow_from_text(self, text: str, execute: bool = False, mode: str = "auto") -> dict[str, Any]:
        lowered = text.lower()
        steps = []
        if "focus" in lowered or "okno" in lowered:
            hints = ["vscode"]
            for app in ["windsurf", "cursor", "vscode", "vscodium", "zed", "chrome", "firefox"]:
                if app in lowered:
                    hints = [app]
                    break
            steps.append({
                "action": "focus_window",
                "config": {"window_name_hints": hints}
            })
        if "type" in lowered or "wpisz" in lowered or "napisz" in lowered:
            words = text.split()
            literal = "hello"
            for i, word in enumerate(words):
                if word.lower() in ("type", "wpisz", "napisz") and i + 1 < len(words):
                    literal = " ".join(words[i+1:])
                    break
            steps.append({
                "action": "inject_keys",
                "config": {"literal_text": literal, "submit": True}
            })
        return {
            "status": "complete",
            "steps": steps,
            "text": text,
        }


def get_nlp2dsl_client() -> Any:
    """Return the real NLP2DSLClient if available, otherwise the fallback."""
    if ExternalNLP2DSLClient is not None:
        return ExternalNLP2DSLClient
    return FallbackNLP2DSLClient


class NLPBridgeClient:
    """Bridge to nlp2dsl backend for resolving natural language commands."""

    def __init__(self, client: Any | None = None) -> None:
        ClientClass = get_nlp2dsl_client()
        self.client = client or ClientClass()

    def parse_intent(self, text: str) -> list[dict[str, Any]]:
        """Parse natural language command into structured workflow steps."""
        try:
            res = self.client.workflow_from_text(text)
            return res.get("steps") or []
        except Exception as exc:
            # Fallback to local heuristic parser if remote call fails
            fallback_client = FallbackNLP2DSLClient()
            try:
                res = fallback_client.workflow_from_text(text)
                return res.get("steps") or []
            except Exception:
                raise RuntimeError(f"Failed to parse NLP intent via nlp2dsl: {exc}") from exc
