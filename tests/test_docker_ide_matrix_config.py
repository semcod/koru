from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_SYSTEMS = ("debian-slim", "debian-bookworm", "ubuntu-noble", "fedora", "alpine")
NATIVE_SYSTEMS = ("ubuntu-latest", "windows-latest", "macos-latest")
MATRIX_IDES = ("vscode", "vscodium", "cursor", "windsurf", "jetbrains", "zed")
PLUGIN_MANAGED_IDES = ("vscode", "vscodium", "cursor", "windsurf", "jetbrains")


def test_docker_ide_matrix_script_covers_supported_systems_and_ides() -> None:
    script = (ROOT / "scripts" / "docker-ide-matrix.sh").read_text(encoding="utf-8")

    for system in MATRIX_SYSTEMS:
        assert system in script
    for ide in MATRIX_IDES:
        assert ide in script


def test_docker_ide_matrix_dockerfile_installs_fake_cli_surface() -> None:
    dockerfile = (ROOT / "tests" / "docker" / "ide-matrix.Dockerfile").read_text(
        encoding="utf-8",
    )

    for tool in (
        "code",
        "code-oss",
        "codium",
        "vscodium",
        "cursor",
        "windsurf",
        "zed",
        "pycharm",
        "idea",
        "wtype",
        "xdotool",
        "ydotool",
        "wl-copy",
        "wl-paste",
        "xclip",
        "xsel",
    ):
        assert tool in dockerfile


def test_docker_ide_matrix_workflow_exposes_full_matrix() -> None:
    workflow = (ROOT / ".github" / "workflows" / "docker-ide-matrix.yml").read_text(
        encoding="utf-8",
    )

    for key in ("system:", "ide:", "scripts/docker-ide-matrix.sh"):
        assert key in workflow
    for system in MATRIX_SYSTEMS:
        assert system in workflow
    for ide in MATRIX_IDES:
        assert ide in workflow


def test_docker_ide_matrix_entrypoint_manages_plugin_ides() -> None:
    entrypoint = (ROOT / "scripts" / "docker-ide-matrix-entrypoint.sh").read_text(
        encoding="utf-8",
    )

    assert 'autopilot manage --ide "${ide}"' in entrypoint
    for ide in PLUGIN_MANAGED_IDES:
        assert f'"${{ide}}" == "{ide}"' in entrypoint


def test_native_ide_matrix_workflow_exposes_windows_and_macos() -> None:
    workflow = (ROOT / ".github" / "workflows" / "native-ide-matrix.yml").read_text(
        encoding="utf-8",
    )

    for system in NATIVE_SYSTEMS:
        assert system in workflow
    for ide in MATRIX_IDES:
        assert ide in workflow
    for command in (
        "tests/test_docker_ide_matrix.py",
        "autopilot drive",
        "autopilot manage",
    ):
        assert command in workflow


def test_readme_documents_current_ide_matrix_state() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for heading in (
        "Docker OS × IDE smoke matrix",
        "Native OS × IDE smoke matrix",
    ):
        assert heading in readme
    for system in (*MATRIX_SYSTEMS, *NATIVE_SYSTEMS):
        assert system in readme
    for ide in MATRIX_IDES:
        assert ide in readme
    for phrase in (
        "VS Code and VSCodium are separate lanes",
        "koru-autopilot-vscodium.sock",
        "iOS is intentionally not part of this matrix",
    ):
        assert phrase in readme


def test_ide_router_docs_document_current_matrix_state() -> None:
    docs = (ROOT / "docs" / "ide-router.md").read_text(encoding="utf-8")

    for system in (*MATRIX_SYSTEMS, *NATIVE_SYSTEMS):
        assert system in docs
    for ide in MATRIX_IDES:
        assert ide in docs
    for phrase in (
        "vscode` and `vscodium` are intentionally separate lanes",
        "koru-autopilot-vscodium.sock",
        "iOS is not part of the matrix",
    ):
        assert phrase in docs
