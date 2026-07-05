# STARTER-564: Guard: facade late-binding contract test

model: qwen/qwen3-coder-next

## Prompt

Third facade-extraction regression in one day (coru/cli 19 red, readiness 2 red, autonomous_cycle slim broke 20 late-bound names and wedged the gate red for ~2h). Add a contract test that: (1) collects every _cycle_mod./_runner_mod./_readiness_facade.-style late-bound attribute reference across src, (2) asserts the facade exposes each name, (3) collects monkeypatch targets on facades from tests and asserts call sites resolve through the facade. Template: tests/test_tillm_registry_contract.py. This converts the recurring incident class into a red test at author time.

---
Deliverable: a concrete, ordered action plan with exact shell commands and file paths where applicable, short enough to execute directly. State assumptions explicitly; do not pad.

## Answer

**Assumptions**  
1. Project uses `src/` as source root, `tests/` as test root.  
2. Late-bound facade attributes follow pattern: `_cycle_mod`, `_runner_mod`, `_readiness_facade`, etc. (i.e., underscore-prefixed, `_mod`/`_facade` suffix).  
3. Facades are defined in `src/tillm/registry/facades.py` (adjust if different; default assumed).  
4. Tests use `pytest`; monkeypatches are via `monkeypatch` fixture.  
5. `coru/cli 19`, `readiness`, `autonomous_cycle` are concrete modules in `src/`.  

---

### Action Plan (≤15 min execution)

#### 1. Create contract test template  
```bash
mkdir -p tests
cat > tests/test_tillm_registry_contract.py << 'EOF'
"""Contract test: late-bound facade attributes must be exposed and resolvable."""
import ast
import os
from pathlib import Path
from types import ModuleType

import pytest

SRC_ROOT = Path("src")
FACADE_PATH = SRC_ROOT / "tillm" / "registry" / "facades.py"
FACADE_MODULE_NAME = "tillm.registry.facades"


def _collect_late_bound_refs() -> set[str]:
    """Find all `_cycle_mod`, `_runner_mod`, `_readiness_facade`-style refs in src/."""
    pattern = "_*_(mod|facade)$"
    refs = set()
    for path in SRC_ROOT.rglob("*.py"):
        if "test" in str(path) or "__pycache__" in str(path):
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.attr.startswith("_"):
                    if node.attr.endswith("_mod") or node.attr.endswith("_facade"):
                        refs.add(node.attr)
    return refs


def _collect_monkeypatch_targets() -> set[tuple[str, str]]:
    """Find all `monkeypatch.setattr(facade, name, ...)` in tests/."""
    targets = set()
    for path in Path("tests").rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setattr"
                and len(node.args) >= 2
            ):
                # Expect: monkeypatch.setattr(facade_module, "attr_name", ...)
                if isinstance(node.args[0], ast.Attribute):
                    mod_name = ast.unparse(node.args[0].value)
                    attr_name = node.args[0].attr
                elif isinstance(node.args[0], ast.Name):
                    mod_name = node.args[0].id
                    attr_name = node.args[1].value if isinstance(node.args[1], ast.Constant) else None
                else:
                    continue
                if mod_name == FACADE_MODULE_NAME and attr_name:
                    targets.add((mod_name, attr_name))
    return targets


def _load_facade_module() -> ModuleType:
    import importlib
    return importlib.import_module(FACADE_MODULE_NAME)


def test_facade_exposes_all_late_bound_refs():
    """Assert facade module exposes every late-bound attribute found in src/."""
    refs = _collect_late_bound_refs()
    facade = _load_facade_module()
    missing = [r for r in refs if not hasattr(facade, r)]
    assert not missing, f"Facade missing late-bound attrs: {missing}"


def test_monkeypatch_targets_resolve_through_facade():
    """Assert every monkeypatch target in tests/ resolves via the facade."""
    targets = _collect_monkeypatch_targets()
    facade = _load_facade_module()
    unresolved = []
    for mod_name, attr in targets:
        if not hasattr(facade, attr):
            unresolved.append(f"{mod_name}.{attr}")
    assert not unresolved, f"Monkeypatch targets not exposed by facade: {unresolved}"
EOF
```


#### 2. Run test to confirm it fails (red) on current codebase  
```bash
pytest tests/test_tillm_registry_contract.py -v
# Expected: FAIL (missing late-bound attrs)
```


#### 3. Fix the facade (if needed)  
- Edit `src/tillm/registry/facades.py` to expose all missing attributes (e.g., `from coru.cli import _cycle_mod as _cycle_mod`).  
- Re-run test until green:  
```bash
pytest tests/test_tillm_registry_contract.py -v
```


#### 4. Commit test + fix  
```bash
git add tests/test_tillm_registry_contract.py src/tillm/registry/facades.py
git commit -m "test: add contract test for late-bound facade attributes"
```
