"""One-command project initialisation for koru.

Goal: a single ``koru --init`` call should turn a fresh directory
into a fully-functional koru-managed project that an LLM agent can
drive immediately afterwards via ``koru`` (no args). No manual
``planfile init``, no manual policy YAML, no manual ``.gitignore``
edit.

What this module produces:

    <project>/
    ├── koru.yaml                        # optional: when/what pipeline
    │                                    # (created on first --init if absent)
    ├── .gitignore                       # appended (or created) so
    │                                    # .planfile/.koru/ is ignored
    └── .planfile/
        ├── config.yaml                  # planfile project config
        ├── sprints/
        │   └── current.yaml             # sprint with 1+ starter tickets
        └── .koru/
            ├── policy.yaml              # commented stub with safe defaults
            ├── shell-env.sh             # optional: autopilot/queue lane exports
            ├── run-autonomous.sh        # optional: koru autonomous up wrapper
            ├── setup-autopilot-host.sh # optional: injector / apt vs human checklist
            ├── host-environment.json    # optional: desktop + injector probe (koru --init)
            ├── host-environment.md      # human-readable companion
            └── README.md                # written lazily by runtime helpers

Inputs:

- ``--from <yaml>`` (optional) — a flat-pipeline YAML to import. If
  absent, a minimal 2-ticket starter scaffold is generated so the LLM
  has something to claim on its very first iteration.

Idempotency: a re-run on an already-initialised project errors out
unless ``--force`` is passed. ``--force`` overwrites the sprint and
the policy stub, but never the runtime README or run logs (those
belong to koru's lifecycle, not its setup). Root ``koru.yaml`` is
**never** overwritten after the first creation — edit it in git like
any other config. To add or refresh only
the agent-lane shell helpers on an existing project, use
``koru --init-agent-lane`` (see ``--agent-lane``). With ``--agent-lane auto``,
an existing ``.planfile/.koru/shell-env.sh`` lane is honoured first; otherwise
lane markers are read in a fixed order (``.cursor``, ``.windsurf``, ``.vscode``,
``.idea``, ``.zed``) before falling back to ``local``. ``CI`` / ``GITHUB_ACTIONS``
force ``local`` so CI jobs do not pick a lane from committed IDE folders.
"""


import contextlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

import yaml

from koru.agents import (
    agent_lane_environment,
    format_agent_lane_exports,
    normalize_agent_lane_id,
)
from koru.bootstrap import import_flat_pipeline
from koru.init_host_environment import write_host_environment_bundle
from koru.project_pipeline import write_koru_project_pipeline_if_absent
from koru.runtime import planfile_dir, runtime_dir

