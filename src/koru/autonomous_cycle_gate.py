"""
Backward compatibility shim for koru.autonomy.cycle.cycle_gate module migration.

This module maintains backward compatibility by re-exporting from the new
autonomy.cycle.cycle_gate submodule. Remove this shim after one release.
"""

# Re-export everything from the new module location
from koru.autonomy.cycle.cycle_gate import *  # noqa: F401, F403

# Also expose the module for test monkeypatching and private function access
from koru.autonomy.cycle import cycle_gate as _module_impl  # noqa: F401
import sys
_current_module = sys.modules[__name__]
for attr in dir(_module_impl):
    if not attr.startswith("__"):
        if not hasattr(_current_module, attr):
            setattr(_current_module, attr, getattr(_module_impl, attr))
