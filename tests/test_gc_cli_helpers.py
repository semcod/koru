"""Tests for gc CLI helpers."""

from __future__ import annotations

from koru.gc import GcCandidate, GcResult
from koru.gc_cli_helpers import gc_result_to_json, gc_statuses_from_args, print_gc_text_report


def test_gc_statuses_from_args_splits_csv() -> None:
    assert gc_statuses_from_args("done, closed ") == frozenset({"done", "closed"})


def test_gc_result_to_json_shape() -> None:
    result = GcResult(
        candidates=[
            GcCandidate("PLF-1", "x", "done", "done", None, 30.0),
        ],
        removed=["PLF-1"],
        dry_run=True,
    )
    payload = gc_result_to_json(result)
    assert payload["dry_run"] is True
    assert payload["candidates"][0]["ticket_id"] == "PLF-1"


def test_print_gc_text_report_empty(capsys) -> None:
    print_gc_text_report(GcResult(dry_run=True), max_age_days=90)
    assert "no stale tickets" in capsys.readouterr().out
