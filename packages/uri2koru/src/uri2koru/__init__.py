"""koru:// URI addressing for dsl2koru commands."""

from uri2koru.decode import uri_to_dsl
from uri2koru.nlp2uri import ResolvedKoruUri, best_uri, nlp2uri
from uri2koru.run import run_uri
from uri2koru.uri import KORU_SCHEME, is_koru_uri, uri_for_block, uri_for_cmd

__all__ = [
    "KORU_SCHEME",
    "ResolvedKoruUri",
    "best_uri",
    "is_koru_uri",
    "nlp2uri",
    "run_uri",
    "uri_for_block",
    "uri_for_cmd",
    "uri_to_dsl",
]
