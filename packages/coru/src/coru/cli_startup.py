

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from coru.cli import Plan
def _koru_subprocess_timeout(koru_args: Sequence[str]) -> float | None:
    """Return timeout for koru subprocess calls; ``None`` for long-running commands."""
    from coru.cli import _KORU_SUBPROCESS_TIMEOUT_S
    if not koru_args:
        return _KORU_SUBPROCESS_TIMEOUT_S
    head = str(koru_args[0]).lower()
    if head in {"auto", "autonomous", "serve"}:
        return None
    if head == "autopilot" and len(koru_args) > 1 and str(koru_args[1]).lower() == "daemon":
        return None
    return _KORU_SUBPROCESS_TIMEOUT_S


def _project_from_argv(argv: Sequence[str]) -> str | None:
    for idx, token in enumerate(argv):
        if token == "--project" and idx + 1 < len(argv):
            value = str(argv[idx + 1]).strip()
            return value or None
        if token.startswith("--project="):
            value = token.split("=", 1)[1].strip()
            return value or None
    return None


def _chain_project_from_plans(plans: Sequence[Plan]) -> str | None:
    for plan in plans:
        project = _project_from_argv(plan.auto_args)
        if project:
            return project
    return None


def _normalize_log_format(raw: str | None) -> str:
    from coru.cli import _VALID_LOG_FORMATS
    value = (raw or "").strip().lower()
    if value in _VALID_LOG_FORMATS:
        return value
    fallback = (os.environ.get("KORU_STDIO_FORMAT") or "").strip().lower()
    if fallback in _VALID_LOG_FORMATS:
        return fallback
    return "human"


def _current_log_format() -> str:
    return _normalize_log_format(os.environ.get("CORU_LOG_FORMAT"))


def _emit_log(
    *,
    component: str,
    level: str,
    action: str,
    result: str,
    rc: int | None = None,
    verbose: bool = False,
    corr: str = "coru-cli",
    **extra: Any,
) -> None:
    record: dict[str, Any] = {
        "ts": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "corr": corr,
        "component": component,
        "level": level,
        "action": action,
        "result": result,
    }
    if rc is not None:
        record["rc"] = int(rc)
    if extra:
        record.update(extra)

    log_format = _current_log_format()
    if log_format == "jsonl":
        print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return
    if not verbose:
        return
    line = f"[coru] {level} action={action} result={result}"
    if rc is not None:
        line += f" rc={rc}"
    if "ide" in record and "instance" in record:
        line += f" ide={record['ide']} instance={record['instance']}"
    print(line, file=sys.stderr)


def _distribution_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        if distribution == "coru":
            try:
                return metadata.version("koru")
            except metadata.PackageNotFoundError:
                pass
            except Exception:
                return "unknown"
        return "not-installed"
    except Exception:
        return "unknown"


def _print_runtime_versions() -> None:
    from coru.cli import _distribution_version
    print(f"versions: coru={_distribution_version('coru')} koru={_distribution_version('koru')}")


def _startup_mode() -> str:
    """Default bare ``coru`` behavior: autonomous loop unless CORU_MODE=chat."""
    from coru.cli import _VALID_STARTUP_MODES
    mode = (os.environ.get("CORU_MODE") or "auto").strip().lower()
    if mode not in _VALID_STARTUP_MODES:
        print(
            f"[coru] warning: unknown CORU_MODE={mode!r}; use auto|chat (defaulting to auto)",
            file=sys.stderr,
        )
        return "auto"
    return mode


def _autonomous_startup_chain(auto_args: Sequence[str] = (), *, base: Plan | None = None) -> list[Plan]:
    """ensure → lane env → manage → diagnose → ``koru auto``."""
    from coru.cli import Plan, _resolve_defaults
    base = base or _resolve_defaults(Plan(action="auto"))
    return [
        Plan(action="ensure", ide=base.ide, instance=base.instance, install=True),
        Plan(action="lane", ide=base.ide, instance=base.instance),
        Plan(action="manage", ide=base.ide, instance=base.instance),
        Plan(action="diagnose", ide=base.ide, instance=base.instance),
        Plan(
            action="auto",
            ide=base.ide,
            instance=base.instance,
            auto_args=tuple(auto_args),
        ),
    ]


