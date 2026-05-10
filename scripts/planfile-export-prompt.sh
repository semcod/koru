#!/usr/bin/env bash
# scripts/planfile-export-prompt.sh — pipe a planfile ticket into an
# LLM-agnostic prompt file any coding agent can consume verbatim.
#
# Usage:
#   scripts/planfile-export-prompt.sh PLF-123 [output.md]
#
# Output layout (markdown; see docs/planfile-llm-guide.md for contract):
#
#   # Ticket <ID> — <title>
#   ## 🚨 Context ... (copied from ticket description)
#   ...
#   ## 🧭 Hand-off note for the agent
#   (fixed footer telling the agent how to verify its patch)

set -euo pipefail

TICKET_ID="${1:-}"
OUTPUT="${2:-}"

if [ -z "$TICKET_ID" ]; then
  echo "usage: $0 <TICKET_ID> [output.md]" >&2
  exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

if ! command -v planfile >/dev/null 2>&1; then
  echo "planfile CLI not installed. Try: pipx install planfile" >&2
  exit 1
fi

# Fetch ticket as YAML and parse it in one python invocation so we
# preserve unicode + multi-line block literals intact.
TITLE_DESC=$(planfile ticket show "$TICKET_ID" --format yaml 2>/dev/null | python3 -c "
import sys, yaml
data = yaml.safe_load(sys.stdin) or {}
if not data or 'name' not in data:
    sys.exit(3)
# Emit title on one line, then a marker, then the full description verbatim.
print(data.get('name', '(no title)'))
print('---DESC-START---')
print(data.get('description', ''))
" 2>/dev/null) || {
  echo "Ticket $TICKET_ID not found or planfile CLI failed." >&2
  exit 3
}

TITLE=$(printf '%s' "$TITLE_DESC" | head -n 1)
DESC=$(printf '%s' "$TITLE_DESC" | awk '/^---DESC-START---$/{flag=1; next} flag')

render() {
  printf "# Ticket %s — %s\n\n" "$TICKET_ID" "$TITLE"
  printf "%s\n" "$DESC"
  cat <<'FOOTER'

---

## 🧭 Hand-off note for the agent

You now have every piece of information needed to fix this. Process:

1. Read the files under **📂 Likely-affected areas** before editing.
2. Reproduce the failure with the **🔁 Reproduction** commands.
3. Propose the *smallest* patch that satisfies every checkbox in
   **✅ Acceptance criteria** while honouring the **🔒 Constraints**.
4. Verify with the project's CI gate (see `koru --doctor` for the configured command).
5. Close the ticket via `planfile ticket complete TICKET_ID` (substitute the ID above).

If you cannot satisfy all acceptance criteria in < 80 lines of diff,
**split the ticket** — don't weaken it.
FOOTER
}

if [ -n "$OUTPUT" ]; then
  render > "$OUTPUT"
  echo "Wrote $OUTPUT"
else
  render
fi
