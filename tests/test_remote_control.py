import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from koru.remote import KoruRemoteClient


def test_remote_client_init() -> None:
    client = KoruRemoteClient(host="10.0.0.5", port=9000)
    assert client.base_url == "http://10.0.0.5:9000"


@patch("urllib.request.urlopen")
def test_remote_client_get_status(mock_urlopen) -> None:
    # Setup mock response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "project": "remote-c2004",
        "ides": [{"id": "cursor", "running": True}],
        "plugins": [{"id": "cursor", "version": "0.1.55"}]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    client = KoruRemoteClient()
    status = client.get_status()
    
    assert status["project"] == "remote-c2004"
    assert status["ides"][0]["id"] == "cursor"
    assert len(client.list_running_ides()) == 1
    assert len(client.list_connected_plugins()) == 1


@patch("urllib.request.urlopen")
def test_remote_client_send_drive(mock_urlopen) -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "ok": True,
        "result": {"winning_submit": "Ctrl+Return", "chars": 15}
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    client = KoruRemoteClient()
    res = client.send_drive_command(ide="cursor", text="write tests")
    
    assert res["ok"] is True
    assert res["result"]["winning_submit"] == "Ctrl+Return"
