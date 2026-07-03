---
description: run on-change gates (regix + testql + wup status + plugin tests) with real-time deduplicated task capture
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
test -f regix.yaml && python scripts/koru-gate-capture.py \
  --gate regix \
  --command "regix gates 2>&1 | tail -20" \
  --fail-regex "target:|failed|violation" \
  --update-existing \
  --next-step "Lower offending complexity/quality metric or relax gate threshold intentionally." || \
echo "(regix not configured)"
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
test -f "$SCENARIO" && python scripts/koru-gate-capture.py \
  --gate testql \
  --command "testql run '$SCENARIO' --output console 2>&1 | tail -20" \
  --update-existing \
  --next-step "Fix failing scenario assertion or align endpoint behavior." || \
echo "(no scenario at $SCENARIO)"
```

### 4. wup — daemon status

If `wup.yaml` exists, check the daemon. wup is a long-running watcher,
so this only reports presence; do not start/stop it from the slash
command (that is the human's choice).

// turbo

```bash
test -f wup.yaml && python scripts/koru-gate-capture.py \
  --gate wup \
  --command "wup status 2>&1 | head -20" \
  --fail-regex "error|failed|not running|down" \
  --update-existing \
  --next-step "Restart/fix wup daemon and verify configuration paths." || \
echo "(wup not configured)"
```

### 5. koru autopilot plugin tests (optional)

If this repository contains the VS Code autopilot plugin, run its local
test suite so slash-workflow gates match the default `POLICY_STUB`
behavior.

// turbo

```bash
test -f plugins/koru-autopilot-vscode/package.json && (
  python scripts/koru-gate-capture.py \
    --gate plugin \
    --command "cd plugins/koru-autopilot-vscode && npm test 2>&1 | tail -20" \
    --update-existing \
    --next-step "Fix failing plugin unit/compile checks in koru-autopilot-vscode."
) || echo "(koru-autopilot-vscode plugin not present)"
```

### 6. Aggregate, capture, continue

- **All green** — say so, return control to the user.
- **Any red** — do NOT drop context and do NOT duplicate findings.
  Immediately record a follow-up in planfile with a stable finding key,
  then continue the flow.

Real-time capture is handled entirely by
`scripts/koru-gate-capture.py` (already invoked with
`--update-existing` in steps 2–5). It builds the finding key
(sha1 of gate + normalized failing line), dedupes against existing
`koru-gate` tickets, appends a `still failing` note when the key is
already tracked, and creates a ticket with the exact failing line,
command, and next step otherwise.

Do NOT run `planfile ticket create` by hand for gate findings — and
never with template placeholders like `<finding_key>` or `<gate>`.
If a capture invocation itself fails, re-run it with `--dry-run` to
inspect what it would create, then report the error to the user
instead of creating the ticket manually.

After capture, continue with remaining gates so the user sees full
problem set in one pass.

## Rationale

The core triad covers three orthogonal failure modes:

- `regix` — *quality regression* (metric got worse).
- `testql` — *behavioral regression* (HTTP probe broken).
- `wup` — *coverage of incremental change* (the watcher itself is up).

For the `koru` repo itself, the optional plugin check adds IDE bridge
stability coverage (`koru-autopilot-vscode`).

A clean run means the change has been pre-validated by each layer. A
red run is a signal to create/update a deduplicated planfile task in
real time, so remediation is explicit and traceable without stopping
the whole loop.

## Footnotes

- This slash command may mutate planfile state only to create
  deduplicated gate tickets via `planfile ticket create`.
- For a continuous (per-save) version of the same gates, run
  `wup watch` in a side terminal. See `workflows/on-change-gates.md`.
