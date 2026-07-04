"""
Backward compatibility alias for koru.autonomy.operator.operator_processes.

The old shim copied attributes and re-implemented two wrappers so that test
monkeypatches through the legacy path would work — duplicating impl logic.
Registering the implementation module under the legacy name keeps both
import paths one and the same module object, so patches land everywhere and
the duplicated wrappers are unnecessary.
Remove after one release once callers import koru.autonomy.operator.operator_processes.
"""

import sys

from koru.autonomy.operator import operator_processes as _module_impl

sys.modules[__name__] = _module_impl
