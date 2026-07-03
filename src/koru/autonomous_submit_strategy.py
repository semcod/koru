"""
Backward compatibility shim for koru.autonomy.drive.submit_strategy module migration.

This module maintains backward compatibility by re-exporting from the new
autonomy.drive submodule. Remove this shim after one release.
"""

from koru.autonomy.drive.submit_strategy import *  # noqa: F401, F403
