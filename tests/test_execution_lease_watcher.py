from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import yaml

from koru.autonomy.execution_lease_watcher import (
    TAKEOVER_GRACE_SECONDS,
    emit_takeover_notices,
    takeover_at,
)


def _write_tickets(project: Path, tickets: list[dict]) -> None:
    path = project / ".planfile" / "sprints" / "current.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"sprint": {"tickets": {ticket["id"]: ticket for ticket in tickets}}}),
        encoding="utf-8",
    )


def _ok() -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_takeover_at_uses_fixed_grace_period() -> None:
    expiry = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    ticket = {"execution": {"lease_expires_at": expiry.isoformat()}}

    assert takeover_at(ticket) == expiry + timedelta(seconds=TAKEOVER_GRACE_SECONDS)


def test_expiry_emits_one_non_runnable_deduplicated_notice(tmp_path: Path) -> None:
    now = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    expiry = now - timedelta(seconds=TAKEOVER_GRACE_SECONDS + 1)
    target = {
        "id": "PLF-7",
        "status": "in_progress",
        "execution": {
            "assigned_to": "actor-old",
            "lease_expires_at": expiry.isoformat(),
        },
    }
    _write_tickets(tmp_path, [target])
    created: list[dict] = []

    def create_task(project: Path, description: str, **kwargs):
        created.append({"description": description, **kwargs})
        notice = {
            "id": "PLF-8",
            "status": "open",
            "source": {
                "tool": "koru-execution-lease-watcher",
                "context": kwargs["scaffold"]["source_context"],
            },
            "execution": {"state": "waiting_input", "queue": "handoff"},
        }
        _write_tickets(project, [target, notice])
        return SimpleNamespace(ticket_id="PLF-8")

    calls: list[list[str]] = []

    def runner(command, _project):
        calls.append(list(command))
        return _ok()

    assert emit_takeover_notices(tmp_path, now=now, runner=runner, create_task=create_task) == 1
    assert len(created) == 1
    assert created[0]["scaffold"]["execution_state"] == "waiting_input"
    assert created[0]["scaffold"]["source_context"]["dedupe_key"] == (
        "koru:execution-lease-takeover:PLF-7"
    )
    assert "not write authority" in created[0]["description"]

    # A later cycle refreshes the existing notice instead of creating another.
    assert emit_takeover_notices(tmp_path, now=now, runner=runner, create_task=create_task) == 1
    assert len(created) == 1
    assert calls == [["planfile", "ticket", "update", "PLF-8", "--description", calls[0][-1]]]


def test_malformed_or_missing_expiry_never_emits_notice(tmp_path: Path) -> None:
    _write_tickets(
        tmp_path,
        [
            {"id": "PLF-bad", "status": "in_progress", "execution": {"lease_expires_at": "nope"}},
            {"id": "PLF-missing", "status": "in_progress", "execution": {}},
        ],
    )
    created: list[object] = []

    assert emit_takeover_notices(
        tmp_path,
        now=datetime.now(UTC),
        runner=lambda _command, _project: _ok(),
        create_task=lambda *_args, **_kwargs: created.append(json.dumps(_kwargs)),
    ) == 0
    assert created == []


def test_renewed_lease_resolves_existing_notice(tmp_path: Path) -> None:
    now = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    expired = now - timedelta(seconds=TAKEOVER_GRACE_SECONDS + 1)
    renewed = now + timedelta(hours=1)
    target = {
        "id": "PLF-9",
        "status": "in_progress",
        "execution": {"lease_expires_at": expired.isoformat()},
    }
    notice = {
        "id": "PLF-10",
        "status": "open",
        "source": {
            "tool": "koru-execution-lease-watcher",
            "context": {
                "signal": "execution_lease_takeover",
                "target_ticket_id": "PLF-9",
            },
        },
    }
    _write_tickets(tmp_path, [target, notice])
    calls: list[list[str]] = []

    def runner(command, _project):
        calls.append(list(command))
        return _ok()

    target["execution"]["lease_expires_at"] = renewed.isoformat()
    _write_tickets(tmp_path, [target, notice])

    assert emit_takeover_notices(tmp_path, now=now, runner=runner) == 1
    assert calls and calls[0][1:] == [
        "ticket",
        "done",
        "PLF-10",
        "--note",
        "Lease renewed for PLF-9; takeover notice resolved.",
        "--actor",
        "koru",
    ]
