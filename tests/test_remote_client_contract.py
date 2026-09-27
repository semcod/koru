"""Service contract tests for KoruRemoteClient."""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from koru.remote.client import KoruRemoteClient


def test_remote_client_initialization() -> None:
    client_default = KoruRemoteClient()
    assert client_default.base_url == "http://127.0.0.1:8765"

    client_custom = KoruRemoteClient(host="koru.node.lan", port=9999, use_ssl=False)
    assert client_custom.base_url == "http://koru.node.lan:9999"

    client_ssl = KoruRemoteClient(host="secure.koru.lan", port=443, use_ssl=True)
    assert client_ssl.base_url == "https://secure.koru.lan:443"


def test_remote_client_request_get() -> None:
    client = KoruRemoteClient()

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"status": "running", "ides": []}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client._request("/api/dashboard")
        assert res == {"status": "running", "ides": []}
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://127.0.0.1:8765/api/dashboard"
        assert req.get_method() == "GET"
        assert req.data is None
        assert mock_urlopen.call_args[1]["timeout"] == 5.0


def test_remote_client_request_post() -> None:
    client = KoruRemoteClient()

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client._request("/api/remote/drive", method="POST", data={"ide": "cursor", "text": "hello"})
        assert res == {"ok": True}
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://127.0.0.1:8765/api/remote/drive"
        assert req.get_method() == "POST"
        assert json.loads(req.data.decode("utf-8")) == {"ide": "cursor", "text": "hello"}
        assert req.headers["Content-type"] == "application/json"


def test_remote_client_request_http_error_with_json() -> None:
    client = KoruRemoteClient()

    error_json = json.dumps({"error": "Plugin not connected"}).encode("utf-8")
    http_err = urllib.error.HTTPError(
        url="http://127.0.0.1:8765/api/remote/drive",
        code=404,
        msg="Not Found",
        hdrs=MagicMock(),
        fp=io.BytesIO(error_json),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(RuntimeError, match=r"Remote command failed: HTTP 404 - Plugin not connected"):
            client.send_drive_command(ide="cursor", text="drive", require_plugin=True)


def test_remote_client_request_http_error_without_json() -> None:
    client = KoruRemoteClient()

    http_err = urllib.error.HTTPError(
        url="http://127.0.0.1:8765/api/dashboard",
        code=502,
        msg="Bad Gateway",
        hdrs=MagicMock(),
        fp=io.BytesIO(b"<html>Bad Gateway</html>"),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(RuntimeError, match=r"Remote command failed: HTTP 502 - Bad Gateway"):
            client.get_status()


def test_remote_client_request_connection_failure() -> None:
    client = KoruRemoteClient(host="unreachable.local", port=9999)

    err_pattern = (
        r"Cannot reach remote Koru node at http://unreachable\.local:9999: "
        r"<urlopen error Connection refused>"
    )
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(RuntimeError, match=err_pattern):
            client.get_status()


def test_remote_client_get_logs() -> None:
    client = KoruRemoteClient()

    with patch.object(client, "_request", return_value={"logs": ["line1", "line2"]}) as mock_req:
        # Default limit
        res_default = client.get_logs()
        assert res_default == {"logs": ["line1", "line2"]}
        mock_req.assert_called_with("/api/plugin-logs?limit=100")

        # Custom limit
        client.get_logs(limit=25)
        mock_req.assert_called_with("/api/plugin-logs?limit=25")


def test_remote_client_send_drive_command() -> None:
    client = KoruRemoteClient()

    with patch.object(client, "_request", return_value={"ok": True, "chars": 10}) as mock_req:
        res = client.send_drive_command(ide="vscode", text="implement tests", require_plugin=True)
        assert res == {"ok": True, "chars": 10}
        mock_req.assert_called_once_with(
            "/api/remote/drive",
            method="POST",
            data={
                "ide": "vscode",
                "text": "implement tests",
                "require_plugin": True,
            },
        )


def test_remote_client_list_helpers() -> None:
    client = KoruRemoteClient()

    # Case 1: Populated status
    status_payload = {
        "ides": [{"id": "cursor", "running": True}, {"id": "vscode", "running": False}],
        "plugins": [{"id": "cursor", "version": "1.0.0"}],
    }
    with patch.object(client, "get_status", return_value=status_payload):
        ides = client.list_running_ides()
        assert len(ides) == 2
        assert ides[0]["id"] == "cursor"

        plugins = client.list_connected_plugins()
        assert len(plugins) == 1
        assert plugins[0]["id"] == "cursor"

    # Case 2: Empty or missing keys
    with patch.object(client, "get_status", return_value={}):
        assert client.list_running_ides() == []
        assert client.list_connected_plugins() == []
