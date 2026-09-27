"""Service contract tests for LocalManagerClient and LocalManagerSession."""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from koru.local_manager_client import (
    LIFECYCLE_STOP_ACTIONS,
    LocalManagerClient,
    LocalManagerSession,
    _koru_version,
    _truthy,
    default_local_manager_url,
    lifecycle_decision_action,
    lifecycle_should_stop,
)


def test_truthy_helper() -> None:
    for val in ("1", "true", "True", "TRUE", "yes", "YES", "on", "  on  "):
        assert _truthy(val) is True
    for val in ("0", "false", "no", "off", "", None, "random", "2"):
        assert _truthy(val) is False


def test_koru_version() -> None:
    ver = _koru_version()
    assert isinstance(ver, str)
    assert len(ver) > 0

    with patch("koru.local_manager_client.version", side_effect=ImportError("PackageNotFoundError")):
        # If version raises PackageNotFoundError or similar
        from importlib.metadata import PackageNotFoundError

        with patch("koru.local_manager_client.version", side_effect=PackageNotFoundError):
            assert _koru_version() == "0.0.0"


def test_default_local_manager_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_LOCAL_MANAGER_URL", raising=False)
    monkeypatch.delenv("KORU_LOCAL_SERVICE_URL", raising=False)
    monkeypatch.delenv("KORU_LOCAL_MANAGER_ENABLED", raising=False)

    # Disabled by default
    assert default_local_manager_url() is None

    # Explicit KORU_LOCAL_MANAGER_URL takes precedence and strips trailing slash
    monkeypatch.setenv("KORU_LOCAL_MANAGER_URL", "http://mgr.internal:8000/ ")
    assert default_local_manager_url() == "http://mgr.internal:8000"

    # Explicit KORU_LOCAL_SERVICE_URL fallback
    monkeypatch.delenv("KORU_LOCAL_MANAGER_URL", raising=False)
    monkeypatch.setenv("KORU_LOCAL_SERVICE_URL", "http://svc.internal:9000/")
    assert default_local_manager_url() == "http://svc.internal:9000"

    # Enabled via flag with default host:port
    monkeypatch.delenv("KORU_LOCAL_SERVICE_URL", raising=False)
    monkeypatch.setenv("KORU_LOCAL_MANAGER_ENABLED", "1")
    assert default_local_manager_url() == "http://127.0.0.1:18766"

    # Custom host and port
    monkeypatch.setenv("KORU_LOCAL_SERVICE_HOST", "0.0.0.0")
    monkeypatch.setenv("KORU_LOCAL_SERVICE_PORT", "9999")
    assert default_local_manager_url() == "http://0.0.0.0:9999"


def test_lifecycle_decision_helpers() -> None:
    assert lifecycle_decision_action(None) == "continue"
    assert lifecycle_decision_action({}) == "continue"
    assert lifecycle_decision_action({"decision": "not-a-dict"}) == "continue"
    assert lifecycle_decision_action({"decision": {}}) == "continue"
    assert lifecycle_decision_action({"decision": {"action": "quarantine"}}) == "quarantine"

    assert lifecycle_should_stop(None) is False
    assert lifecycle_should_stop({"decision": {"action": "continue"}}) is False
    for stop_action in LIFECYCLE_STOP_ACTIONS:
        assert lifecycle_should_stop({"decision": {"action": stop_action}}) is True


def test_local_manager_client_disabled() -> None:
    client = LocalManagerClient(url=None)
    assert client.enabled is False
    assert client.post("/test", {"a": 1}) is None


def test_local_manager_client_post_success() -> None:
    client = LocalManagerClient(url="http://127.0.0.1:18766", timeout=1.0)
    assert client.enabled is True

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"ok": True, "worker_id": "w1"}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client.post("/workers/register", {"key": "val"})
        assert res == {"ok": True, "worker_id": "w1"}
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://127.0.0.1:18766/workers/register"
        assert req.get_method() == "POST"
        assert json.loads(req.data.decode("utf-8")) == {"key": "val"}
        assert req.headers["Content-type"] == "application/json"


