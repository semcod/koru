---
description: run on-change gates (regix + testql + wup status) for the current koru-managed project
---

# /koru-gate — manual on-change gate run

Use this when you want to verify the current state before continuing
edits, especially:
- Right after a series of file changes inside a ticket scope.
- Before calling `planfile ticket complete` (mandatory if policy
  `require_ci_pass_before_complete: true` and `task quality:gate` is
  not the canonical gate for the change kind, e.g. YAML/config-only).
- When inheriting an unfamiliar branch and you want a clean baseline.

## Steps

### 1. Detect available gates

```bash
test -f wup.yaml      && echo "✓ wup.yaml present"      || echo "✗ wup.yaml missing"
test -f regix.yaml    && echo "✓ regix.yaml present"    || echo "✗ regix.yaml missing"
test -d testql-testing/scenarios && \
  echo "✓ testql-testing/scenarios/ present ($(ls testql-testing/scenarios/*.yaml 2>/dev/null | wc -l) scenarios)" || \
  echo "✗ no testql scenarios"
```

### 2. regix gates — absolute thresholds

If `regix.yaml` exists:

// turbo
```bash
regix gates 2>&1 | tail -20
```

Exit 0 = green. Exit non-zero = at least one absolute threshold (CC,
MI, coverage, smell) violated. Surface the violations to the user
verbatim — do NOT auto-fix.

### 3. testql — quick smoke (or scenario-in-scope)

If a ticket is active and has files in scope, prefer the testql
scenarios that cover those files. Otherwise default to
`realtime-health.testql.toon.yaml` if it exists.

// turbo
```bash
SCENARIO="${1:-testql-testing/scenarios/realtime-health.testql.toon.yaml}"
test -f "$SCENARIO" && testql run "$SCENARIO" --output console 2>&1 | tail -10 || echo "(no scenario at $SCENARIO)"
```

### 4. wup — daemon status

If `wup.yaml` exists, check the daemon. wup is a long-running watcher,
so this only reports presence; do not start/stop it from the slash
command (that is the human's choice).

// turbo
```bash
test -f wup.yaml && wup status 2>&1 | head -20 || echo "(wup not configured)"
```

### 5. Aggregate & decide

- **All green** — say so, return control to the user.
- **Any red** — do NOT proceed with edits or `ticket complete`. Instead
  call `planfile ticket input <id> --prompt "<what failed, with the
  exact failing line>"` and stop, per koru policy.

## Rationale

The triad covers three orthogonal failure modes:
- `regix` — *quality regression* (metric got worse).
- `testql` — *behavioral regression* (HTTP probe broken).
- `wup` — *coverage of incremental change* (the watcher itself is up).

A clean run means the change has been pre-validated by each layer. A
red run is a hard signal to pause and route through planfile lifecycle
instead of pushing through.

## Footnotes

- This slash command is read-only. It never edits files, runs git, or
  mutates planfile state. It only emits diagnostics.
- For a continuous (per-save) version of the same gates, run
  `wup watch` in a side terminal. See `workflows/on-change-gates.md`.
