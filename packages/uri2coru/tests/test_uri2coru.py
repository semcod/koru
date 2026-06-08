from uri2coru.decode import uri_to_dsl
from uri2coru.nlp2uri import nlp2uri
from uri2coru.run import run_uri


def test_uri_decode_repair_history() -> None:
    line = uri_to_dsl("coru://block/repair/history?default_file=.")
    assert line.startswith("REPAIR_HISTORY")


def test_nlp2uri_repair_history() -> None:
    hits = nlp2uri("show repair history", default_file=".")
    assert hits
    assert hits[0].dsl.startswith("REPAIR_HISTORY")


def test_run_uri_lane() -> None:
    uri = "coru://cmd/LANE?ide=auto&instance=default&default_file=."
    result = run_uri(uri, default_file=".")
    assert result.ok is True
