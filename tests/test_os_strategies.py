"""Per-OS strategy tests.

Each OS gets its own behaviour module under :mod:`koruos.strategies`.
The tests prove that:

* the right strategy auto-resolves for the current platform / display server,
* capabilities only advertise tools that are actually on ``PATH``,
* focus / keyboard fallbacks pick the documented order, and
* ``KeySequence`` validation rejects ambiguous payloads.

Higher layers must consume these strategies instead of branching on
``sys.platform`` themselves; see ``koru.ide_adapters.ide_reload``.
"""

from __future__ import annotations

import os
import unittest
from typing import Any
from unittest import mock

from koruos.strategies.base import KeySequence, OsCapabilities
from koruos.strategies.darwin import DarwinStrategy
from koruos.strategies.registry import (
    list_os_strategy_ids,
    resolve_active_os_strategy,
)
from koruos.strategies.wayland_linux import WaylandLinuxStrategy
from koruos.strategies.windows import WindowsStrategy
from koruos.strategies.x11_linux import X11LinuxStrategy


class RegistryTests(unittest.TestCase):
    def test_all_shipped_strategies_registered(self) -> None:
        ids = list_os_strategy_ids()
        for expected in ("linux-wayland", "linux-x11", "darwin", "windows"):
            self.assertIn(expected, ids)

    def test_resolve_active_picks_a_real_strategy(self) -> None:
        strategy = resolve_active_os_strategy()
        self.assertIn(strategy.id, list_os_strategy_ids())


class KeySequenceTests(unittest.TestCase):
    def test_rejects_both_key_and_literal(self) -> None:
        with self.assertRaises(ValueError):
            KeySequence(key="Return", literal_text="hi")

    def test_rejects_neither_key_nor_literal(self) -> None:
        with self.assertRaises(ValueError):
            KeySequence()

    def test_accepts_modifiers_plus_key(self) -> None:
        sequence = KeySequence(modifiers=("ctrl", "shift"), key="p")
        self.assertEqual(sequence.modifiers, ("ctrl", "shift"))
        self.assertEqual(sequence.key, "p")


