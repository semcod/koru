"""coru:// URI addressing for dsl2coru commands."""

from uri2coru.decode import uri_to_dsl
from uri2coru.nlp2uri import ResolvedCoruUri, best_uri, nlp2uri
from uri2coru.run import run_uri
from uri2coru.uri import CORU_SCHEME, is_coru_uri, uri_for_block, uri_for_cmd

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
