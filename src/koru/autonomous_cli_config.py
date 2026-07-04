"""
Backward compatibility alias for koru.autonomy.configuration.config_cli_config.

The old copy-attributes shim desynced monkeypatches: patching
``koru.autonomous_cli_config.<name>`` mutated the shim's copy while the implementation
kept calling its own module globals. Registering the implementation module
under the legacy name keeps both import paths one and the same module
object, so patches land regardless of which path is used.
Remove after one release once callers import koru.autonomy.configuration.config_cli_config.
"""

import sys

from koru.autonomy.configuration import config_cli_config as _module_impl

sys.modules[__name__] = _module_impl
