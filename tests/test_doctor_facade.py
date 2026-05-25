"""Regression tests for doctor refactoring.

Tests verify that the doctor module works correctly after extracting
constants and problem catalog into doctor_constants.py.
"""

import pytest


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
    from koru.doctor_constants import ProblemCatalogEntry, _PROBLEM_CATALOG

    assert isinstance(_PROBLEM_CATALOG, tuple)
    assert len(_PROBLEM_CATALOG) >= 20  # Should have at least 20 problem entries
    assert all(isinstance(entry, ProblemCatalogEntry) for entry in _PROBLEM_CATALOG)


def test_doctor_imports_from_constants():
    """Verify that doctor.py can import constants from doctor_constants."""
    from koru.doctor import FAIL, PASS, SKIP, WARN, ProblemCatalogEntry, _PROBLEM_CATALOG

    assert FAIL == "fail"
    assert PASS == "pass"
    assert SKIP == "skip"
    assert WARN == "warn"
    assert isinstance(_PROBLEM_CATALOG, tuple)
    assert len(_PROBLEM_CATALOG) >= 20


def test_doctor_constants_vs_doctor_consistency():
    """Verify that doctor_constants exports match doctor.py imports."""
    from koru import doctor
    from koru import doctor_constants

    # Check that constants are identical
    assert doctor.FAIL == doctor_constants.FAIL
    assert doctor.PASS == doctor_constants.PASS
    assert doctor.WARN == doctor_constants.WARN
    assert doctor.SKIP == doctor_constants.SKIP

    # Check that problem catalog values match (not necessarily the same object)
    assert doctor._PROBLEM_CATALOG == doctor_constants._PROBLEM_CATALOG
    assert doctor.ProblemCatalogEntry is doctor_constants.ProblemCatalogEntry


def test_doctor_project_checks_are_reexported():
    """Verify extracted project checks remain available from koru.doctor."""
    from koru import doctor
    from koru import doctor_project_checks

    assert doctor._check_detected_environment is doctor_project_checks._check_detected_environment
    assert doctor._check_detected_configuration is doctor_project_checks._check_detected_configuration
    assert (
        doctor._detected_configuration_presence_bits
        is doctor_project_checks._detected_configuration_presence_bits
    )
    assert doctor._detected_configuration_json_bits is doctor_project_checks._detected_configuration_json_bits


def test_doctor_plugin_bundle_checks_are_reexported():
    """Verify extracted plugin bundle checks remain available from koru.doctor."""
    from koru import doctor
    from koru import doctor_plugin_bundle

    assert doctor._check_autopilot_plugin_bundle is doctor_plugin_bundle._check_autopilot_plugin_bundle
    assert doctor._read_json_file is doctor_plugin_bundle._read_json_file
    assert doctor._package_lock_root_version is doctor_plugin_bundle._package_lock_root_version
    assert (
        doctor._autopilot_plugin_bundle_detail_bits
        is doctor_plugin_bundle._autopilot_plugin_bundle_detail_bits
    )
    assert doctor._autopilot_plugin_bundle_issues is doctor_plugin_bundle._autopilot_plugin_bundle_issues
    assert doctor._autopilot_plugin_bundle_paths is doctor_plugin_bundle._autopilot_plugin_bundle_paths


def test_doctor_runtime_checks_are_reexported():
    """Verify extracted runtime checks remain available from koru.doctor."""
    from koru import doctor
    from koru import doctor_runtime_checks

    assert doctor._check_koru_runtime_identity is doctor_runtime_checks._check_koru_runtime_identity
    assert doctor._check_python_venv_alignment is doctor_runtime_checks._check_python_venv_alignment
    assert doctor._read_project_version is doctor_runtime_checks._read_project_version
    assert doctor._installed_koru_version is doctor_runtime_checks._installed_koru_version
    assert (
        doctor._path_koru_supports_auto_subcommand
        is doctor_runtime_checks._path_koru_supports_auto_subcommand
    )
    assert doctor._koru_path_version_issues is doctor_runtime_checks._koru_path_version_issues
    assert doctor._is_relative_to is doctor_runtime_checks._is_relative_to
