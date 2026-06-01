"""Shared helpers for VS Code–family IDE adapters."""

from __future__ import annotations

import json
import os
import re
import socket
import sqlite3
from pathlib import Path

from koru.ide_adapters.base import Hypothesis, Remediation, SettingsReport
from koruide.ides import get_strategy as _get_ide_strategy
from koruide.plugin_installer import (
    EXTENSION_ID,
    extension_id_for_ide,
)

SOCKET_SETTING_KEY = "koruAutopilot.socketPath"
PUBLISHER_ID = "semcod"
_ANSI_YELLOW = "\033[33m"
_ANSI_RESET = "\033[0m"

# Legacy fallbacks for unknown IDE ids only — all supported autopilot IDEs
# register a ``koruide.ides.<ide>`` strategy module.
_LEGACY_CONFIG_DIRS: dict[str, str] = {}
_LEGACY_VSCODE_WORKSPACE_IDES: frozenset[str] = frozenset()


def _yellow(text: str, *, enabled: bool) -> str:
    return f"{_ANSI_YELLOW}{text}{_ANSI_RESET}" if enabled else text


def config_home_for_ide(ide: str) -> Path | None:
    # Per-IDE modules (e.g. ``koruide.ides.cursor``) own this knowledge.
    # Fall back to the legacy dict for IDEs that have not been extracted.
    strategy = _get_ide_strategy(ide)
    if strategy is not None:
        return strategy.config_home()
    dirname = _LEGACY_CONFIG_DIRS.get(ide)
    if dirname is None:
        return None
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    return base / dirname


def user_settings_path(ide: str) -> Path | None:
    strategy = _get_ide_strategy(ide)
    if strategy is not None:
        return strategy.user_settings_path()
    home = config_home_for_ide(ide)
    if home is None:
        return None
    return home / "User" / "settings.json"


def workspace_settings_path(project: Path, ide: str) -> Path | None:
    strategy = _get_ide_strategy(ide)
    if strategy is not None:
        candidate = strategy.workspace_settings_path(project)
        return candidate if candidate is not None and candidate.is_file() else None
    if ide in _LEGACY_VSCODE_WORKSPACE_IDES:
        candidate = project / ".vscode" / "settings.json"
    else:
        return None
    return candidate if candidate.is_file() else None


