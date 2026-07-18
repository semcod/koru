"""Tests for koru fleet bootstrap — multi-project discovery + soft ensure."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from koru.cli_fleet import discover_projects, fleet_main
from koru.fleet_bootstrap import (
    BootstrapStatus,
    bootstrap_workspace,
    discover_bootstrap_candidates,
    ensure_koru_project,
    is_koru_managed,
)
from koru.runtime import planfile_dir, runtime_dir


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir()
    return path


def _write_tickets(project: Path, ticket_id: str = "REAL-001") -> Path:
    sprint = planfile_dir(project) / "sprints" / "current.yaml"
    sprint.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "sprint": {
            "id": "current",
            "tickets": {
                ticket_id: {
                    "id": ticket_id,
                    "name": "Keep me",
                    "status": "open",
                    "priority": "high",
                }
            },
        }
    }
    sprint.write_text(yaml.safe_dump(body), encoding="utf-8")
    return sprint


class TestDiscoverBootstrapCandidates:
    def test_finds_git_children_depth_one(self, tmp_path: Path) -> None:
        a = _git_repo(tmp_path / "alpha")
        b = _git_repo(tmp_path / "beta")
        (tmp_path / "plain").mkdir()
        found = discover_bootstrap_candidates(tmp_path, depth=1)
        assert found == sorted([a.resolve(), b.resolve()])

    def test_skips_non_git_by_default(self, tmp_path: Path) -> None:
        (tmp_path / "no-git").mkdir()
        assert discover_bootstrap_candidates(tmp_path) == []

    def test_allow_non_git_via_require_git_false(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()
        found = discover_bootstrap_candidates(tmp_path, require_git=False)
        assert plain.resolve() in found

    def test_exclude_backups(self, tmp_path: Path) -> None:
        keep = _git_repo(tmp_path / "runtime")
        _git_repo(tmp_path / "backups")
        found = discover_bootstrap_candidates(tmp_path)
        assert found == [keep.resolve()]

    def test_include_globs(self, tmp_path: Path) -> None:
        _git_repo(tmp_path / "runtime")
        _git_repo(tmp_path / "logo")
        _git_repo(tmp_path / "core")
        found = discover_bootstrap_candidates(
            tmp_path, include=["runtime", "core"]
        )
        names = {p.name for p in found}
        assert names == {"runtime", "core"}

    def test_umbrella_adds_workspace_root(self, tmp_path: Path) -> None:
        _git_repo(tmp_path / "child")
        found = discover_bootstrap_candidates(tmp_path, umbrella=True)
        assert tmp_path.resolve() in found

    def test_umbrella_with_include_still_adds_root(self, tmp_path: Path) -> None:
        _git_repo(tmp_path / "runtime")
        _git_repo(tmp_path / "logo")
        found = discover_bootstrap_candidates(
            tmp_path, umbrella=True, include=["runtime"]
        )
        names = {p.name for p in found}
        assert tmp_path.resolve() in found
        assert "runtime" in names
        assert "logo" not in names

    def test_depth_two_finds_nested(self, tmp_path: Path) -> None:
        nested = _git_repo(tmp_path / "group" / "nested")
        found = discover_bootstrap_candidates(tmp_path, depth=2)
        assert nested.resolve() in found


class TestEnsureKoruProject:
    def test_fresh_init(self, tmp_path: Path) -> None:
        project = _git_repo(tmp_path / "fresh")
        result = ensure_koru_project(project, prepare_host_environment=False)
        assert result.status == BootstrapStatus.INITIALIZED
        assert is_koru_managed(project)

    def test_idempotent_skip(self, tmp_path: Path) -> None:
        project = _git_repo(tmp_path / "once")
        ensure_koru_project(project, prepare_host_environment=False)
        second = ensure_koru_project(project, prepare_host_environment=False)
        assert second.status == BootstrapStatus.SKIPPED

    def test_soft_ensure_adds_policy_without_clobbering_tickets(
        self, tmp_path: Path
    ) -> None:
        """Regression: must NOT need --force just to add policy.yaml."""
        project = _git_repo(tmp_path / "existing")
        # Simulate a planfile project that never got koru policy.
        pf = planfile_dir(project)
        pf.mkdir(parents=True)
        (pf / "config.yaml").write_text("project: existing\n", encoding="utf-8")
        sprint = _write_tickets(project, "REAL-042")

        result = ensure_koru_project(project, prepare_host_environment=False)
        assert result.status == BootstrapStatus.POLICY_ADDED
        assert is_koru_managed(project)

        data = yaml.safe_load(sprint.read_text(encoding="utf-8"))
        assert "REAL-042" in data["sprint"]["tickets"]
        # Starter tickets must not appear
        assert "STARTER-001" not in data["sprint"]["tickets"]

    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        project = _git_repo(tmp_path / "dry")
        result = ensure_koru_project(project, dry_run=True)
        assert result.status == BootstrapStatus.WOULD_INIT
        assert not (planfile_dir(project) / "config.yaml").exists()
        assert not is_koru_managed(project)

    def test_dry_run_policy_only(self, tmp_path: Path) -> None:
        project = _git_repo(tmp_path / "dry-pf")
        pf = planfile_dir(project)
        pf.mkdir(parents=True)
        (pf / "config.yaml").write_text("project: dry\n", encoding="utf-8")
        result = ensure_koru_project(project, dry_run=True)
        assert result.status == BootstrapStatus.WOULD_ADD_POLICY
        assert not (runtime_dir(project) / "policy.yaml").exists()


class TestBootstrapWorkspace:
    def test_summary_and_fleet_ls_see_new_projects(self, tmp_path: Path) -> None:
        a = _git_repo(tmp_path / "a")
        b = _git_repo(tmp_path / "b")
        summary = bootstrap_workspace(tmp_path, prepare_host_environment=False)
        assert len(summary.results) == 2
        assert all(r.status == BootstrapStatus.INITIALIZED for r in summary.results)
        managed = discover_projects(tmp_path)
        assert set(managed) == {a.resolve(), b.resolve()}

    def test_second_run_all_skipped(self, tmp_path: Path) -> None:
        _git_repo(tmp_path / "a")
        bootstrap_workspace(tmp_path, prepare_host_environment=False)
        again = bootstrap_workspace(tmp_path, prepare_host_environment=False)
        assert all(r.status == BootstrapStatus.SKIPPED for r in again.results)

    def test_no_clobber_across_workspace(self, tmp_path: Path) -> None:
        fresh = _git_repo(tmp_path / "fresh")
        existing = _git_repo(tmp_path / "existing")
        pf = planfile_dir(existing)
        pf.mkdir(parents=True)
        (pf / "config.yaml").write_text("project: existing\n", encoding="utf-8")
        _write_tickets(existing, "KEEP-1")

        summary = bootstrap_workspace(tmp_path, prepare_host_environment=False)
        by_name = {r.project.name: r for r in summary.results}
        assert by_name["fresh"].status == BootstrapStatus.INITIALIZED
        assert by_name["existing"].status == BootstrapStatus.POLICY_ADDED

        sprint = yaml.safe_load(
            (planfile_dir(existing) / "sprints" / "current.yaml").read_text(
                encoding="utf-8"
            )
        )
        assert "KEEP-1" in sprint["sprint"]["tickets"]
        assert is_koru_managed(fresh)
        assert is_koru_managed(existing)


class TestFleetBootstrapCli:
    def test_bootstrap_dry_run_cli(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        _git_repo(tmp_path / "proj")
        rc = fleet_main(["bootstrap", str(tmp_path), "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "would_init" in out
        assert not is_koru_managed(tmp_path / "proj")

    def test_bootstrap_alias_init(self, tmp_path: Path) -> None:
        _git_repo(tmp_path / "proj")
        rc = fleet_main(["init", str(tmp_path)])
        assert rc == 0
        assert is_koru_managed(tmp_path / "proj")

    def test_full_init_then_ls(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        _git_repo(tmp_path / "proj")
        assert fleet_main(["bootstrap", str(tmp_path)]) == 0
        assert fleet_main(["ls", "--workspace", str(tmp_path)]) == 0
        assert str((tmp_path / "proj").resolve()) in capsys.readouterr().out
