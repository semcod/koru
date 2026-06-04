"""Regression tests for doctor refactoring.

Tests verify that the doctor module works correctly after extracting
constants and problem catalog into doctor_constants.py.
"""


def test_doctor_constants_module_exists():
    """Verify that doctor_constants module can be imported."""
    from koru import doctor_constants

    assert doctor_constants is not None


def test_doctor_constants_status_values():
    """Verify that status constants have correct values."""
    from koru.doctor_constants import FAIL, PASS, SKIP, WARN

    assert FAIL == "fail"
    assert PASS == "pass"
    assert SKIP == "skip"
    assert WARN == "warn"


def test_doctor_constants_problem_catalog():
    """Verify that problem catalog is properly defined."""
    from koru.doctor_constants import _PROBLEM_CATALOG, ProblemCatalogEntry

    assert isinstance(_PROBLEM_CATALOG, tuple)
    assert len(_PROBLEM_CATALOG) >= 20  # Should have at least 20 problem entries
    assert all(isinstance(entry, ProblemCatalogEntry) for entry in _PROBLEM_CATALOG)


def test_doctor_imports_from_constants():
    """Verify that doctor.py can import constants from doctor_constants."""
    from koru.doctor import _PROBLEM_CATALOG, FAIL, PASS, SKIP, WARN, ProblemCatalogEntry

    assert FAIL == "fail"
    assert PASS == "pass"
    assert SKIP == "skip"
    assert WARN == "warn"
    assert ProblemCatalogEntry.__name__ == "ProblemCatalogEntry"
    assert isinstance(_PROBLEM_CATALOG, tuple)
    assert len(_PROBLEM_CATALOG) >= 20


def test_doctor_constants_vs_doctor_consistency():
    """Verify that doctor_constants exports match doctor.py imports."""
    from koru import doctor, doctor_constants

    # Check that constants are identical
    assert doctor.FAIL == doctor_constants.FAIL
    assert doctor.PASS == doctor_constants.PASS
    assert doctor.WARN == doctor_constants.WARN
    assert doctor.SKIP == doctor_constants.SKIP

    # Check that problem catalog values match (not necessarily the same object)
    assert doctor._PROBLEM_CATALOG == doctor_constants._PROBLEM_CATALOG
    assert doctor.ProblemCatalogEntry is doctor_constants.ProblemCatalogEntry


def test_doctor_report_models_are_reexported():
    """Verify extracted report models remain available from koru.doctor."""
    from koru import doctor, doctor_models

    assert doctor.Check is doctor_models.Check
    assert doctor.DoctorReport is doctor_models.DoctorReport


def test_doctor_runner_uses_facade_symbols(monkeypatch, tmp_path):
    """Moved runner must still honor monkeypatches on the doctor facade."""
    from koru import doctor, doctor_runner

    monkeypatch.setattr(
        doctor_runner,
        "probe_specs",
        lambda _project: [("git_repo", "_check_git_repo")],
    )
    monkeypatch.setattr(
        doctor,
        "_check_git_repo",
        lambda _project: ("warn", "patched facade check"),
    )

    report = doctor.run_diagnostics(tmp_path)

    assert report.checks[0].name == "git_repo"
    assert report.checks[0].status == "warn"
    assert report.checks[0].detail == "patched facade check"


def test_doctor_runner_probe_specs_keep_conditionals(tmp_path):
    """Verify moved probe registry preserves git and pytest conditional checks."""
    from koru import doctor_runner

    names = [name for name, _attr in doctor_runner.probe_specs(tmp_path)]
    assert "gitignore" not in names
    assert "pytest_collect" not in names
    assert names[-1] == "ci_command"

    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    names = [name for name, _attr in doctor_runner.probe_specs(tmp_path)]
    assert "gitignore" in names
    assert names[-2:] == ["ci_command", "pytest_collect"]


def test_doctor_project_checks_are_reexported():
    """Verify extracted project checks remain available from koru.doctor."""
    from koru import doctor, doctor_project_checks

    assert (
        doctor._check_detected_environment
        is doctor_project_checks._check_detected_environment
    )
    assert (
        doctor._check_detected_configuration
        is doctor_project_checks._check_detected_configuration
    )
    assert (
        doctor._detected_configuration_presence_bits
        is doctor_project_checks._detected_configuration_presence_bits
    )
    assert (
        doctor._detected_configuration_json_bits
        is doctor_project_checks._detected_configuration_json_bits
    )


