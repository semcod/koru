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
    "llm_model": "qwen/qwen3-coder-next",
    "llm_endpoint": "https://openrouter.ai/api/v1/chat/completions",
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


INTEGRATION_CATALOG: tuple[Integration, ...] = (
    Integration("openrouter", "OpenRouter LLM", "executor.kind=llm tickets + shell prompts via API", True),
    Integration("qoder_chat", "Qoder / IDE chat", "autopilot injects prompts into the IDE chat (vscode lane)"),
    Integration("planfile_queue", "Planfile queue", "ticket queue drain (koru --queue --loop)", True),
    Integration("vdisplay", "vdisplay", "screen capture + verified injection for autopilot"),
    Integration("code2llm", "code2llm scan", "code-smell discovery tickets"),
    Integration("testql", "TestQL", "on-change quick test gates"),
    Integration("wup", "wup health", "service health probes feeding cycle decisions"),
    Integration("goal", "goal", "commit/publish advisory signals"),
    Integration("costs", "costs", "LLM cost tracking badge"),
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
        return {str(item) for item in stored}
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


def _checkbox_picker(
    title: str,
    items: list[tuple[str, str, bool]],
) -> list[str] | None:
    """Arrow-key checkbox list → selected keys, or None on cancel.

    ``items`` is (key, rendered_label, checked). Falls back to numeric input
    when stdin is not a TTY.
    """
    checked = {key for key, _, is_on in items if is_on}
    if not sys.stdin.isatty():  # numeric fallback (tests, pipes)
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
        key_pressed = _read_key()
        if key_pressed == "up":
            cursor = (cursor - 1) % len(items)
        elif key_pressed == "down":
            cursor = (cursor + 1) % len(items)
        elif key_pressed == " ":
            item_key = items[cursor][0]
            checked.symmetric_difference_update({item_key})
        elif key_pressed in {"\r", "\n"}:
            return sorted(checked)
        elif key_pressed in {"q", "esc", "\x03"}:
            return None


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


def _api_key(project: Path) -> str:
    env_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        for line in (project / ".env").read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _ask_llm(project: Path, settings: dict, prompt: str) -> str:
    key = _api_key(project)
    if not key:
        return f"{RED}OPENROUTER_API_KEY not set (env or .env) — /config to review settings.{RESET}"
    body = {
        "model": settings["llm_model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        str(settings["llm_endpoint"]),
        data=json.dumps(body).encode(),
        headers={
            "authorization": f"Bearer {key}",
            "content-type": "application/json",
            "x-title": "koru-shell",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        return payload["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"{RED}LLM call failed: {exc}{RESET}"


# ── slash commands ───────────────────────────────────────────────────────────
def _cmd_help(_ctx: "ShellContext", _arg: str) -> None:
    rows = [
        ("/help", "show this help"),
        ("/config", "interactive settings (model, actor, drain batch, auto-drain)"),
        ("/integration", "checkbox picker: which integrations are active"),
        ("/status", "queue + integrations overview"),
        ("/tickets", "list open tickets"),
        ("/drain [n]", "run the OpenRouter queue drain (default n from /config)"),
        ("/ticket <text>", "add a backlog ticket"),
        ("/doctor", "run koru doctor"),
        ("/exit", "leave the shell"),
    ]
    width = max(len(cmd) for cmd, _ in rows)
    print(_box([f"{CYAN}{cmd.ljust(width)}{RESET}  {desc}" for cmd, desc in rows]))
    print(f"{DIM}Plain text (no slash) is sent to {RESET}{CYAN}the configured LLM{RESET}{DIM} and printed here.{RESET}")


def _cmd_integration(ctx: "ShellContext", _arg: str) -> None:
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


def _cmd_config(ctx: "ShellContext", _arg: str) -> None:
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


def _cmd_status(ctx: "ShellContext", _arg: str) -> None:
    tickets = _open_tickets(ctx.project)
    current = enabled_integrations(ctx.config)
    settings = shell_settings(ctx.config)
    lines = [
        f"project      {ctx.project}",
        f"open tickets {BOLD}{len(tickets)}{RESET}",
        f"llm          {CYAN}{settings['llm_model']}{RESET}",
        "integrations "
        + " ".join(
            (f"{GREEN}☑{RESET}" if item.key in current else "☐") + item.key
            for item in INTEGRATION_CATALOG
        ),
    ]
    print(_box(lines))


def _cmd_tickets(ctx: "ShellContext", _arg: str) -> None:
    tickets = _open_tickets(ctx.project)
    if not tickets:
        print(f"{DIM}queue is empty{RESET}")
        return
    for t in tickets[:20]:
        executor = (t.get("executor") or {}).get("kind") or "?"
        print(f"  {CYAN}{t.get('id')}{RESET} {DIM}[{executor}]{RESET} {str(t.get('name'))[:70]}")


def _cmd_drain(ctx: "ShellContext", arg: str) -> None:
    if "openrouter" not in enabled_integrations(ctx.config):
        print(f"{YELLOW}openrouter integration is disabled — enable it via /integration{RESET}")
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


def _cmd_ticket(ctx: "ShellContext", arg: str) -> None:
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


def _cmd_doctor(ctx: "ShellContext", _arg: str) -> None:
    subprocess.run(["koru", "doctor"], cwd=ctx.project)


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
