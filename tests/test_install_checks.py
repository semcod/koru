"""Tests for install_checks module (R-IM1 extraction).

These tests target the extracted check_* helpers directly, providing
focused coverage independent of the install_manager orchestration layer.
"""

from __future__ import annotations

from pathlib import Path

from koru.autopilot.install_checks import (
    ManagerIssue,
    check_daemon_issues,
    check_koru_path_issues,
    check_plugin_installed_ok_but_not_connected_issue,
    check_plugin_installed_version_mismatch_issue,
    check_plugin_live_host_stale_issue,
    check_plugin_not_connected_issue,
    check_plugin_version_mismatch_issue,
    check_plugin_version_missing_issue,
    check_pyenv_shim_issue,
    check_version_mismatch_issue,
    is_pyenv_shim,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_is_pyenv_shim_true_for_pyenv_shim_path() -> None:
    assert is_pyenv_shim(Path("/home/user/.pyenv/shims/koru")) is True


def test_is_pyenv_shim_false_for_venv_path() -> None:
    assert is_pyenv_shim(Path("/home/user/.venv/bin/koru")) is False


def test_is_pyenv_shim_false_for_none() -> None:
    assert is_pyenv_shim(None) is False


# ---------------------------------------------------------------------------
# ManagerIssue.to_dict serialization preserves install_manager contract
# ---------------------------------------------------------------------------


def test_manager_issue_to_dict_omits_empty_fix() -> None:
    issue = ManagerIssue(code="x", severity="info", message="m")
    payload = issue.to_dict()
    assert "fix" not in payload
    assert payload == {"code": "x", "severity": "info", "message": "m"}


def test_manager_issue_to_dict_includes_fix_when_present() -> None:
    issue = ManagerIssue(code="x", severity="error", message="m", fix="do it")
    payload = issue.to_dict()
    assert payload["fix"] == "do it"


# ---------------------------------------------------------------------------
# Path / environment checks
# ---------------------------------------------------------------------------


def test_check_koru_path_issues_flags_missing_path(tmp_path: Path) -> None:
    issues = check_koru_path_issues(None, None, source_root=tmp_path)
    assert [i.code for i in issues] == ["koru_not_in_path"]


def test_check_koru_path_issues_flags_path_mismatch(tmp_path: Path) -> None:
    issues = check_koru_path_issues(
        Path("/usr/bin/koru"),
        Path("/repo/.venv/bin/koru"),
        source_root=tmp_path,
    )
    assert [i.code for i in issues] == ["koru_path_mismatch"]


def test_check_koru_path_issues_skips_mismatch_when_editable_source_matches(tmp_path: Path) -> None:
    issues = check_koru_path_issues(
        Path("/usr/bin/koru"),
        Path("/repo/.venv/bin/koru"),
        source_root=tmp_path,
        editable_source_root=tmp_path.resolve(),
    )
    assert issues == []


def test_check_pyenv_shim_issue_flags_shim() -> None:
    issues = check_pyenv_shim_issue(Path("/home/u/.pyenv/shims/koru"))
    assert [i.code for i in issues] == ["koru_pyenv_shim"]


def test_check_pyenv_shim_issue_silent_for_venv() -> None:
    assert check_pyenv_shim_issue(Path("/home/u/.venv/bin/koru")) == []


def test_check_version_mismatch_issue_silent_when_versions_match() -> None:
    assert check_version_mismatch_issue("1.0", "1.0") == []


def test_check_version_mismatch_issue_flags_divergence() -> None:
    issues = check_version_mismatch_issue("1.0", "0.9")
    assert [i.code for i in issues] == ["koru_version_mismatch"]


def test_check_version_mismatch_issue_silent_when_either_missing() -> None:
    assert check_version_mismatch_issue(None, "1.0") == []
    assert check_version_mismatch_issue("1.0", None) == []


# ---------------------------------------------------------------------------
# Daemon / plugin checks
# ---------------------------------------------------------------------------


def test_check_daemon_issues_warns_when_not_running() -> None:
    issues = check_daemon_issues({"running": False})
    assert [i.code for i in issues] == ["daemon_not_running"]


def test_check_daemon_issues_silent_when_running() -> None:
    assert check_daemon_issues({"running": True}) == []


def test_check_plugin_version_missing_issue_flags_connected_without_version() -> None:
    issues = check_plugin_version_missing_issue(
        {"running": True},
        {"connected": True, "connected_version": None},
        "vscode",
    )
    assert [i.code for i in issues] == ["plugin_version_missing"]


def test_check_plugin_version_missing_issue_silent_when_version_present() -> None:
    issues = check_plugin_version_missing_issue(
        {"running": True},
        {"connected": True, "connected_version": "0.1.75"},
        "vscode",
    )
    assert issues == []


def test_check_plugin_installed_version_mismatch_issue_flags_old_install() -> None:
    issues = check_plugin_installed_version_mismatch_issue(
        {"installed_version": "0.1.70", "expected_version": "0.1.75"},
        "vscode",
    )
    codes = [i.code for i in issues]
    assert codes == ["plugin_installed_version_mismatch"]
    assert issues[0].severity == "error"


def test_check_plugin_installed_ok_but_not_connected_issue_severity_is_info() -> None:
    issues = check_plugin_installed_ok_but_not_connected_issue(
        {"running": False},
        {"connected": False, "installed_version": "0.1.75", "expected_version": "0.1.75"},
        "vscode",
    )
    assert [i.code for i in issues] == ["plugin_installed_ok_but_not_connected"]
    assert issues[0].severity == "info"


def test_check_plugin_live_host_stale_issue_flags_stale_reconnects() -> None:
    issues = check_plugin_live_host_stale_issue(
        {
            "running": True,
            "rejected_plugins": [
                {"ide": "vscode", "version": "0.1.70", "expected_version": "0.1.75"},
                {"ide": "vscode", "version": "0.1.72", "expected_version": "0.1.75"},
            ],
        },
        {"installed_version": "0.1.75", "expected_version": "0.1.75"},
        "vscode",
    )
    assert [i.code for i in issues] == ["plugin_live_host_stale"]
    assert "0.1.70, 0.1.72" in issues[0].message


def test_check_plugin_version_mismatch_issue_flags_connected_mismatch() -> None:
    issues = check_plugin_version_mismatch_issue(
        {"running": True},
        {
            "connected": True,
            "connected_version": "0.1.70",
            "expected_version": "0.1.75",
        },
        "vscode",
    )
    assert [i.code for i in issues] == ["plugin_version_mismatch"]


def test_check_plugin_not_connected_issue_when_daemon_running_without_plugin() -> None:
    issues = check_plugin_not_connected_issue(
        {"running": True},
        {"connected": False},
        "vscode",
    )
    assert [i.code for i in issues] == ["plugin_not_connected"]


def test_check_plugin_not_connected_issue_mentions_reload_after_stale_rejection() -> None:
    issues = check_plugin_not_connected_issue(
        {
            "running": True,
            "rejected_plugins": [
                {"ide": "vscode", "version": "0.1.74", "expected_version": "0.1.75"},
            ],
        },
        {"connected": False},
        "vscode",
    )

    assert [i.code for i in issues] == ["plugin_not_connected"]
    assert "Developer: Reload Window" in (issues[0].fix or "")


def test_check_plugin_not_connected_issue_silent_when_daemon_down() -> None:
    assert (
        check_plugin_not_connected_issue({"running": False}, {"connected": False}, "vscode")
        == []
    )
