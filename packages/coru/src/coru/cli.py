from __future__ import annotations

import argparse
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from coru import ide_detection, repair_registry
from coru.repair import RecordDiagnosisCommand, RepairHistoryQuery, RepairService

_LANE_ENV_KEYS = ("KORU_AUTOPILOT_IDE", "KORU_AUTOPILOT_INSTANCE", "KORU_AUTOPILOT_SOCKET")
_STRICT_PLUGIN_ENV_KEYS = (
    "KORU_STRICT_PLUGIN_VERSION",
    "KORU_STRICT_PLUGIN_ACK",
    "KORU_PLUGIN_VERSION_POLICY",
)
_LANE_SESSION_ENV_KEYS = (*_LANE_ENV_KEYS, *_STRICT_PLUGIN_ENV_KEYS)
_ORIGINAL_SUBPROCESS_RUN = subprocess.run
_LANE_ENV_PAYLOAD_TIMEOUT_S = float(os.environ.get("CORU_LANE_ENV_PAYLOAD_TIMEOUT_S", "5"))
_KORU_SUBPROCESS_TIMEOUT_S = float(os.environ.get("CORU_KORU_SUBPROCESS_TIMEOUT_S", "20"))


def _koru_subprocess_timeout(koru_args: Sequence[str]) -> float | None:
    """Return timeout for koru subprocess calls; ``None`` for long-running commands."""
    if not koru_args:
        return _KORU_SUBPROCESS_TIMEOUT_S
    head = str(koru_args[0]).lower()
    if head in {"auto", "autonomous", "serve"}:
        return None
    if head == "autopilot" and len(koru_args) > 1 and str(koru_args[1]).lower() == "daemon":
        return None
    return _KORU_SUBPROCESS_TIMEOUT_S



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
    project: str | None = None
    lane_override_warned: bool = False


@dataclass(frozen=True)
class AutoReadiness:
    rc: int
    ide: str
    instance: str
    reason: str = field(default="", compare=False)


_CHAIN_CONTEXT: SessionContext | None = None


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


def _coru_normalize_project(path: Path | str | None) -> Path | None:
    if path is None:
        return None
    try:
        from koru.autonomous_runtime import normalize_project_root

        return normalize_project_root(path)
    except Exception:
        pass
    try:
        current = Path(path).expanduser().resolve()
    except OSError:
        return None
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / ".git").exists():
            return candidate
    return current


def _coru_projects_equivalent(left: Path | str | None, right: Path | str | None) -> bool:
    try:
        from koru.autonomous_runtime import projects_equivalent

        return projects_equivalent(left, right)
    except Exception:
        left_norm = _coru_normalize_project(left)
        right_norm = _coru_normalize_project(right)
        if left_norm is None or right_norm is None:
            return False
        return left_norm == right_norm


def _active_project_root() -> Path | None:
    ctx = _CHAIN_CONTEXT
    if ctx is not None and ctx.project:
        return _coru_normalize_project(ctx.project)
    return _coru_normalize_project(_project_repo_root())


_VALID_LOG_FORMATS = frozenset({"human", "jsonl"})
_VALID_STARTUP_MODES = frozenset({"auto", "chat"})
_FALSE_ENV_VALUES = frozenset({"0", "false", "no", "off"})
_BLOCKING_PLUGIN_MANAGE_CODES = frozenset(
    {
        "plugin_build_missing",
        "plugin_build_mismatch",
        "plugin_installed_version_mismatch",
        "plugin_live_host_stale",
        "plugin_version_missing",
        "plugin_version_mismatch",
    }
)


def _trace_enabled() -> bool:
    return os.environ.get("CORU_TRACE", "").strip().lower() in {"1", "true", "yes", "oql"}


def _trace(step: str, **kv: Any) -> None:
    """Emit an OQL-style RESOLVE trace line to stderr.

    Format:  RESOLVE step  key=value key=value ...
    Enabled by CORU_TRACE=1 (or CORU_TRACE=oql).
    """
    if not _trace_enabled():
        return
    parts = [f"RESOLVE {step}"]
    for k, v in kv.items():
        parts.append(f"{k}={v}")
    print(" ".join(parts), file=sys.stderr)


def _normalize_log_format(raw: str | None) -> str:
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
    print(f"versions: coru={_distribution_version('coru')} koru={_distribution_version('koru')}")


def _startup_mode() -> str:
    """Default bare ``coru`` behavior: autonomous loop unless CORU_MODE=chat."""
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


def _run_default_autonomous(
    auto_args: Sequence[str],
    *,
    shell: str = "bash",
    verbose: bool = False,
) -> int:
    ctx = SessionContext()
    chain_project = _project_from_argv(auto_args)
    if chain_project:
        ctx.project = chain_project
    selected_lane = _agent_lane_from_auto_args(auto_args)
    resolved = _resolve_defaults(Plan(action="auto", instance=selected_lane), context=ctx)
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
    root = _project_repo_root()
    if root is not None:
        readiness = _import_koru_readiness_module()
        if readiness is not None:
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
    if len(running) <= 1:
        return []
    terminal_ide, _terminal_source, terminal_integrated = _terminal_shell_context()
    if terminal_integrated and terminal_ide in running:
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
    projects = _supervisor_project_choices()
    root = _project_repo_root()
    if root is not None:
        root_s = str(root)
        if root_s not in projects:
            projects.insert(0, root_s)
    if len(projects) <= 1:
        return []
    selected_project = _choose_option("projekt", projects, default=str(root) if root is not None else projects[0])
    return ["--project", selected_project]


def _interactive_default_auto_args() -> list[str]:
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
    return _binary_path(name) is not None


def _binary_path(name: str) -> str | None:
    candidates: list[Path] = []
    seen_roots: set[str] = set()
    for root in (_project_repo_root(), _repo_root()):
        if root is None:
            continue
        root_key = str(root.resolve())
        if root_key in seen_roots:
            continue
        seen_roots.add(root_key)
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


def _cwd_repo_root() -> Path | None:
    for parent in (Path.cwd(), *Path.cwd().parents):
        if (parent / ".git").exists() and (parent / "pyproject.toml").exists():
            return parent
    return None


def _project_repo_root() -> Path | None:
    return _cwd_repo_root() or _repo_root()


def _project_venv_candidates(root: Path) -> list[str]:
    candidates: list[str] = []
    for venv_name in (".venv", "venv"):
        for python_name in ("python", "python3"):
            candidate = root / venv_name / "bin" / python_name
            if candidate.exists():
                candidates.append(str(candidate))
                break
    return candidates


def _venv_has_installed_module(venv_python: str, package: str) -> bool:
    try:
        venv_bin = Path(venv_python).absolute().parent
        if venv_bin.name != "bin":
            return False
        venv_root = venv_bin.parent
    except Exception:
        return False
    for lib_dir in venv_root.glob("lib/python*"):
        site_packages = lib_dir / "site-packages"
        if (site_packages / package / "__init__.py").exists():
            return True
        if any(site_packages.glob(f"__editable__.{package}*.pth")):
            return True
    return (venv_bin / package).exists()


def _project_venv_python() -> str | None:
    root = _project_repo_root()
    if root is None:
        return None
    candidates = _project_venv_candidates(root)
    if not candidates:
        return None
    for python in candidates:
        if _venv_has_installed_module(python, "coru"):
            return python
    return candidates[0]


def _maybe_reexec_into_project_python(argv: Sequence[str]) -> bool:
    """Re-exec coru under repo-local .venv to avoid mixed runtime environments."""
    if os.environ.get("CORU_DISABLE_AUTO_REEXEC") == "1":
        return False
    if os.environ.get("CORU_REEXEC_DONE") == "1":
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False

    project_python = _project_venv_python()
    if not project_python:
        return False

    try:
        current_python = Path(sys.executable)
        target_python = Path(project_python)
        target_venv = target_python.parent.parent.resolve()
    except Exception:
        return False

    try:
        if current_python.resolve() == target_python.resolve() and Path(sys.prefix).resolve() == target_venv:
            return False
    except Exception:
        if str(current_python) == str(target_python):
            return False

    if str(current_python) == str(target_python):
        return False

    source_dir = _module_runtime_source_dir("coru.cli")
    env = dict(os.environ)
    env["CORU_REEXEC_DONE"] = "1"

    if source_dir is not None:
        runner = (
            "import sys; "
            f"sys.path.insert(0, {str(source_dir)!r}); "
            "from coru.cli import main; "
            "raise SystemExit(main(sys.argv[1:]))"
        )
        cmd = [str(target_python), "-c", runner, *list(argv)]
    elif _venv_has_installed_module(str(target_python), "coru"):
        cmd = [str(target_python), "-m", "coru.cli", *list(argv)]
    else:
        return False

    print(
        f"[coru] re-exec into project venv: {target_python}",
        file=sys.stderr,
    )
    os.execve(str(target_python), cmd, env)
    return True


def _local_module_source_dir(module_name: str) -> Path | None:
    root = _project_repo_root() or _repo_root()
    if root is None:
        return None
    package = module_name.split(".", 1)[0]
    if package == "koru":
        source = root / "src"
    else:
        source = root / "packages" / package / "src"
    module_path = source / package
    if (module_path / "__init__.py").exists():
        return source
    return None


def _installed_module_source_dir(module_name: str) -> Path | None:
    package = module_name.split(".", 1)[0]
    module = sys.modules.get(package)
    origin: Path | None = None
    if module is not None and getattr(module, "__file__", None):
        origin = Path(module.__file__).resolve()
    else:
        import importlib.util

        try:
            spec = importlib.util.find_spec(package)
        except Exception:
            return None
        if spec is None or spec.origin is None:
            return None
        origin = Path(spec.origin).resolve()
    if origin.name == "__init__.py":
        return origin.parent.parent
    return origin.parent


def _module_runtime_source_dir(module_name: str) -> Path | None:
    return _local_module_source_dir(module_name) or _installed_module_source_dir(module_name)


def _tool_available(binary: str, module: str) -> bool:
    return (
        _binary_path(binary) is not None
        or _python_module_exists(module)
        or _local_module_source_dir(module) is not None
    )


def _ensure_commands(install: bool) -> int:
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
    rc = _ensure_commands(install=True)
    if rc != 0:
        return rc
    if _project_venv_python() is not None:
        print("ready: use 'source .venv/bin/activate' then run 'coru'")
    else:
        print("ready: run 'coru ensure' to verify commands")
    return 0


def _runtime_metadata_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    for candidate in (_project_repo_root(), _repo_root()):
        if candidate is None:
            continue
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        roots.append(candidate)
    return roots


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
    if package == "coru" and (candidate / "pyproject.toml").exists():
        return str(candidate)
    if (candidate / "pyproject.toml").exists():
        return str(candidate)
    return None


_VALID_AUTOPILOT_IDES = frozenset(
    {"auto", "vscode", "vscodium", "cursor", "windsurf", "jetbrains", "zed", "antigravity"}
)

_WORKSPACE_SETTINGS_BY_IDE: dict[str, Path] = {
    "cursor": Path(".cursor") / "settings.json",
    "vscode": Path(".vscode") / "settings.json",
    "vscodium": Path(".vscode-oss") / "settings.json",
    "windsurf": Path(".windsurf") / "settings.json",
    "antigravity": Path(".antigravity") / "settings.json",
}

_PROJECT_IDE_SETTINGS_NAME = "settings.json"


def _ide_from_vscode_pid() -> str | None:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._ide_from_vscode_pid()


def _vscode_family_env_hint() -> str | None:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._vscode_family_env_hint()


def _windsurf_terminal_marker() -> bool:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._windsurf_terminal_marker()


def _terminal_ide_hint() -> str | None:
    """Best-effort IDE owning this shell."""
    ide, _source, _integrated = _terminal_shell_context()
    return ide


def _terminal_shell_context() -> tuple[str | None, str, bool]:
    """Return ``(ide, source, integrated)`` for the current shell context."""
    fallback = _terminal_shell_context_fallback()
    if fallback[2]:
        return fallback
    try:
        from koruide.ide import detect_terminal_host_context
        ctx = detect_terminal_host_context()
        return ctx.ide, ctx.source, ctx.integrated
    except Exception:
        return fallback


def _terminal_host_kind() -> str:
    return ide_detection.terminal_host_kind()


def _print_terminal_context(*, prefix: str = "[coru]") -> None:
    from koru.autonomy.ide_operator_guidance import terminal_kind_label

    ide, source, integrated = ide_detection.terminal_shell_context()
    kind = ide_detection.terminal_host_kind()
    if ide:
        print(
            f"{prefix} terminal: ide={ide} kind={kind} "
            f"({terminal_kind_label(kind)}) source={source}",
            file=sys.stderr,
        )
    else:
        print(f"{prefix} terminal: system shell (no IDE host detected)", file=sys.stderr)
    if integrated and ide:
        print(
            f"{prefix} lane hint: integrated {ide} terminal — "
            f"use `coru {ide} auto` unless another IDE lane is intentional",
            file=sys.stderr,
        )


def _terminal_shell_context_fallback() -> tuple[str | None, str, bool]:
    """Provider-first shell context detection (brand name before generic vscode)."""
    return ide_detection._terminal_shell_context_fallback(
        ide_from_vscode_pid=_ide_from_vscode_pid,
        vscode_family_env_hint=_vscode_family_env_hint,
        windsurf_terminal_marker=_windsurf_terminal_marker,
    )


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


