import importlib
import sys

import pytest


def test_legacy_cli_warns_and_reexports_canonical_entrypoints(monkeypatch) -> None:
    sys.modules.pop("cli2coru", None)
    sys.modules.pop("cli2coru.cli", None)
    with pytest.warns(DeprecationWarning, match="cli2coru is deprecated"):
        legacy_cli = importlib.import_module("cli2coru.cli")
    legacy_shell = importlib.import_module("cli2coru.shell")
    canonical_cli = importlib.import_module("cli2koru.cli")
    canonical_shell = importlib.import_module("cli2koru.shell")

    assert legacy_cli.main is canonical_cli.main
    assert legacy_shell.run_shell is canonical_shell.run_shell

    monkeypatch.setitem(canonical_cli._HANDLERS, "exec", lambda _args: 23)
    argv = ["exec", "VALIDATE_LANE IDE auto INSTANCE default"]
    assert canonical_cli.main(argv) == 23
    assert legacy_cli.main(argv) == 23
