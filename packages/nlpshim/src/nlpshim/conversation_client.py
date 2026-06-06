"""Multi-turn conversation test client for nlp2dsl (mock-friendly)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nlpshim.client import FallbackNLP2DSLClient, get_nlp2dsl_client


@dataclass
class ConversationState:
    conversation_id: str = ""
    status: str = ""
    missing: list[str] = field(default_factory=list)
    dsl: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)


class ConversationTestClient:
    """Thin wrapper for TestQL-style multi-turn tests against nlp2dsl."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or get_nlp2dsl_client()
        self._state = ConversationState()

    @property
    def state(self) -> ConversationState:
        return self._state

    def start(self, **payload: Any) -> str:
        if hasattr(self._client, "chatstart"):
            result = self._client.chatstart(payload)
            body = result if isinstance(result, dict) else getattr(result, "body", result)
        else:
            body = {"conversationId": "local-conv-1", **payload}
        self._state.conversation_id = str(body.get("conversationId", "local-conv-1"))
        self._record("chatstart", body)
        return self._state.conversation_id

    def message(self, text: str, **context: Any) -> dict[str, Any]:
        payload = {"conversationId": self._state.conversation_id, "text": text, **context}
        if hasattr(self._client, "chatmessage"):
            result = self._client.chatmessage(payload)
            body = result if isinstance(result, dict) else getattr(result, "body", result)
        elif hasattr(self._client, "workflow_from_text"):
            try:
                body = self._client.workflow_from_text(text, execute=bool(context.get("execute")))
            except Exception:
                body = FallbackNLP2DSLClient().workflow_from_text(text)
        else:
            body = FallbackNLP2DSLClient().workflow_from_text(text)
        if not isinstance(body, dict):
            body = dict(body) if hasattr(body, "items") else {"result": body}
        self._state.status = str(body.get("status", "complete"))
        self._state.missing = list(body.get("missing") or [])
        if body.get("dsl"):
            self._state.dsl = dict(body["dsl"])
        self._record("chatmessage", body)
        return body

    def run_dsl(self, dsl: dict[str, Any] | None = None, **payload: Any) -> dict[str, Any]:
        body_in = {"conversationId": self._state.conversation_id, "dsl": dsl or self._state.dsl, **payload}
        if hasattr(self._client, "runworkflow"):
            result = self._client.runworkflow(body_in)
            body = result if isinstance(result, dict) else getattr(result, "body", result)
        else:
            body = {"status": "success", "resultId": "mock-result-1"}
        self._record("runworkflow", body)
        return body

    def export_trace(self) -> dict[str, Any]:
        return {
            "conversationId": self._state.conversation_id,
            "status": self._state.status,
            "missing": list(self._state.missing),
            "dsl": self._state.dsl,
            "turns": list(self._state.trace),
        }

    def _record(self, endpoint: str, body: dict[str, Any]) -> None:
        self._state.trace.append({"endpoint": endpoint, "body": dict(body)})
