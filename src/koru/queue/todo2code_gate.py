"""Read-only verification gate for autonomous todo2code repair tickets."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from koru.queue.todo2code_support import build_pipeline_cmd


def infer_project_verify_commands(project: Path) -> list[list[str]]:
    """Return all declared completion gates, or one conventional fallback."""
    koru_yaml = project / "koru.yaml"
    if koru_yaml.is_file():
        try:
            import yaml

            data = yaml.safe_load(koru_yaml.read_text(encoding="utf-8")) or {}
            commands = (((data.get("when") or {}).get("before_complete_ticket") or {}).get(
                "commands",
            ) or [])
            declared = [str(command).strip() for command in commands if str(command).strip()]
            if declared:
                return [["sh", "-lc", command] for command in declared]
        except (OSError, AttributeError, ValueError):
            pass

    package_json = project / "package.json"
    if package_json.is_file():
        try:
            scripts = (json.loads(package_json.read_text(encoding="utf-8")) or {}).get("scripts") or {}
        except (OSError, ValueError, json.JSONDecodeError):
            scripts = {}
        for name in ("verify", "test"):
            if str(scripts.get(name) or "").strip():
                return [["npm", "run", name]]

    if (project / "pyproject.toml").is_file() or (project / "pytest.ini").is_file():
        if (project / "tests").is_dir():
            return [[sys.executable, "-m", "pytest", "-q"]]
        return [[sys.executable, "-m", "compileall", "-q", "."]]
    if (project / "go.mod").is_file():
        return [["go", "test", "./..."]]
    if (project / "Cargo.toml").is_file():
        return [["cargo", "test", "--all-targets"]]
    if (project / "pom.xml").is_file():
        return [["mvn", "test", "-q"]]
    if (project / "gradlew").is_file():
        return [["./gradlew", "test"]]
    return []


def infer_project_verify_command(project: Path) -> list[str] | None:
    """Compatibility facade returning the first resolved verification gate."""
    commands = infer_project_verify_commands(project)
    return commands[0] if commands else None


def _compose_path(project: Path) -> Path | None:
    for name in ("compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"):
        candidate = project / name
        if candidate.is_file():
            return candidate
    return None


def _docker_verification(project: Path) -> tuple[dict, str | None]:
    """Load the explicit container boundary for todo2code verification."""
    try:
        import yaml
    except ImportError:
        return {}, "Docker todo2code verification requires PyYAML"

    try:
        data = yaml.safe_load((project / "koru.yaml").read_text(encoding="utf-8")) or {}
        value = ((((data.get("queue") or {}).get("todo2code") or {}).get("verification")) or {})
    except (OSError, AttributeError, ValueError, yaml.YAMLError):
        value = {}
    if not isinstance(value, dict) or str(value.get("runtime") or "").lower() != "docker":
        return {}, (
            "Docker project requires queue.todo2code.verification.runtime=docker "
            "in koru.yaml; host fallback is forbidden"
        )
    service = str(value.get("service") or "").strip()
    if not service:
        return {}, "Docker todo2code verification requires an explicit compose service"
    return value, None


def resolve_project_verify_commands(project: Path) -> tuple[list[list[str]], str | None]:
    """Resolve verification commands without silently escaping a Docker manifest."""
    commands = infer_project_verify_commands(project)
    if not commands:
        return [], "no conventional project verify command could be inferred"

    compose = _compose_path(project)
    docker_project = (project / "Dockerfile").is_file() and compose is not None
    if not docker_project:
        return commands, None

    config, error = _docker_verification(project)
    if error:
        return [], error
    declared = config.get("commands") if isinstance(config.get("commands"), list) else []
    container_commands = [
        ["sh", "-lc", str(command).strip()]
        for command in declared
        if str(command).strip()
    ]
    if container_commands:
        commands = container_commands
    configured_compose = str(config.get("compose_file") or compose.name).strip()
    compose_path = (project / configured_compose).resolve()
    try:
        compose_path.relative_to(project.resolve())
    except ValueError:
        return [], "todo2code verification compose_file must stay inside the project"
    if not compose_path.is_file():
        return [], f"todo2code verification compose file not found: {configured_compose}"

    base = ["docker", "compose", "-f", configured_compose]
    profiles = config.get("profiles") if isinstance(config.get("profiles"), list) else []
    for profile in profiles:
        if str(profile).strip():
            base.extend(["--profile", str(profile).strip()])
    service = str(config["service"]).strip()
    wrapped = []
    for command in commands:
        shell_command = command[2] if command[:2] == ["sh", "-lc"] else shlex.join(command)
        wrapped.append(
            [*base, "run", "--rm", "--entrypoint", "sh", service, "-lc", shell_command]
        )
    return wrapped, None


def _run(command: Sequence[str], project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )


def run_todo2code_gate(
    project: Path,
    *,
    t2c: str,
    diagnostic_ids: Sequence[str],
) -> tuple[bool, str]:
    """Run repository tests, re-analyse intent, and require target diagnostics to clear."""
    project = project.resolve()
    verify_commands, verify_error = resolve_project_verify_commands(project)
    if verify_error:
        return False, verify_error

    for verify in verify_commands:
        tested = _run(verify, project)
        if tested.returncode != 0:
            detail = (tested.stderr or tested.stdout or "project verify failed").strip()
            return False, (
                f"project verify failed ({tested.returncode}) for "
                f"{shlex.join(verify)}: {detail[-4000:]}"
            )

    output = project / ".intent-koru-gate"
    analysed = _run(build_pipeline_cmd(t2c, project, out_dir=output), project)
    if analysed.returncode != 0:
        detail = (analysed.stderr or analysed.stdout or "todo2code pipeline failed").strip()
        return False, f"todo2code pipeline failed ({analysed.returncode}): {detail[-4000:]}"

    try:
        latest = json.loads((output / "latest.json").read_text(encoding="utf-8"))
        run_directory = project / str(latest["runDirectory"])
        diagnostics = json.loads((run_directory / "diagnostics.json").read_text(encoding="utf-8"))
        findings = [item for item in diagnostics.get("diagnostics", []) if isinstance(item, dict)]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return False, f"todo2code gate artifacts are unreadable: {exc}"

    expected = {value for value in diagnostic_ids if value}
    remaining = sorted(
        str(item.get("id")) for item in findings if str(item.get("id") or "") in expected
    )
    blocking = sorted(
        str(item.get("id")) for item in findings if item.get("severity") == "blocking"
    )
    if remaining:
        return False, f"target diagnostics still open: {', '.join(remaining)}"
    if blocking:
        return False, f"blocking diagnostics present after patch: {', '.join(blocking)}"
    return True, "project tests passed and target todo2code diagnostics cleared"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--t2c", required=True)
    parser.add_argument("--diagnostic", action="append", default=[])
    args = parser.parse_args(argv)
    ok, detail = run_todo2code_gate(
        args.project,
        t2c=args.t2c,
        diagnostic_ids=args.diagnostic,
    )
    stream = sys.stdout if ok else sys.stderr
    print(detail, file=stream)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