def _agent_lane_from_auto_args(auto_args: Sequence[str]) -> str | None:
    for idx, token in enumerate(auto_args):
        if token == "--agent-lane" and idx + 1 < len(auto_args):
            value = str(auto_args[idx + 1]).strip()
            return value or None
        if token.startswith("--agent-lane="):
            value = token.split("=", 1)[1].strip()
            return value or None
    return None


def _print_autonomous_banner(resolved: Plan, auto_args: Sequence[str]) -> None:
    """Print the koru-auto intro: runtime versions, terminal host, lane and log locations."""
    from coru.cli import _print_runtime_versions, _print_troubleshooting_log_locations, _terminal_shell_context
    term_ide, term_source, integrated = _terminal_shell_context()
    print("coru autonomous mode (koru auto). Press Ctrl+C to stop.")
    _print_runtime_versions()
    if integrated and term_ide:
        print(f"terminal host: integrated ide={term_ide} source={term_source}")
    else:
        print("terminal host: system shell (no IDE integrated terminal detected)")
    print(f"lane: ide={resolved.ide} instance={resolved.instance}")
    _print_troubleshooting_log_locations(resolved.ide, resolved.instance)
    if auto_args:
        print(f"[coru] koru auto args: {' '.join(auto_args)}")


def _enforce_runtime_readiness(root: Path | None) -> int | None:
    """Run the koru runtime-consistency check; return an exit code on fail-fast, else None."""
    from coru.cli import _import_koru_readiness_module
    if root is None:
        return None
    readiness = _import_koru_readiness_module()
    if readiness is None:
        return None
    strict = os.environ.get("CORU_READINESS_STRICT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    runtime = readiness.check_runtime_consistency(
        root,
        launcher_executable=sys.executable,
        strict=strict,
    )
    for line in readiness.format_readiness_lines(runtime, prefix="[coru]"):
        print(line, file=sys.stderr)
    if strict and not runtime.ok:
        if runtime.primary_fix:
            print(f"[coru] readiness fail-fast: {runtime.primary_fix}", file=sys.stderr)
        return 1
    return None


def _run_default_autonomous(
    auto_args: Sequence[str],
    *,
    shell: str = "bash",
    verbose: bool = False,
) -> int:
    from coru.cli import Plan, SessionContext, _execute_plans, _repo_root, _resolve_defaults
    ctx = SessionContext()
    chain_project = _project_from_argv(auto_args)
    if chain_project:
        ctx.project = chain_project
    selected_lane = _agent_lane_from_auto_args(auto_args)
    resolved = _resolve_defaults(Plan(action="auto", instance=selected_lane), context=ctx)
    _print_autonomous_banner(resolved, auto_args)
    readiness_exit = _enforce_runtime_readiness(_repo_root())
    if readiness_exit is not None:
        return readiness_exit
    plans = _autonomous_startup_chain(auto_args, base=resolved)
    return _execute_plans(plans, shell=shell, context=ctx, announce=verbose)


def _running_ide_choices() -> list[str]:
    try:
        from koruide.ide import detect_running_ides

        ids = [str(ide.id).strip().lower() for ide in detect_running_ides() if getattr(ide, "id", None)]
    except Exception:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for ide_id in ids:
        if not ide_id or ide_id in seen:
            continue
        seen.add(ide_id)
        ordered.append(ide_id)
    return ordered


def _supervisor_project_choices() -> list[str]:
    try:
        from coru.supervisor.paths import registry_path
        from coru.supervisor.registry import load_registry

        if not registry_path().is_file():
            return []
        registry = load_registry()
    except Exception:
        return []
    choices: list[str] = []
    seen: set[str] = set()
    for record in registry.lanes.values():
        project = str(getattr(record, "project", "") or "").strip()
        if not project:
            continue
        if project in seen:
            continue
        seen.add(project)
        choices.append(project)
    return choices


