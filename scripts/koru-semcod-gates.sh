#!/usr/bin/env bash
set -u

PROJECT="${PROJECT:-.}"
PRIORITY="${PRIORITY:-high}"
DRY_RUN="${DRY_RUN:-0}"
UPDATE_EXISTING="${UPDATE_EXISTING:-1}"

ROOT="$(cd "$PROJECT" && pwd)"
KORU_GATE_CAPTURE="${KORU_GATE_CAPTURE:-$(dirname "$0")/koru-gate-capture.py}"

extra_args=()
if [ "$DRY_RUN" = "1" ] || [ "$DRY_RUN" = "true" ]; then
  extra_args+=(--dry-run)
fi
if [ "$UPDATE_EXISTING" = "1" ] || [ "$UPDATE_EXISTING" = "true" ]; then
  extra_args+=(--update-existing)
fi

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

run_gate() {
  gate="$1"
  command_text="$2"
  fail_regex="$3"
  next_step="$4"

  echo "=== semcod gate: ${gate} ==="
  python3 "$KORU_GATE_CAPTURE" \
    --project "$ROOT" \
    --gate "$gate" \
    --command "$command_text" \
    --fail-regex "$fail_regex" \
    --priority "$PRIORITY" \
    --next-step "$next_step" \
    "${extra_args[@]}"
}

echo "=== koru semcod scan -> planfile ==="
scan_args=(scan --project "$ROOT" --semcod-artifacts)
if [ "$DRY_RUN" != "1" ] && [ "$DRY_RUN" != "true" ]; then
  scan_args+=(--apply)
fi
if has_cmd koru; then
  koru "${scan_args[@]}"
else
  python3 -m koru.cli "${scan_args[@]}"
fi

if has_cmd regix && [ -f "$ROOT/regix.yaml" ]; then
  run_gate "regix" "regix gates" "fail|error|violation|regression" \
    'Inspect regix gate output, reduce the regression, then rerun `regix gates`.'
else
  echo "semcod gate: regix skipped (missing command or regix.yaml)"
fi

if has_cmd wup && [ -f "$ROOT/wup.yaml" ]; then
  run_gate "wup" "wup status" "fail|down|error|unhealthy|regression" \
    'Inspect WUP service health/dependency status, fix the affected service or watcher config, then rerun `wup status`.'
else
  echo "semcod gate: wup skipped (missing command or wup.yaml)"
fi

if has_cmd testql && [ -d "$ROOT/testql-scenarios" ]; then
  run_gate "testql" "testql suite --pattern \"*.testql.toon.yaml\" --output console --fail-fast" "fail|failed|error|❌" \
    'Repair the failing API/behavioral scenario, then rerun the TestQL suite.'
else
  echo "semcod gate: testql skipped (missing command or testql-scenarios/)"
fi

if has_cmd redup; then
  run_gate "redup" "redup scan . --min-lines 10" "fail|error|duplicate|threshold" \
    'Triage duplicate-code output, extract shared code, then rerun `redup scan . --min-lines 10`.'
else
  echo "semcod gate: redup skipped (missing command)"
fi

if [ -x "$ROOT/scripts/sumr-refresh.sh" ]; then
  run_gate "sumr" "scripts/sumr-refresh.sh --status" "stale|fail|error" \
    'Refresh or repair SUMR/SUMD project snapshots, then rerun `scripts/sumr-refresh.sh --status`.'
else
  echo "semcod gate: sumr skipped (scripts/sumr-refresh.sh missing)"
fi

if has_cmd doql && [ -f "$ROOT/app.doql.less" ]; then
  run_gate "doql" "doql check app.doql.less" "fail|error|drift" \
    'Resolve declarative app/infra drift, then rerun the DOQL check.'
else
  echo "semcod gate: doql skipped (missing command or app.doql.less)"
fi

if has_cmd redsl && [ -f "$ROOT/redsl.yaml" ]; then
  run_gate "redsl" "redsl gate check ." "fail|error|violation" \
    'Resolve the REDSL quality gate finding, then rerun `redsl gate check .`.'
else
  echo "semcod gate: redsl skipped (missing command or redsl.yaml)"
fi
