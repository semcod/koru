from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class Plan:
    action: str
    ide: str | None = None
    instance: str | None = None
    text: str = ""
    install: bool = False
    auto_args: tuple[str, ...] = ()


@dataclass
class SessionContext:
    ide: str | None = None
    instance: str | None = None
    lane_override_warned: bool = False


def _distribution_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not-installed"
    except Exception:
        return "unknown"


def _print_runtime_versions() -> None:
    print(f"versions: coru={_distribution_version('coru')} koru={_distribution_version('koru')}")


def _extract_global_flags(argv: Sequence[str]) -> tuple[list[str], bool, bool]:
    """Parse leading global flags without breaking text shorthand mode."""
    rest = list(argv)
    verbose = False
    show_version = False
    while rest and rest[0] in {"-v", "--verbose", "-V", "--version"}:
        token = rest.pop(0)
        if token in {"-v", "--verbose"}:
            verbose = True
        if token in {"-V", "--version"}:
            show_version = True
    return rest, verbose, show_version


def _run(command: Sequence[str], *, passthrough: bool = True) -> int:
    try:
        proc = subprocess.run(list(command), check=False)
    except KeyboardInterrupt:
        return 130
    if passthrough:
        return int(proc.returncode)
    return int(proc.returncode)


def _cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _python_module_exists(module_name: str) -> bool:
    try:
        __import__(module_name)
    except Exception:
        return False
    return True


def _tool_argv(binary: str, module: str, args: Sequence[str]) -> list[str]:
    if _cmd_exists(binary):
        return [binary, *args]
    if _python_module_exists(module):
        return [sys.executable, "-m", module, *args]
    raise FileNotFoundError(binary)


def _project_venv_python() -> str | None:
    root = _repo_root()
    if root is None:
        return None
    candidate = root / ".venv" / "bin" / "python"
    if candidate.exists():
        return str(candidate)
    return None


def _ensure_commands(install: bool) -> int:
    missing: list[str] = []
    if not (_cmd_exists("koruenv") or _python_module_exists("koruenv.cli")):
        missing.append("koruenv")
    if not (_cmd_exists("koru") or _python_module_exists("koru.cli")):
        missing.append("koru")

    if not missing:
        print("ok: koruenv and koru are available")
        return 0

    if not install:
        print(f"missing commands: {', '.join(missing)}", file=sys.stderr)
        print("run: coru ensure --install", file=sys.stderr)
        return 1

    install_targets: list[str] = []
    for pkg in ("koruenv", "koru"):
        if pkg not in missing:
            continue
        local = _local_install_target(pkg)
        if local is not None:
            install_targets.extend(["-e", local])
        else:
            install_targets.append(pkg)
    installer_python = _project_venv_python() or sys.executable
    cmd = [installer_python, "-m", "pip", "install", "-U", *install_targets]
    rc = _run(cmd)
    if rc == 0 and installer_python != sys.executable:
        print("note: packages were installed into repo-local .venv")
        print("use: source .venv/bin/activate")
    return rc


def _setup_environment() -> int:
    rc = _ensure_commands(install=True)
    if rc != 0:
        return rc
    if _project_venv_python() is not None:
        print("ready: use 'source .venv/bin/activate' then run 'coru'")
    else:
        print("ready: run 'coru ensure' to verify commands")
    return 0


def _repo_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists() and (parent / "pyproject.toml").exists():
            return parent
    return None


def _local_install_target(package: str) -> str | None:
    root = _repo_root()
    if root is None:
        return None
    if package == "koru":
        if (root / "pyproject.toml").exists() and (root / "src" / "koru").is_dir():
            return str(root)
        return None
    candidate = root / "packages" / package
    if (candidate / "pyproject.toml").exists():
        return str(candidate)
    return None


_VALID_AUTOPILOT_IDES = frozenset(
    {"auto", "vscode", "vscodium", "cursor", "windsurf", "jetbrains", "zed", "antigravity"}
)


def _ide_from_vscode_pid() -> str | None:
    pid = (os.environ.get("VSCODE_PID") or "").strip()
    if not pid.isdigit():
        return None
    exe_path = Path(f"/proc/{pid}/exe")
    try:
        target = str(exe_path.resolve()).lower()
    except Exception:
        return None
    if "cursor" in target:
        return "cursor"
    if "windsurf" in target:
        return "windsurf"
    if "codium" in target or "vscodium" in target:
        return "vscodium"
    if "code" in target or "vscode" in target:
        return "vscode"
    return None


