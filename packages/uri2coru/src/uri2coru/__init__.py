"""Compatibility namespace for :mod:`uri2koru`."""

from __future__ import annotations

import warnings

from uri2koru import (
    KORU_SCHEME as CORU_SCHEME,
)
from uri2koru import (
    ResolvedKoruUri as ResolvedCoruUri,
)
from uri2koru import (
    best_uri,
    nlp2uri,
    run_uri,
    uri_for_block,
    uri_for_cmd,
    uri_to_dsl,
)
from uri2koru import (
    is_koru_uri as is_coru_uri,
)

warnings.warn(
    "uri2coru is deprecated for one compatibility release; import uri2koru instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "CORU_SCHEME",
    "ResolvedCoruUri",
    "best_uri",
    "is_coru_uri",
    "nlp2uri",
    "run_uri",
    "uri_for_block",
    "uri_for_cmd",
    "uri_to_dsl",
]
