#!/usr/bin/env bash
# Local publication orchestration for a target PR without GitHub Actions on that repo.
# Publishes standard-pack conformance via REST, observes the protected local
# OneDev executor, then invokes the deployed local Validator direct-pr adapter.
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
  echo "  --merge     Pass --merge to the local Validator adapter."
  echo "  --dry-run   Run checks and observe OneDev; skip script status publish and Validator."
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
LOCAL_VALIDATOR_ENV_FILE="${LOCAL_VALIDATOR_ENV_FILE:-$HOME/.config/subactor/local-validator.env}"
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

commit_status_description() {
  local sha="$1"
  local context="$2"
  gh api "repos/${REPO_SLUG}/commits/${sha}/status" \
    --jq ".statuses[] | select(.context==\"${context}\") | .description" 2>/dev/null | head -n1
}

wait_for_deployed_onedev() {
  local main_sha="$1"
  local deadline=$((SECONDS + 1800))
  local state=""
  local description=""
  while (( SECONDS < deadline )); do
    state="$(commit_status_context_state "$FROZEN_HEAD" "onedev/local-verify" || true)"
    description="$(commit_status_description "$FROZEN_HEAD" "onedev/local-verify" || true)"
    if [[ "$state" == "success" && "$description" == *"main ${main_sha:0:12}"* ]]; then
      echo "onedev/local-verify=success (deployed local OneDev; main=${main_sha})"
      return 0
    fi
    if [[ "$state" == "failure" || "$state" == "error" ]]; then
      die "onedev/local-verify=${state} on ${FROZEN_HEAD}: ${description:-no description}"
    fi
    echo "onedev/local-verify=${state:-pending}; waiting for deployed local OneDev executor"
    sleep 15
  done
  die "timed out waiting for deployed onedev/local-verify on ${FROZEN_HEAD} against main ${main_sha} (last=${state:-pending})"
}

echo "=== Resolve agent paths ==="
[[ -d "$ONEDEV_AGENT" ]] || die "ONEDEV_AGENT not found: $ONEDEV_AGENT"
[[ -f "${ONEDEV_AGENT}/config/repositories.toml" ]] || die "missing ${ONEDEV_AGENT}/config/repositories.toml"
if [[ "$DRY_RUN" != true ]]; then
  [[ -f "$LOCAL_VALIDATOR_ENV_FILE" && ! -L "$LOCAL_VALIDATOR_ENV_FILE" ]] \
    || die "protected local Validator environment not found: $LOCAL_VALIDATOR_ENV_FILE"
  env_mode="$(stat -c '%a' "$LOCAL_VALIDATOR_ENV_FILE")"
  env_owner="$(stat -c '%u' "$LOCAL_VALIDATOR_ENV_FILE")"
  [[ "$env_owner" == "$(id -u)" ]] \
    || die "local Validator environment is not owned by the current user"
  (( (8#$env_mode & 0077) == 0 )) \
    || die "local Validator environment permissions are too open"
  set -a
  # shellcheck disable=SC1090
  source "$LOCAL_VALIDATOR_ENV_FILE"
  set +a
  [[ -n "${VALIDATOR_ROOT:-}" ]] || die "local Validator environment lacks VALIDATOR_ROOT"
  VALIDATOR_SCRIPT="${VALIDATOR_RUNNER:-${VALIDATOR_ROOT}/bin/run-local-direct-pr.sh}"
  [[ -x "$VALIDATOR_SCRIPT" ]] || die "missing deployed local Validator adapter: $VALIDATOR_SCRIPT"
  [[ -n "${VALIDATOR_APP_PRIVATE_KEY_FILE:-}" ]] \
    || die "local Validator environment lacks VALIDATOR_APP_PRIVATE_KEY_FILE"
  [[ -f "$VALIDATOR_APP_PRIVATE_KEY_FILE" && ! -L "$VALIDATOR_APP_PRIVATE_KEY_FILE" ]] \
    || die "Validator App key is not a protected file"
fi
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
    --primary-checkout /workspace > "$record"
  python3 .governance/worktree_path_check.py validate "$record"
  python3 - "$record" <<'PY'
import json
import sys

record = json.load(open(sys.argv[1], encoding="utf-8"))
assert record["branch"] == "ticket/777-ci-probe", record
assert record["worktreePath"] == (
    "/workspace/.worktrees/ticket-777--ci-probe"
), record
assert record["leasePath"] == (
    f"/workspace/.subactor/leases/"
    f"ticket-777--ci-probe.json"
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

echo "=== Observe deployed OneDev local profile ==="
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  GITHUB_TOKEN="$(gh auth token)"
  export GITHUB_TOKEN
fi
LOCAL_MAIN_SHA="$(gh api "repos/${REPO_SLUG}/git/ref/heads/main" --jq .object.sha)"
[[ "$LOCAL_MAIN_SHA" =~ ^[0-9a-f]{40}$ ]] || die "could not resolve main SHA for ${REPO_SLUG}"
echo "main_sha=${LOCAL_MAIN_SHA}"
wait_for_deployed_onedev "$LOCAL_MAIN_SHA"

echo "=== Verify onedev/local-verify on frozen head ==="
ONEDEV_STATE="$(commit_status_context_state "$FROZEN_HEAD" "onedev/local-verify" || true)"
if [[ "$DRY_RUN" == true && -z "$ONEDEV_STATE" ]]; then
  ONEDEV_STATE="success"
fi
echo "onedev/local-verify=${ONEDEV_STATE:-success}"
[[ "$ONEDEV_STATE" == "success" || "$DRY_RUN" == true ]] || die "onedev/local-verify is not success on ${FROZEN_HEAD}"

if [[ "$DRY_RUN" == true ]]; then
  echo "=== Dry run: skipping local Validator adapter ==="
  echo "publish-local-onedev-validator: dry_run complete for ${REPO_SLUG}#${PR} @ ${FROZEN_HEAD}"
  exit 0
fi

echo "=== Deployed local Validator direct-pr ==="
VALIDATOR_ARGS=(
  "$VALIDATOR_SCRIPT"
  --repository "$REPO_SLUG"
  --pull-request "$PR"
  --ticket "$TICKET"
  --expected-head-sha "$FROZEN_HEAD"
  --key-file "$VALIDATOR_APP_PRIVATE_KEY_FILE"
)
if [[ "$MERGE" == true ]]; then
  VALIDATOR_ARGS+=(--merge)
else
  VALIDATOR_ARGS+=(--apply)
fi
if [[ -n "${VALIDATOR_SUBLLM_ROOT:-}" ]]; then
  VALIDATOR_ARGS+=(--subllm-root "$VALIDATOR_SUBLLM_ROOT")
fi
"${VALIDATOR_ARGS[@]}"

echo "publish-local-onedev-validator: completed for ${REPO_SLUG}#${PR} @ ${FROZEN_HEAD}"
