"""koruide is the single source of IDE identity maps.

Guards the boundary-refactoring step 3 consolidation: binary candidates,
window titles, and alias normalization live in ``koruide.ide``; koru surfaces
(environment probe, plugin installer, MCP provisioning, window focus) must
derive from it instead of keeping private copies.
"""

from __future__ import annotations

from koruide.ide import (
    autopilot_ide_choices,
    ide_binary_candidates,
    ide_window_name,
    normalize_ide_id,
    supported_autopilot_ide_ids,
)


class TestKoruideSource:
    def test_every_supported_ide_has_binary_candidates(self):
        for ide in supported_autopilot_ide_ids() - {"auto"}:
            assert ide_binary_candidates(ide), f"no binary candidates for {ide}"

    def test_every_supported_ide_has_window_name(self):
        for ide in supported_autopilot_ide_ids() - {"auto"}:
            assert ide_window_name(ide), f"no window name for {ide}"

    def test_binary_candidates_normalize_aliases(self):
        assert ide_binary_candidates("codium") == ide_binary_candidates("vscodium")
        assert "code" in ide_binary_candidates("vscode")
        assert "pycharm" in ide_binary_candidates("jetbrains")

    def test_window_name_normalizes_aliases(self):
        assert ide_window_name("code") == "Visual Studio Code"
        assert ide_window_name("pycharm") == "JetBrains"


class TestKoruSurfacesDerive:
    def test_environment_known_ides_match_koruide(self):
        from koru.autonomy.environment import KNOWN_IDES

        assert set(KNOWN_IDES) == supported_autopilot_ide_ids() - {"auto"}
        # jetbrains and antigravity were historically missing from the probe
        assert "jetbrains" in KNOWN_IDES
        assert "antigravity" in KNOWN_IDES

    def test_environment_resolves_codium_binary(self, tmp_path):
        import stat

        from koru.autonomy.environment import probe_ide_presence

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        codium = bin_dir / "codium"
        codium.write_text("#!/bin/sh\nexit 0\n")
        codium.chmod(codium.stat().st_mode | stat.S_IXUSR)

        presences = probe_ide_presence(tmp_path, environ={"PATH": str(bin_dir)})
        vscodium = next(p for p in presences if p.ide == "vscodium")
        assert vscodium.installed

    def test_plugin_ide_cli_derives_from_koruide(self):
        from koru.autopilot.install_plugin_cli import PLUGIN_IDE_CLI

        for ide, binaries in PLUGIN_IDE_CLI.items():
            assert binaries == ide_binary_candidates(ide)

    def test_mcp_targets_resolve_via_normalization(self):
        from koru.mcp_provision import _resolve_targets

        assert _resolve_targets("code") == ["vscode"]
        assert _resolve_targets("code-oss") == ["vscodium"]
        assert _resolve_targets("zed-editor") == ["zed"]
        assert _resolve_targets("antigravity") == ["vscode"]

    def test_parser_editor_choices_are_supported_ides(self):
        # Editor tokens accepted by --ide must be koruide-supported ids.
        editor_choices = {"antigravity", "windsurf", "vscode", "vscodium", "cursor", "jetbrains", "zed"}
        assert editor_choices <= set(autopilot_ide_choices())
        for token in editor_choices:
            assert normalize_ide_id(token) == token