def _workspace_settings_path_for_ide(ide: str) -> Path | None:
    root = _project_repo_root()
    rel = _WORKSPACE_SETTINGS_BY_IDE.get((ide or "").strip().lower())
    if root is None or rel is None:
        return None
    return root / rel


def _workspace_socket_path_for_ide(ide: str) -> str | None:
    path = _workspace_settings_path_for_ide(ide)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    raw = payload.get("koruAutopilot.socketPath")
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    return value or None


def _instance_from_socket_path(socket_path: str | None) -> str | None:
    if not socket_path:
        return None
    name = Path(socket_path).name
    match = re.match(r"^koru-autopilot-([A-Za-z0-9_-]+)\.sock$", name)
    if not match:
        return None
    instance = match.group(1).strip().lower()
    return instance or None


def _workspace_lane_hint(preferred_ide: str | None = None) -> tuple[str | None, str | None]:
    order: list[str] = []
    preferred = (preferred_ide or "").strip().lower()
    if preferred in _WORKSPACE_SETTINGS_BY_IDE:
        order.append(preferred)
    for ide in _WORKSPACE_SETTINGS_BY_IDE:
        if ide not in order:
            order.append(ide)

    for ide in order:
        instance = _instance_from_socket_path(_workspace_socket_path_for_ide(ide))
        if instance:
            return _ide_from_instance(instance) or ide, instance
    return None, None


def _project_ide_settings_path(ide: str) -> Path | None:
    root = _project_repo_root()
    ide_id = (ide or "").strip().lower()
    if root is None or ide_id not in _VALID_AUTOPILOT_IDES or ide_id == "auto":
        return None
    return root / ".koru" / ide_id / _PROJECT_IDE_SETTINGS_NAME


def _load_project_ide_settings(ide: str) -> dict[str, Any]:
    path = _project_ide_settings_path(ide)
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _project_ide_settings_lane(ide: str) -> tuple[str, str] | None:
    ide_id = (ide or "").strip().lower()
    if ide_id not in _VALID_AUTOPILOT_IDES or ide_id == "auto":
        return None
    settings = _load_project_ide_settings(ide_id)
    raw_instance = settings.get("instance") or settings.get("agent_lane") or settings.get("lane")
    if isinstance(raw_instance, str) and raw_instance.strip():
        return _normalize_lane_pair(ide_id, raw_instance.strip())
    raw_socket = settings.get("socket") or settings.get("socket_path") or settings.get("socketPath")
    if isinstance(raw_socket, str):
        instance = _instance_from_socket_path(raw_socket)
        if instance:
            return _normalize_lane_pair(ide_id, instance)
    return None


