#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję vallm…"

# Vallm wymaga Python 3.12+
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ! python3 -c "import sys; assert sys.version_info >= (3, 12)" 2>/dev/null; then
    echo "  ⚠ vallm wymaga Python 3.12+; masz $PYVER"
    echo "    Healing-webhook ma własny Python 3.12 w obrazie (OK)"
    echo "    Local: zainstaluj python3.12 lub uruchom przez Docker"
    exit 1
fi

if ! command -v vallm >/dev/null 2>&1; then
    pip install --user "vallm>=0.1.71"
else
    echo "  ✓ vallm już zainstalowany"
fi

# Smoke test tier-1 (no LLM, no API key)
echo "→ Smoke test: vallm check (tier-1, LLM-free)"
TMPDIR=$(mktemp -d)
TMPFILE="$TMPDIR/test_vallm.py"
echo 'print("test")' > "$TMPFILE"
VALLM_OUTPUT=$(vallm check --file "$TMPFILE" 2>&1 || true)
if echo "$VALLM_OUTPUT" | grep -q "PASS"; then
    echo "  ✓ vallm check działa"
else
    echo "  ⚠ vallm check zwrócił nietypowy output (sprawdź ręcznie):"
    echo "$VALLM_OUTPUT" | head -3 | sed 's/^/    /'
fi
rm -rf "$TMPDIR"

# Sprawdź healing-webhook integration
if grep -q "vallm" monitoring/healing-webhook/app.py 2>/dev/null; then
    echo "  ✓ healing-webhook ma integrację vallm"
else
    echo "  ⚠ healing-webhook nie ma integracji vallm — patrz README.md"
fi

# Tier-2 wymaga API key
if [ -f ".env" ]; then
    set -a; source .env; set +a
fi

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "  ℹ Tier-2 (LLM-as-judge) wyłączone — brak OPENROUTER_API_KEY"
    echo "    Tier-1 wystarczy do większości scenariuszy"
fi

echo "✓ vallm gotowy. Komendy: vallm check --file <plik> | vallm validate --file <plik>"
