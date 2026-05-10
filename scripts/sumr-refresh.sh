#!/usr/bin/env bash
# sumr-refresh.sh — debounced refresh of SUMR.md (LLM-snapshot for refactor profile).
#
# Why debounced?
#   `sumr .` runs `code2llm`, `redup`, `doql sync` and re-parses the whole
#   monorepo. It's expensive (~30-90s) and the output drifts slowly, so we
#   only want to regenerate after a meaningful chunk of work has landed.
#
# Triggers refresh when ANY of:
#   • SUMR.md does not exist
#   • >= ${SUMR_MAX_COMMITS:-25} commits on HEAD since SUMR.md last touched
#   • >= ${SUMR_MAX_DAYS:-7} days since SUMR.md mtime
#   • --force (or SUMR_FORCE=1) supplied
#
# Updates only the deps that `sumr` actually invokes:
#   sumd   — the tool itself (provides `sumr` entry point)
#   code2llm — code map / TOON snapshots (used by --analyze)
#   redup    — duplicate detector (used by --analyze)
#   doql     — DOQL skeleton + `doql sync` (default-on in sumr)
#
# vallm is intentionally skipped (heavy LLM deps, off by default).
#
# Flags:
#   --force     ignore debounce (always refresh)
#   --status    print status only, do not run anything (exit 0=fresh, 1=stale)
#   --help      this help
#
# Env knobs:
#   SUMR_MAX_COMMITS   trigger threshold in commits since last refresh (default 25)
#   SUMR_MAX_DAYS      trigger threshold in days since last refresh    (default 7)
#   SUMR_FORCE         set to 1 to always refresh (same as --force)
#   SUMR_VENV          venv path containing `sumr` binary (default: venv)
#   SUMR_SKIP_DEPS     set to 1 to skip the dep update step (use last installed)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

MAX_COMMITS="${SUMR_MAX_COMMITS:-25}"
MAX_DAYS="${SUMR_MAX_DAYS:-7}"
VENV="${SUMR_VENV:-venv}"
SUMR_FILE="${REPO_ROOT}/SUMR.md"
STATE_DIR="${REPO_ROOT}/.sumr"
STATE_FILE="${STATE_DIR}/state.json"

FORCE="${SUMR_FORCE:-0}"
STATUS_ONLY=0

# ── arg parsing ────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --force)  FORCE=1 ;;
    --status) STATUS_ONLY=1 ;;
    --help|-h)
      sed -n '2,33p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "[sumr-refresh] unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

# ── helpers ────────────────────────────────────────────────────────────────
log()  { echo "[sumr-refresh] $*"; }
warn() { echo "[sumr-refresh] WARN: $*" >&2; }

# Commits between SUMR.md and HEAD (counts commits on HEAD that are NOT
# reachable from the commit that last touched SUMR.md). When SUMR.md is
# tracked, this is monotonic and survives merges; when untracked or missing,
# returns the total commit count so we always refresh.
commits_since_sumr() {
  if [ ! -f "${SUMR_FILE}" ]; then
    git rev-list --count HEAD 2>/dev/null || echo 999999
    return
  fi
  local last_sumr_commit
  last_sumr_commit=$(git log -n 1 --format=%H -- "${SUMR_FILE}" 2>/dev/null || true)
  if [ -z "${last_sumr_commit}" ]; then
    git rev-list --count HEAD 2>/dev/null || echo 999999
  else
    git rev-list --count "${last_sumr_commit}..HEAD" 2>/dev/null || echo 0
  fi
}

# Filesystem age in whole days (mtime → today).
days_since_sumr_mtime() {
  if [ ! -f "${SUMR_FILE}" ]; then
    echo 999999
    return
  fi
  local now mtime
  now=$(date +%s)
  mtime=$(stat -c '%Y' "${SUMR_FILE}" 2>/dev/null || echo "${now}")
  echo $(( (now - mtime) / 86400 ))
}

is_stale() {
  local commits days
  commits=$(commits_since_sumr)
  days=$(days_since_sumr_mtime)
  if [ ! -f "${SUMR_FILE}" ]; then
    echo "missing"
    return
  fi
  if [ "${commits}" -ge "${MAX_COMMITS}" ]; then
    echo "stale-commits:${commits}>=${MAX_COMMITS}"
    return
  fi
  if [ "${days}" -ge "${MAX_DAYS}" ]; then
    echo "stale-days:${days}>=${MAX_DAYS}"
    return
  fi
  echo "fresh:commits=${commits}/${MAX_COMMITS},days=${days}/${MAX_DAYS}"
}

# ── status mode ────────────────────────────────────────────────────────────
state="$(is_stale)"
if [ "${STATUS_ONLY}" -eq 1 ]; then
  log "SUMR.md state: ${state}"
  case "${state}" in
    fresh:*) exit 0 ;;
    *)       exit 1 ;;
  esac
fi

# ── debounce ───────────────────────────────────────────────────────────────
if [ "${FORCE}" -ne 1 ]; then
  case "${state}" in
    fresh:*)
      log "up-to-date — skipping (${state}). Use --force to override."
      exit 0
      ;;
    *)
      log "stale — refreshing (${state})"
      ;;
  esac
else
  log "force-refresh requested (state was: ${state})"
fi

# ── ensure venv ────────────────────────────────────────────────────────────
PIP="${VENV}/bin/pip"
SUMR_BIN="${VENV}/bin/sumr"

if [ ! -x "${PIP}" ]; then
  log "creating venv at ${VENV}/"
  python3 -m venv "${VENV}"
fi

# ── update sumr-relevant deps ──────────────────────────────────────────────
if [ "${SUMR_SKIP_DEPS:-0}" -ne 1 ]; then
  log "updating sumr-relevant deps: sumd code2llm redup doql"
  "${PIP}" install --upgrade --quiet \
    sumd \
    code2llm \
    redup \
    doql \
    || { warn "dep upgrade failed — continuing with installed versions"; }
else
  log "SUMR_SKIP_DEPS=1 — using installed dep versions"
fi

if [ ! -x "${SUMR_BIN}" ]; then
  warn "${SUMR_BIN} not found after install; aborting"
  exit 3
fi

# ── run sumr ───────────────────────────────────────────────────────────────
log "running: ${SUMR_BIN} ."
"${SUMR_BIN}" .

# ── persist state ──────────────────────────────────────────────────────────
mkdir -p "${STATE_DIR}"
HEAD_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SUMR_VERSION=$("${VENV}/bin/python" -c "import sumd, sys; sys.stdout.write(getattr(sumd, '__version__', '?'))" 2>/dev/null || echo "?")

cat > "${STATE_FILE}" <<EOF
{
  "last_refresh_iso": "${NOW_ISO}",
  "head_sha": "${HEAD_SHA}",
  "sumd_version": "${SUMR_VERSION}",
  "thresholds": {
    "max_commits": ${MAX_COMMITS},
    "max_days": ${MAX_DAYS}
  }
}
EOF

log "done — SUMR.md regenerated, state → ${STATE_FILE}"