class WaylandLinuxStrategyTests(unittest.TestCase):
    def test_matches_when_wayland_display_present(self) -> None:
        with (
            mock.patch.dict(
                "os.environ",
                {"WAYLAND_DISPLAY": "wayland-0", "XDG_SESSION_TYPE": "wayland"},
                clear=False,
            ),
            mock.patch("sys.platform", "linux"),
        ):
            self.assertTrue(WaylandLinuxStrategy().matches_current_environment())

    def test_does_not_match_macos(self) -> None:
        with mock.patch("sys.platform", "darwin"):
            self.assertFalse(WaylandLinuxStrategy().matches_current_environment())

    def test_capabilities_use_shutil_which(self) -> None:
        def fake_which(name: str) -> str | None:
            return f"/usr/bin/{name}" if name in {"wtype", "wl-copy"} else None

        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                side_effect=fake_which,
            ),
            mock.patch.dict(os.environ, {"TERM_PROGRAM": ""}, clear=False),
        ):
            caps = WaylandLinuxStrategy().capabilities()
        self.assertEqual(caps.keyboard_tool, "wtype")
        self.assertTrue(caps.can_paste_clipboard)
        self.assertFalse(caps.can_focus_window)

    def test_focus_returns_integrated_terminal_on_wayland_with_term_program(self) -> None:
        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                return_value=None,
            ),
            mock.patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}, clear=False),
        ):
            outcome = WaylandLinuxStrategy().focus_window(("Cursor",))
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.method, "integrated_terminal")

    def test_focus_explains_wayland_failure(self) -> None:
        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                return_value=None,
            ),
            mock.patch.dict("os.environ", {}, clear=True),
        ):
            outcome = WaylandLinuxStrategy().focus_window(("Cursor",))
        self.assertFalse(outcome.ok)
        self.assertIn("wmctrl", outcome.detail)
        self.assertIn("TERM_PROGRAM=vscode", outcome.detail)

    def test_inject_keys_builds_correct_wtype_argv(self) -> None:
        runs: list[list[str]] = []

        def fake_run(argv: list[str], **_kw: Any) -> Any:
            runs.append(list(argv))
            return mock.Mock(returncode=0, stdout="", stderr="")

        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                lambda name: f"/usr/bin/{name}" if name == "wtype" else None,
            ),
            mock.patch("koruos.strategies.wayland_linux._run", fake_run),
        ):
            self.assertTrue(
                WaylandLinuxStrategy().inject_keys(
                    KeySequence(modifiers=("ctrl", "shift"), key="p")
                ),
            )
        self.assertEqual(runs[-1][:1], ["wtype"])
        self.assertIn("-M", runs[-1])
        self.assertIn("ctrl", runs[-1])
        self.assertIn("shift", runs[-1])

    def test_inject_literal_text_uses_minus_t(self) -> None:
        runs: list[list[str]] = []

        def fake_run(argv: list[str], **_kw: Any) -> Any:
            runs.append(list(argv))
            return mock.Mock(returncode=0, stdout="", stderr="")

        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                lambda name: f"/usr/bin/{name}" if name == "wtype" else None,
            ),
            mock.patch("koruos.strategies.wayland_linux._run", fake_run),
        ):
            self.assertTrue(
                WaylandLinuxStrategy().inject_keys(
                    KeySequence(literal_text="Developer: Reload Window")
                ),
            )
        self.assertEqual(runs[-1], ["wtype", "-t", "Developer: Reload Window"])

    def test_wtype_returncode_zero_but_stderr_unsupported_is_failure(self) -> None:
        # Mutter/GNOME compositors routinely print
        # "Compositor doesn't support virtual-keyboard-v1" yet still
        # return 0 — wtype must be treated as failed in that case so
        # the strategy escalates to ydotool.
        runs: list[list[str]] = []
        ydotool_called: dict[str, bool] = {"hit": False}

        def fake_run(argv: list[str], **_kw: Any) -> Any:
            runs.append(list(argv))
            if argv[0] == "wtype":
                return mock.Mock(
                    returncode=0,
                    stdout="",
                    stderr="Compositor doesn't support virtual-keyboard-v1",
                )
            if argv[0] == "ydotool":
                ydotool_called["hit"] = True
                return mock.Mock(returncode=0, stdout="", stderr="")
            return mock.Mock(returncode=1, stdout="", stderr="unknown")

        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                lambda name: f"/usr/bin/{name}" if name in {"wtype", "ydotool"} else None,
            ),
            mock.patch("koruos.strategies.wayland_linux._run", fake_run),
            mock.patch.dict(
                "os.environ",
                {"KORU_OS_PREFER_YDOTOOL": "0", "XDG_CURRENT_DESKTOP": "KDE"},
                clear=False,
            ),
        ):
            ok = WaylandLinuxStrategy().inject_keys(
                KeySequence(modifiers=("ctrl", "shift"), key="p"),
            )
        self.assertTrue(ok, "expected ydotool fallback to take over from wtype")
        self.assertTrue(ydotool_called["hit"])

    def test_gnome_compositor_prefers_ydotool_first(self) -> None:
        runs: list[list[str]] = []

        def fake_run(argv: list[str], **_kw: Any) -> Any:
            runs.append(list(argv))
            return mock.Mock(returncode=0, stdout="", stderr="")

        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                lambda name: f"/usr/bin/{name}" if name in {"wtype", "ydotool"} else None,
            ),
            mock.patch("koruos.strategies.wayland_linux._run", fake_run),
            mock.patch.dict(
                "os.environ",
                {"XDG_CURRENT_DESKTOP": "GNOME", "KORU_OS_PREFER_YDOTOOL": ""},
                clear=False,
            ),
        ):
            self.assertTrue(
                WaylandLinuxStrategy().inject_keys(
                    KeySequence(modifiers=("ctrl", "shift"), key="p"),
                ),
            )
        self.assertEqual(runs[0][0], "ydotool")

    def test_ydotool_chord_emits_press_release_in_order(self) -> None:
        runs: list[list[str]] = []

        def fake_run(argv: list[str], **_kw: Any) -> Any:
            runs.append(list(argv))
            return mock.Mock(returncode=0, stdout="", stderr="")

        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                lambda name: f"/usr/bin/{name}" if name == "ydotool" else None,
            ),
            mock.patch("koruos.strategies.wayland_linux._run", fake_run),
            mock.patch.dict(
                "os.environ",
                {"KORU_OS_PREFER_YDOTOOL": "1"},
                clear=False,
            ),
        ):
            self.assertTrue(
                WaylandLinuxStrategy().inject_keys(
                    KeySequence(modifiers=("ctrl", "shift"), key="p"),
                ),
            )
        # 29=ctrl, 42=shift, 25=p — press low→high, release high→low.
        self.assertEqual(
            runs[-1],
            ["ydotool", "key", "29:1", "42:1", "25:1", "25:0", "42:0", "29:0"],
        )

    def test_ydotool_return_uses_correct_scancode(self) -> None:
        runs: list[list[str]] = []

        def fake_run(argv: list[str], **_kw: Any) -> Any:
            runs.append(list(argv))
            return mock.Mock(returncode=0, stdout="", stderr="")

        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                lambda name: f"/usr/bin/{name}" if name == "ydotool" else None,
            ),
            mock.patch("koruos.strategies.wayland_linux._run", fake_run),
            mock.patch.dict(
                "os.environ",
                {"KORU_OS_PREFER_YDOTOOL": "1"},
                clear=False,
            ),
        ):
            self.assertTrue(
                WaylandLinuxStrategy().inject_keys(KeySequence(key="Return")),
            )
        self.assertEqual(runs[-1], ["ydotool", "key", "28:1", "28:0"])

    def test_env_override_disables_gnome_preference(self) -> None:
        # GNOME but explicit opt-out → wtype is tried first.
        runs: list[list[str]] = []

        def fake_run(argv: list[str], **_kw: Any) -> Any:
            runs.append(list(argv))
            return mock.Mock(returncode=0, stdout="", stderr="")

        with (
            mock.patch(
                "koruos.strategies.wayland_linux.shutil.which",
                lambda name: f"/usr/bin/{name}" if name in {"wtype", "ydotool"} else None,
            ),
            mock.patch("koruos.strategies.wayland_linux._run", fake_run),
            mock.patch.dict(
                "os.environ",
                {"XDG_CURRENT_DESKTOP": "GNOME", "KORU_OS_PREFER_YDOTOOL": "0"},
                clear=False,
            ),
        ):
            self.assertTrue(
                WaylandLinuxStrategy().inject_keys(
                    KeySequence(modifiers=("ctrl",), key="p"),
                ),
            )
        self.assertEqual(runs[0][0], "wtype")


