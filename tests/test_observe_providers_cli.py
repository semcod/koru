"""Tests for ``koru observe providers`` CLI helpers."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from koruobserve.providers_cli import (
    cmd_providers_list,
    providers_list_payload,
    providers_reset_consent,
    screencast_session_path,
)
from koruvision.providers.detector import probe_capture_providers, provider_diagnostics_rows


def test_provider_diagnostics_rows_marks_selected() -> None:
    ranked, rows = provider_diagnostics_rows()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    names = {row["name"] for row in rows}
    assert "mss" in names or "cli_tools" in names
    for row in rows:
        assert "selected" in row
        assert "rank" in row
    if ranked:
        assert any(row.get("selected") for row in rows)


def test_probe_capture_providers_unknown_name() -> None:
    results = probe_capture_providers("not_a_real_provider_xyz")
    assert len(results) == 1
    assert results[0]["ok"] is False


def test_probe_capture_providers_mss_mocked() -> None:
    from koruvision.providers.base import ProviderAvailability

    fake_frame = {
        "payload": b"\x89PNG\r\n\x1a\n" + b"\x00" * 20,
        "width": 2,
        "height": 2,
        "monitor_id": 0,
    }
    avail = ProviderAvailability(available=True, reason="ok")
    with mock.patch(
        "koruvision.providers.mss.MssProvider.capture_all",
        return_value=[fake_frame],
    ):
        with mock.patch(
            "koruvision.providers.mss.MssProvider.availability",
            return_value=avail,
        ):
            results = probe_capture_providers("mss")
    assert results[0]["ok"] is True
    assert results[0]["frame_count"] == 1


def test_providers_list_payload_structure() -> None:
    payload = providers_list_payload(Path("/tmp/koru-test-providers"))
    assert "providers" in payload
    assert "ranked" in payload
    assert isinstance(payload["providers"], list)


def test_providers_reset_clears_session_file(tmp_path: Path) -> None:
    session = screencast_session_path(tmp_path)
    session.parent.mkdir(parents=True, exist_ok=True)
    session.write_text("{}", encoding="utf-8")
    payload = providers_reset_consent(tmp_path)
    assert payload["ok"] is True
    assert not session.is_file()


def test_cmd_providers_list_prints(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cmd_providers_list(Path.cwd(), json_out=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "koru observe providers" in out
    assert "portal_screencast" in out or "mss" in out
