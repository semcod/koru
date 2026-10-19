# Ticket 470: Lazy operator package barrel to cut koru CLI import time (#730)

- **ID**: ticket-470
- **Owner**: agent:claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Goal and scope

Closes semcod/koru#730. `koru.autonomy.operator/__init__.py` star-imported all
19 `operator_*` modules, so `import koru.cli` (which needs only five helpers
from `operator_runtime`) took 1.0–1.5 s. The package is now a PEP 562 lazy
barrel: submodule names resolve to just that submodule (used by the
`koru.autonomous_*` shims), any other name replays the historical star-imports
once in the same order (later modules win), and `__all__` reproduces the old
package star-export exactly (public globals, including bound submodules).

Implementation drafted by Willman (koru.develop_ticket, glm-5.3). Review fixed
two defects its own test could not see: the star-export dropped submodule
names, and `from koru.autonomy.operator import operator_x` triggered a full
re-entrant load that froze a partial `__all__`.

## Acceptance criteria

- [x] AC-01: `import koru.cli` no longer loads operator_diagnostics/wup/resources/loop_runner/daemon;
  `python -X importtime -c 'import koru.cli'` 1 500 ms -> 90 ms.
- [x] AC-02: `from koru.autonomy.operator import *` exports the same 144 names as before
  (independent baseline captured from the eager barrel); attribute access unchanged.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
