"""Regression tests for the ``koru._legacy_cli_impl`` lazy proxies.

``koru.cli`` (the package) loads ``cli.py`` as ``koru._legacy_cli_impl`` and
``cli_auto._legacy_attr`` resolves ``autonomous_main`` from that module so that
``mock.patch("koru._legacy_cli_impl.autonomous_main")`` keeps working. The
proxy must forward keyword arguments such as ``invoked_as_auto`` to
``koru.autonomous.autonomous_main``.
"""

from __future__ import annotations

import sys
from unittest import mock

import koru.autonomous
import koru.cli  # noqa: F401  # registers koru._legacy_cli_impl in sys.modules
from koru.cli_auto import _auto_main


def test_legacy_autonomous_main_forwards_kwargs() -> None:
    legacy = sys.modules["koru._legacy_cli_impl"]
    with mock.patch.object(
        koru.autonomous, "autonomous_main", return_value=0
    ) as inner:
        rc = legacy.autonomous_main(["status"], invoked_as_auto=False)
    assert rc == 0
    inner.assert_called_once_with(["status"], invoked_as_auto=False)


def test_auto_maintenance_action_passes_invoked_as_auto() -> None:
    with mock.patch.object(
        koru.autonomous, "autonomous_main", return_value=0
    ) as inner:
        rc = _auto_main(["status"])
    assert rc == 0
    inner.assert_called_once_with(["status"], invoked_as_auto=False)