def test_doctor_autopilot_checks_are_reexported():
    """Verify extracted autopilot checks remain available from koru.doctor."""
    from koru import doctor, doctor_autopilot_checks

    assert doctor._selected_autopilot_ide is doctor_autopilot_checks._selected_autopilot_ide
    assert doctor._has_autopilot_selection is doctor_autopilot_checks._has_autopilot_selection
    assert (
        doctor._resolve_autopilot_socket_for_doctor
        is doctor_autopilot_checks._resolve_autopilot_socket_for_doctor
    )
    assert doctor._autopilot_env_snapshot is doctor_autopilot_checks._autopilot_env_snapshot
    assert (
        doctor._autopilot_env_detail_bits
        is doctor_autopilot_checks._autopilot_env_detail_bits
    )
    assert doctor._autopilot_env_status is doctor_autopilot_checks._autopilot_env_status
    assert doctor._check_autopilot_env is doctor_autopilot_checks._check_autopilot_env
    assert doctor._check_autopilot_socket is doctor_autopilot_checks._check_autopilot_socket
    assert doctor._check_autopilot_manage is doctor_autopilot_checks._check_autopilot_manage
    assert doctor._check_ide_runtime_presence is doctor_autopilot_checks._check_ide_runtime_presence


def test_doctor_plugin_bundle_checks_are_reexported():
    """Verify extracted plugin bundle checks remain available from koru.doctor."""
    from koru import doctor, doctor_plugin_bundle

    assert (
        doctor._check_autopilot_plugin_bundle
        is doctor_plugin_bundle._check_autopilot_plugin_bundle
    )
    assert doctor._read_json_file is doctor_plugin_bundle._read_json_file
    assert doctor._package_lock_root_version is doctor_plugin_bundle._package_lock_root_version
    assert (
        doctor._autopilot_plugin_bundle_detail_bits
        is doctor_plugin_bundle._autopilot_plugin_bundle_detail_bits
    )
    assert (
        doctor._autopilot_plugin_bundle_issues
        is doctor_plugin_bundle._autopilot_plugin_bundle_issues
    )
    assert (
        doctor._autopilot_plugin_bundle_paths
        is doctor_plugin_bundle._autopilot_plugin_bundle_paths
    )


def test_doctor_runtime_checks_are_reexported():
    """Verify extracted runtime checks remain available from koru.doctor."""
    from koru import doctor, doctor_runtime_checks

    assert (
        doctor._check_koru_runtime_identity
        is doctor_runtime_checks._check_koru_runtime_identity
    )
    assert doctor._check_python_venv_alignment is doctor_runtime_checks._check_python_venv_alignment
    assert doctor._read_project_version is doctor_runtime_checks._read_project_version
    assert doctor._installed_koru_version is doctor_runtime_checks._installed_koru_version
    assert (
        doctor._path_koru_supports_auto_subcommand
        is doctor_runtime_checks._path_koru_supports_auto_subcommand
    )
    assert doctor._koru_path_version_issues is doctor_runtime_checks._koru_path_version_issues
    assert doctor._is_relative_to is doctor_runtime_checks._is_relative_to


def test_doctor_autopilot_debug_checks_are_reexported():
    """Verify extracted autopilot debug helpers remain available from koru.doctor."""
    from koru import doctor, doctor_autopilot_debug

    assert doctor._autopilot_debug_log_path is doctor_autopilot_debug.autopilot_debug_log_path
    assert (
        doctor._read_recent_autopilot_activity_lines
        is doctor_autopilot_debug.read_recent_autopilot_activity_lines
    )
    assert doctor._autopilot_debug_event_name is doctor_autopilot_debug.autopilot_debug_event_name
    assert (
        doctor._daemon_console_logs_for_doctor
        is doctor_autopilot_debug.daemon_console_logs_for_doctor
    )
    assert (
        doctor._plugin_console_entry_matches_selected
        is doctor_autopilot_debug.plugin_console_entry_matches_selected
    )
