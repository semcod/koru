from pathlib import Path

from dsl2coru.bus import dispatch


def test_parity_cli_uri_rest_payloads(tmp_path: Path) -> None:
    line = "REPAIR_HISTORY"
    text = dispatch(line, default_project=str(tmp_path))
    json_payload = {"verb": "REPAIR_HISTORY"}
    json_result = dispatch(json_payload, default_project=str(tmp_path))
    assert text.ok == json_result.ok
    assert text.verb == json_result.verb
