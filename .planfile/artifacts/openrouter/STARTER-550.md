# STARTER-550: R-F1.2: Replace os.environ writes in autonomy with explicit AutonomousContext

model: qwen/qwen3-coder-next

## Prompt

24 os.environ writes in autonomous modules (KORU_TILLM_CLIENT, lane exports, socket) leak process-global state. Introduce an AutonomousContext passed down the call chain; set env only at subprocess boundaries (env= argument).

---
Deliverable: a concrete, ordered action plan with exact shell commands and file paths where applicable, short enough to execute directly. State assumptions explicitly; do not pad.

## Answer

**Assumptions**  
1. Codebase uses `os.environ` directly in modules: `KORU_TILLM_CLIENT`, `lane_exports`, `socket` (likely `socket.py` or custom wrapper).  
2. Subprocesses are spawned via `subprocess.Popen`/`run`; `env=` argument is *not* currently used.  
3. No existing `AutonomousContext` class; must be created.  
4. All modules are Python 3.8+; `contextvars` available.  
5. No external dependencies beyond stdlib.

---

### Action Plan

#### 1. Create `AutonomousContext` class  
**File**: `src/autonomous_context.py`  
```bash
mkdir -p src && cat > src/autonomous_context.py << 'EOF'
from contextvars import ContextVar
from typing import Optional, Dict, Any

class AutonomousContext:
    _instance: ContextVar[Optional['AutonomousContext']] = ContextVar('autonomous_context', default=None)

    def __init__(self, env_overrides: Optional[Dict[str, str]] = None):
        self.env_overrides = env_overrides or {}

    @classmethod
    def get_current(cls) -> 'AutonomousContext':
        ctx = cls._instance.get()
        if ctx is None:
            raise RuntimeError("AutonomousContext not set in current context")
        return ctx

    @classmethod
    def set_current(cls, ctx: 'AutonomousContext') -> None:
        cls._instance.set(ctx)

    def apply_to_env(self, env: Dict[str, str]) -> Dict[str, str]:
        """Return a copy of `env` with overrides applied."""
        result = env.copy()
        result.update(self.env_overrides)
        return result
EOF
```

#### 2. Replace direct `os.environ` usage in modules  
**Pattern**: Replace `os.environ[...]` / `os.environ.get(...)` with `AutonomousContext.get_current().env_overrides.get(...)` or `os.environ[...]` *only* if fallback to process env is acceptable (rare). Prefer explicit context propagation.

**Files to modify** (example edits):

- **`src/koru_tillm_client.py`**  
```bash
sed -i 's/^import os$/import os\nfrom .autonomous_context import AutonomousContext/' src/koru_tillm_client.py
sed -i 's/os\.environ\[\([^]]*\)\]/AutonomousContext.get_current().env_overrides.get(\1, os.environ.get(\1))/g' src/koru_tillm_client.py
sed -i 's/os\.environ\.get(\([^,]*\), \([^)]*\))/AutonomousContext.get_current().env_overrides.get(\1, \2)/g' src/koru_tillm_client.py
```
> *Note*: Manual review required after `sed` — ensure no false positives (e.g., `os.environ.setdefault`). Prefer manual edits for correctness.

- **`src/lanes/exports.py`** (assuming `lanes/exports.py`)  
```bash
mkdir -p src/lanes && sed -i 's/^import os$/import os\nfrom ..autonomous_context import AutonomousContext/' src/lanes/exports.py
# Apply same pattern as above
```

- **`src/autonomous_socket.py`** (rename if `socket.py` is stdlib shadow)  
```bash
cat > src/autonomous_socket.py << 'EOF'
import os
import socket as _socket
from .autonomous_context import AutonomousContext

class Socket(_socket.socket):
    def connect(self, *args, **kwargs):
        # Example: inject env-based socket options if needed
        ctx = AutonomousContext.get_current()
        # ... apply context-specific behavior ...
        return super().connect(*args, **kwargs)
EOF
```
> Replace all `import socket` → `from .autonomous_socket import Socket` in dependent modules.

#### 3. Introduce `AutonomousContext` at subprocess boundaries  
**File**: `src/subprocess_utils.py`  
```bash
cat > src/subprocess_utils.py << 'EOF'
import os
import subprocess
from .autonomous_context import AutonomousContext

def run_with_context(cmd, **kwargs):
    ctx = AutonomousContext.get_current()
    env = kwargs.pop('env', os.environ.copy())
    env = ctx.apply_to_env(env)
    return subprocess.run(cmd, env=env, **kwargs)

def Popen_with_context(cmd, **kwargs):
    ctx = AutonomousContext.get_current()
    env = kwargs.pop('env', os.environ.copy())
    env = ctx.apply_to_env(env)
    return subprocess.Popen(cmd, env=env, **kwargs)
EOF
```

#### 4. Update entry points to set `AutonomousContext`  
**File**: `src/main.py` (or CLI entrypoint)  
```bash
sed -i '1i from .autonomous_context import AutonomousContext' src/main.py
sed -i '/^def main\(\):/a\    AutonomousContext.set_current(AutonomousContext(env_overrides={"MY_VAR": "value"}))' src/main.py
```
> Replace `{"MY_VAR": "value"}` with actual initial env overrides.

#### 5. Verify no remaining `os.environ` leaks  
```bash
grep -rn 'os\.environ\[' src/ --include='*.py' | grep -v 'autonomous_context.py' | grep -v 'subprocess_utils.py'
grep -rn 'os\.environ\.setdefault\|os\.environ\.update' src/ --include='*.py'
```
→ Manually fix any hits.

#### 6. Run tests  
```bash
python -m pytest tests/ -v
```

---

**Total files created/modified**:  
- Created: `src/autonomous_context.py`, `src/subprocess_utils.py`, `src/autonomous_socket.py`  
- Modified: `src/koru_tillm_client.py`, `src/lanes/exports.py`, `src/main.py`  
- Estimated time: ≤ 2 hours (excluding test fixes).
