#!/usr/bin/env bash
set -e

VENV="venv"
PIP="$VENV/bin/pip"
# Generated/derived artifacts (schema pipeline: Pydantic → JSON Schema → Zod) — kept
# out of the project map since the source of truth is the Pydantic models, not these.
CODE2LLM_GENERATED="--exclude frontend/src/generated/** --exclude shared/schemas/** --exclude backend/generated/** --exclude desktop/src-tauri/gen/schemas/** --exclude testql-testing/scenarios/generated/** --exclude generated/**"
CODE2LLM_EXCLUDES="--exclude .venv-test/** --exclude venv/** --exclude .venv/** --exclude node_modules/** --exclude .code2llm_cache/** --exclude .playwright-browsers/** --exclude build/** --exclude dist/** --exclude .koru/** --exclude .regres/** $CODE2LLM_GENERATED"

# Quick helper: run backend access-code management without executing
# the heavy project generation pipeline below.
if [ "${1:-}" = "access-codes" ]; then
    shift
    exec ./backend/scripts/set_user_access_codes_local.sh "$@"
fi

clear || true

if [ ! -f "$PIP" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV"
fi

$PIP install regix --upgrade --quiet
#$PIP install pyqual --upgrade --quiet
$PIP install prefact --upgrade --quiet
#$PIP install vallm --upgrade --quiet

$PIP install glon --upgrade --quiet
$PIP install goal --upgrade --quiet
$PIP install code2logic --upgrade --quiet

$PIP install code2llm --upgrade --quiet
#$VENV/bin/code2llm ./ -f toon,evolution,code2logic,project-yaml -o ./project --no-chunk
$VENV/bin/code2llm ./ -f all -o ./project --no-chunk $CODE2LLM_EXCLUDES
#$VENV/bin/code2llm report --format all       # → all views

$PIP install redup --upgrade --quiet
$VENV/bin/redup scan . --format toon --output ./project
#$VENV/bin/redup scan . --functions-only -f toon --output ./project
#$VENV/bin/vallm batch ./src --recursive --semantic --model qwen2.5-coder:7b
#$VENV/bin/vallm batch --parallel .
#$VENV/bin/vallm batch . --recursive --format toon --output ./project
$VENV/bin/prefact -a -e "examples/**"

$PIP install doql --upgrade --quiet
$VENV/bin/doql adopt . --format less --output app.doql.less --force

$PIP install sumd --upgrade --quiet
$VENV/bin/sumd .

$PIP install code2docs --upgrade --quiet
$VENV/bin/code2docs ./ --readme-only
$VENV/bin/sumr .
