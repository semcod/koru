import json

from uri2koru.cli import main
from uri2koru.decode import uri_to_dsl
from uri2koru.nlp2uri import nlp2uri
from uri2koru.run import run_uri


def test_uri_decode_repair_history() -> None:
    line = uri_to_dsl("koru://block/repair/history?project=.")
    assert line.startswith("QUERY_REPAIR_HISTORY")


def test_nlp2uri_repair_history() -> None:
    hits = nlp2uri("show repair history", project=".")
    assert hits
    assert hits[0].dsl.startswith("QUERY_REPAIR_HISTORY")


def test_run_uri_validate_lane() -> None:
    uri = "koru://cmd/VALIDATE_LANE?ide=auto&instance=default&project=."
    result = run_uri(uri, default_project=".")
    assert result.ok is True


def test_cli_decode_prints_dsl_line(capsys) -> None:
    code = main(["decode", "--uri", "koru://block/repair/history?project=."])

    assert code == 0
    assert capsys.readouterr().out.startswith("QUERY_REPAIR_HISTORY")


def test_cli_run_text_prints_output(capsys) -> None:
    uri = "koru://cmd/VALIDATE_LANE?ide=auto&instance=default&project=."

    code = main(["run", "--uri", uri, "--project", "."])

    assert code == 0
    assert capsys.readouterr().out.strip() == "ok"


def test_cli_run_json_outputs_result(capsys) -> None:
    uri = "koru://cmd/VALIDATE_LANE?ide=auto&instance=default&project=."

    code = main(["run", "--uri", uri, "--project", ".", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["output"] == "ok"


def test_cli_resolve_prints_hits(capsys) -> None:
    code = main(["resolve", "show repair history", "--project", "."])

    assert code == 0
    assert "koru://block/repair/history" in capsys.readouterr().out


def test_cli_resolve_json_outputs_hits(capsys) -> None:
    code = main(["resolve", "show repair history", "--project", ".", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload[0]["dsl"].startswith("QUERY_REPAIR_HISTORY")