def _terminal_ide_hint() -> str | None:
    """Best-effort IDE owning this shell (no koru/koruide dependency)."""
    chrome = os.environ.get("CHROME_DESKTOP", "").strip().lower()
    if "cursor" in chrome or os.environ.get("CURSOR_AGENT") or os.environ.get("CURSOR_CLI"):
        return "cursor"
    term_program_version = os.environ.get("TERM_PROGRAM_VERSION", "").strip().lower()
    if (
        "windsurf" in term_program_version
        or os.environ.get("WINDSURF_CASCADE_TERMINAL")
        or "windsurf" in chrome
        or "windsurf" in os.environ.get("GIO_LAUNCHED_DESKTOP_FILE", "").lower()
    ):
        return "windsurf"
    terminal_emulator = os.environ.get("TERMINAL_EMULATOR", "").strip().lower()
    if (
        "jetbrains" in terminal_emulator
        or "jediterm" in terminal_emulator
        or os.environ.get("IDEA_INITIAL_DIRECTORY")
        or os.environ.get("PYCHARM_HOSTED")
        or os.environ.get("JETBRAINS_IDE")
    ):
        return "jetbrains"
    term_program = os.environ.get("TERM_PROGRAM", "").strip().lower()
    if term_program in {"vscode", "code"} and os.environ.get("VSCODE_PID"):
        via_pid = _ide_from_vscode_pid()
        if via_pid:
            return via_pid
        if "vscodium" in chrome:
            return "vscodium"
        return "vscode"
    if term_program in _VALID_AUTOPILOT_IDES and term_program != "auto":
        return term_program
    return None


def _instance_matches_ide(instance: str, ide: str) -> bool:
    return _ide_from_instance(instance) == ide


def _ide_from_instance(instance: str) -> str | None:
    normalized = instance.strip().lower()
    if not normalized or normalized == "auto":
        return None
    if normalized in _VALID_AUTOPILOT_IDES:
        return normalized
    prefix = normalized.split("-", 1)[0]
    return prefix if prefix in _VALID_AUTOPILOT_IDES else None


def _infer_default_ide() -> str:
    env_ide = (os.environ.get("KORU_AUTOPILOT_IDE") or "").strip().lower()
    hint = _terminal_ide_hint()
    if env_ide and env_ide != "auto":
        if hint and hint != env_ide and hint != "vscode":
            return hint
        return env_ide
    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip().lower()
    from_instance = _ide_from_instance(env_instance)
    if from_instance:
        if hint and hint != from_instance and hint != "vscode":
            return hint
        return from_instance
    return hint or "auto"


def _infer_default_instance(*, ide: str) -> str:
    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    if env_instance and env_instance.lower() != "auto":
        if ide == "auto":
            # Ignore generic "main" when IDE is unknown; prefer terminal-derived lane.
            if _ide_from_instance(env_instance):
                return env_instance
        elif _instance_matches_ide(env_instance, ide):
            return env_instance
    if ide and ide != "auto":
        return f"{ide}-main"
    terminal = _terminal_ide_hint()
    if terminal:
        return f"{terminal}-main"
    return "main"


def _maybe_warn_lane_override(ide: str, instance: str, *, context: SessionContext | None = None) -> None:
    if context is not None and context.lane_override_warned:
        return

    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    if not env_instance or env_instance == instance:
        return

    env_ide = _ide_from_instance(env_instance)
    should_warn = env_instance.lower() in {"main", "auto"} or (env_ide is not None and env_ide != ide)
    if not should_warn:
        return

    print(f"[coru] stale lane overridden: {env_instance} -> {instance}", file=sys.stderr)
    if context is not None:
        context.lane_override_warned = True


