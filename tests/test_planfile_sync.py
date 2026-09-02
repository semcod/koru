from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from koru.queue.planfile_sync import (
    PlanfileSyncConfig,
    load_planfile_sync_config,
    stamp_ticket_integrations,
    sync_after_ticket_create,
    sync_planfile_integrations,
)


def test_stamp_ticket_integrations_merges_without_duplicates() -> None:
    ticket = {"integration": ["github"]}
    changed = stamp_ticket_integrations(ticket, ["github", "gitlab"])
    assert changed is True
    assert ticket["integration"] == ["github", "gitlab"]


def test_load_planfile_sync_config_reads_policy_section(tmp_path: Path) -> None:
    policy_dir = tmp_path / ".planfile" / ".koru"
    policy_dir.mkdir(parents=True)
    (policy_dir / "policy.yaml").write_text(
        yaml.safe_dump(
            {
                "planfile_sync": {
                    "enabled": True,
                    "integrations": ["github"],
                    "on_create": True,
                    "on_update": False,
                }
            }
        ),
        encoding="utf-8",
    )
    config = load_planfile_sync_config(tmp_path)
    assert config == PlanfileSyncConfig(
        enabled=True,
        integrations=("github",),
        direction="to",
        on_create=True,
        on_update=False,
    )


def test_sync_after_ticket_create_stamps_and_syncs(tmp_path: Path, monkeypatch) -> None:
    policy_dir = tmp_path / ".planfile" / ".koru"
    policy_dir.mkdir(parents=True)
    (policy_dir / "policy.yaml").write_text("planfile_sync:\n  integrations: [github]\n", encoding="utf-8")

    sync_calls: list[str] = []

    def _fake_sync_integration(integration: str, project: Path, *, direction: str, dry_run: bool) -> str | None:
        sync_calls.append(integration)
        return None

    monkeypatch.setattr("koru.queue.planfile_sync._sync_integration", _fake_sync_integration)
    result = sync_after_ticket_create(tmp_path, "REFACTOR-001")
    assert result.ok is True
    assert sync_calls == ["github"]


def test_sync_planfile_integrations_noops_when_disabled(tmp_path: Path, monkeypatch) -> None:
    policy_dir = tmp_path / ".planfile" / ".koru"
    policy_dir.mkdir(parents=True)
    (policy_dir / "policy.yaml").write_text("planfile_sync:\n  enabled: false\n", encoding="utf-8")

    with patch("planfile.cli.groups.sync.core.sync_integration") as mocked:
        result = sync_planfile_integrations(tmp_path)
    assert result.ok is True
    assert result.integrations == ()
    mocked.assert_not_called()
