#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję pfix…"

if ! command -v pfix >/dev/null 2>&1; then
    pip install --user pfix
else
    echo "  ✓ pfix już zainstalowany"
fi

# Sprawdź env
if [ -f ".env" ]; then
    set -a; source .env; set +a
fi

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "  ⚠ Brak OPENROUTER_API_KEY — pfix nie zadziała"
    echo "    Ustaw: OPENROUTER_API_KEY=sk-or-v1-... w .env"
    exit 1
fi

# Sprawdź konfiguracje per-package
for pkg_env in backend/.env site/.env dsl/.env.example; do
    if [ -f "$pkg_env" ]; then
        if grep -q "^PFIX_MODEL=" "$pkg_env"; then
            MODEL=$(grep "^PFIX_MODEL=" "$pkg_env" | cut -d= -f2)
            echo "  ✓ $pkg_env: PFIX_MODEL=$MODEL"
        else
            echo "  ⚠ $pkg_env: brak PFIX_MODEL — dodaj wiersz: PFIX_MODEL=openrouter/deepseek/deepseek-v4-pro"
        fi
    fi
done

# Smoke test — sprawdź że CLI odpowiada
if pfix --help >/dev/null 2>&1; then
    echo "  ✓ pfix CLI działa"
else
    echo "  ✗ pfix CLI nie odpowiada"
    exit 1
fi

# Ostrzeżenie o PFIX_AUTO_APPLY
if grep -q "^PFIX_AUTO_APPLY=true" .env site/.env backend/.env dsl/.env 2>/dev/null; then
    echo "  ⚠ PFIX_AUTO_APPLY=true — pfix MODYFIKUJE pliki bez review!"
    echo "    Zalecane na local-only. Dla CI: PFIX_AUTO_APPLY=false"
fi

echo "✓ pfix gotowy. Komenda: pfix run python <script>.py"
