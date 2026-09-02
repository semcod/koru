"""All-verb parity contract for the descriptor-driven protobuf codec."""

from __future__ import annotations

import pytest
from dsl2koru.pb_codec import decode_protobuf, dict_to_envelope, encode_protobuf

_CASES = [
    ({"verb": "QUERY_REPAIR_HISTORY"}, {"verb": "QUERY_REPAIR_HISTORY", "project": ".", "limit": 20}),
    ({"verb": "QUERY_REPAIR_HISTORY", "project": "p", "limit": 3, "code": "E"}, None),
    ({"verb": "QUERY_LANE_STATUS"}, {"verb": "QUERY_LANE_STATUS", "ide": "auto", "instance": "default"}),
    ({"verb": "QUERY_LANE_STATUS", "ide": "cursor", "instance": "lane-a"}, None),
    ({"verb": "VALIDATE_LANE"}, {"verb": "VALIDATE_LANE", "ide": "auto", "instance": "default"}),
    ({"verb": "RESOLVE"}, None),
    ({"verb": "RESOLVE", "prompt": "go", "project": "p"}, None),
    ({"verb": "REPAIR_RUN"}, {"verb": "REPAIR_RUN", "ide": "auto", "instance": "default"}),
    (
        {"verb": "REPAIR_RUN", "ide": "cursor", "instance": "lane-a", "project": "p", "trigger": "auto", "fix": True},
        None,
    ),
    ({"verb": "STATUS"}, None),
    ({"verb": "STATUS", "probe": True}, None),
    ({"verb": "REPAIR_HISTORY"}, None),
    ({"verb": "ENV"}, None),
    ({"verb": "ENV", "file": "project.toml"}, None),
    ({"verb": "QUERY"}, None),
    ({"verb": "QUERY", "target": "status"}, None),
    ({"verb": "AUTO"}, None),
    ({"verb": "AUTO", "shell": "bash", "auto_args": ["--once", "x"], "target": "repo"}, None),
    ({"verb": "AUTO", "auto_args": "--once x"}, {"verb": "AUTO", "auto_args": ["--once", "x"]}),
    ({"verb": "LANE"}, None),
    ({"verb": "LANE", "ide": "cursor", "instance": "lane-a", "file": "f", "lane_status": True}, None),
    ({"verb": "ENSURE"}, None),
    ({"verb": "ENSURE", "install": True}, None),
    ({"verb": "DOCTOR"}, None),
    ({"verb": "DOCTOR", "fix": True, "probe": True, "probe_prompt": "health"}, None),
    ({"verb": "CALIBRATION"}, None),
    (
        {"verb": "CALIBRATION", "skip_fix": True, "skip_desktop": True, "skip_bridge": True, "probe_prompt": "p"},
        None,
    ),
    ({"verb": "CHAT"}, None),
    ({"verb": "CHAT", "llm": True, "shell": "bash", "single_action": True}, None),
    ({"verb": "TEXT"}, None),
    ({"verb": "TEXT", "target": "hello", "llm": True, "shell": "bash", "single_action": True}, None),
    ({"verb": "SYNC"}, None),
    ({"verb": "SYNC", "all_ides": True}, None),
]


@pytest.mark.parametrize(("payload", "expected"), _CASES)
def test_every_body_round_trips(payload: dict[str, object], expected: dict[str, object] | None) -> None:
    assert decode_protobuf(encode_protobuf(payload)) == (expected or payload)


def test_envelope_metadata_remains_outside_the_body() -> None:
    envelope = dict_to_envelope(
        {"verb": "ENV", "file": "compat.env"},
        default_project="project-root",
        default_file="compat.env",
        correlation_id="correlation-1",
    )
    assert envelope.default_project == "project-root"
    assert envelope.default_file == "compat.env"
    assert envelope.correlation_id == "correlation-1"
