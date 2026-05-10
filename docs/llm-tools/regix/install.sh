#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję regix…"

if ! command -v regix >/dev/null 2>&1; then
    pip install --user regix
else
    echo "  ✓ regix już zainstalowany"
fi

# Backends
echo "→ Sprawdzam backendy regix:"
REGIX_STATUS=$(regix status 2>&1 || true)
for backend in lizard radon coverage vallm; do
    if echo "$REGIX_STATUS" | grep -E "^\s+✓\s+$backend" >/dev/null; then
        echo "  ✓ $backend dostępny"
    else
        echo "  ⚠ $backend brak — pip install --user $backend"
    fi
done

# Config
if [ ! -f "regix.yaml" ]; then
    echo "  ⚠ Brak regix.yaml — generuję domyślny…"
    regix init --output regix.yaml
fi

# Pre-commit hook
if grep -q "regix" .pre-commit-config.yaml 2>/dev/null; then
    echo "  ✓ pre-commit hook regix skonfigurowany"
else
    echo "  ⚠ Pre-commit hook regix brak — patrz README.md"
fi

# Smoke test
echo "→ Test: regix check (working tree vs HEAD)"
if regix check 2>&1 | head -3 | grep -qE "PASS|FAIL"; then
    echo "  ✓ regix check działa"
else
    echo "  ⚠ regix check nie odpowiada (może brak commitów)"
fi

# Taskfile integration
if grep -q "quality:regix:local" Taskfile.yml 2>/dev/null; then
    echo "  ✓ Taskfile ma quality:regix:local"
fi

echo "✓ regix gotowy. Komenda: task quality:regix:local | regix compare HEAD~1 HEAD"
