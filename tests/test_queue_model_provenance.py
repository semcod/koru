from types import SimpleNamespace

import pytest

from koru.queue.runner import _execute_action
from koru.queue.runners import _DEFAULT_LLM_MODEL


@pytest.mark.parametrize(
    ("runtime_model", "requested_model", "expected_model"),
    [
        ("local-development/gpt-oss:20b", "cursor/grok-4.6", "local-development/gpt-oss:20b"),
        ("local-development/gemma4:12b", None, "local-development/gemma4:12b"),
        ("", "requested/model", "requested/model"),
        (None, "requested/model", "requested/model"),
        (None, None, _DEFAULT_LLM_MODEL),
    ],
)
@pytest.mark.parametrize("exit_code", [0, 7])
def test_queue_label_uses_executed_model(
    monkeypatch, tmp_path, runtime_model, requested_model, expected_model, exit_code
):
    monkeypatch.setattr("koru.queue.runner._enrich_llm_request_with_context", lambda action, _: action)
    result = SimpleNamespace(returncode=exit_code, stdout="answer", stderr="diagnostic")
    if runtime_model is not None:
        result.model = runtime_model
    request = {"prompt": "fixture"}
    if requested_model is not None:
        request["model"] = requested_model

    def run_llm(action, project):
        assert action == request
        assert project == tmp_path
        return result

    def unexpected_runner(*args):
        pytest.fail("another executor was selected")

    actual, label = _execute_action(
        "llm", request, tmp_path, "PLF-001", unexpected_runner, run_llm, unexpected_runner
    )

    assert actual is result
    assert actual.returncode == exit_code
    assert actual.stdout == "answer"
    assert actual.stderr == "diagnostic"
    assert label == f"llm {expected_model}"
