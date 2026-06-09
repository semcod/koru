"""Re-export imgl autodiagnostics (logic lives in imgl package)."""

from imgl.autodiag import *  # noqa: F403
from imgl.freshness import (  # noqa: F401
    capture_sidecar_path,
    clear_vql_cache,
    image_freshness,
    mark_capture_fresh,
    max_image_age_seconds,
    sync_vql_cache_with_image,
    verify_capture_updated,
    vql_cache_paths,
)
