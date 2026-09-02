from types import SimpleNamespace

import pytest
from nlp2koru.llm_backend import legacy_llm_plan, llm_plan
from nlp2koru.to_dsl import KoruIntent, heuristic_plan, to_dsl_lines


@pytest.mark.parametrize(
    ("prompt", "action", "install", "ide", "instance"),
    [
        ("install and calibration for cursor-main in cursor", "ensure", True, "cursor", "cursor-main"),
        ("kalibracja dla windsurf-dev", "calibration", False, "windsurf", "windsurf-dev"),
        ("doctor diagnostyka", "doctor", False, None, None),
        ("set lane vscode-prod in vscode", "lane", False, "vscode", "vscode-prod"),
        ("synchronizuj", "sync", False, None, None),
        ("refakotryzuj module", "auto", False, None, None),
        ("show status", "status", False, None, None),
        ("wyślij chat hello", "chat", False, None, None),
        ("run autonomous", "auto", False, None, None),
        ("unknown request", "status", False, None, None),
    ],
)
def test_heuristic_precedence_matrix(prompt, action, install, ide, instance) -> None:
    assert heuristic_plan(prompt).steps == [KoruIntent(action=action, install=install, ide=ide, instance=instance)]


@pytest.mark.parametrize(
    ("prompt", "lines"),
    [
        ("check status", ["STATUS"]),
        ("doctor", ["DOCTOR"]),
        ("synchronizuj", ["SYNC"]),
        ("ustaw lane cursor-main w cursor", ["LANE", "--ide", "cursor", "--instance", "cursor-main"]),
        ("wyślij chat let's fix it", ['CHAT --text "wyślij chat let\'s fix it"']),
        (
            "refaktoryzuj dla zed-main w zed",
            ["ENSURE --install", "LANE --ide zed --instance zed-main", "DOCTOR", "DIAGNOSE", "AUTO"],
        ),
    ],
)
def test_rendering_matrix(prompt, lines) -> None:
    actual = to_dsl_lines(prompt)
    if prompt.startswith("ustaw lane"):
        assert actual[0].split() == lines
    else:
        assert actual == lines


@pytest.mark.parametrize(
    ("planner", "route"),
    [(llm_plan, "nl-to-koru-dsl"), (legacy_llm_plan, "nl-to-coru-dsl")],
)
def test_central_route_matrix(monkeypatch, planner, route) -> None:
    observed = []

    def run(messages, project, *, route_function):
        observed.append((messages, project, route_function))
        return SimpleNamespace(returncode=0, stdout='prefix {"action":"doctor"} suffix', stderr="")

    monkeypatch.setattr("korullm.run_subllm_messages", run)

    plan = planner("diagnose")

    assert plan.steps == [KoruIntent(action="doctor")]
    assert plan.use_llm is True
    assert observed[0][2] == route


@pytest.mark.parametrize("payload", ['{"action":"unsupported"}', '{"action":"status"}'])
def test_llm_action_validation(payload) -> None:
    class Backend:
        def complete(self, **_kwargs):
            return payload

    assert llm_plan("anything", backend=Backend()).steps == [KoruIntent(action="status")]
