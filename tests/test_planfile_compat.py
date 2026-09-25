"""Behavior pinning for `koru.planfile_compat.merge_missing_ticket_records`.

The merge must stay a read-only compatibility layer: reported (validated)
records stay authoritative, raw sprint records the CLI could not parse are
recovered with an operator-facing diagnostic, and the report counts stay
derivable from the recovered payload alone.
"""

from __future__ import annotations

from pathlib import Path

from koru.planfile_compat import (
    LEGACY_STATUS,
    PlanfileCompatibilityReport,
    merge_missing_ticket_records,
)


def write_sprint(project: Path, name: str, body: str) -> None:
    sprint_dir = project / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    (sprint_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_no_sprint_directory_returns_empty_report(tmp_path: Path) -> None:
    merged, report = merge_missing_ticket_records([], tmp_path)

    assert merged == []
    assert report == PlanfileCompatibilityReport()
    assert report.migration_candidate_count == 0


def test_legacy_skipped_record_is_recovered_with_diagnostic(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "current",
        """sprint:
  tickets:
    PLF-1:
      id: PLF-1
      name: Historical work
      status: skipped
""",
    )

    merged, report = merge_missing_ticket_records([], tmp_path)

    assert [record["id"] for record in merged] == ["PLF-1"]
    record = merged[0]
    assert record["legacy_status"] == "skipped"
    assert record["status_diagnostic"] == {
        "kind": "legacy-status",
        "status": "skipped",
        "action": "run koru queue migrate-legacy-skipped --apply",
    }
    assert "_compat_sprint" not in record
    assert report.raw_ticket_count == 1
    assert report.reported_ticket_count == 0
    assert report.recovered_ticket_count == 1
    assert report.migration_candidate_count == 1
    assert report.legacy_status_counts == {"skipped": 1}
    assert report.unknown_status_count == 0
    assert report.read_errors == ()


def test_unknown_status_is_recovered_without_automatic_mutation(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "current",
        """tickets:
  PLF-2:
    ticket_id: PLF-2
    name: Weird state
    status: Frozen
""",
    )

    merged, report = merge_missing_ticket_records([], tmp_path)

    record = merged[0]
    assert record["legacy_status"] == "frozen"
    assert record["status_diagnostic"] == {
        "kind": "unknown-status",
        "status": "frozen",
        "action": "inspect and migrate explicitly; no automatic mutation",
    }
    assert report.legacy_status_counts == {"frozen": 1}
    assert report.unknown_status_count == 1
    assert report.migration_candidate_count == 0


def test_missing_status_counts_as_missing_and_recovers_undecorated_field(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "current",
        """tickets:
  PLF-3:
    id: PLF-3
    name: No status at all
""",
    )

    merged, report = merge_missing_ticket_records([], tmp_path)

    record = merged[0]
    assert record["legacy_status"] is None
    assert record["status_diagnostic"] == {
        "kind": "unknown-status",
        "status": None,
        "action": "inspect and migrate explicitly; no automatic mutation",
    }
    assert report.legacy_status_counts == {"<missing>": 1}
    assert report.unknown_status_count == 1


def test_supported_status_is_recovered_without_diagnostic(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "current",
        """tickets:
  PLF-4:
    id: PLF-4
    status: in_progress
  PLF-5:
    id: PLF-5
    status: Ready
""",
    )

    merged, report = merge_missing_ticket_records([], tmp_path)

    by_id = {record["id"]: record for record in merged}
    assert set(by_id) == {"PLF-4", "PLF-5"}
    for record in merged:
        assert "legacy_status" not in record
        assert "status_diagnostic" not in record
    assert report.recovered_ticket_count == 2
    assert report.legacy_status_counts == {}
    assert report.unknown_status_count == 0


def test_reported_payload_stays_authoritative_for_shared_ids(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "current",
        """tickets:
  PLF-6:
    id: PLF-6
    status: skipped
  PLF-7:
    ticket_id: PLF-7
    status: open
""",
    )
    reported = [
        {"id": "PLF-6", "status": "done", "source": "cli"},
        {"ticket_id": " PLF-7 ", "status": "review"},
    ]

    merged, report = merge_missing_ticket_records(reported, tmp_path)

    assert merged[:2] == reported
    assert report.recovered_ticket_count == 0
    assert report.reported_ticket_count == 2
    assert report.raw_ticket_count == 2
    assert report.legacy_status_counts == {}


def test_non_dict_reported_entries_are_ignored(tmp_path: Path) -> None:
    merged, report = merge_missing_ticket_records(["nonsense", None, 3], tmp_path)

    assert merged == []
    assert report.reported_ticket_count == 0


def test_duplicate_raw_ids_are_recovered_once(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "alpha",
        """tickets:
  PLF-8:
    id: PLF-8
    status: skipped
""",
    )
    write_sprint(
        tmp_path,
        "beta",
        """tickets:
  PLF-8:
    id: PLF-8
    status: skipped
""",
    )

    merged, report = merge_missing_ticket_records([], tmp_path)

    assert [record["id"] for record in merged] == ["PLF-8"]
    assert report.raw_ticket_count == 2
    assert report.recovered_ticket_count == 1
    assert report.legacy_status_counts == {"skipped": 1}


def test_mapping_key_is_the_last_id_fallback_and_empty_ids_are_dropped(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "current",
        """tickets:
  PLF-9:
    name: id only in mapping key
    status: open
  PLF-10:
    id: ""
    status: open
""",
    )

    merged, report = merge_missing_ticket_records([], tmp_path)

    assert [record["id"] for record in merged] == ["PLF-9"]
    assert report.raw_ticket_count == 2
    assert report.recovered_ticket_count == 1


def test_corrupt_sprint_file_reports_read_error_and_keeps_going(tmp_path: Path) -> None:
    write_sprint(tmp_path, "broken", "tickets: [unclosed")
    write_sprint(
        tmp_path,
        "healthy",
        """tickets:
  PLF-11:
    id: PLF-11
    status: skipped
""",
    )

    merged, report = merge_missing_ticket_records([], tmp_path)

    assert [record["id"] for record in merged] == ["PLF-11"]
    assert len(report.read_errors) == 1
    assert report.read_errors[0].startswith("broken.yaml: ")


def test_non_dict_documents_and_values_are_skipped(tmp_path: Path) -> None:
    write_sprint(tmp_path, "list-root", "- a\n- b\n")
    write_sprint(tmp_path, "tickets-list", "tickets:\n  - id: PLF-12\n")
    write_sprint(tmp_path, "scalar-ticket", "tickets:\n  PLF-13: skipped\n")

    merged, report = merge_missing_ticket_records([], tmp_path)

    assert merged == []
    assert report.raw_ticket_count == 0


def test_input_list_is_not_mutated_and_result_is_new(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "current",
        """tickets:
  PLF-14:
    id: PLF-14
    status: skipped
""",
    )
    reported = [{"id": "PLF-KEEP", "status": "open"}]
    snapshot = [dict(item) for item in reported]

    merged, report = merge_missing_ticket_records(reported, tmp_path)

    assert reported == snapshot
    assert merged is not reported
    assert merged[0] == snapshot[0]
    assert report.recovered_ticket_count == 1


def test_report_to_dict_round_trip(tmp_path: Path) -> None:
    write_sprint(
        tmp_path,
        "current",
        """tickets:
  PLF-15:
    id: PLF-15
    status: skipped
  PLF-16:
    id: PLF-16
    status: archived
""",
    )

    _merged, report = merge_missing_ticket_records([], tmp_path)

    payload = report.to_dict()
    assert payload == {
        "raw_ticket_count": 2,
        "reported_ticket_count": 0,
        "recovered_ticket_count": 2,
        "migration_candidate_count": 1,
        "legacy_status_counts": {"archived": 1, "skipped": 1},
        "unknown_status_count": 1,
        "read_errors": [],
    }
    assert report.migration_candidate_count == report.legacy_status_counts.get(LEGACY_STATUS)