def test_local_manager_client_post_error_handling() -> None:
    client = LocalManagerClient(url="http://127.0.0.1:18766")

    # Non-dict JSON response
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'["not", "a", "dict"]'
    mock_resp.__enter__.return_value = mock_resp
    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert client.post("/test", {}) is None

    # Invalid JSON
    mock_resp.read.return_value = b"invalid json"
    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert client.post("/test", {}) is None

    # URLError / OSError
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        assert client.post("/test", {}) is None

    # HTTPError
    http_err = urllib.error.HTTPError(
        url="http://127.0.0.1:18766/test",
        code=500,
        msg="Internal Error",
        hdrs=MagicMock(),
        fp=io.BytesIO(b"error"),
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        assert client.post("/test", {}) is None


def test_local_manager_client_api_methods() -> None:
    client = LocalManagerClient(url="http://127.0.0.1:18766")

    with patch.object(client, "post", return_value={"ok": True}) as mock_post:
        # register_worker
        res = client.register_worker(
            worker_id="worker-01",
            worker_kind="test-agent",
            capabilities=["pytest"],
            project=Path("/tmp/proj"),
            health="ok",
            metadata={"meta": 1},
        )
        assert res == {"ok": True}
        assert mock_post.call_args[0][0] == "/workers/register"
        payload = mock_post.call_args[0][1]
        assert payload["worker_id"] == "worker-01"
        assert payload["kind"] == "test-agent"
        assert payload["capabilities"] == ["pytest"]
        assert payload["project"] == "/tmp/proj"
        assert payload["metadata"] == {"meta": 1}

        # heartbeat_worker
        client.heartbeat_worker(
            worker_id="worker-01",
            capabilities=["pytest"],
            health="degraded",
            conflict=True,
            metadata={"load": 0.5},
        )
        assert mock_post.call_args[0][0] == "/workers/heartbeat"
        hb_payload = mock_post.call_args[0][1]
        assert hb_payload["worker_id"] == "worker-01"
        assert hb_payload["health"] == "degraded"
        assert hb_payload["conflict"] is True

        # claim_action
        client.claim_action(
            worker_id="worker-01",
            capabilities=["pytest"],
            action_types=["test-run"],
            lease_seconds=60,
        )
        assert mock_post.call_args[0][0] == "/queue/claim"
        claim_payload = mock_post.call_args[0][1]
        assert claim_payload["worker_id"] == "worker-01"
        assert claim_payload["action_types"] == ["test-run"]
        assert claim_payload["lease_seconds"] == 60

        # complete_action
        client.complete_action(
            action_id="act-99",
            worker_id="worker-01",
            status="done",
            result={"exit_code": 0},
        )
        assert mock_post.call_args[0][0] == "/queue/complete"
        comp_payload = mock_post.call_args[0][1]
        assert comp_payload["action_id"] == "act-99"
        assert comp_payload["status"] == "done"
        assert comp_payload["result"] == {"exit_code": 0}


def test_local_manager_session_lifecycle() -> None:
    client = LocalManagerClient(url="http://127.0.0.1:18766")
    session = LocalManagerSession(
        client=client,
        worker_id="worker-session-1",
        worker_kind="cli",
        capabilities=["cli"],
        action_types=["run"],
    )
    assert session.enabled is True

    # 1. Start lifecycle with claim item
    with patch.object(
        client,
        "register_worker",
        return_value={"decision": {"action": "continue"}},
    ), patch.object(
        client,
        "claim_action",
        return_value={"item": {"id": "act-101"}},
    ):
        reply = session.start(project=Path("/tmp/p"), metadata={"run_id": "r1"})
        assert reply == {"decision": {"action": "continue"}}
        assert session.action_id == "act-101"
        assert session.should_stop() is False

    # 2. Heartbeat
    with patch.object(
        client,
        "heartbeat_worker",
        return_value={"decision": {"action": "continue"}},
    ) as mock_hb:
        hb_reply = session.heartbeat(health="ok", conflict=False)
        assert hb_reply == {"decision": {"action": "continue"}}
        mock_hb.assert_called_once()

    # 3. Complete action
    with patch.object(client, "complete_action") as mock_comp:
        session.complete(status="completed", result={"output": "all passed"})
        mock_comp.assert_called_once_with(
            action_id="act-101",
            worker_id="worker-session-1",
            status="completed",
            result={"output": "all passed"},
        )


def test_local_manager_session_early_stop() -> None:
    client = LocalManagerClient(url="http://127.0.0.1:18766")
    session = LocalManagerSession(
        client=client,
        worker_id="worker-session-2",
        worker_kind="cli",
        capabilities=["cli"],
    )

    # If register reply orders quarantine/shutdown, claim_action should not be called
    with patch.object(
        client,
        "register_worker",
        return_value={"decision": {"action": "drain-and-exit"}},
    ), patch.object(client, "claim_action") as mock_claim:
        reply = session.start()
        assert reply == {"decision": {"action": "drain-and-exit"}}
        assert session.should_stop() is True
        mock_claim.assert_not_called()
        assert session.action_id is None

    # Complete when action_id is None should do nothing
    with patch.object(client, "complete_action") as mock_comp:
        session.complete(status="aborted")
        mock_comp.assert_not_called()
