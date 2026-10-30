"""Structured replies must pass task acceptance inside the central attempt."""
import json
from types import SimpleNamespace

import pytest
from nlp2koru.llm_backend import (
    SubLlmBackend,
    legacy_llm_plan,
    llm_plan,
    nl_to_dsl_line,
    rewrite_chat_prompt,
)
from nlp2koru.response_quality import valid_dsl_response, valid_intent_response


@pytest.mark.parametrize("payload", [
    {"action": "doctor"},
    {"action": " AUTO ", "install": True, "ide": "cursor", "instance": "main"},
    {"action": "status", "install": False, "ide": None, "instance": None},
])
def test_valid_intent_contract(payload):
    assert valid_intent_response(json.dumps(payload)) is True


@pytest.mark.parametrize("payload", [
    [], None, {}, {"action": ""}, {"action": "unsupported"}, {"action": 1},
    {"action": "repair", "install": "false"}, {"action": "repair", "install": 1},
    {"action": "repair", "install": None}, {"action": "lane", "ide": []},
    {"action": "lane", "instance": False}, {"action": "doctor", "execute": True},
])
def test_invalid_intent_contract(payload):
    assert valid_intent_response(json.dumps(payload)) is False


@pytest.mark.parametrize("text", [
    "", 'prefix {"action":"doctor"}', '```json\n{"action":"doctor"}\n```',
    '{"action":"doctor","action":"repair"}', '{"action":"status","install":NaN}',
])
def test_structured_response_has_one_unambiguous_json_object(text):
    assert valid_intent_response(text) is False


@pytest.mark.parametrize("line", [
    "QUERY_LANE_STATUS", "VALIDATE_LANE", "QUERY_REPAIR_HISTORY PROJECT . LIMIT 2",
    'RESOLVE "check status" PROJECT .',
])
def test_allowed_dsl_passes_existing_parser(line):
    assert valid_dsl_response(json.dumps({"dsl": line}), project=".") is True


@pytest.mark.parametrize("payload", [
    [], {}, {"dsl": None}, {"dsl": 42}, {"dsl": ""}, {"dsl": "   "},
    {"dsl": "not a command"}, {"dsl": "DOCTOR"},
    {"dsl": "QUERY_LANE_STATUS\nREPAIR_RUN"}, {"dsl": "QUERY_LANE_STATUS\rREPAIR_RUN"},
    {"dsl": "QUERY_LANE_STATUS\0"}, {"dsl": "QUERY_REPAIR_HISTORY LIMIT invalid"},
    {"dsl": "QUERY_LANE_STATUS", "execute": True},
])
def test_unusable_dsl_is_rejected_without_execution(payload):
    assert valid_dsl_response(json.dumps(payload), project=".") is False


@pytest.mark.parametrize(("planner", "route"), [
    (llm_plan, "nl-to-koru-dsl"), (legacy_llm_plan, "nl-to-coru-dsl"),
])
def test_both_routes_attach_task_gate_before_acceptance(monkeypatch, planner, route):
    rejected = SimpleNamespace(content='{"action":"repair","install":"false"}')
    accepted = SimpleNamespace(content='{"action":"doctor","install":false}')
    observed = []

    def complete(application, function, messages, **kwargs):
        assert (application, function) == ("koru-agent", route)
        assert "model" not in kwargs
        assert kwargs["environ"] == {"QUALITY_TEST": "1"}
        assert kwargs["response_format"] == {"type": "json_object"}
        observed.extend([kwargs["quality_gate"](rejected), kwargs["quality_gate"](accepted)])
        return accepted

    monkeypatch.setattr("subllm.complete", complete)
    monkeypatch.setattr("subllm.merged_environment", lambda **_kwargs: {"QUALITY_TEST": "1"})
    plan = planner("diagnose", model="legacy-provider/ignored-model")
    assert observed == [False, True]
    assert plan.use_llm is True
    assert plan.steps[0].action == "doctor"
    assert plan.steps[0].install is False


