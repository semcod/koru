"""Root ``koru.yaml`` — declarative *when / what* map for a koru-managed repo.

The file is **advisory**: operators and LLM agents follow it; koru does not
execute it as a script. It is created on first ``koru --init`` when missing
and surfaced in ``koru --doctor`` and ``koru --context`` so workflows stay
explicit and reviewable in git.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

KORU_PROJECT_PIPELINE_FILENAME = "koru.yaml"


def project_pipeline_path(project: Path) -> Path:
    return project.resolve() / KORU_PROJECT_PIPELINE_FILENAME


def default_koru_project_pipeline_text() -> str:
    """Default ``koru.yaml`` body for new projects (schema 1.0)."""
    from koru.autonomy_strategy.defaults import default_autonomy_strategy_yaml_block

    autonomy_block = default_autonomy_strategy_yaml_block().rstrip()
    return f"""# {KORU_PROJECT_PIPELINE_FILENAME} — project pipeline (schema 1.0)
# Created by `koru --init` when this file was missing. Edit freely and commit.
#
# Paths use `--project .` — run these from the repository root (same on Linux, macOS, CI).
# `koru --init --agent-lane auto` picks a lane from the first present marker, in order:
#   .cursor → .windsurf → .vscode → .idea → .zed → else `local`.
# When CI=true or GITHUB_ACTIONS=true, auto lane is always `local` (no IDE socket from markers).

schema: "1.0"
project: local
description: >
  When to run koru, planfile, and local quality commands. Koru reads this file
  for briefs/doctor; it does not auto-run shell steps.

extends_profile: null
# Optional shared snippets for `koru --context` (see docs / large-repo examples):
# extends_profile: .koru/profiles/default.yaml

# Optional markdown ↔ sprint sync (uncomment and tune `.planfile/config.yaml` keys first):
# planfile_markdown_todo:
#   config_path: .planfile/config.yaml
#   config_key: koru.markdown_todo
#   active_profile: default
#   alternate_profiles: []

environment:
  # Fold semcod exports into `koru scan` / `koru scan --apply` (off unless set):
  # KORU_SCAN_SEMCOD_ARTIFACTS: "1"
  #
  # Autopilot + queue lane (after init, prefer: `source .planfile/.koru/shell-env.sh`):
  # KORU_AUTOPILOT_INSTANCE: "main"       # unique per IDE window; default from init lane
  # KORU_AUTOPILOT_SOCKET: ""            # absolute Unix socket path (overrides instance path)
  # KORU_AUTOPILOT_IDE: "auto"           # auto | cursor | windsurf | vscode | jetbrains | zed
  # KORU_SUGGESTED_QUEUE_ACTOR: ""       # planfile queue actor hint (koru-<lane> from init)

when:
  bootstrap:
    description: First-time planfile + koru runtime wiring.
    commands:
      - koru --init --project .
      - koru --doctor --project .

  ticket_iteration:
    description: Each coding iteration — claim work, refresh brief, gate.
    commands:
      - task tickets:next
      - koru --project .
      - task quality:regix:local

  backlog_hygiene:
    description: Turn repo signals into planfile tickets (dry-run first).
    commands:
      - koru scan --project .
      - koru scan --apply --project .
      - koru scan --apply --semcod-artifacts --project .

  autonomous_outer_loop:
    description: >
      Unattended cycle (scan → queue → optional autopilot). Tune flags with
      `koru autonomous up -h` (e.g. --sleep-seconds, --keep-waiting-input). If the queue
      shows claim_failed, start the planfile HTTP/WebSocket API for your stack. `--agent-lane auto`
      matches the marker order in the header comments (or pass an explicit lane).
    commands:
      - koru autonomous up --project . --max-cycles 1 --agent-lane auto

  before_complete_ticket:
    description: Right before `planfile ticket done` / policy CI hook.
    commands:
      - task quality:regix:local

{autonomy_block}
"""


def write_koru_project_pipeline_if_absent(project: Path) -> bool:
    """Write default ``koru.yaml`` at project root if the file is absent.

    Returns True when a new file was written. Never overwrites an existing
    file (including on ``koru --init --force``).
    """
    project = project.resolve()
    path = project_pipeline_path(project)
    if path.is_file():
        return False
    path.write_text(default_koru_project_pipeline_text(), encoding="utf-8")
    return True


def load_koru_project_pipeline(project: Path) -> dict[str, Any] | None:
    """Parse root ``koru.yaml`` or return None when missing."""
    path = project_pipeline_path(project)
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def build_project_pipeline_brief(project: Path) -> dict[str, Any] | None:
    """Compact structure for ``build_context`` / markdown handoff."""
    raw = load_koru_project_pipeline(project)
    if raw is None:
        return None
    when = raw.get("when")
    phases: list[dict[str, Any]] = []
    if isinstance(when, dict):
        for key, block in when.items():
            if not isinstance(block, dict):
                continue
            cmds = block.get("commands")
            if not isinstance(cmds, list):
                cmds = []
            phases.append(
                {
                    "id": str(key),
                    "description": str(block.get("description") or ""),
                    "commands": [str(c) for c in cmds if c is not None],
                },
            )
    rel = KORU_PROJECT_PIPELINE_FILENAME
    autonomy = raw.get("autonomy")
    strategy = autonomy.get("strategy") if isinstance(autonomy, dict) else None
    return {
        "path": rel,
        "schema": raw.get("schema"),
        "extends_profile": raw.get("extends_profile"),
        "phases": phases,
        "autonomy_strategy": strategy if isinstance(strategy, dict) else None,
    }
