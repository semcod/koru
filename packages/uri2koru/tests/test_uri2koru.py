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
