"""
Backward compatibility alias for koru.autonomy.cycle.cycle_skip_conditions.

The old copy-attributes shim desynced monkeypatches: patching
``koru.autonomous_cycle_skip_conditions.<name>`` mutated the shim's copy while the implementation
kept calling its own module globals. Registering the implementation module
under the legacy name keeps both import paths one and the same module
object, so patches land regardless of which path is used.
Remove after one release once callers import koru.autonomy.cycle.cycle_skip_conditions.
"""

import sys

from koru.autonomy.cycle import cycle_skip_conditions as _module_impl

sys.modules[__name__] = _module_impl
