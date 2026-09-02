#!/usr/bin/env bash
# Local publication orchestration for a target PR without GitHub Actions on that repo.
# Publishes standard-pack conformance via REST, runs onedev-agent locally, then
# dispatches validator-agent direct-pr (workflow runs only on validator-agent).
#
# Usage:
#   publish-local-onedev-validator.sh --owner OWNER --name NAME --pr N \
#     --ticket ticket-NNN [--merge] [--dry-run]

set -euo pipefail

OWNER=""
NAME=""
PR=""
TICKET=""
MERGE=false
DRY_RUN=false

usage() {
  sed -n '2,8p' "$0" | tail -n +2
  echo "  --merge     Pass --merge to validator dispatch."
  echo "  --dry-run   Run checks and onedev; skip status publish and validator dispatch."
}

die() {
  echo "publish-local-onedev-validator: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner) OWNER="${2:-}"; shift 2 ;;
    --name) NAME="${2:-}"; shift 2 ;;
    --pr) PR="${2:-}"; shift 2 ;;
    --ticket) TICKET="${2:-}"; shift 2 ;;
    --merge) MERGE=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -n "$OWNER" && -n "$NAME" && -n "$PR" && -n "$TICKET" ]] || {
  usage
  die "missing required --owner, --name, --pr, or --ticket"
}
[[ "$PR" =~ ^[0-9]+$ ]] || die "--pr must be a positive integer"
[[ "$TICKET" =~ ^ticket-[0-9]{3}$ ]] || die "--ticket must match ticket-NNN"

ONEDEV_AGENT="${ONEDEV_AGENT:-$HOME/github/subactor/onedev-agent}"
VALIDATOR_AGENT="${VALIDATOR_AGENT:-$HOME/github/subactor/validator-agent}"
SUBLLM_ROOT="${SUBLLM_ROOT:-$HOME/github/subactor/subllm}"
SUBLLM_POLICY_FILE="${SUBLLM_POLICY_FILE:-${SUBLLM_ROOT}/subllm.toml}"
REPO_SLUG="${OWNER}/${NAME}"
WORK_ROOT=""
RUNNER_TEMP=""

cleanup() {
  if [[ -n "$WORK_ROOT" && -d "$WORK_ROOT" ]]; then
    if [[ -d "${WORK_ROOT}/repo" ]]; then
      git -C "${WORK_ROOT}/repo" worktree remove --force "${WORK_ROOT}/wt" 2>/dev/null || true
      rm -rf "${WORK_ROOT}/wt" 2>/dev/null || true
    fi
    rm -rf "$WORK_ROOT"
  fi
}
trap cleanup EXIT

commit_status_context_state() {
  local sha="$1"
  local context="$2"
  gh api "repos/${REPO_SLUG}/commits/${sha}/status" \
    --jq ".statuses[] | select(.context==\"${context}\") | .state" 2>/dev/null | head -n1
}

wait_for_commit_status() {
  local sha="$1"
  local context="$2"
  local want="${3:-success}"
  local deadline=$((SECONDS + 1800))
  local state=""
  while (( SECONDS < deadline )); do
    state="$(commit_status_context_state "$sha" "$context" || true)"
    if [[ "$state" == "$want" ]]; then
      echo "$state"
      return 0
    fi
    if [[ "$state" == "failure" || "$state" == "error" ]]; then
      die "commit status ${context}=${state} on ${sha}"
    fi
    sleep 15
  done
  die "timed out waiting for ${context}=${want} on ${sha} (last=${state:-pending})"
}

run_onedev_agent() {
  [[ -d "$SUBLLM_ROOT/src" ]] || die "SUBLLM_ROOT not found: $SUBLLM_ROOT"
  [[ -f "$SUBLLM_POLICY_FILE" ]] || die "SUBLLM_POLICY_FILE not found: $SUBLLM_POLICY_FILE"
  export SUBLLM_POLICY_FILE
  export ONEDEV_AGENT_PR_VERIFICATION=true
  export PYTHONPATH="${SUBLLM_ROOT}/src:${ONEDEV_AGENT}/src:${PYTHONPATH:-}"
  python3 -m onedev_agent --config "${ONEDEV_AGENT}/config/repositories.toml" "$@"
}

