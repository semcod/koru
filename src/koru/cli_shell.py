"""koru shell — Claude Code-style interactive REPL for koru.

Launch with ``koru shell``. Slash commands drive koru the way Claude Code is
driven: ``/config`` opens an interactive settings editor, ``/integration``
shows a checkbox picker of integrations, plain text is sent to the configured
LLM lane (OpenRouter). Settings persist in ``.koru/config.json`` next to the
existing ``koru configure`` schema.

No third-party dependencies: ANSI rendering + termios arrow-key widgets, with
a numeric fallback when stdin is not a TTY.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

try:  # readline is optional on non-POSIX builds
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

# ── palette ──────────────────────────────────────────────────────────────────
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
CYAN = "\x1b[36m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
RESET = "\x1b[0m"
INVERT = "\x1b[7m"

CONFIG_REL_PATH = Path(".koru") / "config.json"
SHELL_SECTION = "shell"
INTEGRATIONS_SECTION = "integrations"

DEFAULT_SHELL_CONFIG: dict[str, object] = {
    "llm_model": "cursor/grok-4.6[xhigh]",
    "llm_endpoint": "subllm://koru-agent/planning-assistant",
    "queue_actor": "koru-shell",
    "drain_batch": 10,
    "auto_drain": False,
}


@dataclass(frozen=True)
class Integration:
    key: str
    label: str
    description: str
    default: bool = False
    fix_hint: str = ""


INTEGRATION_CATALOG: tuple[Integration, ...] = (
    Integration(
        "cursor", "Cursor Grok 4.6 xhigh",
        "executor.kind=llm tickets + shell prompts via SubLLM", True,
        "configure CURSOR_API_KEY in subactor/subllm/.env",
    ),
    Integration(
        "qoder_chat", "Qoder / IDE chat",
        "autopilot injects prompts into the IDE chat (vscode lane)", False,
        "run `coru vscode auto` inside the IDE's integrated terminal",
    ),
    Integration(
        "planfile_queue", "Planfile queue",
        "ticket queue drain (koru --queue --loop)", True,
        "install planfile into the project venv",
    ),
    Integration(
        "vdisplay", "vdisplay",
        "screen capture + verified injection for autopilot", False,
        "vdisplay-agent serve, then: vdisplay agent screencast start",
    ),
    Integration("code2llm", "code2llm scan", "code-smell discovery tickets", False, "pip install code2llm"),
    Integration(
        "todo2code",
        "todo2code (t2c)",
        "useful NL/TODO → code-change planfile tickets",
        False,
        "npm i -g / path to todo2code (provides `t2c`)",
    ),
    Integration(
        "ticket2dsl",
        "ticket2dsl",
        "open tickets → work-unit DSL for IDE agents",
        True,
        "built into koru (koru ide ticket2dsl)",
    ),
    Integration("testql", "TestQL", "on-change quick test gates", False, "pip install testql"),
    Integration("wup", "wup health", "service health probes feeding cycle decisions", False, "pip install wup"),
    Integration("goal", "goal", "commit/publish advisory signals", False, "pip install goal"),
    Integration("costs", "costs", "LLM cost tracking badge", False, "pip install costs"),
)


# ── config store (.koru/config.json, shared with `koru configure`) ───────────
def _config_path(project: Path) -> Path:
    return project / CONFIG_REL_PATH


def load_config(project: Path) -> dict:
    path = _config_path(project)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(project: Path, config: dict) -> None:
    path = _config_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def shell_settings(config: dict) -> dict:
    merged = dict(DEFAULT_SHELL_CONFIG)
    merged.update(config.get(SHELL_SECTION) or {})
    return merged


def enabled_integrations(config: dict) -> set[str]:
    section = config.get(INTEGRATIONS_SECTION) or {}
    stored = section.get("enabled")
    if isinstance(stored, list):
        enabled = {str(item) for item in stored}
        if "openrouter" in enabled:
            enabled.remove("openrouter")
            enabled.add("cursor")
        return enabled
    return {item.key for item in INTEGRATION_CATALOG if item.default}


# ── low-level terminal widgets ───────────────────────────────────────────────
def _read_key() -> str:
    """Read one keypress (arrow keys collapse to 'up'/'down')."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            return {"[A": "up", "[B": "down"}.get(seq, "esc")
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _checkbox_picker_numeric(
    title: str,
    items: list[tuple[str, str, bool]],
    checked: set[str],
) -> list[str] | None:
    """Non-TTY fallback: toggle by number list."""
    print(title)
    for idx, (key, label, _) in enumerate(items, start=1):
        mark = "☑" if key in checked else "☐"
        print(f"  {idx}. {mark} {label}")
    raw = input("toggle numbers (space-separated), enter=save, q=cancel: ").strip()
    if raw.lower() == "q":
        return None
    for token in raw.split():
        if token.isdigit() and 1 <= int(token) <= len(items):
            key = items[int(token) - 1][0]
            checked.symmetric_difference_update({key})
    return sorted(checked)


def _checkbox_picker_apply_key(
    key_pressed: str,
    *,
    items: list[tuple[str, str, bool]],
    checked: set[str],
    cursor: int,
) -> tuple[int, list[str] | None, bool]:
    """Apply one keypress. Returns ``(cursor, result_or_None, done)``."""
    if key_pressed == "up":
        return (cursor - 1) % len(items), None, False
    if key_pressed == "down":
        return (cursor + 1) % len(items), None, False
    if key_pressed == " ":
        checked.symmetric_difference_update({items[cursor][0]})
        return cursor, None, False
    if key_pressed in {"\r", "\n"}:
        return cursor, sorted(checked), True
    if key_pressed in {"q", "esc", "\x03"}:
        return cursor, None, True
    return cursor, None, False


def _checkbox_picker_tty(
    title: str,
    items: list[tuple[str, str, bool]],
    checked: set[str],
) -> list[str] | None:
    cursor = 0
    while True:
        sys.stdout.write("\x1b[2J\x1b[H")  # clear screen
        print(f"{BOLD}{title}{RESET}")
        print(f"{DIM}↑/↓ move · space toggle · enter save · q cancel{RESET}\n")
        for idx, (key, label, _) in enumerate(items):
            mark = f"{GREEN}☑{RESET}" if key in checked else "☐"
            line = f" {mark} {label}"
            if idx == cursor:
                print(f"{INVERT}{line}{RESET}")
            else:
                print(line)
        cursor, result, done = _checkbox_picker_apply_key(
            _read_key(),
            items=items,
            checked=checked,
            cursor=cursor,
        )
        if done:
            return result


def _checkbox_picker(
    title: str,
    items: list[tuple[str, str, bool]],
) -> list[str] | None:
    """Arrow-key checkbox list → selected keys, or None on cancel.

    ``items`` is (key, rendered_label, checked). Falls back to numeric input
    when stdin is not a TTY.
    """
    checked = {key for key, _, is_on in items if is_on}
    if not sys.stdin.isatty():
        return _checkbox_picker_numeric(title, items, checked)
    return _checkbox_picker_tty(title, items, checked)


def _box(lines: list[str], color: str = DIM) -> str:
    width = max(len(_strip_ansi(line)) for line in lines)
    top = f"{color}╭{'─' * (width + 2)}╮{RESET}"
    bottom = f"{color}╰{'─' * (width + 2)}╯{RESET}"
    body = [
        f"{color}│{RESET} {line}{' ' * (width - len(_strip_ansi(line)))} {color}│{RESET}"
        for line in lines
    ]
    return "\n".join([top, *body, bottom])


def _strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ── data helpers ─────────────────────────────────────────────────────────────
def _planfile_bin(project: Path) -> str:
    for candidate in (project / ".venv" / "bin" / "planfile", project / "venv" / "bin" / "planfile"):
        if candidate.is_file():
            return str(candidate)
    return "planfile"


def _open_tickets(project: Path) -> list[dict]:
    try:
        proc = subprocess.run(
            [_planfile_bin(project), "ticket", "list", "--status", "open", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=project,
            timeout=30,
        )
        tickets = json.loads(proc.stdout or "[]")
    except Exception:
        return []
    if isinstance(tickets, dict):
        tickets = list(tickets.values())
    return tickets if isinstance(tickets, list) else []


def _ask_llm(project: Path, settings: dict, prompt: str) -> str:
    del settings
    from korullm import run_cursor_llm

    result = run_cursor_llm(
        prompt,
        project,
        route_function="planning-assistant",
        timeout_seconds=180.0,
    )
    if result.returncode != 0:
        return f"{RED}LLM call failed: {result.stderr}{RESET}"
    return result.stdout


# ── integration probes ───────────────────────────────────────────────────────
def _probe_binary(name: str) -> tuple[bool, str]:
    import shutil

    path = shutil.which(name)
    return (True, path) if path else (False, f"{name} not on PATH")


def _probe_qoder_chat(project: Path) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["koru", "autopilot", "status"],
            capture_output=True,
            text=True,
            cwd=project,
            timeout=15,
            env={**os.environ, "KORU_AUTOPILOT_INSTANCE": "vscode"},
        )
        payload = json.loads(proc.stdout or "{}")
    except Exception as exc:
        return False, f"autopilot daemon unreachable ({exc})"
    if payload.get("plugins"):
        return True, "bridge connected"
    if payload.get("daemon_pid"):
        return False, "daemon up, IDE bridge NOT connected"
    return False, "autopilot daemon not running"


def _probe_vdisplay(_project: Path) -> tuple[bool, str]:
    base = os.environ.get("VDISPLAY_AGENT_URL", "http://127.0.0.1:8765").rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        data = payload.get("data") or {}
        return True, f"agent ok (v{data.get('version', '?')})"
    except Exception:
        return False, f"agent unreachable at {base}"


def probe_integration(project: Path, key: str) -> tuple[bool, str]:
    """Live availability check → (ok, one-line detail)."""
    if key == "cursor":
        from korullm import probe_subllm_route

        return probe_subllm_route(project, "queue-executor", provider="cursor")
    if key == "qoder_chat":
        return _probe_qoder_chat(project)
    if key == "planfile_queue":
        binary = _planfile_bin(project)
        return (True, binary) if binary != "planfile" else _probe_binary("planfile")
    if key == "vdisplay":
        return _probe_vdisplay(project)
    return _probe_binary(key)


# ── slash commands ───────────────────────────────────────────────────────────
def _cmd_help(_ctx: "ShellContext", _arg: str) -> None:  # noqa: UP037
    rows = [
        ("/help", "show this help"),
        ("/config", "interactive settings (model, actor, drain batch, auto-drain)"),
        ("/integration", "checkbox picker: which integrations are active"),
        ("/status", "queue + integrations overview"),
        ("/tickets", "list open tickets"),
        ("/drain [n]", "run the OpenRouter queue drain (default n from /config)"),
        ("/ticket <text>", "add a backlog ticket"),
        ("/bridge [start]", "IDE bridge status; start it from the IDE terminal"),
        ("/doctor", "run koru doctor"),
        ("/exit", "leave the shell"),
    ]
    width = max(len(cmd) for cmd, _ in rows)
    print(_box([f"{CYAN}{cmd.ljust(width)}{RESET}  {desc}" for cmd, desc in rows]))
    print(f"{DIM}Plain text (no slash) is sent to {RESET}{CYAN}the configured LLM{RESET}{DIM} and printed here.{RESET}")


def _cmd_integration(ctx: "ShellContext", _arg: str) -> None:  # noqa: UP037
    current = enabled_integrations(ctx.config)
    items = [
        (item.key, f"{item.label:<18} {DIM}{item.description}{RESET}", item.key in current)
        for item in INTEGRATION_CATALOG
    ]
    selected = _checkbox_picker("Integrations — what koru is allowed to use", items)
    if selected is None:
        print(f"{DIM}cancelled — nothing changed{RESET}")
        return
    ctx.config.setdefault(INTEGRATIONS_SECTION, {})["enabled"] = selected
    save_config(ctx.project, ctx.config)
    print(f"{GREEN}saved:{RESET} {', '.join(selected) or '(none)'}")
    hints = {item.key: item.fix_hint for item in INTEGRATION_CATALOG}
    for key in selected:
        ok, detail = probe_integration(ctx.project, key)
        if ok:
            print(f"  {GREEN}✓{RESET} {key}: {detail}")
        else:
            print(f"  {RED}✗{RESET} {key}: {detail}")
            if hints.get(key):
                print(f"    {DIM}fix: {hints[key]}{RESET}")
            if key == "qoder_chat":
                print(f"    {DIM}or: /bridge start (from the IDE's integrated terminal){RESET}")


def _cmd_config(ctx: "ShellContext", _arg: str) -> None:  # noqa: UP037
    settings = shell_settings(ctx.config)
    fields = list(settings.items())
    print(f"{BOLD}Settings{RESET} {DIM}(enter number to edit, blank to finish){RESET}")
    while True:
        for idx, (key, value) in enumerate(fields, start=1):
            print(f"  {CYAN}{idx}{RESET}. {key} = {BOLD}{value}{RESET}")
        choice = input("edit #: ").strip()
        if not choice:
            break
        if not choice.isdigit() or not 1 <= int(choice) <= len(fields):
            print(f"{YELLOW}pick 1-{len(fields)}{RESET}")
            continue
        key, old = fields[int(choice) - 1]
        raw = input(f"{key} [{old}]: ").strip()
        if raw == "":
            continue
        new_value: object = raw
        if isinstance(old, bool):
            new_value = raw.lower() in {"1", "true", "yes", "on"}
        elif isinstance(old, int):
            new_value = int(raw) if raw.isdigit() else old
        fields[int(choice) - 1] = (key, new_value)
    ctx.config[SHELL_SECTION] = dict(fields)
    save_config(ctx.project, ctx.config)
    print(f"{GREEN}saved to {CONFIG_REL_PATH}{RESET}")


def _cmd_status(ctx: "ShellContext", _arg: str) -> None:  # noqa: UP037
    tickets = _open_tickets(ctx.project)
    current = enabled_integrations(ctx.config)
    settings = shell_settings(ctx.config)
    lines = [
        f"project      {ctx.project}",
        f"open tickets {BOLD}{len(tickets)}{RESET}",
        f"llm          {CYAN}{settings['llm_model']}{RESET}",
    ]
    for item in INTEGRATION_CATALOG:
        if item.key not in current:
            lines.append(f"{DIM}☐ {item.key} (disabled){RESET}")
            continue
        ok, detail = probe_integration(ctx.project, item.key)
        mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        lines.append(f"{mark} {item.key:<15} {DIM}{detail}{RESET}")
    print(_box(lines))


def _cmd_tickets(ctx: "ShellContext", _arg: str) -> None:  # noqa: UP037
    tickets = _open_tickets(ctx.project)
    if not tickets:
        print(f"{DIM}queue is empty{RESET}")
        return
    for t in tickets[:20]:
        executor = (t.get("executor") or {}).get("kind") or "?"
        print(f"  {CYAN}{t.get('id')}{RESET} {DIM}[{executor}]{RESET} {str(t.get('name'))[:70]}")


def _cmd_drain(ctx: "ShellContext", arg: str) -> None:  # noqa: UP037
    if "cursor" not in enabled_integrations(ctx.config):
        print(f"{YELLOW}cursor integration is disabled — enable it via /integration{RESET}")
        return
    settings = shell_settings(ctx.config)
    batch = arg.strip() or str(settings["drain_batch"])
    script = ctx.project / ".planfile" / ".koru" / "openrouter-drain.py"
    if script.is_file():
        cmd = [sys.executable, str(script), batch]
    else:
        cmd = ["koru", "--queue", "--loop", "--max-iterations", batch, "--project", str(ctx.project)]
    print(f"{DIM}$ {' '.join(cmd)}{RESET}")
    subprocess.run(cmd, cwd=ctx.project)


def _cmd_ticket(ctx: "ShellContext", arg: str) -> None:  # noqa: UP037
    text = arg.strip()
    if not text:
        print(f"{YELLOW}usage: /ticket <description>{RESET}")
        return
    proc = subprocess.run(
        [_planfile_bin(ctx.project), "ticket", "create", text],
        capture_output=True,
        text=True,
        cwd=ctx.project,
    )
    print((proc.stdout or proc.stderr).strip())


def _cmd_doctor(ctx: "ShellContext", _arg: str) -> None:  # noqa: UP037
    subprocess.run(["koru", "doctor"], cwd=ctx.project)


def _inside_vscode_terminal() -> bool:
    """True inside a VS Code-family integrated terminal (VS Code, Qoder, ...)."""
    return os.environ.get("TERM_PROGRAM", "").lower() == "vscode"


def _cmd_bridge(ctx: "ShellContext", arg: str) -> None:  # noqa: UP037
    action = arg.strip().lower()
    ok, detail = _probe_qoder_chat(ctx.project)
    mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    print(f"{mark} qoder/IDE bridge: {detail}")
    if action != "start":
        if not ok:
            print(f"{DIM}start it with: /bridge start (from the IDE's integrated terminal){RESET}")
        return
    if ok:
        print(f"{DIM}bridge already connected — nothing to do{RESET}")
        return
    if not _inside_vscode_terminal():
        print(
            f"{YELLOW}this shell is not inside a VS Code/Qoder integrated terminal{RESET}\n"
            f"{DIM}open the IDE's terminal and run `coru vscode auto` (or `koru shell` → /bridge start).\n"
            f"Cross-IDE start is deliberately not automated here; if you accept the risk, run\n"
            f"KORU_AUTOPILOT_ALLOW_CROSS_IDE=1 coru vscode auto yourself.{RESET}"
        )
        return
    log_path = ctx.project / ".koru" / "logs" / "bridge.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab") as log:
        subprocess.Popen(
            ["coru", "vscode", "auto"],
            cwd=ctx.project,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    print(f"{GREEN}bridge starting{RESET} {DIM}(log: {log_path}){RESET}")
    print(f"{DIM}check again in a few seconds with /bridge{RESET}")


COMMANDS: dict[str, object] = {
    "/help": _cmd_help,
    "/config": _cmd_config,
    "/integration": _cmd_integration,
    "/integrations": _cmd_integration,
    "/status": _cmd_status,
    "/tickets": _cmd_tickets,
    "/drain": _cmd_drain,
    "/ticket": _cmd_ticket,
    "/doctor": _cmd_doctor,
    "/bridge": _cmd_bridge,
}


@dataclass
class ShellContext:
    project: Path
    config: dict


# ── entry point ──────────────────────────────────────────────────────────────
def _banner(ctx: ShellContext) -> None:
    settings = shell_settings(ctx.config)
    count = len(enabled_integrations(ctx.config))
    print(
        _box(
            [
                f"{CYAN}✻{RESET} {BOLD}koru shell{RESET}",
                "",
                f"{DIM}project:{RESET}      {ctx.project}",
                f"{DIM}llm:{RESET}          {settings['llm_model']}",
                f"{DIM}integrations:{RESET} {count}/{len(INTEGRATION_CATALOG)} enabled",
                "",
                f"{DIM}/help for commands · /config to tune · /integration to pick integrations{RESET}",
            ],
        ),
    )


def _maybe_auto_drain(ctx: ShellContext) -> bool:
    """Honour the /config auto_drain switch on shell startup.

    Returns True when a drain was triggered.
    """
    settings = shell_settings(ctx.config)
    if not settings.get("auto_drain"):
        return False
    if "cursor" not in enabled_integrations(ctx.config):
        print(f"{DIM}auto_drain on, but cursor integration is disabled — skipping{RESET}")
        return False
    if not _open_tickets(ctx.project):
        print(f"{DIM}auto_drain on, queue empty — nothing to do{RESET}")
        return False
    print(f"{DIM}auto_drain on — draining the queue…{RESET}")
    _cmd_drain(ctx, "")
    return True


def _dispatch(ctx: ShellContext, line: str) -> bool:
    """Handle one input line. Returns False when the shell should exit."""
    if line in {"/exit", "/quit", "exit", "quit"}:
        return False
    if line.startswith("/"):
        head, _, arg = line.partition(" ")
        if head in COMMANDS:
            COMMANDS[head](ctx, arg)  # type: ignore[operator]
            return True
        # prefix match, deduplicated by handler so aliases don't collide
        handlers = {COMMANDS[name] for name in COMMANDS if name.startswith(head)}
        if len(handlers) == 1:
            handlers.pop()(ctx, arg)  # type: ignore[operator]
        elif handlers:
            names = sorted(name for name in COMMANDS if name.startswith(head))
            print(f"{YELLOW}ambiguous: {' '.join(names)}{RESET}")
        else:
            print(f"{YELLOW}unknown command — /help{RESET}")
        return True
    if line:
        settings = shell_settings(ctx.config)
        print(f"{DIM}→ {settings['llm_model']} …{RESET}")
        print(_ask_llm(ctx.project, settings, line))
    return True


def shell_main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="koru shell", description="Interactive koru REPL")
    parser.add_argument("--project", default=".", help="Project root (default: cwd)")
    args = parser.parse_args(argv)
    project = Path(args.project).expanduser().resolve()
    ctx = ShellContext(project=project, config=load_config(project))
    _banner(ctx)
    _maybe_auto_drain(ctx)
    while True:
        try:
            line = input(f"{CYAN}>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not _dispatch(ctx, line):
            return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(shell_main(sys.argv[1:]))