POLICY_STUB = """\
# .planfile/.koru/policy.yaml
# Edit this file to LOOSEN koru's strict-by-default LLM agent policy.
# All values default to the safest option; uncomment and flip individual
# gates only after a deliberate decision (and a reviewable git commit).
#
# Reference: README.md → "LLM agent contract — koru as the gate".

llm:
  # Git operations — the agent NEVER runs these by default.
  # Commits and pushes are reserved for CI/CD and human reviewers.
  allow_commit: false
  allow_push: false
  allow_branch_create: false
  allow_branch_switch: false
  allow_tag: false

  # Destructive shell — blocks rm -rf /, dd, mkfs, force-pushes, etc.
  allow_destructive_shell: false

  # Workflow — every state change must go through `planfile ticket *`.
  require_planfile_lifecycle: true

  # CI gate — the agent verifies CI exit 0 before completing a ticket.
  # If you set `ci.command` below, the agent uses it to self-verify.
  # If you leave it empty, the agent must ask a human to run CI.
  require_ci_pass_before_complete: true

  # Optional extra forbidden paths (defaults already cover .git/,
  # .planfile/, .env, secrets/, *.pem, *.key, id_rsa, id_ed25519,
  # node_modules/). Paths listed here ADD to the defaults.
  # forbidden_paths:
  #   - alembic/versions/
  #   - migrations/

ci:
  # Universal CI command — runs quality gates on every ticket completion.
  # Supports multiple tooling stacks; tools are skipped gracefully if not installed.
  command: |
    echo "=== Universal Quality Gates ==="
    echo "1. Running project tests (if available)..."
    if command -v task >/dev/null 2>&1 && task test 2>/dev/null; then
      echo "✅ task test passed"
    elif command -v pytest >/dev/null 2>&1 && pytest -q 2>/dev/null; then
      echo "✅ pytest passed"
    elif [ -f "package.json" ] && command -v npm >/dev/null 2>&1 && npm test 2>/dev/null; then
      echo "✅ npm test passed"
    elif [ -f "Makefile" ] && make test 2>/dev/null; then
      echo "✅ make test passed"
    else
      echo "⚠️  No test runner found or tests failed"
    fi
    
    echo "2. Running TestQL E2E scenarios (if available)..."
    if command -v testql >/dev/null 2>&1; then
      if find . -name "*.testql.toon.yaml" -type f 2>/dev/null | head -1 >/dev/null; then
        if testql suite \\
          --pattern '*.testql.toon.yaml' --output console --fail-fast \\
          2>/dev/null; then
          echo "✅ testQL suite passed"
        else
          echo "⚠️  testQL suite failed or no scenarios"
        fi
      else
        echo "ℹ️  No TestQL scenarios found"
      fi
    else
      echo "ℹ️  testQL not available"
    fi
    
    echo "3. Running WUP dependency analysis (if available)..."
    if command -v wup >/dev/null 2>&1; then
      if [ -f "wup.yaml" ]; then
        wup status 2>/dev/null && echo "✅ WUP status OK" || echo "⚠️  WUP issues detected"
      else
        echo "ℹ️  No wup.yaml configuration"
      fi
    else
      echo "ℹ️  WUP not available"
    fi
    
    echo "4. Running Regix quality gates (if available)..."
    if command -v regix >/dev/null 2>&1; then
      if [ -f "regix.yaml" ]; then
        regix gates 2>/dev/null && echo "✅ Regix gates passed" || echo "⚠️  Regix gates failed"
      else
        echo "ℹ️  No regix.yaml configuration"
      fi
    else
      echo "ℹ️  Regix not available"
    fi

    echo "5. Running koru autopilot plugin tests (if available)..."
    if [ -f "plugins/koru-autopilot-vscode/package.json" ] && command -v npm >/dev/null 2>&1; then
      if (cd plugins/koru-autopilot-vscode && npm test 2>/dev/null); then
        echo "✅ koru-autopilot-vscode tests passed"
      else
        echo "⚠️  koru-autopilot-vscode tests failed"
      fi
    else
      echo "ℹ️  koru-autopilot-vscode plugin not present"
    fi
    
    echo "=== Quality Gates Complete ==="
  timeout_seconds: 600

# Free-form notes embedded in every `koru --context` brief.
# Use these to teach the LLM project-specific conventions.
notes: []
#   - "Always run `task lint` before completing a ticket."
#   - "Never edit migrations under alembic/versions/."
"""


STARTER_PIPELINE_YAML = """\
schema: '1.1'
project: starter
description: |
  Two starter tickets generated by `koru --init`. Replace them with
  your real backlog. The format is documented in
  examples/bootstrap.planfile.yaml.
tasks:
  - id: STARTER-001
    name: Confirm koru is wired correctly
    description: |
      Verify the koru ↔ planfile ↔ LLM loop end-to-end on this project.

      1. Run `koru` (no args) and read the markdown brief.
      2. Confirm the policy table shows all gates as `False`.
      3. Confirm `STARTER-001` is the active ticket.
      4. Run `planfile ticket done STARTER-001`.
    executor:
      kind: shell
      handler: 'echo "koru is wired"'
    execution:
      queue: default
      state: ready
    priority: high

  - id: STARTER-002
    name: Replace starter tickets with your real backlog
    description: |
      Edit `.planfile/sprints/current.yaml` and add the work that
      actually matters for this project. You can also re-run
      `koru --init --force --from your-pipeline.yaml` to import a
      flat pipeline you already maintain elsewhere.
    executor:
      kind: human
      mode: interactive
    execution:
      queue: default
      state: ready
    priority: normal
    blocked_by:
      - STARTER-001
"""


