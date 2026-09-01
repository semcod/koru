from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from koru.scan_collection import collect_suggestions as collect_suggestions_impl
from koru.scan_dedupe_policy import (
    evidence_fingerprint,
    existing_scan_history_keys,
    existing_scan_titles_from_payload,
    scan_duplicate_skip,
)
from koru.scan_ticket_emission import apply_scan_suggestions, create_ticket
from koru.scan_types import Suggestion


def _ok(stdout: str = "", returncode: int = 0, stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_collection_path_invokes_expected_probes() -> None:
    project = Path(".")
    calls: list[str] = []

    def _named_probe(name: str):
        def _probe(_project: Path):
            calls.append(name)
            return [Suggestion(signal=name, title=name, description=name)]

        return _probe

    suggestions = collect_suggestions_impl(
        project,
        skip_pytest=True,
        include_semcod_artifacts=False,
        paths=None,
        scan_pytest_collect=_named_probe("pytest"),
        scan_todo_markers=_named_probe("todo"),
        scan_missing_gates=_named_probe("gates"),
        scan_missing_tools=_named_probe("tools"),
        scan_gitignore_drift=_named_probe("gitignore"),
        scan_semcod_quality_artifacts=_named_probe("semcod"),
        filter_suggestions_by_paths=lambda items, _paths: items,
    )

    assert [item.signal for item in suggestions] == ["todo", "gates", "tools", "gitignore"]
    assert calls == ["todo", "gates", "tools", "gitignore"]


def test_dedupe_policy_prefers_signal_key() -> None:
    payload = [
        {
            "name": "Existing",
            "status": "open",
            "source": {"tool": "koru-scan", "context": {"signal": "hot_signal"}},
        },
    ]
    existing = existing_scan_titles_from_payload(payload, source="koru-scan")

    duplicate = scan_duplicate_skip(
        Suggestion(signal="hot_signal", title="New title", description="x"),
        existing,
    )
    assert duplicate is not None
    assert duplicate[0] == "duplicate_signal"


def _evidence(sha256: str, *, path: str = "project/analysis.toon.yaml") -> dict[str, object]:
    return {
        "schema": "koru.ticket_evidence.v1",
        "kind": "code2llm_analysis",
        "artifact": {"path": path, "sha256": sha256, "mtime_ns": 1},
        "regenerate_command": "/host-specific/command",
    }


def _history_entry(
    *,
    source: str = "koru-scan",
    dedupe_key: str = "semcod:code2llm:refactor:src/app.py",
    sha256: str = "a" * 64,
    path: str = "project/analysis.toon.yaml",
) -> dict[str, object]:
    return {
        "name": "Historical finding",
        "status": "done",
        "source": {
            "tool": source,
            "context": {
                "signal": "code2llm_god",
                "dedupe_key": dedupe_key,
                "evidence": _evidence(sha256, path=path),
            },
        },
    }


def _write_history(path: Path, *entries: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"sprint": {"id": path.stem, "tickets": list(entries)}}),
        encoding="utf-8",
    )


def test_history_index_and_direct_history_files_are_loaded(tmp_path: Path) -> None:
    planfile = tmp_path / ".planfile"
    index = planfile / "index" / "history-locations.yaml"
    index.parent.mkdir(parents=True)
    index.write_text(
        yaml.safe_dump(
            {
                "schema": "planfile.history-locations/v1",
                "tickets": {"T-1": "history-indexed", "T-2": "../escape"},
            },
        ),
        encoding="utf-8",
    )
    indexed = _history_entry(dedupe_key="indexed", sha256="a" * 64)
    direct = _history_entry(dedupe_key="direct", sha256="b" * 64)
    _write_history(planfile / "sprints" / "history-indexed.yaml", indexed)
    _write_history(planfile / "sprints" / "history-direct.yaml", direct)

    keys = existing_scan_history_keys(tmp_path, source="koru-scan")

    assert len(keys) == 2
    assert any(":indexed:" in key for key in keys)
    assert any(":direct:" in key for key in keys)