class X11LinuxStrategyTests(unittest.TestCase):
    def test_does_not_match_when_wayland_display_present(self) -> None:
        with (
            mock.patch.dict(
                "os.environ",
                {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"},
                clear=False,
            ),
            mock.patch("sys.platform", "linux"),
        ):
            self.assertFalse(X11LinuxStrategy().matches_current_environment())

    def test_matches_classic_x11(self) -> None:
        env = {"DISPLAY": ":0"}
        with (
            mock.patch.dict("os.environ", env, clear=True),
            mock.patch("sys.platform", "linux"),
        ):
            self.assertTrue(X11LinuxStrategy().matches_current_environment())

    def test_focus_uses_xdotool_first(self) -> None:
        runs: list[list[str]] = []

        def fake_run(argv: list[str], **_kw: Any) -> Any:
            runs.append(list(argv))
            if argv[0] == "xdotool" and "search" in argv:
                return mock.Mock(returncode=0, stdout="123\n", stderr="")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with (
            mock.patch(
                "koruos.strategies.x11_linux.shutil.which",
                lambda name: f"/usr/bin/{name}",
            ),
            mock.patch("koruos.strategies.x11_linux._run", fake_run),
        ):
            outcome = X11LinuxStrategy().focus_window(("Cursor",))
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.method, "xdotool")


class DarwinStrategyTests(unittest.TestCase):
    def test_matches_only_on_darwin(self) -> None:
        with mock.patch("sys.platform", "darwin"):
            self.assertTrue(DarwinStrategy().matches_current_environment())
        with mock.patch("sys.platform", "linux"):
            self.assertFalse(DarwinStrategy().matches_current_environment())

    def test_focus_uses_osascript(self) -> None:
        with (
            mock.patch(
                "koruos.strategies.darwin.shutil.which",
                lambda name: f"/usr/bin/{name}" if name == "osascript" else None,
            ),
            mock.patch(
                "koruos.strategies.darwin._run",
                lambda *_a, **_kw: mock.Mock(returncode=0),
            ),
        ):
            outcome = DarwinStrategy().focus_window(("Cursor",))
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.method, "osascript")


class WindowsStrategyTests(unittest.TestCase):
    def test_matches_only_on_windows(self) -> None:
        with mock.patch("sys.platform", "win32"):
            self.assertTrue(WindowsStrategy().matches_current_environment())
        with mock.patch("sys.platform", "linux"):
            self.assertFalse(WindowsStrategy().matches_current_environment())

    def test_capabilities_are_empty_placeholder(self) -> None:
        self.assertEqual(WindowsStrategy().capabilities(), OsCapabilities())


if __name__ == "__main__":
    unittest.main()
