"""Tests for autonomous idle diagnostics helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from koru.autonomous_diagnostics import build_idle_checks, run_idle_diagnostics


def test_build_idle_checks_quick_profile_skips_deep_tools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("koru.autonomous_diagnostics.shutil.which", lambda name: name == "regix")
    checks = build_idle_checks(tmp_path, "quick")
    assert [c[0] for c in checks] == ["regix"]


def test_build_idle_checks_full_includes_redup_when_available(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "koru.autonomous_diagnostics.shutil.which",
        lambda name: name in {"regix", "redup"},
    )
    checks = build_idle_checks(tmp_path, "full")
    assert "regix" in [c[0] for c in checks]
    assert "redup" in [c[0] for c in checks]


def test_build_idle_checks_deep_refreshes_code2llm_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "koru.autonomous_diagnostics.shutil.which",
        lambda name: name == "code2llm",
    )

    checks = build_idle_checks(tmp_path, "deep")
    code2llm_check = next(check for check in checks if check[0] == "code2llm")

    assert code2llm_check[2][:7] == [
        "code2llm",
        "./",
        "-f",
        "all",
        "-o",
        "./project",
        "--no-chunk",
    ]
    assert "*.md" in code2llm_check[2]
    assert "node_modules/**" in code2llm_check[2]
    assert "project/**" in code2llm_check[2]


def test_build_idle_checks_full_uses_changed_redup_when_wup_configured(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "wup.yaml").write_text("project:\n  name: test\n", encoding="utf-8")
    monkeypatch.setattr(
        "koru.autonomous_diagnostics.shutil.which",
        lambda name: name in {"redup", "wup"},
    )

    checks = build_idle_checks(tmp_path, "full")
    redup_check = next(check for check in checks if check[0] == "redup")

    assert redup_check[2][:4] == [
        sys.executable,
        "-m",
        "koru.redup_integration",
        "changed-scan",
    ]
    assert ".redup/wup-changed.json" in redup_check[2]


def test_run_idle_diagnostics_profile_off() -> None:
    messages: list[str] = []

    result = run_idle_diagnostics(
        stdio_info=lambda msg, *, fmt: messages.append(msg),
        is_topology_enabled=lambda *_a, **_k: True,
        run_command=lambda *_a, **_k: True,
        clear_marker=lambda *_a, **_k: None,
        create_ticket=lambda **_k: None,
        make_result=lambda status, failed: {"status": status, "failed": failed},
        project=Path("."),
        profile="off",
        cycle=1,
        queue_status="idle",
        diagnostic_tickets=False,
        diagnostic_ticket_queue="default",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=Path("/tmp/diag"),
        topology_integration=False,
    )
    assert result["status"] == "off"
    assert any("disabled" in m for m in messages)
