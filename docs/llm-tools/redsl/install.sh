#!/usr/bin/env bash
# Idempotentny installer dla redsl w c2004.
# Bezpieczny do wielokrotnego uruchomienia.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję redsl…"

# 1. Wymaga Python 3.10+
python3 -c "import sys; assert sys.version_info >= (3, 10), f'Need Python 3.10+, got {sys.version}'"

# 2. Pip install (jeśli nie zainstalowane lub nie editable)
if ! command -v redsl >/dev/null 2>&1; then
    pip install --user redsl
elif redsl --version 2>/dev/null | grep -q "1\."; then
    echo "  ✓ redsl już zainstalowany ($(redsl --version 2>&1))"
fi

# 3. Sprawdź config
if [ ! -f "redsl.yaml" ]; then
    echo "  ⚠ Brak redsl.yaml w repo. Generuję domyślny…"
    redsl init --output redsl.yaml
fi

# 4. Sprawdź env vars (bez wymuszania dla gate check)
if [ -z "${OPENROUTER_API_KEY:-}" ] && [ -f ".env" ]; then
    set -a; source .env; set +a
fi

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "  ⚠ Brak OPENROUTER_API_KEY — 'redsl improve' nie zadziała"
    echo "    Ustaw w .env: OPENROUTER_API_KEY=sk-or-v1-..."
fi

# 5. Test gate check
echo "→ Test: redsl gate check (LLM-free)"
if redsl gate check >/dev/null 2>&1; then
    echo "  ✓ gate PASS"
else
    echo "  ⚠ gate FAIL — repo ma quality issues (to OK, gate to wykrył)"
fi

# 6. Sprawdź pre-commit hook
if grep -q "redsl-gate" .pre-commit-config.yaml 2>/dev/null; then
    echo "  ✓ pre-commit hook redsl-gate już skonfigurowany"
else
    echo "  ⚠ Pre-commit hook redsl-gate nie skonfigurowany"
    echo "    Dodaj do .pre-commit-config.yaml — patrz README.md"
fi

echo "✓ redsl gotowy. Komendy: redsl gate check | redsl improve --dry-run"