def _read_json_object(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def read_socket_from_settings(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    data = _read_json_object(path)
    if not data:
        return None
    value = data.get(SOCKET_SETTING_KEY)
    return str(value).strip() if isinstance(value, str) and value.strip() else None


def analyze_socket_settings(
    *,
    ide: str,
    project: Path | None,
    expected_socket: str,
) -> SettingsReport:
    user_path = user_settings_path(ide)
    workspace_path = workspace_settings_path(project, ide) if project is not None else None
    user_sock = read_socket_from_settings(user_path)
    workspace_sock = read_socket_from_settings(workspace_path)
    expected = str(Path(expected_socket).resolve())
    mismatch = False
    if workspace_sock and Path(workspace_sock).resolve() != Path(expected).resolve():
        mismatch = True
    if user_sock and Path(user_sock).resolve() != Path(expected).resolve():
        if workspace_sock is None:
            mismatch = True
    return SettingsReport(
        expected_socket=expected,
        user_socket=user_sock,
        workspace_socket=workspace_sock,
        mismatch=mismatch,
        workspace_settings_path=str(workspace_path) if workspace_path else None,
        user_settings_path=str(user_path) if user_path else None,
    )


def fix_workspace_socket(*, project: Path, ide: str, expected_socket: str) -> Path | None:
    strategy = _get_ide_strategy(ide)
    if strategy is not None:
        path = strategy.workspace_settings_path(project)
        if path is None:
            return None
    elif ide in _LEGACY_VSCODE_WORKSPACE_IDES:
        path = project / ".vscode" / "settings.json"
    else:
        return None
    data = _read_json_object(path) or {}
    wanted = str(Path(expected_socket).resolve())
    current = data.get(SOCKET_SETTING_KEY)
    if current == wanted:
        return path if path.is_file() else None
    data[SOCKET_SETTING_KEY] = wanted
    if "koruAutopilot.autoConnect" not in data:
        data["koruAutopilot.autoConnect"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def state_vscdb_path(ide: str) -> Path | None:
    home = config_home_for_ide(ide)
    if home is None:
        return None
    return home / "User" / "globalStorage" / "state.vscdb"


def read_vscdb_json(key: str, *, ide: str) -> object | None:
    db_path = state_vscdb_path(ide)
    if db_path is None or not db_path.is_file():
        return None
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        row = con.execute("SELECT value FROM ItemTable WHERE key = ?", (key,)).fetchone()
        con.close()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    raw = row[0]
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def extension_disabled(ide: str) -> bool:
    disabled = read_vscdb_json("extensionsIdentifiers/disabled", ide=ide)
    if not isinstance(disabled, list):
        return False
    ext_id = extension_id_for_ide(ide)
    return ext_id in {str(item) for item in disabled}


def publisher_trusted(ide: str, publisher: str = PUBLISHER_ID) -> bool | None:
    trusted = read_vscdb_json("extensions.trustedPublishers", ide=ide)
    if not isinstance(trusted, dict):
        return None
    return publisher in trusted


def vscode_core_version(ide: str) -> str | None:
    product = config_home_for_ide(ide)
    if product is None:
        return None
    # Cursor/VS Code product.json lives next to resources, not under User/.
    for candidate in (
        Path("/usr/share/cursor/resources/app/product.json"),
        Path("/usr/share/code/resources/app/product.json"),
        Path("/snap/code/current/usr/share/code/resources/app/product.json"),
    ):
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            version = data.get("vscodeVersion") if isinstance(data, dict) else None
            if version:
                return str(version)
        except (OSError, json.JSONDecodeError):
            continue
    return None


def latest_ide_exthost_session(ide: str) -> Path | None:
    """Return the newest log session that has a real IDE window exthost (not CLI-only)."""
    home = config_home_for_ide(ide)
    if home is None:
        return None
    logs_root = home / "logs"
    if not logs_root.is_dir():
        return None
    sessions = sorted(logs_root.glob("20*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for session in sessions:
        if any(session.glob("window*/exthost/exthost.log")):
            return session
    return None


def extension_activated_in_exthost(ide: str, extension_id: str | None = None) -> bool | None:
    """Whether the per-IDE extension activated in the **current** IDE session's extension host.

    Only the newest session with ``window*/exthost/exthost.log`` is checked so a
    stale activation from an older Cursor/VS Code run does not mask a VSIX that was
    installed after the IDE started (requires Reload Window).
    """
    session = latest_ide_exthost_session(ide)
    if session is None:
        return None
    if extension_id is None:
        extension_id = extension_id_for_ide(ide)
    pattern = re.compile(
        rf"_doActivateExtension\s+{re.escape(extension_id)}\b|"
        rf"Extension activated success:\s+{re.escape(extension_id)}\b",
    )
    for log_path in session.glob("window*/exthost/exthost.log"):
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            return True
    return False


def extension_reload_required_lines(
    ide: str,
    *,
    label: str | None = None,
    color: bool = False,
) -> list[str]:
    """Actionable operator lines when VSIX is on disk but exthost never loaded the extension."""
    name = label or ide
    ext_id = extension_id_for_ide(ide)
    lines = [
        _yellow(
            f"koru autonomous: [!] VSIX zainstalowany, ale {ext_id} "
            f"nie jest aktywny w bieżącej sesji {name}.",
            enabled=color,
        ),
        _yellow(
            f"koru autonomous:     1) W {name} naciśnij Ctrl+Shift+P "
            "i uruchom: Developer: Reload Window",
            enabled=color,
        ),
        _yellow(
            "koru autonomous:     2) Po reloadzie uruchom: "
            "koru: Connect autopilot daemon",
            enabled=color,
        ),
        f"koru autonomous:     Diagnostyka: koru ide doctor --ide {ide} --fix --explain",
    ]
    trusted = publisher_trusted(ide)
    if trusted is False:
        lines.insert(
            2,
            _yellow(
                "koru autonomous:     0) Extensions → Trust Publisher „semcod” "
                "(albo: koru ide doctor --fix), potem Reload Window",
                enabled=color,
            ),
        )
    return lines


_LEGACY_EXTENSIONS_DIRNAME: dict[str, str] = {}


def extension_metadata_path(ide: str) -> Path | None:
    strategy = _get_ide_strategy(ide)
    if strategy is not None:
        return strategy.extensions_metadata_path()
    dirname = _LEGACY_EXTENSIONS_DIRNAME.get(ide)
    if dirname is None:
        return None
    return Path.home() / dirname / "extensions" / "extensions.json"


def extension_listed_in_extensions_json(ide: str) -> bool:
    ext_json = extension_metadata_path(ide)
    if not ext_json.is_file():
        return False
    try:
        data = json.loads(ext_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, list):
        return False
    ext_id = extension_id_for_ide(ide)
    for entry in data:
        if not isinstance(entry, dict):
            continue
        ident = entry.get("identifier")
        if not isinstance(ident, dict):
            continue
        extension_entry_id = ident.get("id")
        if extension_entry_id == ext_id or extension_entry_id == EXTENSION_ID:
            return True
    return False


def add_trusted_publisher(ide: str, publisher: str = PUBLISHER_ID) -> bool:
    db_path = state_vscdb_path(ide)
    if db_path is None or not db_path.is_file():
        return False
    try:
        con = sqlite3.connect(db_path)
        row = con.execute(
            "SELECT value FROM ItemTable WHERE key = ?",
            ("extensions.trustedPublishers",),
        ).fetchone()
        if row is None:
            trusted: dict[str, object] = {}
        else:
            raw = row[0]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            trusted = json.loads(raw) if isinstance(raw, str) else {}
            if not isinstance(trusted, dict):
                trusted = {}
        if publisher in trusted:
            con.close()
            return True
        trusted[publisher] = {
            "publisher": publisher,
            "publisherDisplayName": publisher,
        }
        con.execute(
            "INSERT OR REPLACE INTO ItemTable(key, value) VALUES (?, ?)",
            ("extensions.trustedPublishers", json.dumps(trusted)),
        )
        con.commit()
        con.close()
        return True
    except (sqlite3.Error, json.JSONDecodeError, TypeError):
        return False


def socket_reachable(path: str | Path, *, timeout: float = 0.3) -> bool:
    sock_path = Path(path)
    if not sock_path.exists():
        return False
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(timeout)
        client.connect(str(sock_path))
        client.close()
        return True
    except OSError:
        return False


def gc_stale_autopilot_sockets(
    *,
    keep: Path | None = None,
    runtime_dir: Path | None = None,
) -> list[str]:
    """Remove koru-autopilot-*.sock files that refuse connections."""
    xdg = runtime_dir or Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    if not xdg.is_dir():
        return []
    removed: list[str] = []
    keep_resolved = keep.resolve() if keep is not None else None
    for sock in sorted(xdg.glob("koru-autopilot*.sock")):
        if keep_resolved is not None and sock.resolve() == keep_resolved:
            continue
        if socket_reachable(sock):
            continue
        try:
            sock.unlink()
            removed.append(str(sock))
        except OSError:
            continue
    return removed


def settings_mismatch_hypothesis(settings: SettingsReport) -> Hypothesis | None:
    if not settings.mismatch:
        return None
    ws = settings.workspace_socket or "(brak)"
    return Hypothesis(
        id="settings.socket.workspace_mismatch",
        confidence=0.88,
        evidence=(
            f"workspace socketPath={ws} ≠ oczekiwany {settings.expected_socket}"
        ),
        remediation=Remediation(
            kind="command",
            summary="Wyrównaj socket w workspace settings",
            command=(
                "koru ide doctor --fix "
                f"(lub ręcznie {settings.workspace_settings_path})"
            ),
        ),
    )


def untrusted_publisher_hypothesis(ide: str) -> Hypothesis | None:
    trusted = publisher_trusted(ide)
    if trusted is not False:
        return None
    core = vscode_core_version(ide) or "?"
    return Hypothesis(
        id=f"{ide}.trustedPublishers.missing",
        confidence=0.92,
        evidence=(
            f"Publisher '{PUBLISHER_ID}' nie jest w extensions.trustedPublishers "
            f"(VS Code core {core}); wtyczka nie aktywuje się mimo instalacji VSIX"
        ),
        remediation=Remediation(
            kind="manual",
            summary=(
                f"Extensions → koru autopilot → Trust Publisher '{PUBLISHER_ID}' "
                "→ Developer: Reload Window"
            ),
        ),
    )


def inactive_extension_hypothesis(ide: str) -> Hypothesis | None:
    active = extension_activated_in_exthost(ide)
    if active is not False:
        return None
    log_home = config_home_for_ide(ide)
    logs_hint = str(log_home / "logs") if log_home is not None else f"~/.config/{ide}/logs"
    return Hypothesis(
        id=f"{ide}.extension.not_activated",
        confidence=0.75,
        evidence=(
            f"Brak aktywacji {extension_id_for_ide(ide)} w ostatnich logach exthost "
            f"({logs_hint}/.../exthost.log)"
        ),
        remediation=Remediation(
            kind="manual",
            summary=(
                "Developer: Reload Window albo restart IDE, potem Command Palette "
                "→ koru: Connect autopilot daemon. Jeśli komendy brak, IDE "
                "nie załadowało VSIX z obecnej sesji extension host."
            ),
        ),
    )
