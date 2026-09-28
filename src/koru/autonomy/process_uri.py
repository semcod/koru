"""Process URI and URN parsing, validation and GBNF grammar generation.

Conforms to RFC 3986 and wellmanifest/dsl / wellmanifest/nl-dsl-llm standards.
Provides:
  - ProcessUri: Canonical URI representation for action://, koru://, taskand:// and urn:
  - ProcessUriRegistry: Self-describing action catalog with JSON-schema parameter validation
  - to_gbnf(): Fast export to GBNF grammar for grammar-guided LLM decoding
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl, urlsplit


class ProcessUriError(ValueError):
    """Raised when a Process URI or URN is invalid."""


@dataclass(frozen=True)
class ProcessUri:
    """Represents a validated Action URI or Resource URN.

    Action URI format:
      scheme://domain/action[?query_params]

    Resource URN format:
      urn:domain:resource_type:resource_id
    """

    raw: str
    scheme: str
    domain: str
    action_or_resource: str
    query_params: dict[str, str] = field(default_factory=dict)
    is_urn: bool = False

    @classmethod
    def parse(cls, uri_string: str) -> ProcessUri:
        """Parse and validate an action URI or resource URN string."""
        s = uri_string.strip()
        if not s:
            raise ProcessUriError("Empty URI string")

        if s.startswith("urn:"):
            parts = s.split(":")
            if len(parts) < 4:
                raise ProcessUriError(f"Malformed URN: '{s}', expected format urn:<domain>:<type>:<id>")
            domain = parts[1]
            resource = ":".join(parts[2:])
            return cls(
                raw=s,
                scheme="urn",
                domain=domain,
                action_or_resource=resource,
                query_params={},
                is_urn=True,
            )

        split = urlsplit(s)
        if not split.scheme:
            raise ProcessUriError(f"Missing URI scheme in '{s}'")
        if not split.netloc:
            raise ProcessUriError(f"Missing domain/host in URI '{s}'")

        domain = split.netloc
        action = split.path.lstrip("/")
        query = dict(parse_qsl(split.query, keep_blank_values=True))

        return cls(
            raw=s,
            scheme=split.scheme,
            domain=domain,
            action_or_resource=action,
            query_params=query,
            is_urn=False,
        )

    @property
    def canonical_action(self) -> str:
        """Return scheme://domain/action without query parameters."""
        if self.is_urn:
            return self.raw
        return f"{self.scheme}://{self.domain}/{self.action_or_resource}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.canonical_action,
            "scheme": self.scheme,
            "domain": self.domain,
            "action": self.action_or_resource,
            "query": self.query_params,
            "is_urn": self.is_urn,
        }


@dataclass
class ActionDefinition:
    """Descriptor of a registered process action."""

    uri_pattern: str
    description: str
    param_schema: dict[str, Any] = field(default_factory=dict)
    handler: Callable[[ProcessUri, dict[str, Any]], Any] | None = None


class ProcessUriRegistry:
    """Catalog of registered process URIs and actions."""

    def __init__(self) -> None:
        self._actions: dict[str, ActionDefinition] = {}

    def register(
        self,
        uri_pattern: str,
        description: str,
        param_schema: dict[str, Any] | None = None,
        handler: Callable[[ProcessUri, dict[str, Any]], Any] | None = None,
    ) -> None:
        """Register an action pattern."""
        self._actions[uri_pattern] = ActionDefinition(
            uri_pattern=uri_pattern,
            description=description,
            param_schema=param_schema or {},
            handler=handler,
        )

    def get(self, canonical_uri: str) -> ActionDefinition | None:
        return self._actions.get(canonical_uri)

    def list_actions(self) -> list[dict[str, Any]]:
        return [
            {
                "uri": k,
                "description": v.description,
                "param_schema": v.param_schema,
            }
            for k, v in self._actions.items()
        ]

    def validate_invocation(self, uri: ProcessUri, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate payload against registered param schema."""
        action_def = self.get(uri.canonical_action)
        if not action_def:
            raise ProcessUriError(f"Action '{uri.canonical_action}' is not registered in ProcessUriRegistry")

        merged = dict(uri.query_params)
        if payload:
            merged.update(payload)

        schema = action_def.param_schema
        required = schema.get("required", [])
        for req in required:
            if req not in merged:
                raise ProcessUriError(f"Missing required parameter '{req}' for action '{uri.canonical_action}'")

        return merged

    def export_gbnf(self) -> str:
        """Export GBNF grammar constraining LLM to only output valid registered URIs and JSON."""
        if not self._actions:
            return 'root ::= [a-z]+ "://" [a-zA-Z0-9_/-]+ (" " "{" [^}]* "}")?\n'

        escaped_uris = ['"' + re.escape(u) + '"' for u in sorted(self._actions.keys())]
        uri_choices = " | ".join(escaped_uris)

        gbnf_rules = [
            r'root ::= action_line ( "\n" action_line )*',
            r'action_line ::= uri ( " " json_payload )?',
            f"uri ::= {uri_choices}",
            r'json_payload ::= "{" [^}\n]* "}"',
        ]
        return "\n".join(gbnf_rules) + "\n"


def parse_uri_json_line(line: str) -> tuple[ProcessUri, dict[str, Any]]:
    """Parse a 'yaml: uri {json}' or 'uri {json}' formatted line."""
    line = line.strip()
    if line.startswith("- "):
        line = line[2:].strip()
    if line.startswith("action:"):
        line = line[len("action:"):].strip()
    if line.startswith("uri:"):
        line = line[len("uri:"):].strip()

    # Split URI and JSON body
    parts = line.split(" ", 1)
    uri_part = parts[0].strip()
    payload: dict[str, Any] = {}

    if len(parts) > 1:
        json_part = parts[1].strip()
        if json_part:
            payload = json.loads(json_part)

    parsed_uri = ProcessUri.parse(uri_part)
    return parsed_uri, payload
