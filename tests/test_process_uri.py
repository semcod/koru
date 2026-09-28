"""Unit tests for ProcessUri, ProcessUriRegistry and GBNF grammar export."""

import pytest

from koru.autonomy.process_uri import (
    ProcessUri,
    ProcessUriError,
    ProcessUriRegistry,
    parse_uri_json_line,
)


def test_process_uri_action_parsing():
    uri = ProcessUri.parse("koru://queue/task/claim?ticket_id=334&worker=gemini")
    assert uri.scheme == "koru"
    assert uri.domain == "queue"
    assert uri.action_or_resource == "task/claim"
    assert uri.query_params == {"ticket_id": "334", "worker": "gemini"}
    assert not uri.is_urn
    assert uri.canonical_action == "koru://queue/task/claim"


def test_process_uri_urn_parsing():
    urn = ProcessUri.parse("urn:wellmanifest:standard:nl-dsl-llm@0.1.0")
    assert urn.scheme == "urn"
    assert urn.domain == "wellmanifest"
    assert urn.action_or_resource == "standard:nl-dsl-llm@0.1.0"
    assert urn.is_urn
    assert urn.canonical_action == "urn:wellmanifest:standard:nl-dsl-llm@0.1.0"


def test_process_uri_invalid():
    with pytest.raises(ProcessUriError):
        ProcessUri.parse("")

    with pytest.raises(ProcessUriError):
        ProcessUri.parse("no-scheme-uri")

    with pytest.raises(ProcessUriError):
        ProcessUri.parse("urn:invalid")


def test_process_uri_registry_validation():
    registry = ProcessUriRegistry()
    registry.register(
        "taskand://git/commit",
        "Commit changes to branch",
        {"required": ["message"]},
    )

    uri = ProcessUri.parse("taskand://git/commit?message=test_commit")
    merged = registry.validate_invocation(uri)
    assert merged["message"] == "test_commit"

    uri_without_param = ProcessUri.parse("taskand://git/commit")
    with pytest.raises(ProcessUriError, match="Missing required parameter"):
        registry.validate_invocation(uri_without_param)

    # Payload merges correctly
    merged_payload = registry.validate_invocation(uri_without_param, {"message": "payload_message"})
    assert merged_payload["message"] == "payload_message"


def test_export_gbnf_grammar():
    registry = ProcessUriRegistry()
    registry.register("koru://workspace/allocate", "Allocate worktree")
    registry.register("taskand://git/commit", "Commit changes")

    grammar = registry.export_gbnf()
    assert '"koru://workspace/allocate"' in grammar
    assert '"taskand://git/commit"' in grammar
    assert "json_payload" in grammar


def test_parse_uri_json_line():
    line = "action: koru://workspace/allocate {\"ticket_id\": \"ticket-334\"}"
    uri, payload = parse_uri_json_line(line)
    assert uri.canonical_action == "koru://workspace/allocate"
    assert payload == {"ticket_id": "ticket-334"}

    line_yaml = "- uri: taskand://git/commit {\"message\": \"feat: new feature\"}"
    uri2, payload2 = parse_uri_json_line(line_yaml)
    assert uri2.canonical_action == "taskand://git/commit"
    assert payload2 == {"message": "feat: new feature"}