def _alive_daemon_instance(ide: str) -> str | None:
    """Check .planfile/.koru/koru-autopilot-*.daemon.json for a live daemon matching the given IDE."""
    from coru.cli import _ide_from_instance, _instance_from_socket_path
    for root in _runtime_metadata_roots():
        rt = root / ".planfile" / ".koru"
        if not rt.is_dir():
            continue
        for path in sorted(rt.glob("koru-autopilot-*.daemon.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            pid = payload.get("pid")
            if not isinstance(pid, int) or pid <= 0:
                continue
            try:
                os.kill(pid, 0)
            except OSError:
                continue
            instance = _instance_from_socket_path(str(payload.get("socket", "")))
            if not instance:
                instance = (payload.get("env") or {}).get("KORU_AUTOPILOT_INSTANCE", "")
            if not instance:
                continue
            cand_ide = _ide_from_instance(instance)
            if cand_ide == ide:
                return instance
    return None


def _instance_for_ide_choice(ide: str) -> str:
    from coru.cli import _instance_matches_ide
    alive_inst = _alive_daemon_instance(ide)
    if alive_inst:
        return alive_inst
    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    if env_instance and _instance_matches_ide(env_instance, ide):
        return env_instance
    try:
        from coru.supervisor.paths import registry_path
        from coru.supervisor.registry import load_registry

        if registry_path().is_file():
            registry = load_registry()
            if registry.active_lane:
                active = registry.lanes.get(registry.active_lane)
                if active and getattr(active, "ide", None) == ide:
                    return str(active.instance)
            for lane in registry.lanes.values():
                if getattr(lane, "ide", None) == ide:
                    return str(lane.instance)
    except Exception:
        pass
    return ide


def _choose_option(label: str, options: Sequence[str], *, default: str | None = None) -> str:
    if len(options) == 1:
        return options[0]
    print(f"coru: wybierz {label}:")
    default_index = 1
    for idx, option in enumerate(options, start=1):
        marker = ""
        if default is not None and option == default:
            default_index = idx
            marker = " (domyslny)"
        print(f"  {idx}) {option}{marker}")
    while True:
        raw = input(f"wybor [1-{len(options)}] (domyslnie {default_index}): ").strip()
        if not raw:
            return options[default_index - 1]
        if raw.isdigit():
            picked = int(raw)
            if 1 <= picked <= len(options):
                return options[picked - 1]
        print("niepoprawny wybor, sprobuj ponownie")


def _interactive_select_agent_lane(running: Sequence[str]) -> list[str]:
    from coru.cli import (
        _alive_daemon_ide,
        _connected_daemon_instance,
        _infer_default_ide,
        _instance_for_ide_choice,
        _terminal_shell_context,
    )
    if len(running) <= 1:
        return []
    terminal_ide, _terminal_source, terminal_integrated = _terminal_shell_context()
    if terminal_integrated and terminal_ide in running and terminal_ide != "vscode":
        alive_ide = _alive_daemon_ide()
        if alive_ide and alive_ide != terminal_ide and not _connected_daemon_instance(terminal_ide):
            selected_ide = alive_ide
        else:
            selected_ide = terminal_ide
    else:
        default_ide = _infer_default_ide()
        selected_ide = _choose_option(
            "IDE",
            running,
            default=default_ide if default_ide in running else running[0],
        )
    return ["--agent-lane", _instance_for_ide_choice(selected_ide)]


def _interactive_select_project_arg() -> list[str]:
    from coru.cli import _repo_root, _supervisor_project_choices
    projects = _supervisor_project_choices()
    root = _repo_root()
    if root is not None:
        root_s = str(root)
        if root_s not in projects:
            projects.insert(0, root_s)
    if len(projects) <= 1:
        return []
    selected_project = _choose_option("projekt", projects, default=str(root) if root is not None else projects[0])
    return ["--project", selected_project]


def _interactive_default_auto_args() -> list[str]:
    from coru.cli import _running_ide_choices
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return []
    auto_args: list[str] = []
    auto_args.extend(_interactive_select_agent_lane(_running_ide_choices()))
    auto_args.extend(_interactive_select_project_arg())
    return auto_args


def _extract_global_flags(argv: Sequence[str]) -> tuple[list[str], bool, bool, str, bool]:
    """Parse leading global flags without breaking text shorthand mode."""
    rest = list(argv)
    verbose = False
    show_version = False
    log_format = _normalize_log_format(os.environ.get("CORU_LOG_FORMAT"))
    require_plugin = False
    while rest:
        token = rest[0]
        if token not in {"-v", "--verbose", "-V", "--version", "--log-format", "--require-plugin"} and not token.startswith(
            "--log-format="
        ):
            break
        token = rest.pop(0)
        if token in {"-v", "--verbose"}:
            verbose = True
        if token in {"-V", "--version"}:
            show_version = True
        if token == "--require-plugin":
            require_plugin = True
        if token == "--log-format":
            if not rest:
                raise SystemExit("error: --log-format requires one of: human, jsonl")
            log_format = _normalize_log_format(rest.pop(0))
        elif token.startswith("--log-format="):
            log_format = _normalize_log_format(token.split("=", 1)[1])
    return rest, verbose, show_version, log_format, require_plugin


def _run(
    command: Sequence[str],
    *,
    passthrough: bool = True,
    timeout: float | None = None,
) -> int:
    try:
        kwargs: dict[str, Any] = {"check": False}
        if timeout is not None:
            kwargs["timeout"] = timeout
        proc = subprocess.run(list(command), **kwargs)
    except subprocess.TimeoutExpired:
        preview = " ".join(str(part) for part in command[:4])
        limit = timeout if timeout is not None else 0.0
        print(
            f"[coru] command timed out after {limit:.0f}s: {preview}",
            file=sys.stderr,
        )
        return 124
    except KeyboardInterrupt:
        return 130
    if passthrough:
        return int(proc.returncode)
    return int(proc.returncode)


def _cmd_exists(name: str) -> bool:
    from coru.cli import _binary_path
    return _binary_path(name) is not None


def _binary_path(name: str) -> str | None:
    from coru.cli import _repo_root
    candidates: list[Path] = []
    root = _repo_root()
    if root is not None:
        candidates.extend(
            [
                root / ".venv" / "bin" / name,
                root / "venv" / "bin" / name,
            ]
        )
    home = Path.home()
    candidates.append(home / ".venv" / "bin" / name)
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    return None


def _python_module_exists(module_name: str) -> bool:
    try:
        __import__(module_name)
    except Exception:
        return False
    return True


def _tool_argv(binary: str, module: str, args: Sequence[str]) -> list[str]:
    from coru.cli import _binary_path, _local_module_source_dir, _python_module_exists
    binary_path = _binary_path(binary)
    if binary_path is not None:
        return [binary_path, *args]
    if _python_module_exists(module):
        return [sys.executable, "-m", module, *args]
    local_source = _local_module_source_dir(module)
    if local_source is not None:
        runner = (
            "import sys; "
            f"sys.path.insert(0, {str(local_source)!r}); "
            f"from {module} import main; "
            "raise SystemExit(main(sys.argv[1:]))"
        )
        return [sys.executable, "-c", runner, *args]
    raise FileNotFoundError(binary)


def _tool_available(binary: str, module: str) -> bool:
    from coru.cli import _binary_path, _local_module_source_dir, _python_module_exists
    return (
        _binary_path(binary) is not None
        or _python_module_exists(module)
        or _local_module_source_dir(module) is not None
    )


def _ensure_commands(install: bool) -> int:
    from coru.cli import _project_venv_python, _run, _tool_available
    missing: list[str] = []
    for tool, module in (
        ("koruenv", "koruenv.cli"),
        ("koru", "koru.cli"),
        ("coru", "coru.cli"),
    ):
        if not _tool_available(tool, module):
            missing.append(tool)

    if not missing:
        print("ok: koruenv, koru, and coru are available")
        return 0

    if not install:
        print(f"missing commands: {', '.join(missing)}", file=sys.stderr)
        print("run: coru ensure --install", file=sys.stderr)
        return 1

    install_targets: list[str] = []
    for pkg in ("koruenv", "koru", "coru"):
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
    from coru.cli import _ensure_commands, _project_venv_python
    rc = _ensure_commands(install=True)
    if rc != 0:
        return rc
    if _project_venv_python() is not None:
        print("ready: use 'source .venv/bin/activate' then run 'coru'")
    else:
        print("ready: run 'coru ensure' to verify commands")
    return 0


def _runtime_metadata_roots() -> list[Path]:
    from coru.cli import _repo_root
    root = _repo_root()
    return [root] if root is not None else []


def _local_install_target(package: str) -> str | None:
    from coru.cli import _repo_root
    root = _repo_root()
    if root is None:
        return None
    if package == "koru":
        if (root / "pyproject.toml").exists() and (root / "src" / "koru").is_dir():
            return str(root)
        return None
    candidate = root / "packages" / package
    if package == "coru" and (candidate / "pyproject.toml").exists():
        return str(candidate)
    if (candidate / "pyproject.toml").exists():
        return str(candidate)
    return None
