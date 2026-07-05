# STARTER-551: R-F1.3: Unify drive pipelines (autonomous_cycle_drive_retry vs koruide/drive_orchestrator)

model: qwen/qwen3-coder-next

## Prompt

Two parallel fallback-chain mechanisms (~920 and ~965 lines) duplicate strategy logic. Extract a shared strategy registry; one pipeline consumed by both autonomy and the daemon.

---
Deliverable: a concrete, ordered action plan with exact shell commands and file paths where applicable, short enough to execute directly. State assumptions explicitly; do not pad.

## Answer

**Assumptions**  
1. Codebase is in a Git repo with standard layout: `src/`, `lib/`, or similar.  
2. Fallback-chain logic resides in two files: `src/autonomy/fallback_chain.py` (~920 lines) and `src/daemon/fallback_chain.py` (~965 lines).  
3. Strategy logic is encapsulated in functions/classes (e.g., `StrategyA`, `StrategyB`) used by both chains.  
4. Python project using `pyproject.toml` or `setup.py`; no external registry framework.  
5. Shared registry will be a singleton `StrategyRegistry` with registration + lookup.

---

### Action Plan (≤15 min)

1. **Create shared registry module**  
   ```bash
   mkdir -p src/common/strategy
   touch src/common/strategy/__init__.py
   ```

2. **Implement `StrategyRegistry`**  
   ```bash
   cat > src/common/strategy/registry.py << 'EOF'
   class StrategyRegistry:
       _instance = None
       _strategies = {}

       def __new__(cls):
           if cls._instance is None:
               cls._instance = super().__new__(cls)
           return cls._instance

       @classmethod
       def register(cls, name: str, strategy_class):
           cls._strategies[name] = strategy_class

       @classmethod
       def get(cls, name: str):
           return cls._strategies.get(name)

       @classmethod
       def list(cls):
           return list(cls._strategies.keys())
   EOF
   ```

3. **Extract strategy classes**  
   - Identify strategy classes in both files (e.g., `FallbackStrategyA`, `FallbackStrategyB`).  
   - Move them to `src/common/strategy/strategies.py`:  
   ```bash
   # Example: extract class definitions (adjust names/types)
   grep -E "^class Fallback.*Strategy" src/autonomy/fallback_chain.py src/daemon/fallback_chain.py | cut -d: -f2 | sort -u | while read line; do
     # Extract class + its body (naive: grab until next class or EOF)
     # Use sed to extract from `class ...` to next `^class ` or end
     echo "TODO: Manually extract strategy classes into strategies.py"
   done
   ```
   **→ Manual step**: Copy-paste strategy classes into `src/common/strategy/strategies.py`, then register them:  
   ```bash
   cat >> src/common/strategy/strategies.py << 'EOF'

   # Register strategies on module load
   from .registry import StrategyRegistry
   StrategyRegistry.register("alpha", FallbackStrategyA)
   StrategyRegistry.register("beta", FallbackStrategyB)
   # ... add others
   EOF
   ```

4. **Refactor autonomy pipeline**  
   ```bash
   # Backup original
   cp src/autonomy/fallback_chain.py src/autonomy/fallback_chain.py.bak

   # Replace strategy instantiations with registry lookups
   sed -i 's/from.*fallback_chain import FallbackStrategyA/from common.strategy import StrategyRegistry/' src/autonomy/fallback_chain.py
   sed -i 's/FallbackStrategyA()/StrategyRegistry.get("alpha")()/' src/autonomy/fallback_chain.py
   # Repeat for other strategies (adjust names)
   ```

5. **Refactor daemon pipeline**  
   ```bash
   cp src/daemon/fallback_chain.py src/daemon/fallback_chain.py.bak
   sed -i 's/from.*fallback_chain import FallbackStrategyA/from common.strategy import StrategyRegistry/' src/daemon/fallback_chain.py
   sed -i 's/FallbackStrategyA()/StrategyRegistry.get("alpha")()/' src/daemon/fallback_chain.py
   ```

6. **Verify imports & run tests**  
   ```bash
   python -c "from src.common.strategy import StrategyRegistry; print(StrategyRegistry.list())"
   pytest src/autonomy/test_fallback.py src/daemon/test_fallback.py -v  # or your test command
   ```

7. **Delete duplicated strategy code**  
   ```bash
   # Remove strategy classes from both original files (keep only pipeline logic)
   # Example: delete lines 120–250 in autonomy/fallback_chain.py (adjust ranges)
   sed -i '120,250d' src/autonomy/fallback_chain.py
   sed -i '130,270d' src/daemon/fallback_chain.py
   ```

8. **Update `__init__.py` for public API**  
   ```bash
   echo "from .registry import StrategyRegistry" >> src/common/strategy/__init__.py
   echo "from . import strategies" >> src/common/strategy/__init__.py
   ```

**Done.** Both autonomy and daemon now consume the same registry; strategy logic is centralized.
