"""Interpreter compatibility without starting or stopping a daemon."""

from __future__ import annotations

from pathlib import Path

import pytest

from koru.autonomy.operator.operator_daemon import daemon_status_compatible


def _check(project, daemon_python, current_python, **kwargs):
    return daemon_status_compatible(
        {"daemon_version": "1.0", "daemon_metadata": {"python_executable": daemon_python}},
        current_version=lambda: "1.0",
        project=project,
        current_python=current_python,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("env/python", "env/python", True),
        ("env/python", "env/python3", True),
        ("env/python3", "env/python", True),
        ("env/python3.13", "env/python3.13", True),
        ("env/python3.13", "env/python3", False),
        ("env/python", "other/python", False),
        ("env/pypy", "env/python", False),
    ],
)
def test_interpreter_identity_and_alias_boundaries(tmp_path, left, right, expected):
    daemon_python = str(tmp_path / left)
    current_python = tmp_path / right
    reason = "daemon version 1.0" if expected else (f"daemon python {daemon_python} != current python {current_python}")
    assert _check(tmp_path, daemon_python, current_python) == (expected, reason)


def test_symlinks_resolve_to_same_interpreter(tmp_path):
    interpreter = tmp_path / "python3.13"
    interpreter.touch()
    alias = tmp_path / "linked-python"
    alias.symlink_to(interpreter)
    assert _check(tmp_path, str(alias), interpreter) == (True, "daemon version 1.0")


def test_home_expansion_is_preserved(tmp_path):
    assert _check(
        tmp_path, "~/.koru-compatibility-probe/python", Path.home() / ".koru-compatibility-probe/python3"
    ) == (True, "daemon version 1.0")


@pytest.mark.parametrize(("daemon_python", "current_python"), [("", "other"), (" ", "other"), ("env/python", None)])
def test_incomplete_interpreter_metadata_does_not_reject(tmp_path, daemon_python, current_python):
    assert _check(tmp_path, daemon_python, current_python) == (True, "daemon version 1.0")


def test_version_mismatch_precedes_interpreter_conversion(tmp_path):
    class InvalidPath:
        def __str__(self):
            pytest.fail("interpreter examined before rejecting the daemon version")

    assert daemon_status_compatible(
        {"daemon_version": "old", "daemon_metadata": {"python_executable": InvalidPath()}},
        current_version=lambda: "new",
        project=tmp_path,
        current_python="python",
    ) == (False, "daemon version old != current koru new")


def test_missing_project_skips_interpreter_check():
    assert _check(None, "env/python", "other/python") == (True, "daemon version 1.0")