GITIGNORE_MARKER = "# koru runtime artefacts (generated)"
GITIGNORE_LINE = ".planfile/.koru/"


@dataclass
class InitReport:
    """Summary of what ``init_project`` actually changed on disk."""

    project: Path
    planfile_created: bool
    sprint_imported: int
    policy_written: bool
    gitignore_updated: bool
    used_starter_pipeline: bool
    agent_lane: str | None = None
    agent_lane_files_written: bool = False
    agent_lane_refresh_only: bool = False
    autopilot_host_setup_written: bool = False
    koru_project_pipeline_yaml_written: bool = False
    host_environment_written: bool = False

    def _env_bit(self) -> str:
        return (
            "; host-environment: .planfile/.koru/host-environment.{json,md}"
            if self.host_environment_written
            else ""
        )

    def _lane_summary(self) -> str:
        env_bit = self._env_bit()
        if self.agent_lane_files_written and self.agent_lane:
            return f"agent-lane: {self.agent_lane} (shell-env.sh, run-autonomous.sh){env_bit}"
        if self.agent_lane is None:
            return f"agent-lane: off (shell helpers removed){env_bit}"
        if self.autopilot_host_setup_written:
            return f"agent-lane: refresh; autopilot-host: setup-autopilot-host.sh{env_bit}"
        return f"agent-lane: refresh{env_bit}"

    def _init_summary(self) -> str:
        bits = [f"tickets: {self.sprint_imported} imported"]
        if self.policy_written:
            bits.append("policy: stub written")
        if self.gitignore_updated:
            bits.append(".gitignore: updated")
        if self.used_starter_pipeline:
            bits.append("pipeline: starter scaffold")
        if self.agent_lane_files_written and self.agent_lane:
            bits.append(f"agent-lane: {self.agent_lane} (shell-env.sh, run-autonomous.sh)")
        if self.autopilot_host_setup_written:
            bits.append("autopilot-host: setup-autopilot-host.sh")
        if self.koru_project_pipeline_yaml_written:
            bits.append("koru.yaml: created")
        if self.host_environment_written:
            bits.append("host-environment: host-environment.{json,md}")
        return ", ".join(bits)

    def summary(self) -> str:
        if self.agent_lane_refresh_only:
            return self._lane_summary()
        return self._init_summary()


@dataclass(frozen=True)
class _InitPipelineImport:
    tickets_imported: int
    used_starter: bool


@dataclass(frozen=True)
class _InitArtifacts:
    policy_written: bool
    gitignore_updated: bool
    agent_lane: str | None
    agent_lane_files_written: bool
    autopilot_host_setup_written: bool
    koru_project_pipeline_yaml_written: bool
    host_environment_written: bool


