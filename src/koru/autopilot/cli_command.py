"""``koru autopilot`` subcommand wiring.

Kept in its own module to keep ``koru.cli`` digestible. The single
public entrypoint is :func:`autopilot_main` which mirrors the
``_task_main`` / ``_scan_main`` style used elsewhere.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import default_socket_path
from .audit import AuditLog, default_log_path
from .client import AutopilotClient
from .daemon import AutopilotDaemon
from .ide import detect_focused_ide_id, detect_running_ides
from .injector import Injector, InjectorError
from .utils.client_helpers import call_daemon_method, resolve_xdg_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru autopilot",
        description=(
            "Drive an IDE's LLM chat panel from the terminal. "
            "Run `koru autopilot daemon` once in a background terminal, "
            "then `koru autopilot drive '<text>'` from anywhere to type "
            "into the focused IDE."
        ),
    )
    parser.add_argument(
        "--socket",
        type=Path,
        default=None,
        help=(
            "Unix-socket path (default from KORU_AUTOPILOT_SOCKET / "
            "KORU_AUTOPILOT_INSTANCE / XDG_RUNTIME_DIR — see koru autopilot docs)."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)

    daemon = sub.add_parser("daemon", help="Run the autopilot broker.")
    daemon.add_argument(
        "--idempotent",
        action="store_true",
        help="If a healthy daemon already runs, exit 0 instead of failing.",
    )
    daemon.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root used to build the koru brief on session.ended (default: cwd).",
    )
    handoff_group = daemon.add_mutually_exclusive_group()
    handoff_group.add_argument(
        "--handoff",
        dest="handoff",
        action="store_true",
        default=True,
        help="On session.ended from a plugin, type the koru brief back into the chat (default).",
    )
    handoff_group.add_argument(
        "--no-handoff",
        dest="handoff",
        action="store_false",
        help="Disable auto-handoff; just ack session events.",
    )
    daemon.add_argument(
        "--handoff-cooldown",
        type=float,
        default=2.0,
        help="Seconds to wait after typing before reacting to session.ended (anti-loop).",
    )

    drive = sub.add_parser("drive", help="Type text into the active IDE chat.")
    drive.add_argument("text", nargs="+", help="Text to type. Multiple args are joined with spaces.")
    drive.add_argument(
        "--ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"),
        help="Target IDE (default: auto-detect the focused one).",
    )
    drive.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Do not press the submit key after typing.",
    )
    drive.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be typed and exit without touching the keyboard.",
    )
    drive.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the daemon and inject directly via local backends.",
    )

    sub.add_parser("status", help="Print daemon health + connected plugins.")
    sub.add_parser("shutdown", help="Ask a running daemon to stop.")

    sub.add_parser("ide-list", help="List currently running IDEs (process scan).")
    doctor = sub.add_parser("doctor", help="Report which injection backends are available.")
    doctor.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    doctor.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Show guided remediation and next commands "
            "(including optional package auto-install)."
        ),
    )

    setup_host = sub.add_parser(
        "setup-host",
        help=(
            "Probe injector tools, list apt install hints, and optional apt install "
            "(Debian/Ubuntu). Separates automated steps from human (uinput, IDE plugin)."
        ),
    )
    setup_host.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    setup_host.add_argument(
        "--install",
        action="store_true",
        help="Run sudo apt-get install -y for missing xdotool/wtype/ydotool (requires apt).",
    )
    setup_host.add_argument(
        "--dry-run",
        dest="install_dry_run",
        action="store_true",
        help="With --install, print the apt-get command but do not run it.",
    )

    install_plugin = sub.add_parser(
        "install-plugin",
        help=(
            "Install the koru autopilot editor extension for the current IDE "
            "(auto-detect from terminal/focus/running IDEs)."
        ),
    )
    install_plugin.add_argument(
        "--ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor"),
        help="Target editor CLI (default: auto-detect current IDE).",
    )
    install_plugin.add_argument(
        "--vsix",
        type=Path,
        default=None,
        help=(
            "Path to .vsix package (default: newest plugins/koru-autopilot-vscode/"
            "koru-autopilot-*.vsix)."
        ),
    )
    install_plugin.add_argument(
        "--force",
        action="store_true",
        help="Pass --force to the editor extension installer.",
    )
    install_plugin.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved install command without executing it.",
    )
    install_plugin.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )

    handoff = sub.add_parser(
        "handoff",
        help="Build the koru brief for --project and type it into the IDE chat.",
    )
    handoff.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root used to build the brief (default: cwd).",
    )
    handoff.add_argument(
        "--ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"),
        help="Target IDE (default: auto-detect the focused one).",
    )
    handoff.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Type the brief but do not press the submit key.",
    )
    handoff.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the brief and exit; do not contact the daemon.",
    )

    install_unit = sub.add_parser(
        "install-unit",
        help="Install the systemd --user service unit (P2.6).",
    )
    install_unit.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Override destination (default: $XDG_CONFIG_HOME/systemd/user/koru-autopilot.service).",
    )
    install_unit.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing unit file.",
    )
    install_unit.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="Print the rendered unit to stdout instead of writing.",
    )

    tail = sub.add_parser(
        "tail",
        help="Pretty-print the persistent audit log (P2.7/P2.8).",
    )
    tail.add_argument(
        "-n", "--lines", type=int, default=20,
        help="Number of trailing entries to show (default: 20).",
    )
    tail.add_argument(
        "--log",
        type=Path,
        default=None,
        help=f"Log file path (default: {default_log_path()}).",
    )
    tail.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser


def _client(args: argparse.Namespace) -> AutopilotClient:
    return AutopilotClient(socket_path=args.socket)


# ----- action handlers ------------------------------------------------------

def _action_daemon(args: argparse.Namespace) -> int:
    socket_path = args.socket or default_socket_path()
    if args.idempotent:
        probe = AutopilotClient(socket_path=socket_path, timeout=0.5)
        if probe.is_running():
            print(f"koru autopilot: daemon already running on {socket_path}")
            return 0
    project = args.project.resolve() if args.handoff else None
    audit = AuditLog(enabled=True)
    daemon = AutopilotDaemon(
        socket_path=socket_path,
        log=print,
        project=project,
        handoff_cooldown=args.handoff_cooldown,
        audit=audit,
    )
    if audit.enabled:
        print(f"koru autopilot daemon: audit log at {audit.path}")
    try:
        daemon.start()
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot daemon: {exc}", file=sys.stderr)
        return 1
    if args.handoff:
        print(f"koru autopilot daemon: handoff enabled for project={project}")
    else:
        print("koru autopilot daemon: handoff disabled (--no-handoff)")
    try:
        daemon.serve_forever()
    except KeyboardInterrupt:
        print()
        print("koru autopilot daemon: interrupted")
    return 0


def _action_drive(args: argparse.Namespace) -> int:
    text = " ".join(args.text)
    if args.direct:
        injector = Injector()
        try:
            result = injector.type_text(
                text,
                ide="default" if args.ide == "auto" else args.ide,
                submit=args.submit,
                dry_run=args.dry_run,
            )
        except InjectorError as exc:
            print(f"koru autopilot drive: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0
    client = _client(args)
    if not client.is_running():
        print(
            "koru autopilot drive: daemon not running. "
            "Start it with `koru autopilot daemon`, or pass --direct "
            "to inject from this terminal.",
            file=sys.stderr,
        )
        return 2
    if args.dry_run:
        print(f"[dry-run] would send {len(text)} chars to daemon ide={args.ide}")
        return 0
    try:
        reply = client.drive(text, submit=args.submit, ide=args.ide)
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot drive: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(reply, indent=2, sort_keys=True))
    return 0 if reply.get("ok", True) else 1


def _action_status(args: argparse.Namespace) -> int:
    client = _client(args)
    return call_daemon_method(
        client, "status", "koru autopilot status", not_running_return_code=1
    )


def _action_shutdown(args: argparse.Namespace) -> int:
    client = _client(args)
    return call_daemon_method(
        client, "shutdown", "koru autopilot shutdown", not_running_return_code=0
    )


def _action_ide_list(_args: argparse.Namespace) -> int:
    ides = detect_running_ides()
    if not ides:
        print("koru autopilot: no IDE processes detected")
        return 0
    focused = detect_focused_ide_id()
    for ide in ides:
        suffix = "  [focused]" if focused is not None and ide.id == focused else ""
        print(f"  {ide.id:<10} pid={ide.pid:<7} {ide.label}  ({ide.exe}){suffix}")
    return 0


def _doctor_fix_payload() -> dict[str, object]:
    """Guided remediation payload reused by text and json outputs."""
    from .host_setup import build_setup_host_report

    report = build_setup_host_report()
    return {
        "commands": [
            "koru autopilot setup-host",
            "koru autopilot setup-host --install --dry-run",
            "koru autopilot setup-host --install",
            "koru autopilot install-plugin",
        ],
        "automated_apt_suggestion": report.get("automated_apt_suggestion"),
        "human_actions_required": report.get("human_actions_required") or [],
    }


def _render_doctor_text(
    injector: Injector,
    statuses: list,
    selected: str | None,
    fix_payload: dict[str, object] | None,
) -> None:
    """Render doctor output in text format."""
    print(f"session: {injector.session or 'unknown'}")
    print(f"selected backend: {selected or '(none — install xdotool/wtype/ydotool)'}")
    print("backends:")
    for s in statuses:
        mark = "✓" if s.available else "✗"
        print(f"  {mark} {s.name:<10} {s.reason}")
    ides = detect_running_ides()
    focused = detect_focused_ide_id()
    print(f"running IDEs ({len(ides)}):")
    for ide in ides:
        marker = " [focused]" if focused is not None and ide.id == focused else ""
        print(f"  · {ide.label} (pid={ide.pid}){marker}")
    if fix_payload is not None:
        print("\nnext steps (guided fix):")
        for cmd in fix_payload.get("commands", []):
            print(f"  - {cmd}")
        apt_hint = fix_payload.get("automated_apt_suggestion")
        if isinstance(apt_hint, str) and apt_hint:
            print(f"  - apt suggestion: {apt_hint}")
        human_actions = fix_payload.get("human_actions_required")
        if isinstance(human_actions, list) and human_actions:
            print("human actions still required:")
            for line in human_actions:
                print(f"  - {line}")


def _render_doctor_json(
    injector: Injector,
    statuses: list,
    selected: str | None,
    fix_payload: dict[str, object] | None,
) -> None:
    """Render doctor output in JSON format."""
    focused = detect_focused_ide_id()
    payload = {
        "session": injector.session,
        "selected_backend": selected,
        "backends": [s.to_dict() for s in statuses],
        "ides": [i.to_dict() for i in detect_running_ides()],
        "focused_ide": focused,
    }
    if fix_payload is not None:
        payload["fix"] = fix_payload
    print(json.dumps(payload, indent=2, sort_keys=True))


def _action_doctor(args: argparse.Namespace) -> int:
    injector = Injector()
    statuses = injector.probe()
    selected = injector.select_backend()
    fix_payload = _doctor_fix_payload() if args.fix else None
    if args.output_format == "json":
        _render_doctor_json(injector, statuses, selected, fix_payload)
        return 0
    _render_doctor_text(injector, statuses, selected, fix_payload)
    return 0 if selected else 1


def _action_setup_host(args: argparse.Namespace) -> int:
    from .host_setup import run_host_setup

    return run_host_setup(
        output_format=args.output_format,
        install=args.install,
        install_dry_run=args.install_dry_run,
    )


_PLUGIN_IDE_CLI: dict[str, tuple[str, ...]] = {
    "windsurf": ("windsurf",),
    "cursor": ("cursor",),
    "vscode": ("code", "code-insiders", "code-oss", "vscodium", "codium"),
}


def _plugin_repo_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "plugins" / "koru-autopilot-vscode"


def _resolve_plugin_vsix_path(vsix: Path | None) -> Path:
    if vsix is not None:
        candidate = vsix.expanduser().resolve()
        if not candidate.is_file():
            raise RuntimeError(f"vsix not found: {candidate}")
        return candidate
    plugin_dir = _plugin_repo_dir()
    matches = sorted(
        plugin_dir.glob("koru-autopilot-*.vsix"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise RuntimeError(
            "no packaged .vsix found under plugins/koru-autopilot-vscode; "
            "build one with: `cd plugins/koru-autopilot-vscode && npm install && npm run package`"
        )
    return matches[0]


def _ide_from_terminal_env() -> str | None:
    term_program = os.environ.get("TERM_PROGRAM", "").strip().lower()
    if term_program in ("vscode", "code"):
        return "vscode"
    if term_program == "cursor":
        return "cursor"
    if term_program == "windsurf":
        return "windsurf"
    if os.environ.get("VSCODE_PID"):
        return "vscode"
    return None


def _resolve_plugin_target_ide(raw_ide: str) -> str:
    if raw_ide != "auto":
        return raw_ide
    env_guess = _ide_from_terminal_env()
    if env_guess is not None:
        return env_guess
    focused = detect_focused_ide_id()
    if focused in _PLUGIN_IDE_CLI:
        return str(focused)
    detected = [ide for ide in detect_running_ides() if ide.id in _PLUGIN_IDE_CLI]
    if len(detected) == 1:
        return detected[0].id
    if not detected:
        raise RuntimeError(
            "could not detect running editor for plugin install; pass --ide windsurf|vscode|cursor"
        )
    ids = ", ".join(ide.id for ide in detected)
    raise RuntimeError(
        "multiple supported IDEs detected with no clear active one "
        f"({ids}); pass --ide windsurf|vscode|cursor"
    )


def _resolve_plugin_editor_bin(ide: str) -> str:
    for candidate in _PLUGIN_IDE_CLI[ide]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    choices = "|".join(_PLUGIN_IDE_CLI[ide])
    raise RuntimeError(f"could not find editor CLI in PATH for {ide} (tried: {choices})")


def _render_install_plugin_dry_run(
    ide: str,
    editor_bin: str,
    vsix_path: Path,
    cmd: list[str],
    output_format: str,
) -> None:
    """Render install-plugin dry-run output."""
    payload = {
        "ide": ide,
        "editor": editor_bin,
        "vsix": str(vsix_path),
        "command": cmd,
        "dry_run": True,
        "ok": True,
    }
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("koru autopilot install-plugin: dry-run")
        print("  " + " ".join(cmd))


def _render_install_plugin_result(
    ide: str,
    editor_bin: str,
    cmd: list[str],
    ok: bool,
    stdout: str,
    stderr: str,
    output_format: str,
) -> None:
    """Render install-plugin execution result."""
    payload = {
        "ide": ide,
        "editor": editor_bin,
        "command": cmd,
        "ok": ok,
        "returncode": 0 if ok else 1,
        "stdout": stdout,
        "stderr": stderr,
    }
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if ok:
            print(f"koru autopilot install-plugin: installed for {ide} via {editor_bin}")
        else:
            print(f"koru autopilot install-plugin: install failed for {ide}", file=sys.stderr)
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)


def _action_install_plugin(args: argparse.Namespace) -> int:
    try:
        ide = _resolve_plugin_target_ide(args.ide)
        editor_bin = _resolve_plugin_editor_bin(ide)
        vsix_path = _resolve_plugin_vsix_path(args.vsix)
    except RuntimeError as exc:
        print(f"koru autopilot install-plugin: {exc}", file=sys.stderr)
        return 1

    cmd = [editor_bin, "--install-extension", str(vsix_path)]
    if args.force:
        cmd.append("--force")

    if args.dry_run:
        _render_install_plugin_dry_run(ide, editor_bin, vsix_path, cmd, args.output_format)
        return 0

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        print(f"koru autopilot install-plugin: {exc}", file=sys.stderr)
        return 1

    ok = proc.returncode == 0
    _render_install_plugin_result(
        ide,
        editor_bin,
        cmd,
        ok,
        proc.stdout.strip(),
        proc.stderr.strip(),
        args.output_format,
    )
    return 0 if ok else 1


def _build_brief(project: Path) -> str:
    """Build the koru markdown brief for ``project``.

    Imported lazily so ``autopilot doctor`` / ``ide-list`` don't drag
    in the heavy ``context`` stack on every CLI invocation.
    """
    from ..context import build_context, render_markdown_handoff

    ctx = build_context(project=project)
    return render_markdown_handoff(ctx)


def _action_handoff(args: argparse.Namespace) -> int:
    """P2.5: build the koru brief and pipe it through ``drive``."""
    project = args.project.resolve()
    try:
        brief = _build_brief(project)
    except Exception as exc:  # pragma: no cover — surfaces context errors
        print(f"koru autopilot handoff: {exc}", file=sys.stderr)
        return 1
    if not brief.strip():
        print("koru autopilot handoff: empty brief, refusing to drive", file=sys.stderr)
        return 1
    if args.dry_run:
        print(brief)
        return 0
    client = _client(args)
    if not client.is_running():
        print(
            "koru autopilot handoff: daemon not running. "
            "Start it with `koru autopilot daemon`.",
            file=sys.stderr,
        )
        return 2
    try:
        reply = client.drive(brief, submit=args.submit, ide=args.ide)
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot handoff: {exc}", file=sys.stderr)
        return 1
    summary = {
        "ok": reply.get("ok", False),
        "chars": len(brief),
        "ide": args.ide,
        "submit": args.submit,
        "backend": reply.get("backend") or ("plugin" if reply.get("delivered") else "?"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if reply.get("ok", True) else 1


def _format_tail_entry(entry: dict) -> str:
    """Render one audit-log line as a single text row."""
    ts = entry.get("ts", "?")
    event = entry.get("event", "?")
    parts = [ts, event]
    for key in ("ide", "backend", "chars", "submit", "ok", "chat", "reason",
                "version", "source", "socket", "handoff", "error"):
        if key in entry and entry[key] is not None:
            parts.append(f"{key}={entry[key]}")
    return "  ".join(str(p) for p in parts)


def _render_tail_json(tail: list[str]) -> None:
    """Render tail output in JSON format."""
    parsed = []
    for line in tail:
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    print(json.dumps(parsed, indent=2, sort_keys=True))


def _render_tail_text(tail: list[str]) -> None:
    """Render tail output in text format."""
    for line in tail:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        print(_format_tail_entry(entry))


def _action_tail(args: argparse.Namespace) -> int:
    """P2.8: dump the last ``--lines`` audit entries."""
    log_path = args.log or default_log_path()
    if not log_path.is_file():
        print(f"koru autopilot tail: no log at {log_path}", file=sys.stderr)
        return 1
    try:
        raw = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        print(f"koru autopilot tail: {exc}", file=sys.stderr)
        return 1
    tail = raw[-args.lines:] if args.lines > 0 else raw
    if args.output_format == "json":
        _render_tail_json(tail)
        return 0
    _render_tail_text(tail)
    return 0


def _systemd_user_dir() -> Path:
    """Resolve the XDG ``systemd/user`` directory."""
    return resolve_xdg_path("systemd/user")


def _resolve_koru_bin() -> str:
    """Best-effort absolute path to the ``koru`` executable.

    Priority:
    1) ``koru`` on ``PATH``;
    2) sibling of ``sys.executable`` (common for virtualenvs);
    3) user-local default used in docs.
    """
    on_path = shutil.which("koru")
    if on_path:
        return on_path
    sibling = Path(sys.executable).with_name("koru")
    if sibling.is_file() and os.access(sibling, os.X_OK):
        return str(sibling)
    prefixed = Path(sys.prefix) / "bin" / "koru"
    if prefixed.is_file() and os.access(prefixed, os.X_OK):
        return str(prefixed)
    return "%h/.local/bin/koru"


def _render_unit(koru_bin: str) -> str:
    """Build the systemd unit text with the resolved koru binary path.

    The shipped template under ``systemd/koru-autopilot.service`` is the
    source of truth; we read it, substitute the ExecStart line so it
    matches the user's actual koru install, and write the result.
    """
    template_path = Path(__file__).resolve().parents[3] / "systemd" / "koru-autopilot.service"
    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError:
        # Fallback to a minimal inline template if the file isn't shipped
        # (e.g. in a wheel that excluded it).
        template = (
            "[Unit]\n"
            "Description=koru autopilot daemon\n"
            "After=graphical-session.target\n"
            "PartOf=graphical-session.target\n\n"
            "[Service]\n"
            "Type=simple\n"
            "ExecStart=__KORU_BIN__ autopilot daemon --idempotent --no-handoff\n"
            "Restart=on-failure\n"
            "RestartSec=2\n\n"
            "[Install]\n"
            "WantedBy=default.target\n"
        )
    # Replace the ExecStart line so the user gets the koru that's
    # actually available in this environment, not a hard-coded path.
    lines = []
    for line in template.splitlines():
        if line.startswith("ExecStart=") and "autopilot daemon" in line:
            lines.append(f"ExecStart={koru_bin} autopilot daemon --idempotent --no-handoff")
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def _action_install_unit(args: argparse.Namespace) -> int:
    """P2.6: install the systemd --user service unit."""
    koru_bin = _resolve_koru_bin()
    rendered = _render_unit(koru_bin)
    if args.print_only:
        sys.stdout.write(rendered)
        return 0
    dest = args.dest or _systemd_user_dir() / "koru-autopilot.service"
    if dest.exists() and not args.force:
        print(
            f"koru autopilot install-unit: {dest} already exists "
            "(pass --force to overwrite).",
            file=sys.stderr,
        )
        return 1
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        print(f"koru autopilot install-unit: {exc}", file=sys.stderr)
        return 1
    print(f"koru autopilot: installed {dest}")
    print()
    print("Next steps:")
    print("  systemctl --user daemon-reload")
    print("  systemctl --user enable --now koru-autopilot.service")
    print("  journalctl --user -u koru-autopilot -f      # follow logs")
    print()
    print(f"To enable auto-handoff for a project, override ExecStart with:")
    print(f"  systemctl --user edit koru-autopilot.service")
    return 0


_ACTIONS = {
    "daemon": _action_daemon,
    "drive": _action_drive,
    "status": _action_status,
    "shutdown": _action_shutdown,
    "ide-list": _action_ide_list,
    "doctor": _action_doctor,
    "setup-host": _action_setup_host,
    "install-plugin": _action_install_plugin,
    "handoff": _action_handoff,
    "tail": _action_tail,
    "install-unit": _action_install_unit,
}


def autopilot_main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    handler = _ACTIONS[args.action]
    return handler(args)


__all__ = ["autopilot_main"]
