#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję llx…"

if ! command -v llx >/dev/null 2>&1; then
    pip install --user llx
else
    echo "  ✓ llx już zainstalowany ($(llx --version 2>&1 | head -1 || echo 'unknown'))"
fi

# Sprawdź config
if [ ! -f "llx.yaml" ]; then
    echo "  ⚠ Brak llx.yaml — generuję domyślny…"
    cat > llx.yaml <<'EOF'
models:
  balanced:
    provider: openrouter
    model_id: openrouter/deepseek/deepseek-v4-pro
  cheap:
    provider: anthropic
    model_id: claude-haiku-4-5-20251001
  free:
    provider: openrouter
    model_id: openrouter/nvidia/nemotron-3-super-120b-a12b:free

proxy:
  port: 4000
EOF
    echo "  ✓ Utworzono llx.yaml (basic)"
fi

# Env vars
if [ -f ".env" ]; then
    set -a; source .env; set +a
fi

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "  ⚠ Brak OPENROUTER_API_KEY — dodaj do .env: OPENROUTER_API_KEY=sk-or-v1-..."
fi

# Smoke test
echo "→ Smoke test: lista modeli"
if llx models --tier balanced 2>&1 | head -3 | grep -q "."; then
    echo "  ✓ llx models działa"
else
    echo "  ⚠ llx models nie odpowiada — sprawdź OPENROUTER_API_KEY"
fi

echo "✓ llx gotowy. Komendy: llx chat . -p \"...\" | llx fix . --dry-run"