def _lane_env(ide: str, instance: str, shell: str) -> int:
    try:
        argv = _tool_argv("koruenv", "koruenv.cli", ["env", ide, instance, "--shell", shell])
    except FileNotFoundError:
        print("error: koruenv is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run(argv)


def _lane_status(ide: str, instance: str) -> int:
    try:
        argv = _tool_argv("koruenv", "koruenv.cli", ["status", ide, instance])
    except FileNotFoundError:
        print("error: koruenv is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run(argv)


_REFACTOR_MARKERS = (
    "refactor",
    "refaktoryz",
    "refakotryz",  # common typo: missing 't' (refakotryzuj vs refaktoryzuj)
)


def _refactor_intent(text: str) -> bool:
    t = text.strip().lower()
    if any(m in t for m in _REFACTOR_MARKERS):
        return True
    return re.search(r"refak\w*ryz", t) is not None


def _lane_auto(ide: str, instance: str, extra_args: Sequence[str]) -> int:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127

    run_payload = ["--", *koru_exec, "auto", *extra_args]

    try:
        cmd = _tool_argv("koruenv", "koruenv.cli", ["run", ide, instance, *run_payload])
    except FileNotFoundError:
        print("error: koruenv is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run(cmd)


def _koru_exec_argv() -> list[str] | None:
    if _cmd_exists("koru"):
        return ["koru"]
    if _python_module_exists("koru.cli"):
        return [sys.executable, "-m", "koru.cli"]
    return None


def _lane_chat_prompt(ide: str, instance: str, prompt: str) -> int:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127

    run_payload = ["--", *koru_exec, "autopilot", "drive", "--ide", ide, prompt]
    try:
        cmd = _tool_argv("koruenv", "koruenv.cli", ["run", ide, instance, *run_payload])
    except FileNotFoundError:
        print("error: koruenv is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run(cmd)


def _chat_llm_enabled(use_llm: bool) -> bool:
    return use_llm or bool((os.environ.get("OPENROUTER_API_KEY") or "").strip())


def _llm_rewrite_chat_prompt(text: str, *, ide: str, instance: str) -> str:
    model = os.environ.get("CORU_LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    try:
        from litellm import completion
    except Exception:
        return text

    instruction = (
        "Rewrite the user message into a concise IDE chat prompt for coding assistant. "
        "Preserve intent and language. Return only plain text, no JSON, no markdown fences."
    )
    user = f"ide={ide} instance={instance}\nmessage={text}"
    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()
        if content:
            return content
    except Exception:
        return text
    return text


def _heuristic_plan(text: str) -> Plan:
    t = text.strip().lower()
    ide_match = re.search(r"\b(vscode|vscodium|cursor|windsurf|jetbrains|zed|antigravity)\b", t)
    ide = ide_match.group(1) if ide_match else None

    instance_match = re.search(r"\b([a-z0-9_-]+-(main|a|b|lane|prod|dev))\b", t)
    instance = instance_match.group(1) if instance_match else None

    if any(k in t for k in ("install", "zainstal", "ensure", "napraw", "sprawdz")):
        return Plan(action="ensure", install=True)
    if any(k in t for k in ("status", "stan", "diag")):
        return Plan(action="status", ide=ide, instance=instance)
    if any(k in t for k in ("auto", "autonomous", "autopilot", "run")) or _refactor_intent(t):
        return Plan(action="auto", ide=ide, instance=instance)
    if any(k in t for k in ("lane", "instance", "env", "ustaw")):
        return Plan(action="lane", ide=ide, instance=instance)
    return Plan(action="status", ide=ide, instance=instance)


def _llm_plan(text: str) -> Plan | None:
    model = os.environ.get("CORU_LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    try:
        from litellm import completion
    except Exception:
        return None

    schema_hint = {
        "action": "ensure|lane|status|auto",
        "ide": "optional ide",
        "instance": "optional instance",
        "install": "optional bool",
    }
    prompt = (
        "Return ONLY JSON for coru command routing. "
        f"Schema: {json.dumps(schema_hint)}. "
        f"User text: {text}"
    )

    try:
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": "You route user intents to coru actions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
    except Exception:
        return None

    try:
        content = response.choices[0].message.content
        payload = json.loads(content)
    except Exception:
        return None

    action = str(payload.get("action") or "").strip().lower()
    ide = str(payload.get("ide") or "").strip().lower() or None
    instance = str(payload.get("instance") or "").strip() or None
    if action not in {"ensure", "lane", "status", "auto"}:
        return None
    return Plan(
        action=action,
        ide=ide,
        instance=instance,
        install=bool(payload.get("install", False)),
    )


def _resolve_defaults(plan: Plan, *, context: SessionContext | None = None) -> Plan:
    ide = plan.ide or (context.ide if context else None) or _infer_default_ide()
    instance = plan.instance or (context.instance if context else None) or _infer_default_instance(ide=ide)
    _maybe_warn_lane_override(ide, instance, context=context)
    if context is not None:
        context.ide = ide
        context.instance = instance
    return Plan(
        action=plan.action,
        ide=ide,
        instance=instance,
        text=plan.text,
        install=plan.install,
        auto_args=plan.auto_args,
    )


def _default_lane(ide: str | None, instance: str | None) -> tuple[str, str]:
    resolved_ide = ide or _infer_default_ide()
    resolved_instance = instance or _infer_default_instance(ide=resolved_ide)
    return resolved_ide, resolved_instance


def _execute_plan(
    plan: Plan,
    *,
    shell: str = "bash",
    context: SessionContext | None = None,
) -> int:
    resolved = _resolve_defaults(plan, context=context)
    if resolved.action == "ensure":
        return _ensure_commands(install=resolved.install)
    if resolved.action == "lane":
        return _lane_env(resolved.ide, resolved.instance, shell)
    if resolved.action == "status":
        return _lane_status(resolved.ide, resolved.instance)
    if resolved.action == "auto":
        return _lane_auto(resolved.ide, resolved.instance, list(resolved.auto_args))
    print(f"unsupported action: {resolved.action}", file=sys.stderr)
    return 2


def _build_plan_chain(prompt: str, *, use_llm: bool = False, single_action: bool = False) -> list[Plan]:
    first = _llm_plan(prompt) if use_llm else None
    if first is None:
        first = _heuristic_plan(prompt)
    if single_action:
        return [first]

    text = prompt.strip().lower()
    wants_auto = first.action == "auto" or _refactor_intent(text) or any(
        k in text for k in ("auto", "autonomous", "autopilot")
    )
    wants_setup = any(k in text for k in ("setup", "prepare", "przygotuj", "uruchom", "start"))

    if wants_auto or wants_setup:
        chain = [
            Plan(action="ensure", ide=first.ide, instance=first.instance, install=True),
            Plan(action="lane", ide=first.ide, instance=first.instance),
            Plan(action="status", ide=first.ide, instance=first.instance),
        ]
        if wants_auto:
            chain.append(Plan(action="auto", ide=first.ide, instance=first.instance, auto_args=first.auto_args))
        return chain

    return [first]


def _status_failure_ok_to_continue(plans: Sequence[Plan], index: int) -> bool:
    """Allow auto/setup chains to proceed when daemon is down; koru auto starts it."""
    return any(p.action == "auto" for p in plans[index + 1 :])


def _execute_plans(
    plans: Sequence[Plan],
    *,
    shell: str = "bash",
    context: SessionContext | None = None,
    announce: bool = False,
) -> int:
    ctx = context or SessionContext()
    plans_list = list(plans)
    rc = 0
    for index, plan in enumerate(plans_list):
        if announce:
            print(f"[coru] step={plan.action} ide={plan.ide or ctx.ide or '-'} instance={plan.instance or ctx.instance or '-'}")
        rc = _execute_plan(plan, shell=shell, context=ctx)
        if rc != 0:
            if plan.action == "status" and _status_failure_ok_to_continue(plans_list, index):
                print(
                    "[coru] status: autopilot daemon not ready; "
                    "continuing to auto (koru will start daemon)",
                    file=sys.stderr,
                )
                continue
            return rc
    return rc


def _chat_loop(*, use_llm: bool, shell: str, single_action: bool, verbose: bool = False) -> int:
    print("coru chat mode. Type 'quit' to exit.")
    _print_runtime_versions()
    if verbose:
        print("verbose: on")
    print("chat mode: message -> IDE chat (use '/<command>' for coru actions)")
    # Start with empty context so stale env lane values can be normalized once.
    ctx = SessionContext()
    llm_enabled = _chat_llm_enabled(use_llm)
    while True:
        try:
            line = input("coru> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 130

        if not line:
            continue
        if line.lower() in {"quit", "exit", "q"}:
            return 0

        if line.startswith("/"):
            command_text = line[1:].strip()
            if not command_text:
                continue
            plans = _build_plan_chain(command_text, use_llm=use_llm, single_action=single_action)
            rc = _execute_plans(plans, shell=shell, context=ctx, announce=True)
            if rc != 0:
                print(f"[coru] failed rc={rc}")
            continue

        resolved = _resolve_defaults(Plan(action="status"), context=ctx)
        outbound = line
        if llm_enabled:
            outbound = _llm_rewrite_chat_prompt(line, ide=resolved.ide, instance=resolved.instance)
            if verbose and outbound != line:
                print(f"[coru] llm rewrite: {outbound}")

        if verbose:
            print(f"[coru] drive ide={resolved.ide} instance={resolved.instance}")

        rc = _lane_chat_prompt(resolved.ide, resolved.instance, outbound)
        if rc != 0:
            print(f"[coru] failed rc={rc}")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coru")
    sub = p.add_subparsers(dest="command", required=False)

    p_ensure = sub.add_parser("ensure", help="check/install koruenv + koru")
    p_ensure.add_argument("--install", action="store_true")

    sub.add_parser("setup", help="prepare preferred repo-local environment")

    p_lane = sub.add_parser("lane", help="emit lane environment exports")
    p_lane.add_argument("ide", nargs="?")
    p_lane.add_argument("instance", nargs="?")
    p_lane.add_argument("--shell", choices=("bash", "sh", "zsh", "powershell"), default="bash")
    p_lane.add_argument("--print-env", action="store_true", help="deprecated alias; env is always printed")

    p_status = sub.add_parser("lane-status", help="show lane status")
    p_status.add_argument("ide", nargs="?")
    p_status.add_argument("instance", nargs="?")

    p_status_alias = sub.add_parser("status", help="alias for lane-status")
    p_status_alias.add_argument("ide", nargs="?")
    p_status_alias.add_argument("instance", nargs="?")

    p_env_alias = sub.add_parser("env", help="alias for lane")
    p_env_alias.add_argument("ide", nargs="?")
    p_env_alias.add_argument("instance", nargs="?")
    p_env_alias.add_argument("--shell", choices=("bash", "sh", "zsh", "powershell"), default="bash")

    p_auto = sub.add_parser("auto", help="run koru auto in a lane")
    p_auto.add_argument("ide", nargs="?")
    p_auto.add_argument("instance", nargs="?")
    p_auto.add_argument("rest", nargs=argparse.REMAINDER)

    p_text = sub.add_parser("text", help="natural language command")
    p_text.add_argument("prompt")
    p_text.add_argument("--llm", action="store_true", help="use litellm planner first")
    p_text.add_argument("--shell", choices=("bash", "sh", "zsh", "powershell"), default="bash")
    p_text.add_argument("--single-action", action="store_true", help="execute only one mapped action")

    p_chat = sub.add_parser("chat", help="interactive chat-first mode")
    p_chat.add_argument("--llm", action="store_true", help="use litellm planner first")
    p_chat.add_argument("--shell", choices=("bash", "sh", "zsh", "powershell"), default="bash")
    p_chat.add_argument("--single-action", action="store_true", help="execute only one mapped action")

    return p


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else list(sys.argv[1:])
    raw_argv, verbose, show_version = _extract_global_flags(raw_argv)
    if show_version:
        _print_runtime_versions()
        return 0

    known_commands = {"ensure", "setup", "lane", "lane-status", "status", "env", "auto", "text", "chat"}
    if not raw_argv:
        return _chat_loop(use_llm=False, shell="bash", single_action=False, verbose=verbose)
    if raw_argv[0] not in known_commands and not raw_argv[0].startswith("-"):
        nested_argv = ["text", " ".join(raw_argv)]
        if verbose:
            nested_argv = ["--verbose", *nested_argv]
        return main(nested_argv)

    args = _build_parser().parse_args(raw_argv)

    if args.command == "ensure":
        return _ensure_commands(install=args.install)

    if args.command == "setup":
        return _setup_environment()

    if args.command == "lane":
        ide, instance = _default_lane(args.ide, args.instance)
        return _lane_env(ide, instance, args.shell)

    if args.command == "lane-status":
        ide, instance = _default_lane(args.ide, args.instance)
        return _lane_status(ide, instance)

    if args.command == "status":
        ide, instance = _default_lane(args.ide, args.instance)
        return _lane_status(ide, instance)

    if args.command == "env":
        ide, instance = _default_lane(args.ide, args.instance)
        return _lane_env(ide, instance, args.shell)

    if args.command == "auto":
        ide, instance = _default_lane(args.ide, args.instance)
        rest = list(args.rest)
        if rest and rest[0] == "--":
            rest = rest[1:]
        return _lane_auto(ide, instance, rest)

    if args.command == "text":
        plans = _build_plan_chain(
            args.prompt,
            use_llm=args.llm,
            single_action=args.single_action,
        )
        return _execute_plans(plans, shell=args.shell, announce=verbose)

    if args.command == "chat":
        return _chat_loop(
            use_llm=args.llm,
            shell=args.shell,
            single_action=args.single_action,
            verbose=verbose,
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
