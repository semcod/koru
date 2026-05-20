"""Filesystem contract for koru runtime artefacts.

**koru NEVER writes outside ``<project>/.planfile/``.**

Production code only mutates the planfile-owned directory tree:

    <project>/.planfile/
    ├── config.yaml                  # planfile project config
    ├── sprints/
    │   └── current.yaml             # planfile sprint state (source of truth)
    └── .koru/                       # koru-owned runtime artefacts (this module)
        ├── runs/                    # one log file per `koru --queue [--loop]` run
        │   └── <run_id>.log
        ├── prompts/                 # captured human prompts (interactive mode)
        ├── llm-cache/               # optional response cache for LlmExecutor
        └── README.md                # explains the layout in-place

This module exposes lightweight helpers so all callers agree on the
layout. It does NOT eagerly create directories — callers create only
what they need, when they need it, so a read-only ``--dry-run`` never
leaves traces.

Test fixtures (``tests/`` and ``tests/e2e/*.sh``) are the ONLY allowed
``/tmp/`` users in the repository, and they MUST be PID-scoped and
cleaned up via ``trap``. Everything else stays under
``<project>/.planfile/`` so users have a single, predictable place to
inspect, gitignore, or back up koru's state.
"""


import os
import time
from pathlib import Path

# Subtree convention. All koru runtime artefacts live under this folder
# inside a planfile project. The leading ``.koru`` keeps it visually
# adjacent to ``.planfile/`` data but clearly distinct from
# planfile-owned files (``sprints/``, ``config.yaml``).
KORU_SUBDIR = ".koru"


def planfile_dir(project: Path) -> Path:
    """Return ``<project>/.planfile``. Does not create it."""
    from koru.utils.subprocess_runner import resolve_planfile_subpath

    return resolve_planfile_subpath(project)


def runtime_dir(project: Path) -> Path:
    """Return ``<project>/.planfile/.koru``. Does not create it."""
    return planfile_dir(project) / KORU_SUBDIR


def runs_dir(project: Path) -> Path:
    """Return ``<project>/.planfile/.koru/runs``. Does not create it."""
    return runtime_dir(project) / "runs"


def new_run_id(prefix: str = "queue") -> str:
    """Return a deterministic, sortable run id like ``queue-20260510T130437Z-12345``.

    The format intentionally interleaves an ISO-ish UTC timestamp with
    the process id so concurrent invocations never collide and listing
    ``runs/`` gives a chronological view.
    """
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{prefix}-{stamp}-{os.getpid()}"


def ensure_runs_dir(project: Path) -> Path:
    """Create ``<project>/.planfile/.koru/runs`` if missing and return it.

    A ``README.md`` stub is written on first creation so users who stumble
    across the directory know what it is and that it can be safely
    deleted (re-deriving runs from planfile + git history).
    """
    runs = runs_dir(project)
    runs.mkdir(parents=True, exist_ok=True)
    readme = runtime_dir(project) / "README.md"
    if not readme.exists():
        readme.write_text(_RUNTIME_README, encoding="utf-8")
    return runs


_RUNTIME_README = """\
# `.planfile/.koru/` — koru runtime artefacts

This directory is owned by **koru** (not planfile). It contains
non-authoritative runtime by-products of `koru --queue` runs:

- `runs/` — one log file per queue run, named
  `queue-<UTC-timestamp>-<pid>.log`. Useful for postmortems but **safe
  to delete at any time** — planfile sprint YAML is the source of truth.
- `prompts/` — captured human prompts and answers (when koru is run
  with `--interactive`). These mirror what is also recorded in the
  ticket via `planfile ticket done` (see also the planfile lifecycle docs).
- `llm-cache/` — opt-in cache for `executor.kind=llm` responses.

**Gitignored by default.** Add `.planfile/.koru/` to `.gitignore`
unless you want to share run history across collaborators.

koru never writes outside `.planfile/`. If you find koru artefacts
in `/tmp/` or anywhere else, that's a bug — please report it.
"""
