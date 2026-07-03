"""STARTER-563 Phase 2: ``import koruide`` must be standalone-safe.

Spawns a fresh interpreter with a meta-path blocker that refuses ``koru``
(and, in the second case, ``gillm``) imports, then verifies that
``import koruide`` succeeds, the host hooks degrade to soft no-ops, and the
daemon module is not imported eagerly.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

_PROBE = textwrap.dedent(
    """
    import importlib.abc
    import sys

    blocked = set(sys.argv[1].split(","))


    class _Blocker(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in blocked:
                raise ImportError(f"import of {fullname!r} is blocked for this test")
            return None


    sys.meta_path.insert(0, _Blocker())
    for loaded in [name for name in sys.modules if name.split(".")[0] in blocked]:
        del sys.modules[loaded]

    import koruide

    assert "koruide.daemon" not in sys.modules, "koruide.daemon imported eagerly"
    for root in blocked:
        leaked = [
            name for name in sys.modules if name == root or name.startswith(root + ".")
        ]
        assert not leaked, f"blocked package {root!r} leaked into sys.modules: {leaked}"

    import koruide.host_hooks as host_hooks

    assert callable(host_hooks.record_integration_action)
    assert callable(host_hooks.plugin_socket_command)
    assert callable(host_hooks.emit_action)
    assert callable(host_hooks.emit_verify)
    # Without koru the default hooks must soft no-op instead of raising.
    assert (
        host_hooks.record_integration_action(
            action="probe", intent="standalone", target="test", outcome="ok"
        )
        is None
    )
    assert host_hooks.emit_phase(None, corr="probe") is None

    from koruide.ide import normalize_ide_id

    assert normalize_ide_id("code") == "vscode"

    # Accessing the lazy exports above must not have pulled in the daemon.
    assert "koruide.daemon" not in sys.modules, "koruide.daemon imported eagerly"
    assert "AutopilotDaemon" in koruide.__all__
    print("KORUIDE-STANDALONE-OK")
    """
)


def _run_probe(blocked: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _PROBE, blocked],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_import_koruide_without_koru() -> None:
    result = _run_probe("koru")
    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "KORUIDE-STANDALONE-OK" in result.stdout


def test_import_koruide_without_koru_and_gillm() -> None:
    result = _run_probe("koru,gillm")
    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "KORUIDE-STANDALONE-OK" in result.stdout