def init_project(
    project: Path,
    *,
    from_file: Path | None = None,
    sprint: str = "current",
    force: bool = False,
    agent_lane: str = "auto",
    prepare_host_environment: bool = True,
) -> InitReport:
    """Initialise (or re-initialise with ``force``) a koru project.

    Steps:
        1. Refuse if ``.planfile/config.yaml`` already exists and not ``force``.
        2. Import flat pipeline (``from_file`` or generated starter).
        3. Write ``.planfile/.koru/policy.yaml`` stub if absent.
        4. Append ``.planfile/.koru/`` to ``.gitignore`` if absent.
        5. Write root ``koru.yaml`` (project pipeline map) if absent.
        6. If ``prepare_host_environment`` is true, write
           ``.planfile/.koru/host-environment.{json,md}`` (host/session snapshot).

    With ``force``, the sprint and policy stub may be overwritten; policy and
    ``.gitignore`` are not blindly replaced if they already contain user content.
    """
    project = project.resolve()
    project.mkdir(parents=True, exist_ok=True)

    pf_dir = planfile_dir(project)
    config_path = pf_dir / "config.yaml"
    if config_path.exists() and not force:
        raise FileExistsError(
            f"{config_path} already exists. Use --force to re-initialise "
            "(this overwrites the sprint and the policy stub but keeps "
            ".planfile/.koru/runs/ intact).",
        )

    pipeline = _import_init_pipeline(project, pf_dir, from_file, sprint=sprint, force=force)
    artifacts = _write_init_artifacts(
        project,
        agent_lane=agent_lane,
        prepare_host_environment=prepare_host_environment,
    )

    return InitReport(
        project=project,
        planfile_created=True,
        sprint_imported=pipeline.tickets_imported,
        policy_written=artifacts.policy_written,
        gitignore_updated=artifacts.gitignore_updated,
        used_starter_pipeline=pipeline.used_starter,
        agent_lane=artifacts.agent_lane,
        agent_lane_files_written=artifacts.agent_lane_files_written,
        agent_lane_refresh_only=False,
        autopilot_host_setup_written=artifacts.autopilot_host_setup_written,
        koru_project_pipeline_yaml_written=artifacts.koru_project_pipeline_yaml_written,
        host_environment_written=artifacts.host_environment_written,
    )


