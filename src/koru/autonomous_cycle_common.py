"""
Backward compatibility alias for koru.autonomy.cycle.cycle_common.

The old copy-attributes shim desynced monkeypatches: patching
``koru.autonomous_cycle_common.<name>`` mutated the shim's copy while the implementation
kept calling its own module globals. Registering the implementation module
under the legacy name keeps both import paths one and the same module
object, so patches land regardless of which path is used.
Remove after one release once callers import koru.autonomy.cycle.cycle_common.
"""

import sys

from koru.autonomy.cycle import cycle_common as _module_impl

sys.modules[__name__] = _module_impl
