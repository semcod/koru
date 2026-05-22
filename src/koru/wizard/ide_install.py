"""IDE installation logic for ``koru wizard``.

Provides catalog of IDE install commands and installation orchestration.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from koru.wizard.ide import DetectedIDE, discover_installed_ides
from koru.wizard.tree import Prompter, TreeOption


@dataclass(frozen=True)
class IDEInstallSpec:
    ide_id: str
    label: str
    homepage: str
    commands: dict[str, tuple[str, ...]]


_IDE_INSTALL_ORDER = (
    "vscode",
    "vscodium",
    "zed",
    "jetbrains",
    "cursor",
    "windsurf",
    "antigravity",
)

_IDE_INSTALL_CATALOG: dict[str, IDEInstallSpec] = {
    "vscode": IDEInstallSpec(
        ide_id="vscode",
        label="VS Code",
        homepage="https://code.visualstudio.com/download",
        commands={
            "snap": ("sudo", "snap", "install", "code", "--classic"),
            "flatpak": ("flatpak", "install", "-y", "flathub", "com.visualstudio.code"),
            "apt": ("sudo", "apt-get", "install", "-y", "code"),
            "dnf": ("sudo", "dnf", "install", "-y", "code"),
            "pacman": ("sudo", "pacman", "-S", "--noconfirm", "code"),
            "zypper": ("sudo", "zypper", "install", "-y", "code"),
        },
    ),
    "vscodium": IDEInstallSpec(
        ide_id="vscodium",
        label="VSCodium",
        homepage="https://vscodium.com/",
        commands={
            "flatpak": ("flatpak", "install", "-y", "flathub", "com.vscodium.codium"),
            "snap": ("sudo", "snap", "install", "codium", "--classic"),
            "apt": ("sudo", "apt-get", "install", "-y", "codium"),
            "dnf": ("sudo", "dnf", "install", "-y", "codium"),
            "pacman": ("sudo", "pacman", "-S", "--noconfirm", "vscodium"),
            "zypper": ("sudo", "zypper", "install", "-y", "codium"),
        },
    ),
    "zed": IDEInstallSpec(
        ide_id="zed",
        label="Zed",
        homepage="https://zed.dev/download",
        commands={
            "flatpak": ("flatpak", "install", "-y", "flathub", "dev.zed.Zed"),
        },
    ),
    "jetbrains": IDEInstallSpec(
        ide_id="jetbrains",
        label="JetBrains IDEA Community",
        homepage="https://www.jetbrains.com/idea/download/",
        commands={
            "flatpak": (
                "flatpak",
                "install",
                "-y",
                "flathub",
                "com.jetbrains.IntelliJ-IDEA-Community",
            ),
            "snap": (
                "sudo",
                "snap",
                "install",
                "intellij-idea-community",
                "--classic",
            ),
        },
    ),
    "cursor": IDEInstallSpec(
        ide_id="cursor",
        label="Cursor",
        homepage="https://cursor.com/downloads",
        commands={},
    ),
    "windsurf": IDEInstallSpec(
        ide_id="windsurf",
        label="Windsurf",
        homepage="https://windsurf.com/",
        commands={},
    ),
    "antigravity": IDEInstallSpec(
        ide_id="antigravity",
        label="Antigravity",
        homepage="https://www.antigravity.dev/",
        commands={},
    ),
}

_MANAGER_BINARIES = {
    "apt": "apt-get",
    "dnf": "dnf",
    "pacman": "pacman",
    "zypper": "zypper",
    "snap": "snap",
    "flatpak": "flatpak",
}


def _available_install_managers() -> set[str]:
    return {
        manager
        for manager, binary in _MANAGER_BINARIES.items()
        if shutil.which(binary) is not None
    }


def _format_command(argv: tuple[str, ...]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def _open_download_page(url: str, out: Any) -> None:
    print(f"Open download page: {url}", file=out)
    for opener in (
        ("xdg-open", url),
        ("open", url),
    ):
        if shutil.which(opener[0]) is None:
            continue
        try:
            subprocess.Popen(opener, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Opened in browser via {opener[0]}", file=out)
            return
        except OSError:
            continue
    if os.name == "nt":
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Opened in browser via cmd/start", file=out)
            return
        except OSError:
            pass


def _run_install_command(argv: tuple[str, ...], out: Any) -> bool:
    effective = list(argv)
    if effective and effective[0] == "sudo" and shutil.which("sudo") is None:
        effective = effective[1:]
        print("note: sudo not found, running command without sudo", file=out)
    if not effective:
        return False
    print(f"Running installer command: {_format_command(tuple(effective))}", file=out)
    try:
        proc = subprocess.run(effective, check=False)
    except OSError as exc:
        print(f"installation command failed to start: {exc}", file=out)
        return False
    if proc.returncode != 0:
        print(f"installation command failed with exit code {proc.returncode}", file=out)
        return False
    print("installation command finished successfully", file=out)
    return True


def _build_install_method_options(
    spec: IDEInstallSpec,
    available_managers: set[str],
) -> tuple[tuple[TreeOption, ...], dict[str, tuple[str, ...]]]:
    options: list[TreeOption] = []
    commands: dict[str, tuple[str, ...]] = {}
    for manager in ("snap", "flatpak", "apt", "dnf", "pacman", "zypper"):
        if manager not in available_managers:
            continue
        command = spec.commands.get(manager)
        if not command:
            continue
        option_id = f"install_{manager}"
        options.append(
            TreeOption(
                id=option_id,
                label=f"Install via {manager}: {_format_command(command)}",
            )
        )
        commands[option_id] = command
    options.append(TreeOption(id="open_web", label=f"Open download page ({spec.homepage})"))
    options.append(TreeOption(id="cancel", label="Cancel installation"))
    return tuple(options), commands


def offer_ide_install(prompter: Prompter, out: Any) -> list[DetectedIDE]:
    """Offer IDE installation to user when no IDEs are detected."""
    print("No IDE detected. You can install one now.", file=out)
    ide_options = tuple(
        TreeOption(id=f"install_{ide_id}", label=f"Install {spec.label}")
        for ide_id in _IDE_INSTALL_ORDER
        if (spec := _IDE_INSTALL_CATALOG.get(ide_id)) is not None
    ) + (TreeOption(id="__none", label="Skip installation and continue"),)
    selected = prompter.ask_choice("Choose IDE installation target:", ide_options)
    if selected.id == "__none":
        return []

    ide_id = selected.id.removeprefix("install_")
    spec = _IDE_INSTALL_CATALOG.get(ide_id)
    if spec is None:
        return []

    methods, commands = _build_install_method_options(spec, _available_install_managers())
    method = prompter.ask_choice(f"Choose installation method for {spec.label}:", methods)
    if method.id == "cancel":
        return []
    if method.id == "open_web":
        _open_download_page(spec.homepage, out)
        return discover_installed_ides()

    command = commands.get(method.id)
    if command is None:
        return discover_installed_ides()
    if prompter.ask_yes_no("Run installation command now?", default=True):
        _run_install_command(command, out)
    else:
        print("You can run this command manually:", file=out)
        print(f"  {_format_command(command)}", file=out)

    return discover_installed_ides()
