"""
Backward compatibility shim for koru.autonomy.checkpoint module migration.

This module maintains backward compatibility by re-exporting from the new
autonomy.checkpoint submodule. Remove this shim after one release.
"""

from koru.autonomy.checkpoint import *  # noqa: F401, F403
