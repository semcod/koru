"""Tests for work LLM provenance and commit notifications."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from koru.work.llm_provenance import notify_work_commit, resolve_work_llm_context


def test_resolve_work_llm_context_reads_strategy_model(tmp_path: Path) -> None:
    (tmp_path / "koru.yaml").write_text(
        """
schema: '1.0'
autonomy:
  strategy:
    id: test
    planning_assistant:
      enabled: true
      provider_order: [openrouter]
      openrouter:
        model: openrouter/qwen/qwen3-coder-next
""".strip(),
        encoding="utf-8",
    )
    ctx = resolve_work_llm_context(tmp_path)
    assert ctx.planning_provider == "openrouter"
    assert ctx.planning_model == "qwen/qwen3-coder-next"
    assert ctx.work_uses_llm is False
    assert ctx.work_llm_mode == "task_profiles+ide_work"


def test_notify_work_commit_uses_desktop_notify(tmp_path: Path) -> None:
    (tmp_path / "koru.yaml").write_text("schema: '1.0'\n", encoding="utf-8")
    with patch("koru.work.llm_provenance.notify_desktop", return_value=True) as notify:
        ok = notify_work_commit(
            tmp_path,
            ticket_id="ticket-027",
            commit_sha="abc123",
            message="planfile: start ticket-027",
        )
    assert ok is True
    notify.assert_called_once()
    title = notify.call_args.kwargs["title"]
    body = notify.call_args.kwargs["body"]
    assert "ticket-027" in title
    assert "abc123" in body
