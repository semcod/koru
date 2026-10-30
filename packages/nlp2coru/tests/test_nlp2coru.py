from types import SimpleNamespace

from nlp2coru.apply import apply_prompt
from nlp2coru.heuristic import to_dsl_lines
from nlp2coru.llm import llm_plan
from nlp2coru.to_dsl import to_dsl


def test_to_dsl_offline_status() -> None:
    line = to_dsl("show lane status")
    assert "LANE" in line or "STATUS" in line


def test_heuristic_lines_offline() -> None:
    lines = to_dsl_lines("check status")
    assert lines
    assert lines[0] == "STATUS"


def test_apply_offline_no_execute(monkeypatch) -> None:
    monkeypatch.setattr(
        "nlp2coru.apply._execute_line",
        lambda line, default_file=None: {"ok": True, "verb": line.split()[0]},
    )
    result = apply_prompt("check status", use_llm=False)
    assert result.ok is True
    assert result.lines


def test_default_backend_uses_central_coru_route(monkeypatch) -> None:
    observed = {}

    def run(application, route_function, messages, **kwargs):
        observed.update(messages=messages, route_function=route_function)
        assert application == "koru-agent"
        assert kwargs["response_format"] == {"type": "json_object"}
        result = SimpleNamespace(content='{"action":"doctor","install":false}')
        assert kwargs["quality_gate"](result) is True
        return result

    monkeypatch.setattr("subllm.complete", run)
    monkeypatch.setattr("subllm.merged_environment", lambda **_kwargs: {})

    plan = llm_plan("diagnose it", model="legacy-provider/ignored-model")

    assert plan.steps[0].action == "doctor"
    assert plan.use_llm is True
    assert observed["route_function"] == "nl-to-coru-dsl"
    assert observed["messages"][0]["role"] == "system"
    assert "ignored-model" not in repr(observed)


def test_injected_backend_remains_supported() -> None:
    class Backend:
        observed_model = ""

        def complete(self, *, model, messages, temperature=0.2, response_format=None):
            self.observed_model = model
            assert messages[-1]["role"] == "user"
            assert temperature == 0.2
            assert response_format is None
            return '{"action":"status"}'

    backend = Backend()
    plan = llm_plan("status", model="compatibility-hint", backend=backend)

    assert plan.steps[0].action == "status"
    assert plan.use_llm is True
    assert backend.observed_model == "compatibility-hint"


def test_central_route_failure_falls_back_to_offline_heuristic(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise RuntimeError("unavailable")

    monkeypatch.setattr("subllm.complete", fail)
    monkeypatch.setattr("subllm.merged_environment", lambda **_kwargs: {})

    plan = llm_plan("show status")

    assert plan.steps[0].action == "status"
    assert plan.use_llm is False
