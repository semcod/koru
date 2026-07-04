"""
Backward compatibility shim for koru.autonomy.cycle.cycle_skip_conditions module migration.

This module maintains backward compatibility by re-exporting from the new
autonomy.cycle.cycle_skip_conditions submodule. Remove this shim after one release.
"""

# Re-export everything from the new module location
import sys

# Also expose the module for test monkeypatching and private function access
from koru.autonomy.cycle import cycle_skip_conditions as _module_impl  # noqa: F401
from koru.autonomy.cycle.cycle_skip_conditions import *  # noqa: F401, F403

_current_module = sys.modules[__name__]
for attr in dir(_module_impl):
    if not attr.startswith("__"):
        if not hasattr(_current_module, attr):
            setattr(_current_module, attr, getattr(_module_impl, attr))
