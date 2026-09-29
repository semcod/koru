from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("planfile")

from koru.queue.runner import _run_next_planfile_task_impl
from koru.queue.runners import run_process


class _EmptyPlanfile:
    def next_ticket(self, queue=None):
        return None

    def list_tickets(self, status=None):
        return []


def test_empty_queue_returns_idle_instead_of_assertion(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "planfile.Planfile.auto_discover", staticmethod(lambda project: _EmptyPlanfile())
    )

    result = _run_next_planfile_task_impl(
        project=tmp_path,
        actor="tester",
        queue_name=None,
        planfile_runner=run_process,
    )

    assert result.status == "idle"
    assert "runnable" in (result.message or "")
