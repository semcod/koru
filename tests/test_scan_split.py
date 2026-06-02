from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru.scan_collection import collect_suggestions as collect_suggestions_impl
from koru.scan_dedupe_policy import existing_scan_titles_from_payload, scan_duplicate_skip
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
