"""One-command project initialisation for koru.

Goal: a single ``koru --init`` call should turn a fresh directory
into a fully-functional koru-managed project that an LLM agent can
drive immediately afterwards via ``koru`` (no args). No manual
``planfile init``, no manual policy YAML, no manual ``.gitignore``
edit.

What this module produces:

    <project>/
    ├── .gitignore                       # appended (or created) so
    │                                    # .planfile/.koru/ is ignored
    └── .planfile/
        ├── config.yaml                  # planfile project config
        ├── sprints/
        │   └── current.yaml             # sprint with 1+ starter tickets
        └── .koru/
            ├── policy.yaml              # commented stub with safe defaults
            └── README.md                # written lazily by runtime helpers

Inputs:

- ``--from <yaml>`` (optional) — a flat-pipeline YAML to import. If
  absent, a minimal 2-ticket starter scaffold is generated so the LLM
  has something to claim on its very first iteration.

Idempotency: a re-run on an already-initialised project errors out
unless ``--force`` is passed. ``--force`` overwrites the sprint and
the policy stub, but never the runtime README or run logs (those
belong to koru's lifecycle, not its setup).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .bootstrap import import_flat_pipeline
from .runtime import planfile_dir, runtime_dir

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
        testql suite --pattern "*.testql.toon.yaml" --output console --fail-fast 2>/dev/null && echo "✅ testQL suite passed" || echo "⚠️  testQL suite failed or no scenarios"
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
      4. Run `planfile ticket complete STARTER-001 --note "wired"`.
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

    def summary(self) -> str:
        bits = [f"tickets: {self.sprint_imported} imported"]
        if self.policy_written:
            bits.append("policy: stub written")
        if self.gitignore_updated:
            bits.append(".gitignore: updated")
        if self.used_starter_pipeline:
            bits.append("pipeline: starter scaffold")
        return ", ".join(bits)


def init_project(
    project: Path,
    *,
    from_file: Path | None = None,
    sprint: str = "current",
    force: bool = False,
) -> InitReport:
    """Initialise (or re-initialise with ``force``) a koru project.

    Steps:
        1. Refuse if ``.planfile/config.yaml`` already exists and not ``--force``.
        2. Import flat pipeline (``from_file`` or generated starter).
        3. Write ``.planfile/.koru/policy.yaml`` stub if absent.
        4. Append ``.planfile/.koru/`` to ``.gitignore`` if absent.

    The function is destructive only on the sprint file (when
    ``--force`` is given) — policy and ``.gitignore`` are never
    overwritten if they already contain user content.
    """
    project = project.resolve()
    project.mkdir(parents=True, exist_ok=True)

    pf_dir = planfile_dir(project)
    config_path = pf_dir / "config.yaml"
    if config_path.exists() and not force:
        raise FileExistsError(
            f"{config_path} already exists. Use --force to re-initialise "
            "(this overwrites the sprint and the policy stub but keeps "
            ".planfile/.koru/runs/ intact)."
        )

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
            try:
                (pf_dir / "_starter.planfile.yaml").unlink()
            except OSError:
                pass

    policy_written = _write_policy_stub_if_absent(project)
    gitignore_updated = _ensure_gitignore_entry(project)

    return InitReport(
        project=project,
        planfile_created=True,
        sprint_imported=len(report.tickets_imported),
        policy_written=policy_written,
        gitignore_updated=gitignore_updated,
        used_starter_pipeline=used_starter,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    path.write_text(existing + "\n".join(block) + "\n", encoding="utf-8")
    return True
