#!/usr/bin/env bash
set -e
clear

# Canonical venv for koru autonomous + README is .venv (not venv).
if [ -x ".venv/bin/pip" ]; then
    VENV=".venv"
elif [ -x "venv/bin/pip" ]; then
    VENV="venv"
else
    VENV=".venv"
fi
PIP="$VENV/bin/pip"

if [ ! -f "$PIP" ]; then
    echo "Creating virtual environment at $VENV..."
    python3 -m venv "$VENV"
fi
echo "Using Python env: $VENV"

$PIP install -e ".[dev]"
if [ -d "../nlp2uri" ]; then
    echo "Installing sibling nlp2uri (editable)..."
    $PIP install -e "../nlp2uri[dev,envmap]" --quiet
fi
if [ -d "../env2llm" ]; then
    echo "Installing sibling env2llm (editable)..."
    $PIP install -e "../env2llm[mqtt]" --quiet
fi
if [ -d "../../oqlos/testql" ]; then
    echo "Installing sibling testql (editable)..."
    $PIP install -e "../../oqlos/testql" --quiet
else
    $PIP install "testql>=1.2.55" --quiet
fi
if [ -d "../../oqlos/nlp2oql" ]; then
    echo "Installing sibling nlp2oql (editable)..."
    $PIP install -e "../../oqlos/nlp2oql[full]" --quiet
else
    $PIP install "nlp2oql[browser]>=0.2.0" --quiet
fi
if [ -d "../../wronai/curllm" ]; then
    echo "Installing sibling curllm MCP stack..."
    $PIP install -e "../../wronai/curllm[mcp]" --quiet
else
    $PIP install "curllm[mcp]>=1.0.0" --quiet
fi
if [ -d "../../wronai/nlp2cmd" ]; then
    echo "Installing sibling nlp2cmd MCP stack..."
    PIP="$PIP" PYTHON="$VENV/bin/python" bash "../../wronai/nlp2cmd/scripts/install_mcp_stack.sh"
fi
$PIP install "playwright>=1.40,<2.0" --quiet
if [ -x "$VENV/bin/playwright" ]; then
    echo "Ensuring Playwright Chromium..."
    $VENV/bin/playwright install chromium --quiet 2>/dev/null || $VENV/bin/playwright install chromium
fi
echo ""
echo "=== Browser automation stack (koru) ==="
if [ -x "$VENV/bin/nlp2oql" ]; then
    $VENV/bin/nlp2oql doctor || true
fi
$VENV/bin/python - <<'PY' || true
from pathlib import Path
checks = []
try:
    import testql
    checks.append(f"testql: ok ({getattr(testql, '__version__', '?')})")
except ImportError as e:
    checks.append(f"testql: missing ({e})")
try:
    import nlp2oql
    checks.append(f"nlp2oql: ok ({nlp2oql.__version__})")
except ImportError as e:
    checks.append(f"nlp2oql: missing ({e})")
try:
    import curllm_mcp
    checks.append("curllm_mcp: ok")
except ImportError as e:
    checks.append(f"curllm_mcp: missing ({e})")
try:
    import nlp2cmd
    checks.append("nlp2cmd: ok")
except ImportError:
    import shutil
    checks.append(f"nlp2cmd: {'ok' if shutil.which('nlp2cmd') else 'missing'}")
try:
    from koruapi.nlp2oql_bridge import nlp2oql_available
    checks.append(f"koru_nlp2oql_bridge: {'ok' if nlp2oql_available() else 'missing'}")
except Exception as e:
    checks.append(f"koru_nlp2oql_bridge: error ({e})")
for line in checks:
    print(f"  {line}")
PY
echo ""
$PIP install regix --upgrade --quiet
#$PIP install pyqual --upgrade --quiet
$PIP install prefact --upgrade --quiet
$PIP install vallm --upgrade --quiet
$PIP install redup --upgrade --quiet
$PIP install glon --upgrade --quiet
$PIP install code2logic --upgrade --quiet
$PIP install code2llm --upgrade --quiet
#$VENV/bin/code2llm ./ -f toon,evolution,code2logic,project-yaml -o ./project --no-chunk
$VENV/bin/code2llm ./ -f all -o ./project --no-chunk --exclude '*.md'
#$VENV/bin/code2llm report --format all       # → all views

#$PIP install code2docs --upgrade --quiet
#$VENV/bin/code2docs ./ --readme-only
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
$VENV/bin/sumr .


if [ -d "../goal/goal" ] && [ -f "../goal/pyproject.toml" ]; then
    pip install -e ../goal
    $PIP install -e ../goal --quiet
else
    pip install -U goal
    $PIP install goal --upgrade --quiet
fi
#$VENV/bin/goal -a

if [ -x "./tree.sh" ]; then
    bash ./tree.sh
elif command -v tree >/dev/null 2>&1; then
    tree -L 2
else
    echo "Skipping tree snapshot: ./tree.sh not found and 'tree' is not installed."
fi