def test_terminal_history_suppresses_identical_evidence_fingerprint(tmp_path: Path) -> None:
    entry = _history_entry()
    _write_history(tmp_path / ".planfile" / "sprints" / "history-one.yaml", entry)
    existing = existing_scan_history_keys(tmp_path, source="koru-scan")
    context = entry["source"]["context"]  # type: ignore[index]
    suggestion = Suggestion(
        signal="code2llm_god",
        title="A renamed finding",
        description="same evidence",
        source_context=dict(context),  # type: ignore[arg-type]
    )

    duplicate = scan_duplicate_skip(
        suggestion,
        existing,
        source="koru-scan",
        suggestion_dedupe_key=lambda _source, _suggestion: "unused",
    )

    assert duplicate is not None
    assert duplicate[0] == "duplicate_history_evidence"


def test_changed_evidence_remains_eligible_for_new_regression(tmp_path: Path) -> None:
    entry = _history_entry(sha256="a" * 64)
    _write_history(tmp_path / ".planfile" / "sprints" / "history-one.yaml", entry)
    existing = existing_scan_history_keys(tmp_path, source="koru-scan")
    suggestion = Suggestion(
        signal="code2llm_god",
        title="Historical finding",
        description="changed evidence",
        source_context={
            "dedupe_key": "semcod:code2llm:refactor:src/app.py",
            "evidence": _evidence("b" * 64),
        },
    )

    assert (
        scan_duplicate_skip(
            suggestion,
            existing,
            source="koru-scan",
            suggestion_dedupe_key=lambda _source, _suggestion: "unused",
        )
        is None
    )


def test_malformed_history_and_unrelated_producer_are_ignored(tmp_path: Path) -> None:
    entries = (
        _history_entry(source="another-tool"),
        _history_entry(path="../outside.yaml"),
        _history_entry(sha256="not-a-sha256"),
        {"name": "legacy title only", "status": "done", "source": "koru-scan"},
    )
    _write_history(tmp_path / ".planfile" / "sprints" / "history-bad.yaml", *entries)

    assert existing_scan_history_keys(tmp_path, source="koru-scan") == set()


def test_evidence_fingerprint_ignores_volatile_metadata() -> None:
    first = _evidence("a" * 64)
    second = _evidence("a" * 64)
    second["artifact"]["mtime_ns"] = 999  # type: ignore[index]
    second["regenerate_command"] = "/different/host"

    assert evidence_fingerprint(first) == evidence_fingerprint(second)


def test_ticket_emission_records_apply_and_duplicate_paths(tmp_path: Path) -> None:
    suggestions = [
        Suggestion(signal="dup", title="Duplicate", description="dup desc"),
        Suggestion(signal="ok", title="Create me", description="ok desc"),
    ]
    decisions: list[tuple[str, str | None]] = []

    result = apply_scan_suggestions(
        tmp_path,
        suggestions,
        source="koru-scan",
        runner=None,
        existing_scan_titles=lambda *_args, **_kwargs: {"Duplicate"},
        scan_duplicate_skip=scan_duplicate_skip,
        create_ticket=lambda *_args, **_kwargs: _ok_result(),
        apply_create_result=lambda suggestion, create_result, **kwargs: _forward_apply_result(
            suggestion,
            create_result,
            decisions,
            **kwargs,
        ),
        log_scan_decision=lambda suggestion, **kwargs: decisions.append(
            (suggestion.signal, kwargs.get("reason"))
        ),
    )

    assert result.applied == ["Create me"]
    assert "Duplicate" in result.skipped


def _ok_result():
    return create_ticket(
        Path("."),
        Suggestion(signal="ok", title="Create me", description="ok"),
        source="koru-scan",
        runner=lambda *_args, **_kwargs: _ok("", returncode=0),
        create_nl_task=lambda *_args, **_kwargs: SimpleNamespace(reused=False),
        format_create_exception=lambda exc: str(exc),
        suggestion_dedupe_key=lambda _source, _suggestion: "k",
        default_runner=lambda *_args, **_kwargs: _ok("", returncode=0),
    )


def _forward_apply_result(
    suggestion: Suggestion,
    create_result,
    decisions: list[tuple[str, str | None]],
    **kwargs,
) -> None:
    if create_result.ok:
        kwargs["applied"].append(suggestion.title)
        decisions.append((suggestion.signal, None))
    else:
        kwargs["skipped"].append(suggestion.title)
