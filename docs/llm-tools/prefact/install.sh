#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję prefact…"

if ! command -v prefact >/dev/null 2>&1; then
    pip install --user prefact
else
    echo "  ✓ prefact już zainstalowany"
fi

# Config
if [ ! -f "prefact.yaml" ]; then
    echo "  ⚠ Brak prefact.yaml — generuję domyślny…"
    cat > prefact.yaml <<'EOF'
exclude:
  - "**/_pb2*.py"
  - "archive/**"
  - "_archive/**"
  - "venv/**"
  - "node_modules/**"

checks:
  unused_imports: error
  relative_imports: warning
  hallucinated_symbols: error
  unfinished_functions: warning
EOF
fi

# Smoke test
echo "→ Test: prefact check (LLM-free)"
if prefact check . --exclude "venv/**" --exclude "node_modules/**" >/dev/null 2>&1; then
    echo "  ✓ prefact check PASS"
else
    echo "  ⚠ prefact check znalazł problemy (to OK — to jego rola)"
fi

# Sprawdź pyqual integration
if grep -q "prefact" pyqual.yaml 2>/dev/null; then
    echo "  ✓ pyqual ma stage prefact"
else
    echo "  ℹ pyqual nie używa prefact — opcjonalne"
fi

echo "✓ prefact gotowy. Komenda: prefact check backend/ | prefact -a"
