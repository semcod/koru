import json
from types import SimpleNamespace

from nlp2koru.apply import apply_nl
from nlp2koru.cli import main
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


def test_cli_to_dsl_prints_line(capsys) -> None:
    code = main(["to-dsl", "show repair history", "--project", "."])

    assert code == 0
    assert capsys.readouterr().out.startswith("QUERY_REPAIR_HISTORY")


def test_cli_to_dsl_json_outputs_line(capsys) -> None:
    code = main(["to-dsl", "show repair history", "--project", ".", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload[0].startswith("QUERY_REPAIR_HISTORY")


def test_cli_to_dsl_error_exits_one(capsys, monkeypatch) -> None:
    def fail(prompt, *, project, use_llm, llm_model):
        raise RuntimeError("boom")

    monkeypatch.setattr("nlp2koru.cli.to_dsl", fail)

    code = main(["to-dsl", "show repair history"])

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: boom\n"


def test_cli_apply_json_outputs_result(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "nlp2koru.cli.apply_nl",
        lambda prompt, *, project, use_llm: SimpleNamespace(
            dsl="VALIDATE_LANE --lane main",
            ok=True,
            error=None,
            result=SimpleNamespace(output="ok"),
            to_dict=lambda: {"dsl": "VALIDATE_LANE --lane main", "ok": True},
        ),
    )

    code = main(["apply", "validate lane", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["dsl"] == "VALIDATE_LANE --lane main"


def test_cli_workflow_outputs_json(capsys) -> None:
    code = main(["workflow", "validate lane"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert "steps" in payload


def test_cli_rewrite_prints_rewritten(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "nlp2koru.cli.rewrite_chat_prompt",
        lambda prompt, *, ide, instance, model: f"rewritten:{prompt}",
    )

    code = main(["rewrite-chat", "validate lane", "--ide", "code"])

    assert code == 0
    assert capsys.readouterr().out == "rewritten:validate lane\n"