prepare_onedev_scan_cursor() {
  local queue_root="${ONEDEV_AGENT}/data/pr-state"
  local index=""
  index="$(python3 <<PY
import tomllib
from pathlib import Path

config = tomllib.load(Path("${ONEDEV_AGENT}/config/repositories.toml").open("rb"))
repos = config["pull_request_verification"]["repositories"]
for i, row in enumerate(repos):
    if row.get("full_name") == "${REPO_SLUG}":
        print(i)
        break
else:
    raise SystemExit("repository profile not found: ${REPO_SLUG}")
PY
)"
  mkdir -p "$queue_root"
  printf '{"next_index": %s}\n' "$index" > "${queue_root}/scan-cursor.json"
}

clear_onedev_reported_state() {
  local state_path="${ONEDEV_AGENT}/data/pr-state/reported-state.json"
  [[ -f "$state_path" ]] || return 0
  python3 <<PY
import json
from pathlib import Path

path = Path("${state_path}")
state = json.loads(path.read_text(encoding="utf-8"))
if isinstance(state, dict):
    state.pop("${REPO_SLUG}#${PR}", None)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

run_onedev_until_local_verify() {
  local deadline=$((SECONDS + 1800))
  local state=""
  prepare_onedev_scan_cursor
  clear_onedev_reported_state
  while (( SECONDS < deadline )); do
    coord="$(run_onedev_agent pr-coordinate-once)"
    echo "$coord"
    exec_out="$(run_onedev_agent pr-execute-once)"
    echo "$exec_out"
    state="$(commit_status_context_state "$FROZEN_HEAD" "onedev/local-verify" || true)"
    if [[ "$state" == "success" ]]; then
      echo "onedev/local-verify=${state}"
      return 0
    fi
    if [[ "$state" == "failure" || "$state" == "error" ]]; then
      die "onedev/local-verify=${state} on ${FROZEN_HEAD}"
    fi
    sleep 10
  done
  die "timed out waiting for onedev/local-verify=success on ${FROZEN_HEAD} (last=${state:-pending})"
}

echo "=== Resolve agent paths ==="
[[ -d "$ONEDEV_AGENT" ]] || die "ONEDEV_AGENT not found: $ONEDEV_AGENT"
[[ -d "$VALIDATOR_AGENT" ]] || die "VALIDATOR_AGENT not found: $VALIDATOR_AGENT"
[[ -d "$SUBLLM_ROOT/src" ]] || die "SUBLLM_ROOT not found: $SUBLLM_ROOT"
[[ -f "$SUBLLM_POLICY_FILE" ]] || die "SUBLLM_POLICY_FILE not found: $SUBLLM_POLICY_FILE"
[[ -x "${VALIDATOR_AGENT}/bin/dispatch-direct-pr.sh" ]] || die "missing ${VALIDATOR_AGENT}/bin/dispatch-direct-pr.sh"
command -v gh >/dev/null || die "gh CLI is required"
command -v python3 >/dev/null || die "python3 is required"
command -v git >/dev/null || die "git is required"

echo "=== Freeze PR head (REST) ==="
FROZEN_HEAD="$(gh api "repos/${REPO_SLUG}/pulls/${PR}" --jq .head.sha)"
[[ -n "$FROZEN_HEAD" ]] || die "could not resolve head SHA for PR #${PR}"
echo "frozen_head=${FROZEN_HEAD}"

echo "=== Standard packs / conformance (local worktree at frozen head) ==="
WORK_ROOT="${HOME}/.cache/koru-pr-verify-$$"
RUNNER_TEMP="${WORK_ROOT}/runner-temp"
mkdir -p "$RUNNER_TEMP"
git clone --filter=blob:none "https://github.com/${REPO_SLUG}.git" "${WORK_ROOT}/repo"
git -C "${WORK_ROOT}/repo" fetch origin "${FROZEN_HEAD}"
git -C "${WORK_ROOT}/repo" worktree add "${WORK_ROOT}/wt" "${FROZEN_HEAD}"
WT="${WORK_ROOT}/wt"

(
  set -euo pipefail
  cd "$WT"

  python3 .governance/standard_pack_check.py \
    --root . --format json > "${RUNNER_TEMP}/standard-pack-audit.json"
  python3 .governance/standard_pack_projection_check.py \
    --root . --format json
  python3 - "${RUNNER_TEMP}/standard-pack-audit.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
expected = {
    ("STD-PACK-LEVEL", "profile requires wellmanifest/worktrees at S3"),
    ("STD-PACK-LEVEL", "profile requires wellmanifest/logs at S3"),
}
observed = {
    (item.get("code"), item.get("message"))
    for item in report.get("findings", [])
}
assert report.get("schema") == "wellmanifest.standard-adoption-report/v1", report
assert report.get("profile") == "baseline", report
if report.get("mode") == "audit":
    assert report.get("ok") is False, report
    assert observed == expected, report
elif report.get("mode") == "enforce":
    assert report.get("ok") is True, report
    assert observed == set(), report
else:
    raise AssertionError(report)
PY

  record="${RUNNER_TEMP}/worktree-layout.json"
  python3 .governance/worktree_path_check.py plan \
    --repository "github.com/${OWNER}/${NAME}" \
    --repository-name "${NAME}" \
    --ticket ticket-777 \
    --slug ci-probe \
    --workspace-root /workspace > "$record"
  python3 .governance/worktree_path_check.py validate "$record"
  python3 - "$record" <<'PY'
import json
import sys

record = json.load(open(sys.argv[1], encoding="utf-8"))
name = record["repositoryName"]
assert record["branch"] == "ticket/777-ci-probe", record
assert record["worktreePath"] == (
    f"/workspace/.worktrees/{name}--ticket-777--ci-probe"
), record
assert record["leasePath"] == (
    f"/workspace/.worktrees/.leases/"
    f"{name}--ticket-777--ci-probe.json"
), record
PY

  python3 - <<'PY'
import hashlib
import json
from pathlib import Path

path = Path("src/koru/data/wellmanifest-logs-contract-v0.3.json")
raw = path.read_bytes()
contract = json.loads(raw)
assert hashlib.sha256(raw).hexdigest() == (
    "916ccdd3a6f499b160b631da09a6a060233105e907f5582c12d8eaecae92e2eb"
)
assert contract["schema"] == "wellmanifest.logs/contract-bundle/v1"
assert contract["version"] == "0.3.0"
assert contract["canonical"] == "protobuf"
assert contract["projection"] == "canonical-jsonl"
assert contract["hashProfile"] == "wellmanifest-canonical-json-v1+SHA-256"
assert contract["processes"]["append"].endswith("/command/append")
assert contract["processes"]["inspect"].endswith("/query/inspect")
assert set(contract["vocabulary"]["modes"]) == {"PLAN", "APPLY"}
assert "SECURITY" in contract["vocabulary"]["errorCategories"]
assert contract["schemas"]["evidence"]["additionalProperties"] is False
PY
)

echo "standard packs / conformance: passed locally"

if [[ "$DRY_RUN" == true ]]; then
  echo "=== Dry run: skipping standard-pack status publish ==="
else
  echo "=== Publish standard packs / conformance status (REST) ==="
  gh api "repos/${REPO_SLUG}/statuses/${FROZEN_HEAD}" \
    -f state=success \
    -f context="standard packs / conformance" \
    -f description="local onedev-validator publish script" \
    >/dev/null
fi

echo "=== OneDev PR coordinate + execute (local) ==="
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  GITHUB_TOKEN="$(gh auth token)"
  export GITHUB_TOKEN
fi
(
  cd "$ONEDEV_AGENT"
  echo "ONEDEV_AGENT_PR_VERIFICATION=true"
  run_onedev_until_local_verify
)

echo "=== Verify onedev/local-verify on frozen head ==="
ONEDEV_STATE="$(commit_status_context_state "$FROZEN_HEAD" "onedev/local-verify")"
echo "onedev/local-verify=${ONEDEV_STATE}"
[[ "$ONEDEV_STATE" == "success" ]] || die "onedev/local-verify is not success on ${FROZEN_HEAD}"

if [[ "$DRY_RUN" == true ]]; then
  echo "=== Dry run: skipping validator-agent dispatch ==="
  echo "publish-local-onedev-validator: dry_run complete for ${REPO_SLUG}#${PR} @ ${FROZEN_HEAD}"
  exit 0
fi

echo "=== Validator-agent direct-pr dispatch ==="
DISPATCH_ARGS=(
  "${VALIDATOR_AGENT}/bin/dispatch-direct-pr.sh"
  --owner "$OWNER"
  --name "$NAME"
  --pr "$PR"
  --ticket "$TICKET"
  --wait-checks
)
if [[ "$MERGE" == true ]]; then
  DISPATCH_ARGS+=(--merge --watch)
fi
"${DISPATCH_ARGS[@]}"

echo "publish-local-onedev-validator: completed for ${REPO_SLUG}#${PR} @ ${FROZEN_HEAD}"