def refresh_init_agent_lane(
    project: Path,
    *,
    agent_lane: str = "auto",
    prepare_host_environment: bool = True,
) -> InitReport:
    """Write or remove agent-lane shell helpers on an existing koru project.

    Requires ``.planfile/config.yaml``. Does not import a pipeline or
    touch sprint/policy/gitignore.
    """
    project = project.resolve()
    config_path = planfile_dir(project) / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(
            f"{config_path} not found; run `koru --init` in this project first.",
        )
    lane = _resolve_init_agent_lane(project, agent_lane)
    agent_written = False
    if lane is None:
        _remove_agent_lane_artifacts(runtime_dir(project))
    else:
        agent_written = _write_agent_lane_artifacts(project, lane)
    host_setup_written = _write_autopilot_host_setup_script(project)
    host_env_written = False
    if prepare_host_environment:
        host_env_written = write_host_environment_bundle(project)
    return InitReport(
        project=project,
        planfile_created=False,
        sprint_imported=0,
        policy_written=False,
        gitignore_updated=False,
        used_starter_pipeline=False,
        agent_lane=lane,
        agent_lane_files_written=agent_written,
        agent_lane_refresh_only=True,
        autopilot_host_setup_written=host_setup_written,
        koru_project_pipeline_yaml_written=False,
        host_environment_written=host_env_written,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_init_pipeline(
    project: Path,
    pf_dir: Path,
    from_file: Path | None,
    *,
    sprint: str,
    force: bool,
) -> _InitPipelineImport:
    used_starter = from_file is None
    if used_starter:
        starter = pf_dir / "_starter.planfile.yaml"
        pf_dir.mkdir(parents=True, exist_ok=True)
        starter.write_text(STARTER_PIPELINE_YAML, encoding="utf-8")
        pipeline_source: Path = starter
    else:
        pipeline_source = Path(from_file).resolve()

    try:
        report = import_flat_pipeline(
            pipeline_source,
            project,
            sprint=sprint,
            overwrite=force,
        )
    finally:
        if used_starter:
            with contextlib.suppress(OSError):
                (pf_dir / "_starter.planfile.yaml").unlink()
    return _InitPipelineImport(
        tickets_imported=len(report.tickets_imported),
        used_starter=used_starter,
    )


def _write_init_artifacts(
    project: Path,
    *,
    agent_lane: str,
    prepare_host_environment: bool,
) -> _InitArtifacts:
    policy_written = _write_policy_stub_if_absent(project)
    gitignore_updated = _ensure_gitignore_entry(project)
    lane = _resolve_init_agent_lane(project, agent_lane)
    agent_written = _write_agent_lane_for_init(project, lane)
    host_env_written = write_host_environment_bundle(project) if prepare_host_environment else False
    return _InitArtifacts(
        policy_written=policy_written,
        gitignore_updated=gitignore_updated,
        agent_lane=lane,
        agent_lane_files_written=agent_written,
        autopilot_host_setup_written=_write_autopilot_host_setup_script(project),
        koru_project_pipeline_yaml_written=write_koru_project_pipeline_if_absent(project),
        host_environment_written=host_env_written,
    )


def _write_agent_lane_for_init(project: Path, lane: str | None) -> bool:
    if lane is None:
        _remove_agent_lane_artifacts(runtime_dir(project))
        return False
    return _write_agent_lane_artifacts(project, lane)


def _init_auto_agent_lane(project: Path) -> str:
    """Resolve ``--agent-lane auto`` from repo markers (stable, IDE-agnostic order).

    If the project already has generated lane helpers, that explicit runtime
    choice wins over marker detection. This keeps plain ``koru autonomous up``
    aligned with the lane selected by ``koru --init-agent-lane --agent-lane ...``.

    When several IDE config trees exist, the first match in the fixed list wins so
    Linux/macOS and different checkouts behave the same. ``CI`` / ``GITHUB_ACTIONS``
    force ``local`` so headless runners never inherit a committed ``.cursor`` /
    ``.vscode`` layout as an autopilot lane.
    """
    ci = os.environ.get("CI", "").strip().lower()
    if ci in ("1", "true", "yes") or os.environ.get("GITHUB_ACTIONS", "").strip() == "true":
        return "local"
    persisted_lane = _read_persisted_agent_lane(project)
    if persisted_lane:
        return persisted_lane
    # Order is documented in the default root ``koru.yaml`` (``koru --init``).
    markers: tuple[tuple[str, Path], ...] = (
        ("cursor", project / ".cursor"),
        ("windsurf", project / ".windsurf"),
        ("vscode", project / ".vscode"),
        ("jetbrains", project / ".idea"),
        ("zed", project / ".zed"),
    )
    for lane, path in markers:
        if path.exists():
            return lane
    return "local"


_EXPORT_RE = re.compile(
    r"^export\s+(KORU_AUTOPILOT_INSTANCE|KORU_AUTOPILOT_IDE)=(?P<value>.+)$",
)


def _read_persisted_agent_lane(project: Path) -> str | None:
    """Read the generated shell helper's lane, if present."""
    shell_path = runtime_dir(project) / "shell-env.sh"
    if not shell_path.is_file():
        return None
    try:
        lines = shell_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    values: dict[str, str] = {}
    for line in lines:
        match = _EXPORT_RE.match(line.strip())
        if not match:
            continue
        raw = match.group("value").strip()
        if (raw.startswith("'") and raw.endswith("'")) or (
            raw.startswith('"') and raw.endswith('"')
        ):
            raw = raw[1:-1]
        key = line.strip().split("=", 1)[0].removeprefix("export ").strip()
        values[key] = raw

    for key in ("KORU_AUTOPILOT_INSTANCE", "KORU_AUTOPILOT_IDE"):
        raw = values.get(key, "").strip().lower()
        if raw and raw != "auto":
            return normalize_agent_lane_id(raw)
    return None


def _resolve_init_agent_lane(project: Path, agent_lane: str) -> str | None:
    """Pick lane id for init artefacts (``none`` / ``auto`` / explicit slug)."""
    raw = (agent_lane or "auto").strip().lower()
    if raw in ("", "none", "off", "false", "0"):
        return None
    if raw == "auto":
        return _init_auto_agent_lane(project)
    return normalize_agent_lane_id(raw)


def resolve_project_agent_lane(
    project: Path,
    agent_lane: str = "auto",
) -> str | None:
    """Resolve lane id (``none`` / ``auto`` / slug); same rules as init flags."""
    return _resolve_init_agent_lane(project.resolve(), agent_lane)


RUN_AUTONOMOUS_SH = """#!/usr/bin/env bash
set -euo pipefail
_KORU_RT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROJECT="$(cd "${_KORU_RT}/../.." && pwd)"
cd "${_PROJECT}"
exec koru autonomous up --project "${_PROJECT}" --agent-lane auto "$@"
"""

SETUP_AUTOPILOT_HOST_SH = """#!/usr/bin/env bash
set -euo pipefail
_RT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROJECT="$(cd "${_RT}/../.." && pwd)"
cd "${_PROJECT}"
if command -v koru >/dev/null 2>&1; then
  exec koru autopilot setup-host "$@"
elif command -v python3 >/dev/null 2>&1; then
  exec python3 -m koru.cli autopilot setup-host "$@"
else
  echo "koru: not in PATH; try: python3 -m koru.cli autopilot setup-host" >&2
  exit 127
fi
"""


def _write_autopilot_host_setup_script(project: Path) -> bool:
    rt = runtime_dir(project)
    rt.mkdir(parents=True, exist_ok=True)
    path = rt / "setup-autopilot-host.sh"
    path.write_text(SETUP_AUTOPILOT_HOST_SH, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return True


def _write_agent_lane_artifacts(project: Path, lane: str) -> bool:
    rt = runtime_dir(project)
    rt.mkdir(parents=True, exist_ok=True)
    env = agent_lane_environment(lane)
    body = format_agent_lane_exports(env)
    lines = body.splitlines()
    if lines:
        lines[0] = (
            "# Generated by `koru --init`; source for non-autonomous shells, "
            "or use `koru autonomous up --agent-lane auto` (no source needed)."
        )
    shell_path = rt / "shell-env.sh"
    shell_path.write_text(f"{'\n'.join(lines)}\n", encoding="utf-8")

    runner = rt / "run-autonomous.sh"
    runner.write_text(RUN_AUTONOMOUS_SH, encoding="utf-8")
    mode = runner.stat().st_mode
    runner.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return True


def _remove_agent_lane_artifacts(rt: Path) -> None:
    if not rt.is_dir():
        return
    for name in ("shell-env.sh", "run-autonomous.sh"):
        p = rt / name
        if p.is_file():
            with contextlib.suppress(OSError):
                p.unlink()


def _write_policy_stub_if_absent(project: Path) -> bool:
    rt = runtime_dir(project)
    rt.mkdir(parents=True, exist_ok=True)
    path = rt / "policy.yaml"
    if path.exists():
        return False
    path.write_text(POLICY_STUB, encoding="utf-8")
    # Verify it parses as YAML so a typo in the constant cannot ship.
    try:
        yaml.safe_load(POLICY_STUB)
    except yaml.YAMLError as exc:  # pragma: no cover — guard, not runtime path
        raise RuntimeError(f"POLICY_STUB is malformed: {exc}") from exc
    return True


def _ensure_gitignore_entry(project: Path) -> bool:
    """Append ``.planfile/.koru/`` to ``.gitignore`` unless already present.

    Returns True if the file was modified. Creates ``.gitignore`` if
    absent. Idempotent — never appends a duplicate line.
    """
    path = project / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    if any(stripped == GITIGNORE_LINE for stripped in (line.strip() for line in lines)):
        return False
    block = []
    if existing and not existing.endswith("\n"):
        block.append("")
    if existing:
        block.append("")  # blank line separator
    block.append(GITIGNORE_MARKER)
    block.append(GITIGNORE_LINE)
    path.write_text(f"{existing}{'\n'.join(block)}\n", encoding="utf-8")
    return True