def test_dsl_gate_rejects_unsupported_command_in_central_attempt(monkeypatch, tmp_path):
    def complete(application, function, messages, **kwargs):
        assert (application, function) == ("koru-agent", "nl-to-koru-dsl")
        gate = kwargs["quality_gate"]
        assert gate(SimpleNamespace(content='{"dsl":"rm -rf ."}')) is False
        response = SimpleNamespace(content='{"dsl":"QUERY_LANE_STATUS"}')
        assert gate(response) is True
        return response

    monkeypatch.setattr("subllm.complete", complete)
    monkeypatch.setattr("subllm.merged_environment", lambda **_kwargs: {})
    assert nl_to_dsl_line("status", project=str(tmp_path)) == "QUERY_LANE_STATUS"


def test_structured_backend_forwards_explicit_format(monkeypatch, tmp_path):
    observed = {}

    def complete(*_args, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(content='{"ok":true}')

    monkeypatch.setattr("subllm.complete", complete)
    monkeypatch.setattr("subllm.merged_environment", lambda **_kwargs: {})
    result = SubLlmBackend(tmp_path).complete(
        model="", messages=[{"role": "user", "content": "JSON"}], response_format={"type": "json_object"}
    )
    assert result == '{"ok":true}'
    assert observed["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("payload", ['{"action":"repair","install":"false"}', '[]', '{"action":"unknown"}'])
def test_invalid_custom_intent_uses_offline_plan(payload):
    class Backend:
        def complete(self, **_kwargs):
            return payload

    plan = llm_plan("show status", backend=Backend())
    assert plan.use_llm is False
    assert plan.steps[0].action == "status"
    assert plan.steps[0].install is False


def test_custom_subclass_keeps_its_completion_override(monkeypatch):
    class Backend(SubLlmBackend):
        def complete(self, **_kwargs):
            return 'prefix {"action":"doctor"} suffix'

    def unexpected(*_args, **_kwargs):
        pytest.fail("injected backend must keep its transport")

    monkeypatch.setattr("subllm.complete", unexpected)
    plan = llm_plan("diagnose", backend=Backend())
    assert plan.use_llm is True
    assert plan.steps[0].action == "doctor"


def test_invalid_custom_dsl_fails_safely():
    class Backend:
        def complete(self, **_kwargs):
            return '{"dsl":"not a command"}'

    assert nl_to_dsl_line("status", backend=Backend()) is None


def test_chat_rewrite_preserves_plain_text_transport(monkeypatch):
    def run(messages, project, *, route_function):
        assert "plain text" in messages[0]["content"]
        return SimpleNamespace(returncode=0, stdout="Sprawdź testy", stderr="")

    monkeypatch.setattr("korullm.run_subllm_messages", run)
    assert rewrite_chat_prompt("sprawdz", ide="cursor", instance="main") == "Sprawdź testy"


def test_real_subllm_pipeline_changes_model_after_task_rejection(monkeypatch, tmp_path):
    from subllm import client_routes
    from subllm.client_types import CompletionResponse

    credentials = tmp_path / "empty.env"
    credentials.write_text("# Isolated test credentials\n")
    environment = {
        "ZAI_API_KEY": "id.test-secret", "SUBLLM_PROVIDER_ORDER": "zai",
        "SUBLLM_ENV_FILE": str(credentials),
        "SUBLLM_HEALTH_STATE_FILE": str(tmp_path / "health.json"),
        "SUBLLM_USAGE_DB": str(tmp_path / "usage.sqlite3"),
        "SUBLLM_USE_LOCAL_POSTGRES": "0",
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    for key in ("SUBLLM_POSTGRES_DSN", "SUBLLM_DATABASE_URL", "SUBLLM_GATEWAY_DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("subllm.merged_environment", lambda **_kwargs: environment)
    calls = []

    def invoke(route, *_args, **_kwargs):
        calls.append(route.wire_model)
        # DOCTOR is valid DSL, but outside this task's declared command set.
        line = "DOCTOR" if len(calls) == 1 else "QUERY_LANE_STATUS"
        return CompletionResponse(json.dumps({"dsl": line}), route.provider, route.wire_model,
                                  usage={"prompt_tokens": 10, "completion_tokens": 5}, finish_reason="stop")

    monkeypatch.setattr(client_routes, "_invoke_route", invoke)
    result = nl_to_dsl_line("show status", project=str(tmp_path))
    assert result == "QUERY_LANE_STATUS"
    assert calls == ["glm-5.3", "glm-5.3-flash"]
