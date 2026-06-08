from pathlib import Path

from dsl2koru.bus import dispatch


def test_parity_cli_uri_rest_payloads(tmp_path: Path) -> None:
    line = "QUERY_REPAIR_HISTORY PROJECT . LIMIT 3"
    text = dispatch(line, default_project=str(tmp_path))
    json_payload = {
        "verb": "QUERY_REPAIR_HISTORY",
        "project": str(tmp_path),
        "limit": 3,
    }
    json_result = dispatch(json_payload, project_root=tmp_path)
    assert text.ok == json_result.ok
    assert text.verb == json_result.verb