def _remember_project_ide_settings(ide: str, instance: str) -> None:
    ide_id = (ide or "").strip().lower()
    instance_id = (instance or "").strip()
    path = _project_ide_settings_path(ide_id)
    if path is None or not instance_id or ide_id == "auto":
        return
    existing = _load_project_ide_settings(ide_id)
    payload: dict[str, Any] = dict(existing)
    payload["ide"] = ide_id
    payload["instance"] = instance_id
    root = _project_repo_root()
    if root is not None:
        payload["project"] = str(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        return


def _supervisor_lane_defaults() -> tuple[str, str] | None:
    try:
        from coru.supervisor.paths import registry_path
        from coru.supervisor.registry import active_lane_pair

        if not registry_path().is_file():
            return None
        return active_lane_pair()
    except Exception:
        return None


def _supervisor_lane_project(instance: str | None = None) -> str | None:
    try:
        from coru.supervisor.paths import registry_path
        from coru.supervisor.registry import load_registry

        if not registry_path().is_file():
            return None
        registry = load_registry()
        key = instance or registry.active_lane
        if not key:
            return None
        record = registry.lanes.get(key)
        if record is None or not record.project:
            return None
        project_path = Path(record.project).expanduser()
        if not project_path.is_dir():
            return None
        return str(project_path.resolve())
    except Exception:
        return None


@functools.lru_cache(maxsize=None)
def _is_lane_plugin_connected(ide: str, instance: str) -> bool:
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        if subprocess.run is _ORIGINAL_SUBPROCESS_RUN:
            return False
    status = _lane_status_payload(ide, instance)
    if not status or not isinstance(status, dict):
        connected = False
    else:
        plugins = status.get("plugins")
        rejected = status.get("rejected_plugins")
        has_plugins = bool(plugins) and isinstance(plugins, list) and len(plugins) > 0
        has_rejected = bool(rejected) and isinstance(rejected, list) and len(rejected) > 0
        connected = has_plugins or has_rejected
    _trace("is_lane_plugin_connected", ide=ide, instance=instance, connected=connected)
    return connected


def _connected_daemon_instance(ide: str) -> str | None:
    instance = _alive_daemon_instance(ide)
    if not instance:
        return None
    if _is_lane_plugin_connected(ide, instance):
        return instance
    return None


def _connected_daemon_from_meta(path: Path) -> tuple[str, str, float] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    pid = payload.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    instance = _instance_from_socket_path(str(payload.get("socket", "")))
    if not instance:
        instance = (payload.get("env") or {}).get("KORU_AUTOPILOT_INSTANCE", "")
    if not instance:
        return None
    ide = _ide_from_instance(instance)
    if not ide or not _is_lane_plugin_connected(ide, instance):
        return None
    return ide, instance, path.stat().st_mtime


def _alive_daemon_ide() -> str | None:
    """Check .planfile/.koru/koru-autopilot-*.daemon.json for a live daemon."""
    best_connected: tuple[str, str, float] | None = None  # (ide, instance, mtime)
    for root in _runtime_metadata_roots():
        rt = root / ".planfile" / ".koru"
        if not rt.is_dir():
            continue
        for path in sorted(rt.glob("koru-autopilot-*.daemon.json")):
            candidate = _connected_daemon_from_meta(path)
            if candidate is None:
                continue
            ide, instance, mtime = candidate
            if best_connected is None or mtime > best_connected[2]:
                best_connected = (ide, instance, mtime)
    if best_connected is None:
        return None
    _trace("alive_daemon", ide=best_connected[0], instance=best_connected[1])
    return best_connected[0]


def _prefer_terminal_over_lane(hint: str | None, lane_ide: str) -> bool:
    return bool(hint and hint != lane_ide and hint != "vscode")


def _warn_integrated_terminal_daemon_mismatch(hint: str) -> None:
    if _connected_daemon_instance(hint):
        return
    alive_ide = _alive_daemon_ide()
    if not alive_ide or alive_ide == hint:
        return
    _trace(
        "infer_ide.daemon_mismatch",
        terminal=hint,
        alive_daemon=alive_ide,
        reason="terminal IDE has no connected daemon; keeping terminal IDE",
    )
    print(
        f"[coru] integrated terminal IDE={hint} has no connected daemon "
        f"(alive daemon: {alive_ide}). "
        f"Connect the plugin in {hint}, or pass an explicit lane "
        f"(e.g. `coru calibration {hint}` / KORU_AUTOPILOT_INSTANCE={hint}).",
        file=sys.stderr,
    )


def _integrated_terminal_default_ide(hint: str | None, *, integrated: bool) -> str | None:
    if not integrated or not hint or hint == "auto":
        return None
    _warn_integrated_terminal_daemon_mismatch(hint)
    _trace("infer_ide.result", ide=hint, reason="integrated_terminal")
    return hint


def _project_settings_default_ide(hint: str | None) -> str | None:
    if hint and _project_ide_settings_lane(hint) is not None:
        _trace("infer_ide.result", ide=hint, reason="project_settings")
        return hint
    return None


def _supervisor_default_ide(hint: str | None) -> str | None:
    supervisor = _supervisor_lane_defaults()
    if supervisor is None:
        return None
    if _prefer_terminal_over_lane(hint, supervisor[0]):
        _trace("infer_ide.result", ide=hint, reason="terminal_over_supervisor")
        return hint
    _trace("infer_ide.result", ide=supervisor[0], reason="supervisor")
    return supervisor[0]


def _env_default_ide(hint: str | None, workspace_ide: str | None) -> str | None:
    env_ide = (os.environ.get("KORU_AUTOPILOT_IDE") or "").strip().lower()
    if env_ide and env_ide != "auto":
        if _prefer_terminal_over_lane(hint, env_ide):
            _trace("infer_ide.result", ide=hint, reason="terminal_over_env")
            return hint
        _trace("infer_ide.result", ide=env_ide, reason="env:KORU_AUTOPILOT_IDE")
        return env_ide
    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip().lower()
    from_instance = _ide_from_instance(env_instance)
    if from_instance:
        if _prefer_terminal_over_lane(hint, from_instance):
            _trace("infer_ide.result", ide=hint, reason="terminal_over_instance")
            return hint
        _trace("infer_ide.result", ide=from_instance, reason="env:KORU_AUTOPILOT_INSTANCE")
        return from_instance
    if hint:
        _trace("infer_ide.result", ide=hint, reason="terminal_fallback")
        return hint
    if workspace_ide:
        _trace("infer_ide.result", ide=workspace_ide, reason="workspace_settings")
        return workspace_ide
    return None


def _infer_default_ide() -> str:
    hint = _terminal_ide_hint()
    _term_ide, _term_source, integrated = _terminal_shell_context()
    _trace("infer_ide.start", terminal_hint=hint, integrated=integrated, source=_term_source)
    for resolver in (
        lambda: _integrated_terminal_default_ide(hint, integrated=integrated),
        lambda: _project_settings_default_ide(hint),
        lambda: _supervisor_default_ide(hint),
        lambda: _env_default_ide(hint, _workspace_lane_hint(hint)[0]),
    ):
        ide = resolver()
        if ide:
            return ide
    _trace("infer_ide.result", ide="auto", reason="no_signal")
    return "auto"


def _project_ide_settings_instance(ide: str) -> str | None:
    settings_lane = _project_ide_settings_lane(ide)
    if settings_lane is not None:
        return settings_lane[1]
    return None


def _supervisor_default_instance(ide: str) -> str | None:
    supervisor = _supervisor_lane_defaults()
    if supervisor is None:
        return None
    sup_ide, sup_instance = supervisor
    terminal = _terminal_ide_hint()
    if terminal and terminal != sup_ide and terminal != "vscode":
        if ide == "auto" or ide == terminal:
            terminal_settings = _project_ide_settings_instance(terminal)
            if terminal_settings is not None:
                return terminal_settings
            return terminal
    if ide == "auto" or sup_ide == ide:
        return sup_instance
    return None


def _environment_default_instance(ide: str) -> str | None:
    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    if not env_instance or env_instance.lower() == "auto":
        return None
    if ide == "auto":
        # Ignore generic "main" when IDE is unknown; prefer terminal-derived lane.
        if _ide_from_instance(env_instance):
            return env_instance
        return None
    if _instance_matches_ide(env_instance, ide):
        return env_instance
    return None


def _auto_default_instance() -> str:
    terminal = _terminal_ide_hint()
    if terminal:
        terminal_settings = _project_ide_settings_instance(terminal)
        if terminal_settings is not None:
            return terminal_settings
        return terminal
    _workspace_ide, workspace_instance = _workspace_lane_hint(None)
    if workspace_instance:
        return workspace_instance
    return "main"


def _workspace_default_instance(ide: str) -> str | None:
    workspace_ide, workspace_instance = _workspace_lane_hint(ide)
    if workspace_instance:
        if workspace_ide == ide:
            return workspace_instance
    return None


def _infer_default_instance(*, ide: str) -> str:
    _trace("infer_instance.start", ide=ide)
    sources = [
        ("project_settings", _project_ide_settings_instance(ide)),
        ("supervisor", _supervisor_default_instance(ide)),
        ("environment", _environment_default_instance(ide)),
    ]
    for source_name, candidate in sources:
        if candidate is not None:
            _trace("infer_instance.result", instance=candidate, reason=source_name)
            return candidate

    if ide == "auto":
        result = _auto_default_instance()
        _trace("infer_instance.result", instance=result, reason="auto_default")
        return result

    workspace_instance = _workspace_default_instance(ide)
    if workspace_instance is not None:
        _trace("infer_instance.result", instance=workspace_instance, reason="workspace")
        return workspace_instance

    if ide and ide != "auto":
        _trace("infer_instance.result", instance=ide, reason="ide_as_instance")
        return ide
    _trace("infer_instance.result", instance="main", reason="fallback")
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


def _normalize_lane_pair(ide: str, instance: str) -> tuple[str, str]:
    """Make lane resolution deterministic: explicit instance wins over IDE hint."""
    instance_ide = _ide_from_instance(instance)
    if instance_ide and ide and ide != "auto" and ide != instance_ide:
        print(f"[coru] lane normalized from instance: ide {ide} -> {instance_ide} (instance={instance})", file=sys.stderr)
        return instance_ide, instance
    if ide == "auto" and instance_ide:
        return instance_ide, instance
    return ide, instance


def _lane_subprocess_env(ide: str, instance: str, *, base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    env["KORU_AUTOPILOT_IDE"] = ide
    env["KORU_AUTOPILOT_INSTANCE"] = instance
    env.pop("KORU_AUTOPILOT_SOCKET", None)
    _apply_strict_plugin_policy_defaults(env)
    return env


def _apply_strict_plugin_policy_defaults(env: dict[str, str], *, force: bool = False) -> None:
    if force or (
        env.get("KORU_STRICT_PLUGIN_VERSION") is None
        and env.get("KORU_PLUGIN_VERSION_POLICY") is None
    ):
        env["KORU_STRICT_PLUGIN_VERSION"] = "1"
    if force or env.get("KORU_STRICT_PLUGIN_ACK") is None:
        env["KORU_STRICT_PLUGIN_ACK"] = "1"


@contextmanager
def _bind_lane_session(ide: str, instance: str):
    previous = {key: os.environ[key] for key in _LANE_SESSION_ENV_KEYS if key in os.environ}
    os.environ["KORU_AUTOPILOT_IDE"] = ide
    os.environ["KORU_AUTOPILOT_INSTANCE"] = instance
    os.environ.pop("KORU_AUTOPILOT_SOCKET", None)
    _apply_strict_plugin_policy_defaults(os.environ)
    try:
        yield
    finally:
        for key in _LANE_SESSION_ENV_KEYS:
            if key in previous:
                os.environ[key] = previous[key]
            else:
                os.environ.pop(key, None)


def _run_with_lane_environment(
    command: Sequence[str],
    *,
    ide: str,
    instance: str,
    timeout: float | None = _KORU_SUBPROCESS_TIMEOUT_S,
) -> int:
    previous = {key: os.environ[key] for key in _LANE_SESSION_ENV_KEYS if key in os.environ}
    try:
        os.environ["KORU_AUTOPILOT_IDE"] = ide
        os.environ["KORU_AUTOPILOT_INSTANCE"] = instance
        os.environ.pop("KORU_AUTOPILOT_SOCKET", None)
        _apply_strict_plugin_policy_defaults(os.environ)
        return _run(command, timeout=timeout)
    finally:
        for key in _LANE_SESSION_ENV_KEYS:
            if key in previous:
                os.environ[key] = previous[key]
            else:
                os.environ.pop(key, None)


def _project_for_lane(ide: str, instance: str) -> str | None:
    ctx = _CHAIN_CONTEXT
    if ctx is not None and ctx.project:
        return ctx.project
    root = _project_repo_root()
    if root is not None:
        return str(root)
    supervisor = _supervisor_lane_project(instance)
    if supervisor:
        return supervisor
    return None


def _koru_autopilot_env_payload(ide: str, instance: str) -> dict[str, Any] | None:
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        if subprocess.run is _ORIGINAL_SUBPROCESS_RUN:
            return None
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        return None
    project = _project_for_lane(ide, instance)
    cmd = [*koru_exec, "autopilot", "env", "--ide", ide, "--format", "json"]
    if project:
        cmd.extend(["--project", project])
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            env=_lane_subprocess_env(ide, instance),
            timeout=_LANE_ENV_PAYLOAD_TIMEOUT_S,
            close_fds=True,
        )
    except subprocess.TimeoutExpired:
        print(
            f"[coru] koru autopilot env timed out after {_LANE_ENV_PAYLOAD_TIMEOUT_S:.0f}s "
            f"(ide={ide} instance={instance})",
            file=sys.stderr,
        )
        return None
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return None
    if not isinstance(payload, dict) or not payload.get("ok"):
        return None
    return payload


def _run_with_resolved_lane_env(
    command: Sequence[str],
    *,
    ide: str,
    instance: str,
    timeout: float | None = _KORU_SUBPROCESS_TIMEOUT_S,
) -> int:
    payload = _koru_autopilot_env_payload(ide, instance)
    if not payload:
        if timeout is None:
            return _run(list(command))
        return _run_with_lane_environment(command, ide=ide, instance=instance, timeout=timeout)

    previous = {key: os.environ[key] for key in _LANE_SESSION_ENV_KEYS if key in os.environ}
    resolved_env = payload.get("env") or {}
    try:
        for key, value in resolved_env.items():
            os.environ[str(key)] = str(value)
        if payload.get("instance"):
            os.environ["KORU_AUTOPILOT_INSTANCE"] = str(payload["instance"])
        if payload.get("ide"):
            os.environ["KORU_AUTOPILOT_IDE"] = str(payload["ide"])
        _apply_strict_plugin_policy_defaults(os.environ)
        return _run(command, timeout=timeout)
    finally:
        for key in _LANE_SESSION_ENV_KEYS:
            if key in previous:
                os.environ[key] = previous[key]
            else:
                os.environ.pop(key, None)


def _run_koru_lane(ide: str, instance: str, koru_args: Sequence[str]) -> int:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run_with_resolved_lane_env(
        [*koru_exec, *koru_args],
        ide=ide,
        instance=instance,
        timeout=_koru_subprocess_timeout(koru_args),
    )


def _koruenv_run_fallback(ide: str, instance: str, run_payload: Sequence[str]) -> int:
    try:
        cmd = _tool_argv("koruenv", "koruenv.cli", ["run", ide, instance, *run_payload])
    except FileNotFoundError:
        print("error: koruenv is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run_with_lane_environment(cmd, ide=ide, instance=instance)


def _lane_env(ide: str, instance: str, shell: str) -> int:
    if _koru_exec_argv() is not None:
        args = ["autopilot", "env", "--ide", ide]
        project = _project_for_lane(ide, instance)
        if project:
            args.extend(["--project", project])
        return _run_koru_lane(ide, instance, args)
    try:
        argv = _tool_argv("koruenv", "koruenv.cli", ["env", ide, instance, "--shell", shell])
    except FileNotFoundError:
        print("error: koruenv is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run_with_lane_environment(argv, ide=ide, instance=instance)


def _lane_status_raw(ide: str, instance: str) -> int:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run_koru_lane(
        ide,
        instance,
        ["autopilot", "status", "--ide", ide, "--explain"],
    )


def _lane_status(ide: str, instance: str) -> int:
    return _lane_status_raw(ide, instance)


def _subprocess_blocked_in_tests() -> bool:
    return (
        ("pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"))
        and subprocess.run is _ORIGINAL_SUBPROCESS_RUN
    )


def _lane_status_env(
    ide: str,
    instance: str,
    resolved: dict[str, Any],
) -> dict[str, str]:
    env = _lane_subprocess_env(ide, instance)
    resolved_env = resolved.get("env") if isinstance(resolved.get("env"), dict) else {}
    for key, value in resolved_env.items():
        env[str(key)] = str(value)
    if resolved.get("ide"):
        env["KORU_AUTOPILOT_IDE"] = str(resolved["ide"])
    if resolved.get("instance"):
        env["KORU_AUTOPILOT_INSTANCE"] = str(resolved["instance"])
    if resolved.get("socket"):
        env["KORU_AUTOPILOT_SOCKET"] = str(resolved["socket"])
    return env


def _run_lane_status_json(
    koru_exec: list[str],
    ide: str,
    instance: str,
    env: dict[str, str],
) -> dict[str, Any] | None:
    project = _project_for_lane(ide, instance)
    cmd = [*koru_exec, "autopilot", "status", "--ide", ide, "--json"]
    if project:
        cmd.extend(["--project", project])
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            env=env,
            timeout=_LANE_ENV_PAYLOAD_TIMEOUT_S,
            close_fds=True,
        )
    except (subprocess.TimeoutExpired, Exception):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _lane_status_payload(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if _subprocess_blocked_in_tests():
        return None
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        return None
    resolved = payload or _koru_autopilot_env_payload(ide, instance) or {}
    env = _lane_status_env(ide, instance, resolved)
    return _run_lane_status_json(koru_exec, ide, instance, env)


def _fetch_manage_report(ide: str, instance: str) -> dict[str, Any] | None:
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        if subprocess.run is _ORIGINAL_SUBPROCESS_RUN:
            return None
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        return None
    cmd = [*koru_exec, "autopilot", "manage", "--ide", ide, "--format", "json"]
    project = _project_for_lane(ide, instance)
    if project:
        cmd.extend(["--project", project])
    env = _lane_subprocess_env(ide, instance)
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False, env=env, timeout=_LANE_ENV_PAYLOAD_TIMEOUT_S, close_fds=True)
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None
    if proc.returncode != 0 and not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _manage_repair_context(
    ide: str,
    instance: str,
) -> tuple[dict[str, Any] | None, bool, str | None, list[repair_registry.RepairProblem]]:
    manage = _fetch_manage_report(ide, instance)
    if not manage:
        return None, False, None, []

    daemon_running = bool(
        isinstance(manage.get("daemon"), dict)
        and manage["daemon"].get("running")
    )
    plugin = manage.get("plugin") if isinstance(manage.get("plugin"), dict) else {}
    expected_build = str(plugin.get("expected_build_sha") or "").strip() or None
    problems = repair_registry.collect_problems_from_manage_report(manage)
    return manage, daemon_running, expected_build, problems


def _drive_result_from_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    drive = payload.get("drive") if isinstance(payload.get("drive"), dict) else None
    if drive is None and payload.get("verification"):
        return payload
    return drive


def _problem_from_readiness_issue(
    issue: Any,
    *,
    source: str,
) -> repair_registry.RepairProblem:
    return repair_registry.RepairProblem(
        code=str(issue.code),
        severity="error" if issue.severity == "fail" else "warning",
        message=str(issue.message),
        fix_hint=str(issue.fix_command) if issue.fix_command else None,
        context={"source": source},
    )


def _runtime_readiness_problems(
    readiness: Any,
    root: Path | None,
) -> list[repair_registry.RepairProblem]:
    if readiness is None or root is None or not hasattr(readiness, "check_runtime_consistency"):
        return []
    runtime = readiness.check_runtime_consistency(root, launcher_executable=sys.executable, strict=False)
    return [
        _problem_from_readiness_issue(issue, source="readiness.runtime")
        for issue in runtime.issues
    ]


def _lane_alignment_problems(
    readiness: Any,
    root: Path | None,
    payload: dict[str, Any] | None,
    *,
    ide: str,
    instance: str,
) -> list[repair_registry.RepairProblem]:
    if readiness is None or root is None or not payload:
        return []
    socket_raw = str(payload.get("socket") or "").strip()
    if not socket_raw:
        return []

    terminal_ide, _terminal_source, terminal_integrated = _terminal_shell_context()
    lane = readiness.check_lane_terminal_socket_alignment(
        autopilot_ide=ide,
        lane_instance=instance,
        socket_path=Path(socket_raw),
        terminal_ide=terminal_ide,
        terminal_integrated=terminal_integrated,
        terminal_kind=_terminal_host_kind(),
    )
    return [
        _problem_from_readiness_issue(issue, source="readiness.lane_alignment")
        for issue in lane.issues
    ]


def _collect_lane_repair_problems(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None = None,
) -> list[repair_registry.RepairProblem]:
    problems: list[repair_registry.RepairProblem] = []
    _manage, daemon_running, expected_build, manage_problems = _manage_repair_context(ide, instance)
    problems.extend(manage_problems)

    status = _lane_status_payload(ide, instance, payload=payload)
    problems.extend(
        repair_registry.collect_problems_from_status(
            status,
            ide=ide,
            expected_build=expected_build,
            daemon_running=daemon_running,
        )
    )
    problems.extend(repair_registry.collect_problems_from_console_logs(status, ide=ide))

    drive = _drive_result_from_payload(payload)
    if isinstance(drive, dict):
        problems.extend(repair_registry.collect_problems_from_drive_result(drive, ide=ide))

    readiness = _import_koru_readiness_module()
    root = _project_repo_root()
    problems.extend(_runtime_readiness_problems(readiness, root))
    problems.extend(
        _lane_alignment_problems(
            readiness,
            root,
            payload,
            ide=ide,
            instance=instance,
        )
    )
    return repair_registry.dedupe_problems(problems)


def _repair_reload_ide(ide: str, repo_root: Path | None) -> repair_registry.RepairAttempt:
    try:
        from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide
    except ImportError as exc:
        return repair_registry.RepairAttempt(
            action_id="reload_ide",
            mode="auto",
            ok=False,
            message=f"koru ide reload unavailable: {exc}",
        )
    project = repo_root if repo_root is not None and repo_root.is_dir() else _project_repo_root()
    outcome = try_reload_vscode_family_ide(
        ide,
        project=project,
        allow_reuse_window=True,
    )
    return repair_registry.RepairAttempt(
        action_id="reload_ide",
        mode="auto",
        ok=bool(getattr(outcome, "ok", False)),
        message=(
            f"method={getattr(outcome, 'method', None) or '-'} "
            f"detail={getattr(outcome, 'detail', None) or 'ok'}"
        ),
    )


def _repair_connect_plugin(ide: str) -> repair_registry.RepairAttempt:
    try:
        from koru.ide_adapters.ide_reload import connect_via_command_palette
    except ImportError as exc:
        return repair_registry.RepairAttempt(
            action_id="connect_plugin",
            mode="auto",
            ok=False,
            message=f"koru connect palette unavailable: {exc}",
        )
    outcome = connect_via_command_palette(ide)
    return repair_registry.RepairAttempt(
        action_id="connect_plugin",
        mode="auto",
        ok=bool(getattr(outcome, "ok", False)),
        message=(
            f"method={getattr(outcome, 'method', None) or '-'} "
            f"detail={getattr(outcome, 'detail', None) or 'ok'}"
        ),
    )


def _repair_strict_handshake_cycle(ide: str, instance: str) -> repair_registry.RepairAttempt:
    """Restart daemon with strict plugin policy; stale plugins self-reload on rejection."""
    _run_koru_lane(ide, instance, ["autopilot", "shutdown"])
    time.sleep(0.8)
    rc = _start_autopilot_daemon_for_lane(ide, instance, wait_seconds=5.0, strict_plugin=True)
    return repair_registry.RepairAttempt(
        action_id="strict_handshake_cycle",
        mode="auto",
        ok=rc == 0,
        message="strict daemon restart ok" if rc == 0 else f"strict daemon restart rc={rc}",
    )


def _run_lane_repair(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None = None,
    trigger: str = "coru.repair",
) -> repair_registry.RepairPlan:
    problems = _collect_lane_repair_problems(ide, instance, payload=payload)
    root = _repo_root()
    if root is not None and problems:
        RepairService.for_project(root).record_diagnosis(
            RecordDiagnosisCommand(
                ide=ide,
                instance=instance,
                problems=tuple(problems),
                trigger=f"{trigger}:diagnosis",
                snapshot={"payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else []},
            )
        )
    if not problems:
        return repair_registry.RepairPlan(session_id="", problems=(), attempts=(), resolved=True, trigger=trigger)

    print(f"[coru] repair: detected {len(problems)} issue(s) for ide={ide} instance={instance}", file=sys.stderr)
    plan = repair_registry.run_repair_pipeline(
        ide=ide,
        instance=instance,
        repo_root=root,
        problems=problems,
        trigger=trigger,
        run_koru=lambda args: _run_koru_lane(ide, instance, list(args)),
        replay=lambda lane_ide, lane_instance, args: _run_koru_lane(lane_ide, lane_instance, list(args)),
        fetch_status=lambda lane_ide, lane_instance: _lane_status_payload(
            lane_ide,
            lane_instance,
            payload=payload,
        ),
        ensure_daemon=lambda: _ensure_daemon_running(ide, instance),
        ide_reload=_repair_reload_ide,
        ide_connect=_repair_connect_plugin,
        strict_handshake=lambda: _repair_strict_handshake_cycle(ide, instance),
    )
    for line in repair_registry.format_repair_lines(plan):
        print(line, file=sys.stderr)
    if root is not None:
        store_path = RepairService.for_project(root).store_path
        print(f"[coru] repair: event log → {store_path}", file=sys.stderr)
    return plan


def _status_has_target_plugin(status: dict[str, Any], *, ide: str, project: Path) -> bool:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return False
    project_resolved = str(project.resolve())
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        if plugin_ide != ide:
            continue
        folders = plugin.get("workspaceFolders")
        if not isinstance(folders, list):
            return True
        for folder in folders:
            try:
                if str(Path(str(folder)).expanduser().resolve()) == project_resolved:
                    return True
            except Exception:
                if str(folder) == str(project):
                    return True
    return False


def _running_ide_summary() -> str:
    try:
        from koruide.ide import detect_running_ides

        rows = detect_running_ides()
    except Exception:
        return "unknown"
    if not rows:
        return "none"
    return ", ".join(f"{row.id}(pid={row.pid})" for row in rows[:6])


def _target_plugin_rows(status: dict[str, Any] | None, *, ide: str) -> list[dict[str, Any]]:
    if not isinstance(status, dict):
        return []
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return []
    rows: list[dict[str, Any]] = []
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        if plugin_ide == ide:
            rows.append(plugin)
    return rows


def _plugin_workspace_summary(plugin: dict[str, Any]) -> str:
    folders = plugin.get("workspaceFolders")
    if not isinstance(folders, list) or not folders:
        return "workspace=unknown"
    shown = [str(folder) for folder in folders[:2]]
    suffix = ",..." if len(folders) > 2 else ""
    return "workspace=" + ",".join(shown) + suffix


def _print_ide_control_context(
    ide: str,
    instance: str,
    *,
    status: dict[str, Any] | None = None,
    reason: str = "readiness",
    guidance: bool = False,
) -> None:
    terminal_ide, terminal_source, integrated = _terminal_shell_context()
    print(
        f"[coru] ide context ({reason}): target={ide}/{instance} "
        f"terminal={terminal_ide or 'system'} integrated={'yes' if integrated else 'no'} "
        f"source={terminal_source}",
        file=sys.stderr,
    )
    print(f"[coru] ide context ({reason}): running={_running_ide_summary()}", file=sys.stderr)

    plugins = _target_plugin_rows(status, ide=ide)
    if plugins:
        plugin_bits = "; ".join(
            f"{ide} plugin v{plugin.get('version') or '?'} {_plugin_workspace_summary(plugin)}"
            for plugin in plugins[:3]
        )
        print(f"[coru] ide context ({reason}): plugin=connected {plugin_bits}", file=sys.stderr)
    else:
        print(f"[coru] ide context ({reason}): plugin=missing target={ide}", file=sys.stderr)

    if not guidance:
        return

    if not plugins:
        print(
            f"[coru] next: open {ide} on this project and run Command Palette command "
            "`koru: Connect autopilot daemon`",
            file=sys.stderr,
        )
        print(
            "[coru] next: if the extension is stale, run `Developer: Reload Window` "
            "and connect the plugin again",
            file=sys.stderr,
        )
    if integrated and terminal_ide and terminal_ide != ide and not plugins:
        print(
            f"[coru] next: current terminal belongs to {terminal_ide}; "
            f"for strict plugin control, rerun from {ide}'s integrated terminal",
            file=sys.stderr,
        )
    print(
        f"[coru] next: keep {ide}'s chat/composer visible; if submit stalls, "
        "place the text cursor in the chat input and press Enter/Send",
        file=sys.stderr,
    )


def _lane_doctor(
    ide: str,
    instance: str,
    *,
    fix: bool = False,
    probe: bool = False,
    probe_prompt: str = "test",
    skip_ensure: bool = False,
) -> int:
    rc = _diagnose_lane(ide, instance, skip_ensure=skip_ensure)
    if rc != 0 and not fix:
        return rc

    if fix:
        print("[coru] doctor: bridge repair (registry pipeline)...")
        payload = _koru_autopilot_env_payload(ide, instance)
        repair_plan = _run_lane_repair(ide, instance, payload=payload, trigger="coru.doctor")
        if not repair_plan.resolved:
            print(
                "[coru] doctor: registry repair incomplete; "
                "running fallback koru ide doctor --fix...",
                file=sys.stderr,
            )
            fix_rc = _run_koru_lane(
                ide,
                instance,
                ["ide", "doctor", "--ide", ide, "--fix", "--gc-sockets", "--explain"],
            )
            if fix_rc != 0:
                return fix_rc
        rc = _lane_status_raw(ide, instance)

    if probe:
        print(f"[coru] doctor: plugin-required drive probe (prompt={probe_prompt!r})...")
        probe_rc = _lane_chat_prompt(ide, instance, probe_prompt, require_plugin=True)
        if probe_rc != 0:
            drive_payload = _fetch_drive_payload(ide, instance, probe_prompt, require_plugin=True)
            if drive_payload:
                payload = _koru_autopilot_env_payload(ide, instance) or {}
                payload = {**payload, "drive": drive_payload}
                _run_lane_repair(ide, instance, payload=payload, trigger="coru.doctor.probe")
            return probe_rc

    return rc


from coru.cli_calibration import (  # noqa: E402
    _CALIBRATION_DRIVE_TIMEOUT_S,
    _calibration_desktop_focus_titles,
    _format_calibration_bridge_report,
    _format_calibration_desktop_report,
    _format_calibration_probe_report,
    _lane_calibration,
    _lane_drive_capture,
    _materialize_calibration_desktop_oql,
    _parse_drive_json_from_stdout,
    _register_calibration_command,
    _resolve_calibration_lane,
    _run_calibration_bridge_preflight,
    _run_calibration_desktop_preflight,
    _write_calibration_bridge_testql,
    _write_calibration_desktop_oql,
)


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

    auto_args = list(extra_args)
    if not any(token == "--agent-lane" or token.startswith("--agent-lane=") for token in auto_args):
        auto_args = ["--agent-lane", instance, *auto_args]
    project = _project_for_lane(ide, instance)
    if project and not any(token == "--project" or token.startswith("--project=") for token in auto_args):
        auto_args = ["--project", project, *auto_args]
    return _run_koru_lane(ide, instance, ["auto", *auto_args])


def _env_enabled(name: str, *, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSE_ENV_VALUES


def _gc_stale_lane_socket(ide: str, instance: str) -> int:
    print("[coru] readiness: checking stale daemon/socket state...", file=sys.stderr)
    return _run_koru_lane(
        ide,
        instance,
        ["ide", "doctor", "--ide", ide, "--fix", "--gc-sockets", "--explain"],
    )


def _check_lane_status_and_ownership(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> tuple[int, str]:
    """Return (rc, reason) after checking lane status, self-heal, and ownership."""
    status_rc = _lane_status_raw(ide, instance)
    if status_rc == 0:
        ownership_rc = _auto_ownership_gate(ide, instance, payload=payload)
        return ownership_rc, "ownership" if ownership_rc != 0 else ""

    heal_rc = _attempt_plugin_self_heal(ide, instance)
    if heal_rc == 0:
        status_rc = _lane_status_raw(ide, instance)

    if status_rc == 0:
        ownership_rc = _auto_ownership_gate(ide, instance, payload=payload)
        if ownership_rc != 0:
            return ownership_rc, "ownership"

    if status_rc != 0:
        _print_ide_control_context(
            ide,
            instance,
            status=_lane_status_payload(ide, instance, payload=payload),
            reason="plugin",
            guidance=True,
        )
    return status_rc, "plugin" if status_rc != 0 else ""


def _resolve_readiness_lane(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> tuple[str, str]:
    if not payload:
        return ide, instance
    resolved_ide = str(payload.get("ide") or ide)
    resolved_instance = str(payload.get("instance") or instance)
    if resolved_ide != ide or resolved_instance != instance:
        print(
            f"[coru] readiness: lane resolved to ide={resolved_ide} instance={resolved_instance}",
            file=sys.stderr,
        )
    return resolved_ide, resolved_instance


def _maybe_auto_repair_lane(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> None:
    if not _env_enabled("CORU_AUTO_REPAIR", default=False):
        return
    repair_plan = _run_lane_repair(ide, instance, payload=payload, trigger="coru.doctor")
    if repair_plan.resolved or not _env_enabled("CORU_AUTO_READINESS_GATE", default=True):
        return
    _print_ide_control_context(
        ide,
        instance,
        status=_lane_status_payload(ide, instance, payload=payload),
        reason="repair",
        guidance=True,
    )


def _readiness_plugin_blocker(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> AutoReadiness | None:
    plugin_blocker = _manage_report_plugin_blocker(_fetch_manage_report(ide, instance))
    if plugin_blocker is None:
        return None
    code, message, fix = plugin_blocker
    print(f"[coru] readiness: [FAIL] {code}: {message}", file=sys.stderr)
    if fix:
        print(f"[coru] readiness: fix → {fix}", file=sys.stderr)
    _print_ide_control_context(
        ide,
        instance,
        status=_lane_status_payload(ide, instance, payload=payload),
        reason="plugin-version",
        guidance=True,
    )
    return AutoReadiness(1, ide, instance, reason="plugin")


def _readiness_consistency_step(
    ide: str, instance: str, payload: dict[str, Any] | None
) -> AutoReadiness | None:
    rc = _diagnose_runtime_consistency(ide, instance, payload)
    if rc != 0:
        return AutoReadiness(rc, ide, instance, reason="runtime")
    return None


def _readiness_daemon_step(ide: str, instance: str) -> AutoReadiness | None:
    if _env_enabled("CORU_AUTO_SOCKET_GC", default=True) and _lane_status_raw(ide, instance) != 0:
        _gc_stale_lane_socket(ide, instance)
    daemon_rc = _ensure_daemon_running(ide, instance)
    if daemon_rc != 0:
        _print_ide_control_context(ide, instance, reason="daemon", guidance=True)
        return AutoReadiness(daemon_rc, ide, instance, reason="daemon")
    return None


def _readiness_blocker_step(
    ide: str, instance: str, payload: dict[str, Any] | None
) -> AutoReadiness | None:
    _maybe_auto_repair_lane(ide, instance, payload)
    blocked = _readiness_plugin_blocker(ide, instance, payload)
    if blocked is not None:
        return blocked
    rc, reason = _check_lane_status_and_ownership(ide, instance, payload)
    return AutoReadiness(rc, ide, instance, reason=reason)


def _auto_readiness_gate(ide: str, instance: str) -> AutoReadiness:
    if not _env_enabled("CORU_AUTO_READINESS_GATE", default=True):
        return AutoReadiness(0, ide, instance)

    print(f"[coru] readiness: ide={ide} instance={instance}", file=sys.stderr)
    _print_terminal_context()
    payload = _koru_autopilot_env_payload(ide, instance)
    ide, instance = _resolve_readiness_lane(ide, instance, payload)

    result = _readiness_consistency_step(ide, instance, payload)
    if result is not None:
        return result

    result = _readiness_daemon_step(ide, instance)
    if result is not None:
        return result

    return _readiness_blocker_step(ide, instance, payload)


def _resolve_daemon_alignment(
    readiness: Any,
    daemon: Any,
    status: dict[str, Any],
    root: Path,
    socket_path: Path,
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> tuple[Any, dict[str, Any]]:
    if not daemon.ok and _readiness_issue_codes(daemon) == {"daemon_project_mismatch"}:
        meta = status.get("daemon_metadata") if isinstance(status.get("daemon_metadata"), dict) else {}
        meta_project = str(meta.get("project") or "").strip()
        if meta_project and _coru_projects_equivalent(meta_project, root):
            from koru.autonomous_readiness import ReadinessResult

            daemon = ReadinessResult(ok=True, issues=())
        else:
            status = _restart_stale_lane_daemon(ide, instance, payload=payload)
            if status is not None:
                daemon = readiness.check_daemon_client_alignment(status, project=root, socket_path=socket_path)
    if not daemon.ok and _readiness_issue_codes(daemon) == {"daemon_version_mismatch"}:
        status = _restart_stale_lane_daemon(ide, instance, payload=payload)
        if status is not None:
            daemon = readiness.check_daemon_client_alignment(status, project=root, socket_path=socket_path)
    return daemon, status


def _build_ownership_checks(
    readiness: Any,
    daemon: Any,
    root: Path,
    socket_path: Path,
    status: dict[str, Any],
    ide: str,
    instance: str,
) -> list[Any]:
    terminal_ide, _terminal_source, terminal_integrated = _terminal_shell_context()
    terminal_kind = _terminal_host_kind()
    terminal_integrated_for_lane = terminal_integrated
    if terminal_integrated and terminal_ide != ide and _status_has_target_plugin(status, ide=ide, project=root):
        terminal_integrated_for_lane = False
    return [
        daemon,
        readiness.check_workspace_socket_ownership(root, socket_path, status, autopilot_ide=ide),
        readiness.check_lane_terminal_socket_alignment(
            autopilot_ide=ide,
            lane_instance=instance,
            socket_path=socket_path,
            terminal_ide=terminal_ide,
            terminal_integrated=terminal_integrated_for_lane,
            terminal_kind=terminal_kind,
        ),
    ]


def _apply_ownership_check(
    readiness: Any,
    result: Any,
    *,
    root: Path,
    socket_path: Path,
) -> tuple[bool, str | None]:
    for line in readiness.format_readiness_lines(result, prefix="[coru]"):
        print(line, file=sys.stderr)
    if result.ok:
        return False, None
    primary_fix = result.primary_fix
    if hasattr(readiness, "apply_socket_ownership_repairs"):
        repair_result = readiness.apply_socket_ownership_repairs(root, socket_path, result)
        for action in repair_result.repair_actions:
            print(f"[coru] readiness repair: {action}", file=sys.stderr)
    return True, primary_fix


def _prepare_ownership_context(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> tuple[Any, Path, Path, dict[str, Any]] | None:
    readiness = _import_koru_readiness_module()
    root = _active_project_root()
    socket_raw = str((payload or {}).get("socket") or "").strip()
    if readiness is None or root is None or not socket_raw:
        return None
    status = _lane_status_payload(ide, instance, payload=payload)
    if status is None:
        _print_ide_control_context(ide, instance, reason="ownership", guidance=True)
        return None
    _print_ide_control_context(ide, instance, status=status, reason="ownership", guidance=False)
    return readiness, root, Path(socket_raw), status


def _run_ownership_checks_loop(
    readiness: Any,
    checks: list[Any],
    root: Path,
    socket_path: Path,
) -> tuple[bool, str | None]:
    failed = False
    primary_fix: str | None = None
    for result in checks:
        check_failed, fix = _apply_ownership_check(
            readiness,
            result,
            root=root,
            socket_path=socket_path,
        )
        if check_failed:
            failed = True
            primary_fix = primary_fix or fix
    return failed, primary_fix


def _auto_ownership_gate(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None,
) -> int:
    ctx = _prepare_ownership_context(ide, instance, payload)
    if ctx is None:
        return 0
    readiness, root, socket_path, status = ctx

    daemon = readiness.check_daemon_client_alignment(status, project=root, socket_path=socket_path)
    daemon, status = _resolve_daemon_alignment(readiness, daemon, status, root, socket_path, ide, instance, payload)
    checks = _build_ownership_checks(readiness, daemon, root, socket_path, status, ide, instance)

    failed, primary_fix = _run_ownership_checks_loop(readiness, checks, root, socket_path)
    if failed and primary_fix:
        print(f"[coru] readiness primary fix: {primary_fix}", file=sys.stderr)
        _print_ide_control_context(ide, instance, status=status, reason="readiness-failed", guidance=True)
    return 1 if failed else 0


def _readiness_issue_codes(result: Any) -> set[str]:
    issues = getattr(result, "issues", ()) or ()
    return {str(getattr(issue, "code", "") or "") for issue in issues}


def _restart_stale_lane_daemon(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not _env_enabled("CORU_AUTO_DAEMON_RESTART", default=True):
        return None
    print("[coru] readiness: daemon/client mismatch; restarting lane daemon...", file=sys.stderr)
    _run_koru_lane(ide, instance, ["autopilot", "shutdown"])
    if _ensure_daemon_running(ide, instance) != 0:
        return None
    return _lane_status_payload(ide, instance, payload=payload)


def _status_has_plugin_for_ide(status: Mapping[str, Any], ide: str) -> bool:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return False
    wanted = ide.strip().lower()
    for plugin in plugins:
        if not isinstance(plugin, Mapping):
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        if wanted in {"", "auto"} or plugin_ide == wanted:
            return True
    return False


def _manage_report_plugin_blocker(
    report: Mapping[str, Any] | None,
) -> tuple[str, str, str | None] | None:
    if not isinstance(report, Mapping):
        return None
    issues = report.get("issues")
    if not isinstance(issues, list):
        return None
    for issue in issues:
        if not isinstance(issue, Mapping):
            continue
        code = str(issue.get("code") or "").strip()
        severity = str(issue.get("severity") or "").strip().lower()
        if code not in _BLOCKING_PLUGIN_MANAGE_CODES or severity != "error":
            continue
        message = str(issue.get("message") or code)
        fix = issue.get("fix")
        return code, message, str(fix) if fix else None
    return None


def _status_has_keyboard_backend(status: Mapping[str, Any]) -> bool:
    if str(status.get("selected_backend") or "").strip():
        return True
    backends = status.get("backends")
    if not isinstance(backends, list):
        return False
    return any(isinstance(item, Mapping) and bool(item.get("available")) for item in backends)


def _auto_readiness_can_continue_without_plugin(readiness: AutoReadiness) -> bool:
    if readiness.reason not in {"plugin", "ownership"}:
        return False
    status = _lane_status_payload(readiness.ide, readiness.instance)
    if not isinstance(status, Mapping):
        return False
    if not status.get("daemon"):
        return False
    if _status_has_plugin_for_ide(status, readiness.ide):
        return False
    try:
        from koru.integrations.vdisplay_client import vdisplay_fallback_enabled

        if vdisplay_fallback_enabled(ide=readiness.ide, plugin_connected=False):
            return True
    except Exception:
        pass
    try:
        from koru.autonomy.env import plugin_required_for_ide
    except Exception:
        return False
    if plugin_required_for_ide(readiness.ide):
        return False
    return _status_has_keyboard_backend(status)


def _auto_readiness_can_continue_with_keyboard_fallback(readiness: AutoReadiness) -> bool:
    return _auto_readiness_can_continue_without_plugin(readiness)


def _run_auto_with_readiness(ide: str, instance: str, extra_args: Sequence[str]) -> int:
    with _bind_lane_session(ide, instance):
        readiness = _auto_readiness_gate(ide, instance)
        if readiness.rc != 0:
            if _auto_readiness_can_continue_without_plugin(readiness):
                try:
                    from koru.integrations.vdisplay_client import vdisplay_fallback_enabled

                    fallback = (
                        "vdisplay semantic control"
                        if vdisplay_fallback_enabled(
                            ide=readiness.ide,
                            plugin_connected=False,
                        )
                        else "keyboard fallback"
                    )
                except Exception:
                    fallback = "keyboard fallback"
                print(
                    f"[coru] readiness: plugin is not connected, but {fallback} "
                    "is enabled; entering autonomous cycle",
                    file=sys.stderr,
                )
                return _lane_auto(readiness.ide, readiness.instance, extra_args)
            print(
                "[coru] readiness: autopilot bridge is not ready; "
                "not entering autonomous cycle",
                file=sys.stderr,
            )
            return readiness.rc
        return _lane_auto(readiness.ide, readiness.instance, extra_args)


def _lane_manage_fix(ide: str, instance: str) -> int:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    # Check first without --fix to avoid unnecessary repairs when the lane is
    # already healthy (e.g. plugin already installed and socket responsive).
    manage_args = ["autopilot", "manage", "--ide", ide]
    project = _project_for_lane(ide, instance)
    if project:
        manage_args.extend(["--project", project])
    rc = _run_koru_lane(ide, instance, manage_args)
    if rc == 0:
        return 0
    # Need repair.
    repair_args = ["autopilot", "manage", "--ide", ide, "--fix"]
    if project:
        repair_args.extend(["--project", project])
    rc = _run_koru_lane(ide, instance, repair_args)
    if rc != 0:
        rc = _run_koru_lane(
            ide,
            instance,
            ["ide", "doctor", "--ide", ide, "--fix", "--gc-sockets"],
        )
    return rc


def _lane_daemon_foreground(ide: str, instance: str) -> int:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    args = ["autopilot", "daemon", "--idempotent"]
    project = _project_for_lane(ide, instance)
    if project:
        args.extend(["--project", project])
    return _run_koru_lane(ide, instance, args)


def _koru_exec_argv() -> list[str] | None:
    binary_path = _binary_path("koru")
    if binary_path is not None:
        return [binary_path]
    if _python_module_exists("koru.cli"):
        return [sys.executable, "-m", "koru.cli"]
    local_source = _local_module_source_dir("koru.cli")
    if local_source is not None:
        runner = (
            "import sys; "
            f"sys.path.insert(0, {str(local_source)!r}); "
            "from koru.cli import main; "
            "raise SystemExit(main(sys.argv[1:]))"
        )
        return [sys.executable, "-c", runner]
    return None


def _fetch_drive_payload(
    ide: str,
    instance: str,
    prompt: str,
    *,
    require_plugin: bool = True,
) -> dict[str, Any] | None:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        return None
    cmd = [
        *koru_exec,
        "autopilot",
        "drive",
        "--ide",
        ide,
        "--prompt",
        prompt,
    ]
    if require_plugin:
        cmd.append("--require-plugin")
    env = _lane_subprocess_env(ide, instance)
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            env=env,
            timeout=_CALIBRATION_DRIVE_TIMEOUT_S,
            close_fds=True,
        )
    except Exception:
        return None
    raw = (proc.stdout or "").strip()
    return _parse_drive_json_from_stdout(raw)


def _lane_chat_prompt(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127

    drive_args = ["autopilot", "drive", "--ide", ide]
    if require_plugin:
        drive_args.append("--require-plugin")
    drive_args.append(prompt)
    return _run_koru_lane(ide, instance, drive_args)


def _start_autopilot_daemon_for_lane(
    ide: str,
    instance: str,
    *,
    wait_seconds: float = 5.0,
    strict_plugin: bool = False,
) -> int:
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127

    payload = _koru_autopilot_env_payload(ide, instance)
    env = dict(os.environ)
    if payload and payload.get("env"):
        env.update({str(k): str(v) for k, v in payload["env"].items()})
    else:
        env["KORU_AUTOPILOT_IDE"] = ide
        env["KORU_AUTOPILOT_INSTANCE"] = instance
        env.pop("KORU_AUTOPILOT_SOCKET", None)
    if strict_plugin:
        _apply_strict_plugin_policy_defaults(env, force=True)

    cmd = [*koru_exec, "autopilot", "daemon", "--idempotent"]
    project = _project_for_lane(ide, instance)
    if project:
        cmd.extend(["--project", project])
    try:
        subprocess.Popen(
            cmd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except KeyboardInterrupt:
        return 130
    except Exception:
        return 1

    socket_path = (payload or {}).get("socket")
    if not socket_path:
        time.sleep(0.2)
        return 0

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if Path(str(socket_path)).exists():
            return 0
        time.sleep(0.2)
    return 0


def _ensure_daemon_running(ide: str, instance: str, *, wait_seconds: float = 15.0) -> int:
    if _lane_status_raw(ide, instance) == 0:
        return 0

    print(
        f"[coru] autopilot daemon not ready; starting idempotent daemon "
        f"for ide={ide} instance={instance}",
        file=sys.stderr,
    )
    start_rc = _start_autopilot_daemon_for_lane(ide, instance, wait_seconds=min(wait_seconds, 5.0))
    if start_rc != 0:
        return start_rc

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if _lane_status_raw(ide, instance) == 0:
            return 0
        time.sleep(0.5)

    print(
        "[coru] daemon may be up but bridge is not ready; "
        "run 'coru daemon' in a system terminal and connect the plugin in the IDE",
        file=sys.stderr,
    )
    return 1


def _import_koru_readiness_module() -> Any | None:
    for root in (_project_repo_root(), _repo_root()):
        if root is None:
            continue
        src = root / "src"
        if not src.is_dir() or not (src / "koru").is_dir():
            continue
        src_s = str(src.resolve())
        if src_s not in sys.path:
            sys.path.insert(0, src_s)
    try:
        from koru import autonomous_readiness as readiness

        return readiness
    except ImportError:
        return None


def _coru_readiness_strict() -> bool:
    return os.environ.get("CORU_READINESS_STRICT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _diagnose_readiness_alignment(
    *,
    root: Path | None,
    ide: str,
    instance: str,
    strict: bool,
) -> int | None:
    readiness = _import_koru_readiness_module()
    if root is None or readiness is None:
        return None

    result = readiness.check_runtime_consistency(
        root,
        launcher_executable=sys.executable,
        strict=strict,
    )
    for line in readiness.format_readiness_lines(result, prefix="[coru]"):
        print(line, file=sys.stderr)

    terminal_ide, _terminal_source, terminal_integrated = _terminal_shell_context()
    lane = readiness.check_lane_terminal_socket_alignment(
        autopilot_ide=ide,
        lane_instance=instance,
        socket_path=None,
        terminal_ide=terminal_ide,
        terminal_integrated=terminal_integrated,
    )
    for line in readiness.format_readiness_lines(lane, prefix="[coru]"):
        print(line, file=sys.stderr)

    if strict and not (result.ok and lane.ok):
        fix = result.primary_fix or lane.primary_fix
        if fix:
            print(f"[coru] readiness fail-fast: {fix}", file=sys.stderr)
        return 1
    if not result.ok:
        return 0
    return None


def _warn_python_env_mismatch() -> None:
    project_python = _project_venv_python()
    current_python = str(Path(sys.executable).resolve())
    if project_python:
        project_python = str(Path(project_python).resolve())
    if project_python and current_python != project_python:
        print(
            "[coru] warning: python env mismatch: "
            f"active={current_python} repo_venv={project_python}; "
            "prefer repo .venv to keep daemon/plugin versions aligned",
            file=sys.stderr,
        )


def _warn_koru_exec_outside_repo(root_s: str) -> None:
    koru_exec = _koru_exec_argv() or []
    if not (koru_exec and root_s and os.path.isabs(koru_exec[0])):
        return

    koru_exec_path = str(Path(koru_exec[0]).resolve())
    if not koru_exec_path.startswith(root_s):
        print(
            "[coru] warning: koru executable is outside repo: "
            f"{koru_exec_path} (repo={root_s})",
            file=sys.stderr,
        )


def _warn_lane_project_mismatch(payload: dict[str, Any] | None, root_s: str) -> None:
    if not (payload and root_s):
        return

    payload_project = str(payload.get("project") or "").strip()
    if not payload_project:
        return

    try:
        payload_resolved = str(Path(payload_project).resolve())
    except Exception:
        payload_resolved = payload_project
    if payload_resolved != root_s:
        print(
            "[coru] warning: lane project differs from current repo: "
            f"lane_project={payload_resolved} repo={root_s}",
            file=sys.stderr,
        )


def _diagnose_runtime_consistency(ide: str, instance: str, payload: dict[str, Any] | None) -> int:
    root = _project_repo_root()
    root_s = str(root.resolve()) if root is not None else ""
    readiness_rc = _diagnose_readiness_alignment(
        root=root,
        ide=ide,
        instance=instance,
        strict=_coru_readiness_strict(),
    )
    if readiness_rc is not None:
        return readiness_rc

    _warn_python_env_mismatch()
    _warn_koru_exec_outside_repo(root_s)
    _warn_lane_project_mismatch(payload, root_s)
    return 0


def _attempt_plugin_self_heal(
    ide: str,
    instance: str,
    *,
    timeout_seconds: float = 12.0,
    attempts: int = 3,
) -> int:
    print(
        "[coru] plugin self-heal: attempting IDE reload and plugin reconnect "
        f"for ide={ide} instance={instance}",
        file=sys.stderr,
    )

    readiness = _import_koru_readiness_module()
    if readiness is not None:

        def _reload() -> bool:
            attempt = _repair_reload_ide(ide, _project_repo_root())
            print(f"[coru] plugin self-heal: {attempt.message}", file=sys.stderr)
            if attempt.ok:
                time.sleep(5.0)
            return attempt.ok

        def _wait(timeout: float) -> bool:
            manage = _fetch_manage_report(ide, instance)
            plugin = manage.get("plugin") if isinstance(manage, dict) and isinstance(manage.get("plugin"), dict) else {}
            expected_build = str(plugin.get("expected_build_sha") or "").strip() or None
            deadline = time.monotonic() + max(0.0, timeout)
            while time.monotonic() < deadline:
                status = _lane_status_payload(ide, instance)
                if repair_registry.plugin_build_aligned(status, ide=ide, expected_build=expected_build):
                    return True
                if expected_build is None and _lane_status_raw(ide, instance) == 0:
                    return True
                time.sleep(0.5)
            return False

        if readiness.run_plugin_reconnect_pipeline(
            reload_window=_reload,
            wait_connected=_wait,
            attempts=attempts,
            base_timeout_seconds=timeout_seconds,
        ):
            return 0
        connect = _repair_connect_plugin(ide)
        print(f"[coru] plugin self-heal connect: {connect.message}", file=sys.stderr)
        if connect.ok and _wait(timeout_seconds):
            return 0
        return 1

    # Replay actions are the orchestrated, auditable control path for IDE actions.
    for attempt in range(1, max(1, attempts) + 1):
        if _lane_status_raw(ide, instance) == 0:
            return 0
        reload_rc = _run_koru_lane(ide, instance, ["replay", f"ide reload-window {ide}"])
        connect_rc = _run_koru_lane(ide, instance, ["replay", f"ide connect-plugin {instance}"])
        if reload_rc != 0 and connect_rc != 0:
            continue
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if _lane_status_raw(ide, instance) == 0:
                return 0
            time.sleep(0.8)
        if attempt < attempts:
            time.sleep(min(1.5 * attempt, 3.0))
    return 1


def _resolve_diagnose_lane(
    ide: str,
    instance: str,
) -> tuple[str, str, dict[str, Any] | None]:
    payload = _koru_autopilot_env_payload(ide, instance)
    if not payload:
        print("[coru] lane env: koru autopilot env unavailable; using coru lane defaults", file=sys.stderr)
        return ide, instance, payload
    resolved_ide = str(payload.get("ide") or ide)
    resolved_instance = str(payload.get("instance") or instance)
    print(
        f"[coru] lane resolved: ide={resolved_ide} instance={resolved_instance} "
        f"socket={payload.get('socket')} source={payload.get('source')}"
    )
    return resolved_ide, resolved_instance, payload


def _diagnose_lane_status(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None,
) -> int:
    status_rc = _lane_status_raw(ide, instance)
    if status_rc == 0:
        return 0
    if _attempt_plugin_self_heal(ide, instance) == 0:
        return _lane_status_raw(ide, instance)
    print(
        "[coru] plugin self-heal did not complete; run in IDE: "
        "Developer: Reload Window, then koru: Connect autopilot daemon",
        file=sys.stderr,
    )
    return status_rc


def _diagnose_lane(
    ide: str,
    instance: str,
    *,
    probe_drive: bool = False,
    skip_ensure: bool = False,
) -> int:
    print(f"[coru] diagnose ide={ide} instance={instance}")
    _print_troubleshooting_log_locations(ide, instance)
    _terminal_shell_context()

    if not skip_ensure:
        ensure_rc = _ensure_commands(install=False)
        if ensure_rc != 0:
            return ensure_rc

    ide, instance, payload = _resolve_diagnose_lane(ide, instance)
    if _diagnose_runtime_consistency(ide, instance, payload) != 0:
        return 1

    manage_rc = _lane_manage_fix(ide, instance)
    if manage_rc != 0:
        print("[coru] manage --fix reported issues (continuing)", file=sys.stderr)

    daemon_rc = _ensure_daemon_running(ide, instance)
    if daemon_rc != 0:
        print("[coru] hint: keep `coru daemon` running in a system terminal window", file=sys.stderr)
        print("[coru] hint: in Cursor run command `koru: Connect autopilot daemon` once", file=sys.stderr)

    if _env_enabled("CORU_AUTO_REPAIR", default=False):
        _run_lane_repair(ide, instance, payload=payload, trigger="coru.diagnose")

    if daemon_rc != 0:
        return daemon_rc

    status_rc = _diagnose_lane_status(ide, instance, payload=payload)
    _print_ide_control_context(
        ide,
        instance,
        status=_lane_status_payload(ide, instance, payload=payload),
        reason="diagnose",
        guidance=status_rc != 0,
    )
    if status_rc != 0:
        return status_rc

    if probe_drive:
        print("[coru] probe: koru autopilot drive --require-plugin (prompt=test)")
        return _lane_chat_prompt(ide, instance, "test", require_plugin=True)
    return 0


def _print_troubleshooting_log_locations(ide: str, instance: str) -> None:
    root = _project_repo_root() or Path.cwd()
    plan_dir = root / ".planfile" / ".koru"
    xdg_runtime = (os.environ.get("XDG_RUNTIME_DIR") or "").strip()
    daemon_meta = plan_dir / f"koru-autopilot-{instance}.daemon.json"
    nfo_log = plan_dir / "nfo-events.jsonl"
    audit_log = Path.home() / ".local" / "state" / "koru" / "autopilot.log"
    repair_log = plan_dir / "repair-events.jsonl"
    events_log = (
        Path(xdg_runtime) / "koru-autopilot-events.ndjson"
        if xdg_runtime
        else Path("/tmp/koru-autopilot-events.ndjson")
    )
    print("debug logs:")
    print(f"- repair event log (CQRS/ES): {repair_log}")
    print(f"- daemon audit: {audit_log}")
    print(f"- daemon metadata: {daemon_meta}")
    print(f"- autonomous nfo events: {nfo_log}")
    print(f"- plugin runtime events: {events_log}")
    print(f"- quick check: coru status")
    print(f"- foreground daemon: coru daemon")


def _chat_llm_enabled(use_llm: bool) -> bool:
    return use_llm or bool((os.environ.get("OPENROUTER_API_KEY") or "").strip())


def _llm_rewrite_chat_prompt(text: str, *, ide: str, instance: str) -> str:
    try:
        from nlp2coru.rewrite import rewrite_chat_prompt
    except Exception:
        return text
    model = os.environ.get("CORU_LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    return rewrite_chat_prompt(text, ide=ide, instance=instance, model=model)


def _intent_to_plan(intent) -> Plan:
    return Plan(
        action=str(intent.action),
        ide=intent.ide,
        instance=intent.instance,
        install=bool(intent.install),
        auto_args=tuple(intent.auto_args),
    )


def _import_heuristic_plan_fn():
    try:
        from nlp2coru.heuristic import heuristic_plan

        return heuristic_plan
    except ImportError:
        pass
    repo_root = Path(__file__).resolve().parents[4]
    sibling_src_dirs = (
        repo_root / "packages" / "nlp2coru" / "src",
        repo_root / "packages" / "dsl2coru" / "src",
        repo_root / "packages" / "dsl2koru" / "src",
    )
    if not any(path.is_dir() for path in sibling_src_dirs):
        return None
    import sys

    for sibling_src in sibling_src_dirs:
        if not sibling_src.is_dir():
            continue
        path = str(sibling_src)
        if path not in sys.path:
            sys.path.insert(0, path)
    try:
        from nlp2coru.heuristic import heuristic_plan

        return heuristic_plan
    except ImportError:
        return None


def _heuristic_plan(text: str) -> Plan:
    heuristic_plan = _import_heuristic_plan_fn()
    if heuristic_plan is None:
        return Plan(action="status")
    try:
        coru_plan = heuristic_plan(text)
        if coru_plan.steps:
            return _intent_to_plan(coru_plan.steps[0])
    except Exception:
        pass
    return Plan(action="status")


def _llm_plan(text: str) -> Plan | None:
    try:
        from nlp2coru.llm import llm_plan
    except Exception:
        return None
    model = os.environ.get("CORU_LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    try:
        coru_plan = llm_plan(text, model=model)
    except Exception:
        return None
    if not coru_plan.steps:
        return None
    step = coru_plan.steps[0]
    action = step.action
    if action not in {"ensure", "lane", "diagnose", "status", "auto", "doctor", "calibration", "repair", "sync"}:
        action = "diagnose"
    return Plan(
        action=action,
        ide=step.ide,
        instance=step.instance,
        install=step.install,
    )


def _resolve_defaults(plan: Plan, *, context: SessionContext | None = None) -> Plan:
    _trace("resolve_defaults.start", action=plan.action, plan_ide=plan.ide or "(none)",
           plan_instance=plan.instance or "(none)")
    ide = plan.ide or (context.ide if context else None) or _infer_default_ide()
    instance = plan.instance or (context.instance if context else None) or _infer_default_instance(ide=ide)
    pre_normalize = f"{ide}/{instance}"
    ide, instance = _normalize_lane_pair(ide, instance)
    _trace("resolve_defaults.result", ide=ide, instance=instance,
           pre_normalize=pre_normalize, action=plan.action)
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
    return _normalize_lane_pair(resolved_ide, resolved_instance)


def _dispatch_plan_action(resolved: Plan, shell: str) -> int:
    if resolved.action == "ensure":
        return _ensure_commands(install=resolved.install)
    if resolved.action == "lane":
        return _lane_env(resolved.ide, resolved.instance, shell)
    if resolved.action == "manage":
        return _lane_manage_fix(resolved.ide, resolved.instance)
    if resolved.action in {"status", "diagnose"}:
        return _diagnose_lane(resolved.ide, resolved.instance, skip_ensure=True)
    if resolved.action == "doctor":
        return _lane_doctor(resolved.ide, resolved.instance, fix=False, probe=False, skip_ensure=False)
    if resolved.action == "calibration":
        return _lane_calibration(resolved.ide, resolved.instance)
    if resolved.action == "auto":
        return _run_auto_with_readiness(resolved.ide, resolved.instance, list(resolved.auto_args))
    print(f"unsupported action: {resolved.action}", file=sys.stderr)
    return 2


def _execute_plan(
    plan: Plan,
    *,
    shell: str = "bash",
    context: SessionContext | None = None,
) -> int:
    resolved = _resolve_defaults(plan, context=context)
    return _dispatch_plan_action(resolved, shell)


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
            Plan(action="manage", ide=first.ide, instance=first.instance),
            Plan(action="diagnose", ide=first.ide, instance=first.instance),
        ]
        if wants_auto:
            chain.append(Plan(action="auto", ide=first.ide, instance=first.instance, auto_args=first.auto_args))
        return chain

    return [first]


def _status_failure_ok_to_continue(plans: Sequence[Plan], index: int) -> bool:
    """Allow auto/setup chains to proceed when daemon is down; koru auto starts it."""
    return any(p.action == "auto" for p in plans[index + 1 :])


def _preflight_failure_ok_to_continue(plans: Sequence[Plan], index: int) -> bool:
    """Allow manage/diagnose preflights to continue into auto when they still report issues."""
    plan = plans[index]
    if plan.action not in {"manage", "status", "diagnose"}:
        return False
    return any(p.action == "auto" for p in plans[index + 1 :])


def _plan_step_identity(plan: Plan, ctx: SessionContext) -> tuple[str, str]:
    return plan.ide or ctx.ide or "-", plan.instance or ctx.instance or "-"


def _emit_plan_step_log(
    plan: Plan,
    ctx: SessionContext,
    *,
    announce: bool,
    result: str,
    level: str = "info",
    rc: int | None = None,
) -> None:
    ide, instance = _plan_step_identity(plan, ctx)
    if announce and result == "started":
        print(f"[coru] step={plan.action} ide={ide} instance={instance}")
    kwargs: dict[str, Any] = {
        "component": "planner",
        "level": level,
        "action": plan.action,
        "result": result,
        "verbose": announce,
        "ide": plan.ide or ctx.ide or "",
        "instance": plan.instance or ctx.instance or "",
    }
    if rc is not None:
        kwargs["rc"] = rc
    _emit_log(**kwargs)


def _plan_failure_return(
    plan: Plan,
    *,
    index: int,
    plans_list: list[Plan],
    rc: int,
) -> int | None:
    if plan.action in {"manage", "status", "diagnose"} and _preflight_failure_ok_to_continue(plans_list, index):
        print(
            "[coru] preflight: autopilot bridge not ready; "
            "continuing to auto (koru will retry and/or repair)",
            file=sys.stderr,
        )
        return None
    return rc


def _run_single_plan_with_logging(
    plan: Plan,
    *,
    index: int,
    plans_list: list[Plan],
    ctx: SessionContext,
    shell: str,
    announce: bool,
) -> int | None:
    """Execute one plan, emit logs, and return rc or None to continue past preflight."""
    _emit_plan_step_log(plan, ctx, announce=announce, result="started")
    rc = _execute_plan(plan, shell=shell, context=ctx)
    _emit_plan_step_log(
        plan,
        ctx,
        announce=announce,
        result="ok" if rc == 0 else "failed",
        level="info" if rc == 0 else "error",
        rc=rc,
    )
    if rc != 0:
        return _plan_failure_return(plan, index=index, plans_list=plans_list, rc=rc)
    return rc


def _execute_plans(
    plans: Sequence[Plan],
    *,
    shell: str = "bash",
    context: SessionContext | None = None,
    announce: bool = False,
) -> int:
    global _CHAIN_CONTEXT
    ctx = context or SessionContext()
    chain_project = _chain_project_from_plans(plans)
    if chain_project and not ctx.project:
        ctx.project = chain_project
    plans_list = list(plans)
    if not plans_list:
        return 0
    bootstrap = _resolve_defaults(plans_list[0], context=ctx)
    rc = 0
    previous_chain_context = _CHAIN_CONTEXT
    _CHAIN_CONTEXT = ctx
    try:
        with _bind_lane_session(bootstrap.ide, bootstrap.instance):
            for index, plan in enumerate(plans_list):
                result = _run_single_plan_with_logging(
                    plan, index=index, plans_list=plans_list, ctx=ctx, shell=shell, announce=announce
                )
                if result is not None and result != 0:
                    return result
                if result is None:
                    continue
                rc = result
        return rc
    finally:
        _CHAIN_CONTEXT = previous_chain_context


def _chat_print_header(
    *,
    startup_lane: Plan,
    verbose: bool,
    require_plugin: bool,
) -> None:
    print("coru chat mode. Type 'quit' to exit.")
    _print_runtime_versions()
    if verbose:
        print("verbose: on")
    print("chat mode: message -> IDE chat (use '/<command>' for coru actions)")
    _print_troubleshooting_log_locations(startup_lane.ide, startup_lane.instance)
    transport_label = "plugin-only (no keyboard fallback)" if require_plugin else "plugin or keyboard fallback"
    print(f"chat mode transport: {transport_label}")


def _chat_ensure_daemon(
    ide: str,
    instance: str,
    *,
    action: str,
    verbose: bool,
) -> int:
    daemon_rc = _start_autopilot_daemon_for_lane(ide, instance)
    _emit_log(
        component="chat",
        level="info" if daemon_rc == 0 else "error",
        action=action,
        result="ok" if daemon_rc == 0 else "failed",
        rc=daemon_rc,
        verbose=verbose,
        ide=ide,
        instance=instance,
    )
    if daemon_rc == 0 and verbose:
        print(f"[coru] daemon ready for ide={ide} instance={instance}; retrying drive")
    return daemon_rc


def _chat_drive_with_retry(
    ide: str,
    instance: str,
    outbound: str,
    *,
    require_plugin: bool,
    verbose: bool,
) -> int:
    rc = _lane_chat_prompt(ide, instance, outbound, require_plugin=require_plugin)
    _emit_log(
        component="chat",
        level="info" if rc == 0 else "warning",
        action="drive",
        result="ok" if rc == 0 else "retry_pending" if rc == 2 else "failed",
        rc=rc,
        verbose=verbose,
        ide=ide,
        instance=instance,
    )
    if rc != 2 or not ide or ide == "auto":
        return rc
    daemon_rc = _chat_ensure_daemon(ide, instance, action="daemon_autostart", verbose=verbose)
    if daemon_rc != 0:
        return rc
    rc = _lane_chat_prompt(ide, instance, outbound, require_plugin=require_plugin)
    _emit_log(
        component="chat",
        level="info" if rc == 0 else "error",
        action="drive_retry",
        result="ok" if rc == 0 else "failed",
        rc=rc,
        verbose=verbose,
        ide=ide,
        instance=instance,
    )
    return rc


def _chat_handle_drive(
    line: str,
    ctx: SessionContext,
    *,
    use_llm: bool,
    require_plugin: bool,
    verbose: bool,
) -> None:
    resolved = _resolve_defaults(Plan(action="status"), context=ctx)
    outbound = line
    if _chat_llm_enabled(use_llm):
        outbound = _llm_rewrite_chat_prompt(line, ide=resolved.ide, instance=resolved.instance)
        if verbose and outbound != line:
            print(f"[coru] llm rewrite: {outbound}")
    if verbose:
        print(f"[coru] drive ide={resolved.ide} instance={resolved.instance}")
    if require_plugin and resolved.ide and resolved.ide != "auto":
        if _lane_status(resolved.ide, resolved.instance) != 0:
            _chat_ensure_daemon(resolved.ide, resolved.instance, action="daemon_preflight", verbose=verbose)
    rc = _chat_drive_with_retry(
        resolved.ide,
        resolved.instance,
        outbound,
        require_plugin=require_plugin,
        verbose=verbose,
    )
    if rc != 0:
        print(f"[coru] failed rc={rc}")


def _chat_handle_command(
    line: str,
    ctx: SessionContext,
    *,
    use_llm: bool,
    shell: str,
    single_action: bool,
) -> None:
    command_text = line[1:].strip()
    if not command_text:
        return
    del ctx, shell  # lane context preserved in session; DSL dispatch uses runner env
    from coru.control import apply_nl

    rc = apply_nl(command_text, use_llm=use_llm, single_action=single_action)
    if rc != 0:
        print(f"[coru] failed rc={rc}")


def _chat_loop(
    *,
    use_llm: bool,
    shell: str,
    single_action: bool,
    verbose: bool = False,
    require_plugin: bool = True,
) -> int:
    ctx = SessionContext()
    startup_lane = _resolve_defaults(Plan(action="status"), context=ctx)
    _chat_print_header(startup_lane=startup_lane, verbose=verbose, require_plugin=require_plugin)
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
            _chat_handle_command(line, ctx, use_llm=use_llm, shell=shell, single_action=single_action)
        else:
            _chat_handle_drive(line, ctx, use_llm=use_llm, require_plugin=require_plugin, verbose=verbose)


def _add_lane_identifiers(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("ide", nargs="?")
    parser.add_argument("instance", nargs="?")


def _add_shell_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--shell", choices=("bash", "sh", "zsh", "powershell"), default="bash")


def _register_lane_commands(sub: Any) -> None:
    p_lane = sub.add_parser("lane", help="emit lane environment exports")
    _add_lane_identifiers(p_lane)
    _add_shell_argument(p_lane)
    p_lane.add_argument("--print-env", action="store_true", help="deprecated alias; env is always printed")

    p_status = sub.add_parser("lane-status", help="show lane status")
    _add_lane_identifiers(p_status)

    p_status_alias = sub.add_parser("status", help="orchestrated lane diagnostics (env, daemon, status)")
    _add_lane_identifiers(p_status_alias)
    p_status_alias.add_argument("--probe", action="store_true", help="run plugin-required drive probe")

    p_env_alias = sub.add_parser("env", help="alias for lane")
    _add_lane_identifiers(p_env_alias)
    _add_shell_argument(p_env_alias)


def _register_operational_commands(sub: Any) -> None:
    p_auto = sub.add_parser("auto", help="run koru auto in a lane")
    _add_lane_identifiers(p_auto)
    p_auto.add_argument("rest", nargs=argparse.REMAINDER)

    p_daemon = sub.add_parser("daemon", help="run autopilot daemon in foreground for current lane")
    _add_lane_identifiers(p_daemon)
    p_daemon.add_argument(
        "--allow-integrated-shell",
        action="store_true",
        help="allow running daemon from IDE integrated terminal",
    )

    p_supervisor = sub.add_parser("supervisor", help="background lane registry and daemon supervisor")
    p_supervisor.add_argument("supervisor_args", nargs=argparse.REMAINDER)


def _register_interaction_commands(sub: Any) -> None:
    p_text = sub.add_parser("text", help="natural language command")
    p_text.add_argument("prompt")
    p_text.add_argument("--llm", action="store_true", help="use litellm planner first")
    _add_shell_argument(p_text)
    p_text.add_argument("--single-action", action="store_true", help="execute only one mapped action")

    p_chat = sub.add_parser("chat", help="interactive chat-first mode")
    p_chat.add_argument("--llm", action="store_true", help="use litellm planner first")
    _add_shell_argument(p_chat)
    p_chat.add_argument("--single-action", action="store_true", help="execute only one mapped action")
    p_chat.add_argument(
        "--require-plugin",
        action="store_true",
        default=True,
        help="require connected IDE plugin transport (disable keyboard fallback)",
    )
    p_chat.add_argument(
        "--allow-keyboard-fallback",
        dest="require_plugin",
        action="store_false",
        help="allow OS keyboard injection fallback when plugin transport is unavailable",
    )


def _register_repair_command(sub: Any) -> None:
    p_repair = sub.add_parser("repair", help="bridge autorepair with event-sourced history")
    repair_sub = p_repair.add_subparsers(dest="repair_command", required=True)

    p_history = repair_sub.add_parser("history", help="show repair case history for LLM/operators")
    p_history.add_argument("--limit", type=int, default=20)
    p_history.add_argument("--code", default=None, help="filter sessions that included this problem code")
    p_history.add_argument(
        "--format",
        choices=("llm", "json"),
        default="llm",
        help="llm: markdown brief for agents; json: structured case rows",
    )
    _add_lane_identifiers(p_history)

    p_run = repair_sub.add_parser("run", help="detect problems and run registry repair pipeline")
    p_run.add_argument("--fix", action="store_true", help="alias; repair always runs when problems exist")
    _add_lane_identifiers(p_run)


def _cmd_repair_history(args: argparse.Namespace) -> int:
    ide, instance = _default_lane(args.ide, args.instance)
    root = _project_repo_root()
    if root is None:
        print("[coru] repair history: no repo root; run from a git project", file=sys.stderr)
        return 1
    query = RepairHistoryQuery.for_project(root)
    if args.format == "json":
        print(query.format_json(limit=args.limit, code=args.code))
    else:
        print(query.format_llm(limit=args.limit, code=args.code))
    print(f"[coru] repair: lane filter ide={ide} instance={instance}", file=sys.stderr)
    print(f"[coru] repair: event log → {query.store_path}", file=sys.stderr)
    return 0


def _cmd_repair_run(args: argparse.Namespace) -> int:
    ide, instance = _default_lane(args.ide, args.instance)
    payload = _koru_autopilot_env_payload(ide, instance)
    plan = _run_lane_repair(ide, instance, payload=payload, trigger="coru.repair.run")
    return 0 if plan.resolved else 1


def _cmd_sync(args: argparse.Namespace) -> int:
    from coru.ecosystem import format_sync_report, format_sync_report_json, sync_ecosystem

    root = _repo_root()
    if root is None:
        print("error: coru sync requires a koru git checkout", file=sys.stderr)
        return 2

    ide, instance = _default_lane(args.ide, args.instance)
    resolved = _resolve_defaults(Plan(action="sync", ide=ide, instance=instance))

    def _koru_runner(target_ide: str, koru_args: Sequence[str]) -> int:
        lane_instance = _instance_for_ide_choice(target_ide)
        return _run_koru_lane(target_ide, lane_instance, list(koru_args))

    target_ide = None if args.all_ides else resolved.ide
    report = sync_ecosystem(
        root,
        ide=target_ide,
        python=not args.skip_python,
        plugins=not args.skip_plugins,
        repair=not args.skip_repair,
        all_running_ides=args.all_ides,
        python_executable=_project_venv_python() or sys.executable,
        koru_runner=_koru_runner if (not args.skip_plugins or not args.skip_repair) else None,
    )

    if args.format == "json":
        print(format_sync_report_json(report))
    else:
        print(format_sync_report(report))
    return 0 if report.ok else 1


def _register_sync_command(sub: Any) -> None:
    p_sync = sub.add_parser(
        "sync",
        help="auto-update koru ecosystem (python packages + VSIX plugins + repair)",
    )
    _add_lane_identifiers(p_sync)
    p_sync.add_argument(
        "--all-ides",
        action="store_true",
        help=(
            "sync plugins/repair for running VS Code-family IDEs "
            "(skips Antigravity unless selected with --ide antigravity)"
        ),
    )
    p_sync.add_argument("--skip-python", action="store_true", help="skip pip install -U")
    p_sync.add_argument("--skip-plugins", action="store_true", help="skip VSIX install-plugin")
    p_sync.add_argument("--skip-repair", action="store_true", help="skip manage --fix and self repair")
    p_sync.add_argument("--format", choices=("human", "json"), default="human")


def _register_doctor_command(sub: Any) -> None:
    p_doctor = sub.add_parser("doctor", help="orchestrated diagnostics (status/fix/probe) for current lane")
    _add_lane_identifiers(p_doctor)
    p_doctor.add_argument("--fix", action="store_true", help="run `koru ide doctor --fix --gc-sockets`")
    p_doctor.add_argument("--probe", action="store_true", help="run plugin-required drive probe")
    p_doctor.add_argument("--probe-prompt", default="test", help="prompt used by --probe")
    p_doctor.add_argument(
        "--allow-integrated-shell",
        action="store_true",
        help="allow running diagnostics from IDE integrated terminal",
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coru")
    sub = p.add_subparsers(dest="command", required=False)

    p_ensure = sub.add_parser("ensure", help="check/install koruenv + koru + coru")
    p_ensure.add_argument("--install", action="store_true")

    sub.add_parser("setup", help="prepare preferred repo-local environment")

    _register_sync_command(sub)

    _register_lane_commands(sub)
    _register_operational_commands(sub)
    _register_interaction_commands(sub)
    _register_calibration_command(sub)
    _register_doctor_command(sub)
    _register_repair_command(sub)

    return p


def _restore_log_format(previous_log_format: str | None) -> None:
    if previous_log_format is None:
        os.environ.pop("CORU_LOG_FORMAT", None)
    else:
        os.environ["CORU_LOG_FORMAT"] = previous_log_format


def _maybe_run_default_mode(raw_argv: Sequence[str], *, verbose: bool) -> int | None:
    if not raw_argv or (raw_argv[0] == "--" and len(raw_argv) == 1):
        if _startup_mode() == "chat":
            return _chat_loop(
                use_llm=False,
                shell="bash",
                single_action=False,
                verbose=verbose,
                require_plugin=True,
            )
        auto_args: list[str] = []
        if raw_argv and raw_argv[0] == "--":
            auto_args = list(raw_argv[1:])
        elif not raw_argv:
            auto_args = _interactive_default_auto_args()
        return _run_default_autonomous(auto_args, shell="bash", verbose=verbose)
    if raw_argv[0] == "--":
        return _run_default_autonomous(raw_argv[1:], shell="bash", verbose=verbose)
    return None


def _maybe_rewrite_ide_auto_shorthand(
    raw_argv: Sequence[str],
    known_commands: set[str],
) -> list[str] | None:
    """``coru cursor auto`` → ``coru auto cursor`` (documented lane hint syntax)."""
    if len(raw_argv) < 2:
        return None
    if raw_argv[0] in known_commands or raw_argv[0].startswith("-"):
        return None
    ide = raw_argv[0].strip().lower()
    if ide not in _VALID_AUTOPILOT_IDES or raw_argv[1].strip().lower() != "auto":
        return None
    return ["auto", ide, *raw_argv[2:]]


def _is_text_shorthand(raw_argv: Sequence[str], known_commands: set[str]) -> bool:
    if not raw_argv:
        return False
    token = raw_argv[0]
    return token not in known_commands and not token.startswith("-")


def _rewrite_text_shorthand_argv(
    raw_argv: Sequence[str],
    *,
    verbose: bool,
    log_format: str,
    require_plugin: bool,
) -> list[str]:
    nested_argv = ["text", " ".join(raw_argv)]
    if verbose:
        nested_argv = ["--verbose", *nested_argv]
    if log_format != "human":
        nested_argv = [f"--log-format={log_format}", *nested_argv]
    if require_plugin:
        nested_argv = ["--require-plugin", *nested_argv]
    return nested_argv


def _doctor_or_daemon_requires_system_shell(
    *,
    command: str,
    allow_integrated_shell: bool,
) -> bool:
    term_ide, term_source, integrated = _terminal_shell_context()
    if not integrated or allow_integrated_shell:
        return False
    print(
        f"coru {command}: run this from system shell (outside IDE integrated terminal); "
        f"detected integrated ide={term_ide or '-'} source={term_source}",
        file=sys.stderr,
    )
    print("hint: rerun with --allow-integrated-shell only when necessary", file=sys.stderr)
    return True


def _dispatch_lane_command(args: argparse.Namespace) -> int | None:
    if args.command == "lane":
        ide, instance = _default_lane(args.ide, args.instance)
        return _lane_env(ide, instance, args.shell)

    if args.command == "lane-status":
        ide, instance = _default_lane(args.ide, args.instance)
        return _lane_status(ide, instance)

    if args.command == "status":
        ide, instance = _default_lane(args.ide, args.instance)
        return _diagnose_lane(ide, instance, probe_drive=bool(getattr(args, "probe", False)))

    if args.command == "env":
        ide, instance = _default_lane(args.ide, args.instance)
        return _lane_env(ide, instance, args.shell)

    return None


def _dispatch_auto_command(args: argparse.Namespace) -> int | None:
    if args.command != "auto":
        return None
    ide, instance = _default_lane(args.ide, args.instance)
    if args.ide or args.instance:
        _remember_project_ide_settings(ide, instance)
    rest = list(args.rest)
    if rest and rest[0] == "--":
        rest = rest[1:]
    return _run_auto_with_readiness(ide, instance, rest)


def _dispatch_text_command(args: argparse.Namespace, *, verbose: bool) -> int | None:
    if args.command != "text":
        return None
    from coru.control import apply_nl

    rc = apply_nl(
        args.prompt,
        use_llm=args.llm,
        single_action=args.single_action,
    )
    if verbose and rc == 0:
        print("[coru] dispatched via control bus (nlp2coru → dsl2coru)")
    return rc


def _dispatch_chat_command(
    args: argparse.Namespace,
    *,
    verbose: bool,
    require_plugin: bool,
) -> int | None:
    if args.command != "chat":
        return None
    return _chat_loop(
        use_llm=args.llm,
        shell=args.shell,
        single_action=args.single_action,
        verbose=verbose,
        require_plugin=bool(args.require_plugin or require_plugin),
    )


def _dispatch_supervisor_command(args: argparse.Namespace) -> int | None:
    if args.command != "supervisor":
        return None
    from coru.supervisor.cli import main as supervisor_main

    sup_argv = list(args.supervisor_args)
    if sup_argv and sup_argv[0] == "--":
        sup_argv = sup_argv[1:]
    return supervisor_main(sup_argv, koru_argv=_koru_exec_argv())


def _dispatch_calibration_command(args: argparse.Namespace) -> int | None:
    if args.command != "calibration":
        return None
    ide, instance = _default_lane(args.ide, args.instance)
    ide, instance = _resolve_calibration_lane(
        ide,
        instance,
        explicit_ide=args.ide,
    )
    return _lane_calibration(
        ide,
        instance,
        probe_prompt=args.probe_prompt,
        skip_fix=args.skip_fix,
        skip_desktop=args.skip_desktop,
        skip_bridge=args.skip_bridge,
    )


def _dispatch_doctor_command(args: argparse.Namespace) -> int | None:
    if args.command != "doctor":
        return None
    ide, instance = _default_lane(args.ide, args.instance)
    if _doctor_or_daemon_requires_system_shell(
        command="doctor",
        allow_integrated_shell=args.allow_integrated_shell,
    ):
        return 2
    return _lane_doctor(
        ide,
        instance,
        fix=args.fix,
        probe=args.probe,
        probe_prompt=args.probe_prompt,
    )


def _dispatch_repair_command(args: argparse.Namespace) -> int | None:
    if args.command != "repair":
        return None
    if args.repair_command == "history":
        return _cmd_repair_history(args)
    if args.repair_command == "run":
        return _cmd_repair_run(args)
    return 2


def _dispatch_daemon_command(args: argparse.Namespace) -> int | None:
    if args.command != "daemon":
        return None
    ide, instance = _default_lane(args.ide, args.instance)
    if _doctor_or_daemon_requires_system_shell(
        command="daemon",
        allow_integrated_shell=args.allow_integrated_shell,
    ):
        return 2
    resolved = _resolve_defaults(Plan(action="auto", ide=ide, instance=instance))
    print(
        f"coru daemon: foreground autopilot for ide={resolved.ide} instance={resolved.instance} "
        "(Ctrl+C stops daemon)",
    )
    _print_troubleshooting_log_locations(resolved.ide, resolved.instance)
    return _lane_daemon_foreground(resolved.ide, resolved.instance)


def _dispatch_optional_command(
    args: argparse.Namespace,
    *,
    verbose: bool,
    require_plugin: bool,
) -> int | None:
    for dispatch in (
        lambda: _dispatch_lane_command(args),
        lambda: _dispatch_auto_command(args),
        lambda: _dispatch_text_command(args, verbose=verbose),
        lambda: _dispatch_chat_command(args, verbose=verbose, require_plugin=require_plugin),
        lambda: _dispatch_supervisor_command(args),
        lambda: _dispatch_calibration_command(args),
        lambda: _dispatch_doctor_command(args),
        lambda: _dispatch_repair_command(args),
        lambda: _dispatch_daemon_command(args),
    ):
        rc = dispatch()
        if rc is not None:
            return rc
    return None


def _dispatch_command(args: argparse.Namespace, *, verbose: bool, require_plugin: bool) -> int:
    if args.command == "ensure":
        return _ensure_commands(install=args.install)

    if args.command == "sync":
        return _cmd_sync(args)

    if args.command == "setup":
        return _setup_environment()

    rc = _dispatch_optional_command(
        args,
        verbose=verbose,
        require_plugin=require_plugin,
    )
    if rc is not None:
        return rc

    return 2


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else list(sys.argv[1:])
    if _maybe_reexec_into_project_python(raw_argv):
        return 0
    raw_argv, verbose, show_version, log_format, require_plugin = _extract_global_flags(raw_argv)
    previous_log_format = os.environ.get("CORU_LOG_FORMAT")
    os.environ["CORU_LOG_FORMAT"] = log_format
    if show_version:
        _print_runtime_versions()
        _restore_log_format(previous_log_format)
        return 0

    try:
        known_commands = {
            "ensure",
            "setup",
            "sync",
            "lane",
            "lane-status",
            "status",
            "env",
            "auto",
            "text",
            "chat",
            "supervisor",
            "doctor",
            "calibration",
            "daemon",
            "repair",
        }
        default_mode_rc = _maybe_run_default_mode(raw_argv, verbose=verbose)
        if default_mode_rc is not None:
            return default_mode_rc
        ide_auto_argv = _maybe_rewrite_ide_auto_shorthand(raw_argv, known_commands)
        if ide_auto_argv is not None:
            raw_argv = ide_auto_argv
        if _is_text_shorthand(raw_argv, known_commands):
            nested_argv = _rewrite_text_shorthand_argv(
                raw_argv,
                verbose=verbose,
                log_format=log_format,
                require_plugin=require_plugin,
            )
            return main(nested_argv)

        args = _build_parser().parse_args(raw_argv)
        return _dispatch_command(args, verbose=verbose, require_plugin=require_plugin)
    finally:
        _restore_log_format(previous_log_format)


if __name__ == "__main__":
    raise SystemExit(main())
