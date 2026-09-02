"""Deprecated aliases of the canonical :mod:`uri2koru.uri`."""

from uri2koru.uri import (
    KORU_SCHEME as CORU_SCHEME,
)
from uri2koru.uri import (
    is_koru_uri as is_coru_uri,
)
from uri2koru.uri import (
    parse_koru_uri as parse_coru_uri,
)
from uri2koru.uri import (
    uri_for_block,
    uri_for_cmd,
)

__all__ = [
    "CORU_SCHEME",
    "is_coru_uri",
    "parse_coru_uri",
    "uri_for_block",
    "uri_for_cmd",
]
