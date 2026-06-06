"""NLP shim package for resolving natural language intents."""

from nlpshim.client import NLPBridgeClient
from nlpshim.conversation_client import ConversationState, ConversationTestClient
from nlpshim.conversation_test_api import (
    ConversationContext,
    DialogResponse,
    complete_missing_fields,
    execute_conversation_plan,
    export_trace,
    parse_conversation_step,
)

__all__ = [
    "NLPBridgeClient",
    "ConversationTestClient",
    "ConversationState",
    "ConversationContext",
    "DialogResponse",
    "parse_conversation_step",
    "complete_missing_fields",
    "execute_conversation_plan",
    "export_trace",
]
