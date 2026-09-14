"""Tests for the read-only Wellmanifest fleet freshness scanner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from koru.standard_fleet import (
    StandardCandidate,
    StandardRelease,
    emit_adoption_tickets,
    load_standard_release,
    scan_standard_fleet,
)


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def _init_repo(path: Path, files: dict[str, str], *, remote: str | None = None) -> str:
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.invalid")
    _git(path, "config", "user.name", "Test")
    for relative, content in files.items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    if remote:
        _git(path, "remote", "add", "origin", remote)
    _git(path, "add", ".")
    _git(path, "commit", "-qm", "fixture")
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def _lock(version: str, revision: str) -> str:
    return json.dumps(
        {
            "schema": "new-project.lock/v1",
            "standard": {
                "id": "wellmanifest/new-project",
                "version": version,
                "sourceRepository": "wellmanifest/new-project",
                "sourceRevision": revision,
                "publicationStatus": "published",
            },
            "managedFiles": {},
        }
    )


def test_scan_compares_one_clean_source_and_reports_stale_targets(tmp_path: Path) -> None:
    standard = tmp_path / "new-project"
    standard_revision = _init_repo(standard, {"VERSION": "0.20.29\n"})
    current = tmp_path / "current"
    _init_repo(
        current,
        {
            ".governance/manifest.lock.json": _lock("0.20.29", standard_revision),
        },
        remote="git@github.com:wellmanifest/current.git",
    )
    stale = tmp_path / "stale"
    _init_repo(
        stale,
        {
            ".governance/manifest.lock.json": _lock("0.20.28", "0" * 40),
        },
        remote="https://github.com/wellmanifest/stale.git",
    )
    (stale / "uncommitted.txt").write_text("preserve me\n", encoding="utf-8")
    before_status = subprocess.check_output(["git", "-C", str(stale), "status", "--porcelain"], text=True)

    report = scan_standard_fleet(tmp_path, standard, workers=2)

    assert report.repositories == 2
    assert report.current == 1
    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.identity == "wellmanifest/stale"
    assert candidate.pinned_version == "0.20.28"
    assert candidate.latest_revision == standard_revision
    assert candidate.reasons == ("version-mismatch", "revision-mismatch")
    assert candidate.dirty is True
    assert candidate.linked_worktrees == 0
    after_status = subprocess.check_output(["git", "-C", str(stale), "status", "--porcelain"], text=True)
    assert after_status == before_status


def test_source_must_be_clean_and_release_is_immutable(tmp_path: Path) -> None:
    standard = tmp_path / "new-project"
    revision = _init_repo(standard, {"VERSION": "0.20.29\n"})
    release = load_standard_release(standard)
    assert release == StandardRelease("0.20.29", revision, standard.resolve())

    (standard / "VERSION").write_text("0.20.30\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dirty"):
        load_standard_release(standard)


def test_malformed_lock_is_reported_without_guessing_a_pin(tmp_path: Path) -> None:
    standard = tmp_path / "new-project"
    _init_repo(standard, {"VERSION": "0.20.29\n"})
    target = tmp_path / "malformed"
    _init_repo(
        target,
        {".governance/manifest.lock.json": "{not-json\n"},
        remote="git@github.com:wellmanifest/malformed.git",
    )

    report = scan_standard_fleet(tmp_path, standard)

    assert report.repositories == 1
    candidate = next(item for item in report.candidates if item.path == target)
    assert candidate.identity == "wellmanifest/malformed"
    assert candidate.pinned_version is None
    assert candidate.pinned_revision is None
    assert candidate.reasons == (
        "invalid-standard-lock",
        "version-mismatch",
        "revision-mismatch",
    )


def test_emit_uses_stable_key_and_waiting_input_without_write_authority(
    tmp_path: Path,
) -> None:
    candidate = StandardCandidate(
        path=tmp_path / "target",
        identity="wellmanifest/target",
        pinned_version="0.20.28",
        pinned_revision="0" * 40,
        latest_version="0.20.29",
        latest_revision="a" * 40,
        reasons=("version-mismatch", "revision-mismatch"),
        dirty=True,
        linked_worktrees=2,
    )
    calls: list[dict] = []

    def create_task(project: Path, text: str, **kwargs):
        calls.append({"project": project, "text": text, **kwargs})
        return SimpleNamespace(reused=False)

    emitted, reused, errors = emit_adoption_tickets(
        tmp_path / "planfile",
        [candidate],
        create_task=create_task,
    )

    assert (emitted, reused, errors) == (1, 0, ())
    scaffold = calls[0]["scaffold"]
    assert scaffold["execution_state"] == "waiting_input"
    assert scaffold["executor_kind"] == "human"
    assert scaffold["source_context"]["dedupe_key"].endswith(":" + "a" * 40)
    assert "grants no write or merge authority" in calls[0]["text"]
