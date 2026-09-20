"""Read-only Wellmanifest freshness scan with bounded ticket emission.

The scanner compares each adopted governance lock with one already-fetched,
clean checkout of wellmanifest/new-project. It never edits an adopter.
When explicitly requested, it emits one waiting-input Planfile ticket per
stale repository; the stable source key makes repeated scheduler cycles safe.
Actual adoption remains a repository-owned ticket and protected delivery
operation.

The package splits the former single-module implementation by responsibility:

- :mod:`koru.standard_fleet.models` — data models, schema constants and the
  adoption dedupe key.
- :mod:`koru.standard_fleet.git_observation` — bounded read-only Git
  observation primitives.
- :mod:`koru.standard_fleet.discovery` — standard-source loading and
  governed-repository discovery.
- :mod:`koru.standard_fleet.scan` — scope selection and fleet scan
  orchestration.
- :mod:`koru.standard_fleet.emission` — idempotent Planfile ticket emission.
- :mod:`koru.standard_fleet.reporting` — human-readable report rendering.

The public surface below is unchanged from the previous single module.
"""

from __future__ import annotations

from koru.standard_fleet.discovery import (
    discover_governed_repositories,
    load_standard_release,
)
from koru.standard_fleet.emission import emit_adoption_tickets
from koru.standard_fleet.models import (
    DEDUPE_PREFIX,
    REPORT_SCHEMA,
    SOURCE_TOOL,
    GitObservation,
    GitRunner,
    StandardCandidate,
    StandardExcluded,
    StandardFleetReport,
    StandardRelease,
    adoption_dedupe_key,
)
from koru.standard_fleet.reporting import render_report
from koru.standard_fleet.scan import (
    DEFAULT_ORGANIZATIONS,
    DEFAULT_WORKERS,
    MAX_WORKERS,
    inspect_repository,
    scan_standard_fleet,
)

__all__ = [
    "DEFAULT_ORGANIZATIONS",
    "DEFAULT_WORKERS",
    "DEDUPE_PREFIX",
    "MAX_WORKERS",
    "REPORT_SCHEMA",
    "SOURCE_TOOL",
    "GitObservation",
    "GitRunner",
    "StandardCandidate",
    "StandardExcluded",
    "StandardFleetReport",
    "StandardRelease",
    "adoption_dedupe_key",
    "discover_governed_repositories",
    "emit_adoption_tickets",
    "inspect_repository",
    "load_standard_release",
    "render_report",
    "scan_standard_fleet",
]
