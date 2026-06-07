from __future__ import annotations

import pytest

from koru.ide_status_systemmap import format_autopilot_status_systemmap


SAMPLE_STATUS = {
    "plugins": [
        {
            "ide": "cursor",
            "version": "0.2.34",
            "workspaceFolders": ["/home/tom/github/semcod/koru"],
        }
    ],
}


def test_format_autopilot_status_systemmap() -> None:
    pytest.importorskip("nlp2uri")
    payload = format_autopilot_status_systemmap(
        SAMPLE_STATUS,
        socket_path="/run/user/1000/koru-autopilot-cursor.sock",
    )
    assert payload["ok"] is True
    assert payload["format"] == "system_map_uri.v1"
    assert any(uri.startswith("ide-chat://cursor/send") for uri in payload["entries"])
