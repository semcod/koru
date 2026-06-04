"""Tests for GillmIDEControlClient integration."""

from __future__ import annotations

from koru.ide_adapters.gillm_client import build_gillm_ide_client
from koru.ide_client import build_ide_client


def test_build_gillm_ide_client_dry_run_drive() -> None:
    client = build_gillm_ide_client(dry_run=True)
    reply = client.drive("hello", submit=True, ide="cursor")
    assert reply["ok"] is True
    assert reply["backend"] == "dry_run"
    assert reply["tool_id"] == "cursor"


def test_build_ide_client_selects_gillm_backend(monkeypatch) -> None:
    monkeypatch.setenv("KORU_IDE_BACKEND", "gillm")
    monkeypatch.setenv("KORU_OS_INJECTOR_DRY_RUN", "1")
    client = build_ide_client()
    reply = client.drive("probe", submit=False, ide="cursor")
    assert reply["ok"] is True
    assert reply["backend"] in {"dry_run", "gillm", "os_injector"}
