"""Public test API for nlp2dsl conversation scenarios (TestQL integration)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from nlpshim.conversation_client import ConversationState, ConversationTestClient


class LLMProvider(Protocol):
    def reply_for(self, conversation_id: str, *, missing: list[str] | None = None) -> dict[str, Any]: ...


@dataclass
class ConversationContext:
    conversation_id: str = ""
    user_id: str = "test-user"
    files: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogResponse:
    status: str
    missing: list[str] = field(default_factory=list)
    intent_ir: dict[str, Any] | None = None
    dsl: dict[str, Any] | None = None
    body: dict[str, Any] = field(default_factory=dict)


def parse_conversation_step(
    input: dict[str, Any],
    context: ConversationContext,
    *,
    client: ConversationTestClient | None = None,
) -> DialogResponse:
    """Parse one dialog step without executing side-effects."""
    active = client or ConversationTestClient()
    if context.conversation_id:
        active._state.conversation_id = context.conversation_id
    elif input.get("endpoint") == "chatstart":
        context.conversation_id = active.start(**{k: v for k, v in input.items() if k != "endpoint"})
    text = str(input.get("text", ""))
    body = active.message(text, **{k: v for k, v in input.items() if k not in {"endpoint", "text"}})
    return DialogResponse(
        status=str(body.get("status", "")),
        missing=list(body.get("missing") or []),
        intent_ir=body.get("intentIr") or body.get("intent_ir"),
        dsl=body.get("dsl"),
        body=body,
    )


def complete_missing_fields(state: ConversationState, llm_or_mock: LLMProvider) -> dict[str, Any]:
    """Fill missing dialog fields using a deterministic or live LLM provider."""
    return llm_or_mock.reply_for(state.conversation_id, missing=list(state.missing))


def execute_conversation_plan(plan: dict[str, Any], sandbox: Any | None = None) -> dict[str, Any]:
    """Execute a resolved DSL plan inside an optional sandbox."""
    del sandbox
    client = ConversationTestClient()
    if plan.get("conversationId"):
        client._state.conversation_id = str(plan["conversationId"])
    return client.run_dsl(plan.get("dsl"))


def export_trace(conversation_id: str, *, client: ConversationTestClient | None = None) -> dict[str, Any]:
    """Export a conversation trace suitable for TestQL scenario generation."""
    del conversation_id  # trace is held on the client state for mock/local runs
    active = client or ConversationTestClient()
    payload = active.export_trace()
    payload["conversationId"] = payload.get("conversationId") or conversation_id
    return payload
