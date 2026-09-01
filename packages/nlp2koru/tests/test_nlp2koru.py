from types import SimpleNamespace

from nlp2koru.apply import apply_nl
from nlp2koru.llm_backend import nl_to_dsl_line
from nlp2koru.to_dsl import to_dsl


def test_to_dsl_repair_history() -> None:
    line = to_dsl("show repair history", project=".")
    assert line.startswith("QUERY_REPAIR_HISTORY")


def test_apply_validate_lane() -> None:
    result = apply_nl("validate lane", project=".")
    assert result.dsl.startswith("VALIDATE_LANE")
    assert result.ok is True


def test_default_backend_uses_central_koru_route(monkeypatch, tmp_path) -> None:
    observed = {}

    def run(messages, project, *, route_function):
        observed.update(messages=messages, project=project, route_function=route_function)
        return SimpleNamespace(
            returncode=0,
            stdout='{"dsl":"VALIDATE_LANE --lane main"}',
            stderr="",
        )

    monkeypatch.setattr("korullm.run_subllm_messages", run)

    line = nl_to_dsl_line(
        "validate main",
        project=str(tmp_path),
        model="legacy-provider/ignored-model",
    )

    assert line == "VALIDATE_LANE --lane main"
    assert observed["route_function"] == "nl-to-koru-dsl"
    assert observed["project"] == tmp_path.resolve()
    assert observed["messages"][0]["role"] == "system"
    assert "ignored-model" not in repr(observed)


def test_injected_backend_remains_supported() -> None:
    class Backend:
        observed_model = ""

        def complete(self, *, model, messages, temperature=0.2, response_format=None):
            self.observed_model = model
            assert messages[-1]["role"] == "user"
            assert temperature == 0.2
            assert response_format == {"type": "json_object"}
            return '{"dsl":"QUERY_LANE_STATUS"}'

    backend = Backend()

    assert nl_to_dsl_line("status", model="compatibility-hint", backend=backend) == "QUERY_LANE_STATUS"
    assert backend.observed_model == "compatibility-hint"
