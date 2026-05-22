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
