"""Backward compatibility shim for koru.autonomy.operator.operator_plugin_wait module migration."""

import sys

from koru.autonomy.operator import operator_plugin_wait as _module_impl  # noqa: F401
from koru.autonomy.operator.operator_plugin_wait import *  # noqa: F401, F403

_current_module = sys.modules[__name__]
for attr in dir(_module_impl):
    if not attr.startswith("__"):
        if not hasattr(_current_module, attr):
            setattr(_current_module, attr, getattr(_module_impl, attr))
