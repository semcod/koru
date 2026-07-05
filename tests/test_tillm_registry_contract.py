"""Drift guards between koru's shell-client knowledge and tillm's registry.

tillm (a zero-dependency core dependency of koru) is the single source of
truth for shell LLM clients. koru keeps two derived artifacts that must never
drift from it:

- ``tillm_bridge._FALLBACK_SHELL_CLIENT_TOKENS`` — intent recognition when
  tillm cannot be imported (broken env); a missing token silently reroutes
  ``--ide claude`` to an editor lane (the c2004 incident),
- ``agents._FALLBACK_SHELL_CLIENTS`` — PATH-based lane detection for the
  dashboard when tillm is unavailable.

These tests fail when tillm's registry gains/renames clients that koru's
fallbacks or the ``--ide`` parser choices do not cover.
"""

from __future__ import annotations

import pytest

from koru.tillm_bridge import ensure_local_tillm_path

ensure_local_tillm_path()
tillm_registry = pytest.importorskip(
    "tillm.registry", reason="tillm is a core dependency; install it to run contract tests"
)

from koru.agents import _FALLBACK_SHELL_CLIENTS  # noqa: E402
from koru.autonomous_parser import build_parser  # noqa: E402
from koru.tillm_bridge import _FALLBACK_SHELL_CLIENT_TOKENS, shell_drive_client_id  # noqa: E402


def _registry_specs():
    return tillm_registry.iter_client_specs()


def _parser_ide_choices() -> set[str]:
    parser = build_parser(default_stdio_format="human")
    for action_group in parser._subparsers._group_actions:  # noqa: SLF001
        for sub in action_group.choices.values():
            for action in sub._actions:  # noqa: SLF001
                if "--autopilot-ide" in getattr(action, "option_strings", ()):
                    return set(action.choices)
    raise AssertionError("--autopilot-ide argument not found in autonomous parser")


class TestFallbackTokenContract:
    def test_every_fallback_token_resolves_in_registry(self):
        for token in sorted(_FALLBACK_SHELL_CLIENT_TOKENS):
            assert shell_drive_client_id(token), (
                f"fallback token {token!r} no longer resolves in tillm's registry — "
                "remove it from _FALLBACK_SHELL_CLIENT_TOKENS"
            )

    def test_every_registry_id_is_recognized_as_fallback(self):
        # If tillm gains a client koru's fallback does not know, `--ide <id>`
        # on a tillm-less host would silently misroute to the editor lane.
        missing = sorted(
            spec.id
            for spec in _registry_specs()
            if spec.id not in _FALLBACK_SHELL_CLIENT_TOKENS
        )
        assert not missing, (
            f"tillm registry ids missing from _FALLBACK_SHELL_CLIENT_TOKENS: {missing} — "
            "add them (and to the --ide parser choices if user-selectable)"
        )

    def test_parser_shell_choices_resolve_in_registry(self):
        editor_ids = {
            "auto",
            "antigravity",
            "windsurf",
            "vscode",
            "vscodium",
            "cursor",
            "qoder",
            "jetbrains",
            "zed",
        }
        shell_choices = _parser_ide_choices() - editor_ids
        for token in sorted(shell_choices):
            assert shell_drive_client_id(token), (
                f"--ide choice {token!r} is neither an editor id nor a resolvable "
                "tillm shell client — it would misroute at runtime"
            )

    def test_parser_covers_fallback_tokens(self):
        # Whatever koru promises to recognize offline must be selectable online.
        choices = _parser_ide_choices()
        missing = sorted(_FALLBACK_SHELL_CLIENT_TOKENS - choices)
        assert not missing, f"fallback tokens absent from --ide choices: {missing}"


class TestDashboardFallbackContract:
    def test_fallback_ids_match_registry_ids(self):
        registry_ids = {spec.id for spec in _registry_specs()}
        for agent_id, _label, _binaries in _FALLBACK_SHELL_CLIENTS:
            assert agent_id in registry_ids, (
                f"agents._FALLBACK_SHELL_CLIENTS id {agent_id!r} not in tillm registry"
            )

    def test_fallback_binaries_are_registry_commands(self):
        commands_by_id = {spec.id: set(spec.commands) for spec in _registry_specs()}
        for agent_id, _label, binaries in _FALLBACK_SHELL_CLIENTS:
            unknown = set(binaries) - commands_by_id.get(agent_id, set())
            assert not unknown, (
                f"agents._FALLBACK_SHELL_CLIENTS[{agent_id!r}] probes binaries "
                f"{sorted(unknown)} that tillm's spec does not list"
            )
