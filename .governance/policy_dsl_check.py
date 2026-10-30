#!/usr/bin/env python3
"""Dependency-free Policy DSL v1 parser and conformance checker.

This module parses inert data and emits closed Policy IR. It intentionally has
no action executor and no shell integration.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SYMBOL = r"[A-Za-z_][A-Za-z0-9_.:/-]*"
STABLE_ID = r"[A-Z][A-Z0-9_-]*"
SCALAR_TYPES = {"STRING", "INTEGER", "NUMBER", "BOOLEAN", "URL", "PATH"}
SAFE_CANDIDATE_OPCODES = {"REQUIRE", "ALLOW", "REPORT", "VALIDATE", "RECORD"}


class PolicyError(Exception):
    def __init__(self, code: str, message: str, line: int | None = None):
        self.code = code
        self.line = line
        where = f"line {line}: " if line is not None else ""
        super().__init__(f"{code}: {where}{message}")


@dataclass(frozen=True)
class Statement:
    text: str
    line: int


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int


TOKEN_RE = re.compile(
    r"\s*(?:"
    r"(?P<STRING>\"(?:\\[\"\\/bfnrt]|\\u[0-9a-fA-F]{4}|[^\"\\\x00-\x1f])*\")|"
    r"(?P<NUMBER>[0-9]+(?:\.[0-9]+)?)|"
    r"(?P<PLACEHOLDER>\{" + SYMBOL + r"\})|"
    r"(?P<ARROW>->)|"
    r"(?P<OP>!=|<=|>=|=|<|>|\+|-|\*|/|%)|"
    r"(?P<LBRACK>\[)|(?P<RBRACK>\])|"
    r"(?P<LPAREN>\()|(?P<RPAREN>\))|(?P<COMMA>,)|"
    r"(?P<SYMBOL>" + SYMBOL + r")"
    r")"
)


def _strip_comment(line: str) -> str:
    quoted = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\" and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif char == "#" and not quoted:
            return line[:index]
    return line


def statements(source: str) -> list[Statement]:
    if source.startswith("\ufeff"):
        raise PolicyError("POLICY-SYNTAX-001", "UTF-8 BOM is forbidden", 1)
    if "\r" in source or "\t" in source:
        raise PolicyError("POLICY-SYNTAX-001", "CR and tab characters are forbidden")
    for char in source:
        if char != "\n" and (ord(char) < 0x20 or ord(char) == 0x7F):
            raise PolicyError("POLICY-SYNTAX-001", "control character is forbidden")

    result: list[Statement] = []
    buffer: list[str] = []
    start = 1
    square = round_ = 0
    continuation = False

    def emit() -> None:
        nonlocal buffer, continuation
        result.append(Statement(" ".join(buffer), start))
        buffer = []
        continuation = False

    for number, raw in enumerate(source.splitlines(), 1):
        line = _strip_comment(raw).strip()
        if not line:
            if buffer and square == 0 and round_ == 0 and continuation:
                emit()
            continue
        indented = raw[:1].isspace()
        if buffer and square == 0 and round_ == 0 and continuation and not indented:
            emit()
        # Shell syntax outside a quoted literal violates the inert boundary.
        unquoted = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
        if "$(" in unquoted or "`" in unquoted or re.search(r"(^|\s)(?:;|&&|\|\|)(\s|$)", unquoted):
            raise PolicyError("POLICY-SECURITY-001", "shell syntax is not Policy DSL", number)
        if not buffer:
            start = number
        buffer.append(line)
        quoted = escaped = False
        for char in line:
            if escaped:
                escaped = False
            elif char == "\\" and quoted:
                escaped = True
            elif char == '"':
                quoted = not quoted
            elif not quoted:
                square += (char == "[") - (char == "]")
                round_ += (char == "(") - (char == ")")
        if square < 0 or round_ < 0:
            raise PolicyError("POLICY-SYNTAX-001", "unbalanced delimiter", number)
        if square == 0 and round_ == 0:
            if line.endswith(" WHEN") or (continuation and indented):
                continuation = True
            else:
                emit()
    if buffer and square == 0 and round_ == 0:
        emit()
    if buffer or square or round_:
        raise PolicyError("POLICY-SYNTAX-001", "unterminated multiline statement", start)
    return result


def extract_markdown(source: str) -> str:
    """Extract the canonical distributed Policy DSL document from Markdown."""
    blocks: list[str] = []
    current: list[str] | None = None
    for raw in source.splitlines():
        if current is None:
            if raw.strip() == "```dsl":
                current = []
        elif raw.strip() == "```":
            blocks.append("\n".join(current) + "\n")
            current = None
        else:
            current.append(raw)
    if current is not None:
        raise PolicyError("POLICY-SYNTAX-001", "unterminated dsl fence")

    header: str | None = None
    selected: list[str] = []
    binding_start = re.compile(r"^" + SYMBOL + r"\s+(?:=|IN)\s+")
    policy_starts = ("RULE ", "STATE ", "TRANSITION ", "ENV_FILE ", "VARIABLE ", "SECRET ", "ASSERT ")
    for block in blocks:
        significant = [line.strip() for line in block.splitlines() if _strip_comment(line).strip()]
        if not significant:
            continue
        first = _strip_comment(significant[0]).strip()
        if header is None and re.fullmatch(r"DOCUMENT " + SYMBOL, first):
            header = block
            continue
        if header is not None and (first.startswith(policy_starts) or binding_start.match(first)):
            selected.append(block)
    if header is None:
        raise PolicyError("POLICY-SYNTAX-001", "Markdown has no concrete Policy DSL DOCUMENT fence")
    return header + "".join(selected)


def tokenize(text: str, line: int) -> list[Token]:
    result: list[Token] = []
    position = 0
    while position < len(text):
        match = TOKEN_RE.match(text, position)
        if not match:
            raise PolicyError("POLICY-SYNTAX-001", f"unexpected token near {text[position:position + 16]!r}", line)
        kind = match.lastgroup or ""
        value = match.group(kind)
        if kind == "SYMBOL" and value in {"AND", "OR", "NOT", "IN"}:
            kind = "OP"
        result.append(Token(kind, value, line))
        position = match.end()
    result.append(Token("EOF", "", line))
    return result


class ExpressionParser:
    PRECEDENCE = {
        "OR": 10,
        "AND": 20,
        "IN": 30,
        "=": 40,
        "!=": 40,
        "<": 50,
        "<=": 50,
        ">": 50,
        ">=": 50,
        "+": 60,
        "-": 60,
        "*": 70,
        "/": 70,
        "%": 70,
    }

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def take(self, kind: str | None = None, value: str | None = None) -> Token:
        current = self.current
        if kind is not None and current.kind != kind:
            raise PolicyError("POLICY-SYNTAX-001", f"expected {kind}, found {current.value!r}", current.line)
        if value is not None and current.value != value:
            raise PolicyError("POLICY-SYNTAX-001", f"expected {value!r}, found {current.value!r}", current.line)
        self.index += 1
        return current

    def expression(self, minimum: int = 0) -> dict[str, Any]:
        current = self.current
        if current.kind == "OP" and current.value in {"NOT", "-"}:
            self.take()
            left = {"node": "unary", "operator": current.value, "operand": self.expression(80)}
        else:
            left = self.primary()
        while self.current.kind == "OP" and self.current.value in self.PRECEDENCE:
            operator = self.current.value
            precedence = self.PRECEDENCE[operator]
            if precedence < minimum:
                break
            self.take()
            right = self.expression(precedence + 1)
            left = {"node": "binary", "operator": operator, "left": left, "right": right}
        return left

    def primary(self) -> dict[str, Any]:
        current = self.current
        if current.kind == "STRING":
            self.take()
            return {"node": "literal", "value": json.loads(current.value)}
        if current.kind == "NUMBER":
            self.take()
            value: int | float = float(current.value) if "." in current.value else int(current.value)
            return {"node": "literal", "value": value}
        if current.kind == "SYMBOL":
            self.take()
            if current.value in {"TRUE", "FALSE", "true", "false"}:
                return {"node": "literal", "value": current.value in {"TRUE", "true"}}
            return {"node": "symbol", "name": current.value}
        if current.kind == "PLACEHOLDER":
            self.take()
            return {"node": "symbol", "name": current.value}
        if current.kind == "LBRACK":
            return self.collection("RBRACK", "list")
        if current.kind == "LPAREN":
            return self.collection("RPAREN", "group")
        raise PolicyError("POLICY-SYNTAX-001", f"expected expression, found {current.value!r}", current.line)

    def collection(self, closing: str, kind: str) -> dict[str, Any]:
        self.take()
        items: list[dict[str, Any]] = []
        while self.current.kind != closing:
            if self.current.kind == "EOF":
                raise PolicyError("POLICY-SYNTAX-001", "unterminated collection", self.current.line)
            items.append(self.expression())
            if self.current.kind == "COMMA":
                self.take()
            elif self.current.kind != closing:
                # A parenthesized action payload may be a typed sequence.
                if kind != "group":
                    raise PolicyError("POLICY-SYNTAX-001", "list items require commas", self.current.line)
        self.take(closing)
        if kind == "group" and len(items) == 1:
            return items[0]
        node = "list" if kind == "list" else "sequence"
        if node == "sequence" and len(items) < 2:
            raise PolicyError("POLICY-SYNTAX-001", "empty grouping is forbidden", self.current.line)
        return {"node": node, "items": items}

    def complete(self) -> dict[str, Any]:
        value = self.expression()
        self.take("EOF")
        return value

    def sequence(self) -> dict[str, Any] | None:
        items: list[dict[str, Any]] = []
        while self.current.kind != "EOF":
            if self.current.kind == "COMMA":
                self.take()
                continue
            if self.current.kind == "OP" and self.current.value not in {"NOT", "-"}:
                # Domain actions use words such as IN/AND as typed prepositions
                # when no left operand exists; they remain symbols, not text.
                items.append({"node": "symbol", "name": self.take().value})
                continue
            items.append(self.expression())
        if not items:
            return None
        return items[0] if len(items) == 1 else {"node": "sequence", "items": items}


def parse_expression(text: str, line: int) -> dict[str, Any]:
    return ExpressionParser(tokenize(text, line)).complete()


def parse_condition(text: str, line: int) -> dict[str, Any]:
    value = ExpressionParser(tokenize(text, line)).sequence()
    if value is None:
        raise PolicyError("POLICY-SYNTAX-001", "condition must not be empty", line)
    return value


def parse_action(text: str, line: int) -> dict[str, Any]:
    tokens = tokenize(text, line)
    if tokens[0].kind != "SYMBOL" or not re.fullmatch(r"[A-Z][A-Z0-9_]*", tokens[0].value):
        raise PolicyError("POLICY-SYNTAX-001", "action requires an uppercase opcode", line)
    opcode = tokens[0].value
    body = tokens[1:-1]
    depth = 0
    guard_at: int | None = None
    for index, token in enumerate(body):
        if token.kind in {"LPAREN", "LBRACK"}:
            depth += 1
        elif token.kind in {"RPAREN", "RBRACK"}:
            depth -= 1
        elif depth == 0 and token.kind == "SYMBOL" and token.value == "WHEN":
            guard_at = index
            break
    payload_tokens = body if guard_at is None else body[:guard_at]
    guard_tokens = [] if guard_at is None else body[guard_at + 1:]
    payload = ExpressionParser(payload_tokens + [Token("EOF", "", line)]).sequence()
    guard = None
    if guard_at is not None:
        if not guard_tokens:
            raise PolicyError("POLICY-SYNTAX-001", "action WHEN requires a condition", line)
        guard = ExpressionParser(guard_tokens + [Token("EOF", "", line)]).sequence()
    return {"kind": "action", "opcode": opcode, "payload": payload, "guard": guard}


def parse_next(text: str, line: int) -> list[dict[str, Any]]:
    first = re.fullmatch(r"(" + SYMBOL + r")(.*)", text)
    if not first:
        raise PolicyError("POLICY-SYNTAX-001", "NEXT requires a target", line)
    target, tail = first.group(1), first.group(2).strip()
    if not tail:
        return [{"target": target, "condition": None}]
    if tail.startswith("OR "):
        targets = [target] + tail[3:].split(" OR ")
        if any(not re.fullmatch(SYMBOL, value) for value in targets):
            raise PolicyError("POLICY-SYNTAX-001", "invalid NEXT targets", line)
        return [{"target": value, "condition": None} for value in targets]
    if not tail.startswith("WHEN "):
        raise PolicyError("POLICY-SYNTAX-001", "NEXT accepts OR or WHEN after its target", line)
    condition_text = tail[5:]
    fallback: str | None = None
    fallback_match = re.fullmatch(r"(.+) OR (" + SYMBOL + r")", condition_text)
    if fallback_match:
        condition_text, fallback = fallback_match.group(1), fallback_match.group(2)
    result = [{"target": target, "condition": parse_condition(condition_text, line)}]
    if fallback is not None:
        result.append({"target": fallback, "condition": None})
    return result


def _quoted(value: str, line: int) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise PolicyError("POLICY-SYNTAX-001", "invalid JSON string", line) from error
    if not isinstance(parsed, str):
        raise PolicyError("POLICY-SYNTAX-001", "expected string", line)
    return parsed


class PolicyParser:
    def __init__(self, source: str):
        self.items = statements(source)
        self.index = 0

    @property
    def current(self) -> Statement | None:
        return self.items[self.index] if self.index < len(self.items) else None

    def take(self) -> Statement:
        item = self.current
        if item is None:
            raise PolicyError("POLICY-SYNTAX-001", "unexpected end of document")
        self.index += 1
        return item

    def required_match(self, pattern: str, label: str) -> re.Match[str]:
        item = self.take()
        match = re.fullmatch(pattern, item.text)
        if not match:
            raise PolicyError("POLICY-SYNTAX-001", f"expected {label}", item.line)
        return match

    def parse(self) -> dict[str, Any]:
        name = self.required_match(r"DOCUMENT (" + SYMBOL + r")", "DOCUMENT").group(1)
        version = int(self.required_match(r"VERSION ([1-9][0-9]*)", "VERSION").group(1))
        language: str | None = None
        if self.current and self.current.text.startswith("LANGUAGE "):
            language = self.required_match(r"LANGUAGE (" + SYMBOL + r")", "LANGUAGE").group(1)
        mode = self.required_match(r"MODE (STRICT|PROCEDURAL)", "MODE").group(1)
        purpose = policy = None
        if self.current and self.current.text.startswith("PURPOSE "):
            item = self.take()
            match = re.fullmatch(r"PURPOSE (\".*\")", item.text)
            if not match:
                raise PolicyError("POLICY-SYNTAX-001", "invalid PURPOSE", item.line)
            purpose = _quoted(match.group(1), item.line)
        if self.current and self.current.text.startswith("POLICY "):
            item = self.take()
            match = re.fullmatch(r"POLICY (\".*\")", item.text)
            if not match:
                raise PolicyError("POLICY-SYNTAX-001", "invalid POLICY", item.line)
            policy = _quoted(match.group(1), item.line)

        result: dict[str, Any] = {
            "schema": "wellmanifest.policy/ir/v1",
            "dialect": "wellmanifest.policy/v1",
            "language_version": "1",
            "document": {"name": name, "version": version, "language": language, "mode": mode, "purpose": purpose, "policy": policy},
            "environment": [],
            "bindings": [],
            "rules": [],
            "assertions": [],
            "states": [],
            "transitions": [],
        }
        while self.current is not None:
            text = self.current.text
            if text.startswith("ENV_FILE ") or text.startswith("VARIABLE ") or text.startswith("SECRET "):
                result["environment"].append(self.parse_environment())
            elif text.startswith("RULE "):
                result["rules"].append(self.parse_rule())
            elif text.startswith("STATE "):
                item = self.take()
                match = re.fullmatch(r"STATE (" + SYMBOL + r")", item.text)
                if not match:
                    raise PolicyError("POLICY-SYNTAX-001", "invalid STATE", item.line)
                result["states"].append(match.group(1))
            elif text.startswith("TRANSITION "):
                result["transitions"].append(self.parse_transition())
            elif text.startswith("ASSERT "):
                item = self.take()
                result["assertions"].append(parse_expression(item.text[7:], item.line))
            else:
                result["bindings"].append(self.parse_binding())
        self.semantic_checks(result)
        validate_ir(result)
        return result

    def parse_environment(self) -> dict[str, Any]:
        item = self.take()
        match = re.fullmatch(r"ENV_FILE (\".*\") (OPTIONAL|REQUIRED)", item.text)
        if match:
            return {"kind": "env_file", "path": _quoted(match.group(1), item.line), "required": match.group(2) == "REQUIRED"}
        match = re.fullmatch(r"VARIABLE (" + SYMBOL + r") TYPE (\w+) FROM ENV (REQUIRED|DEFAULT(?: .+)?)", item.text)
        if match:
            value_type, tail = match.group(2), match.group(3)
            if value_type not in SCALAR_TYPES:
                raise PolicyError("POLICY-SEMANTIC-001", f"unknown scalar type {value_type}", item.line)
            default = None
            required = tail == "REQUIRED"
            if tail.startswith("DEFAULT "):
                expression = parse_expression(tail[8:], item.line)
                if expression["node"] != "literal":
                    raise PolicyError("POLICY-SEMANTIC-001", "VARIABLE default must be a literal", item.line)
                default = expression["value"]
            return {"kind": "variable", "name": match.group(1), "value_type": value_type, "required": required, "default": default}
        match = re.fullmatch(r"SECRET (" + SYMBOL + r") TYPE (\w+) FROM ENV REQUIRED REDACT", item.text)
        if match:
            if match.group(2) not in SCALAR_TYPES:
                raise PolicyError("POLICY-SEMANTIC-001", f"unknown scalar type {match.group(2)}", item.line)
            return {"kind": "secret", "name": match.group(1), "value_type": match.group(2), "required": True, "redact": True}
        raise PolicyError("POLICY-SYNTAX-001", "invalid environment declaration", item.line)

    def parse_binding(self) -> dict[str, Any]:
        item = self.take()
        match = re.fullmatch(r"(" + SYMBOL + r")\s+(=|IN)\s+(.+)", item.text)
        if not match:
            raise PolicyError("POLICY-SYNTAX-001", "unknown top-level statement", item.line)
        return {"name": match.group(1), "operator": match.group(2), "value": parse_condition(match.group(3), item.line)}

    def parse_transition(self) -> dict[str, Any]:
        item = self.take()
        match = re.fullmatch(r"TRANSITION (" + SYMBOL + r") -> (" + SYMBOL + r")(?: WHEN (.+))?", item.text)
        if not match:
            raise PolicyError("POLICY-SYNTAX-001", "invalid TRANSITION", item.line)
        condition = parse_condition(match.group(3), item.line) if match.group(3) else None
        return {"from": match.group(1), "to": match.group(2), "condition": condition}

    def parse_rule(self) -> dict[str, Any]:
        header = self.take()
        match = re.fullmatch(r"RULE (" + STABLE_ID + r")(?: TYPE (REQUIRED|FORBIDDEN))?", header.text)
        if not match:
            raise PolicyError("POLICY-SYNTAX-001", "invalid RULE header", header.line)
        if not self.current or not self.current.text.startswith("WHEN "):
            raise PolicyError("POLICY-SYNTAX-001", "RULE requires WHEN", header.line)
        condition_item = self.take()
        rule = {
            "id": match.group(1),
            "type": match.group(2) or "REQUIRED",
            "condition": parse_condition(condition_item.text[5:], condition_item.line),
            "actions": [],
            "forbidden": [],
            "assertions": [],
            "next": [],
        }
        while self.current is not None:
            item = self.current
            if item.text.startswith("DO "):
                self.take()
                rule["actions"].append(parse_action(item.text[3:], item.line))
            elif item.text.startswith("FORBID "):
                self.take()
                rule["forbidden"].append(parse_action(item.text[7:], item.line))
            elif item.text.startswith("ASSERT "):
                self.take()
                rule["assertions"].append(parse_expression(item.text[7:], item.line))
            elif item.text.startswith("NEXT "):
                self.take()
                rule["next"] = parse_next(item.text[5:], item.line)
                break
            else:
                break
        return rule

    @staticmethod
    def semantic_checks(ir: dict[str, Any]) -> None:
        rule_ids = [rule["id"] for rule in ir["rules"]]
        if len(rule_ids) != len(set(rule_ids)):
            raise PolicyError("POLICY-SEMANTIC-001", "duplicate rule identifier")
        if len(ir["states"]) != len(set(ir["states"])):
            raise PolicyError("POLICY-SEMANTIC-001", "duplicate state")
        binding_names = [item["name"] for item in ir["bindings"]]
        if len(binding_names) != len(set(binding_names)):
            raise PolicyError("POLICY-SEMANTIC-001", "duplicate binding")


def parse(source: str) -> dict[str, Any]:
    return PolicyParser(source).parse()


def parse_markdown(source: str) -> dict[str, Any]:
    return parse(extract_markdown(source))


def _keys(value: dict[str, Any], allowed: set[str], required: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise PolicyError("POLICY-SEMANTIC-001", f"{label} must be an object")
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown or missing:
        raise PolicyError("POLICY-SEMANTIC-001", f"closed {label}: unknown={sorted(unknown)}, missing={sorted(missing)}")


def validate_expression(value: Any) -> None:
    if not isinstance(value, dict) or "node" not in value:
        raise PolicyError("POLICY-SEMANTIC-001", "expression must be a typed object")
    node = value["node"]
    if node == "literal":
        _keys(value, {"node", "value"}, {"node", "value"}, "literal")
        if isinstance(value["value"], (dict, list)) or value["value"] is None:
            raise PolicyError("POLICY-SEMANTIC-001", "invalid literal")
        if isinstance(value["value"], float) and not math.isfinite(value["value"]):
            raise PolicyError("POLICY-SEMANTIC-001", "literal number must be finite")
    elif node == "symbol":
        _keys(value, {"node", "name"}, {"node", "name"}, "symbol")
        if not isinstance(value["name"], str) or not re.fullmatch(
            r"(?:" + SYMBOL + r"|\{" + SYMBOL + r"\})", value["name"]
        ) or len(value["name"]) > 160:
            raise PolicyError("POLICY-SEMANTIC-001", "invalid symbol")
    elif node == "unary":
        _keys(value, {"node", "operator", "operand"}, {"node", "operator", "operand"}, "unary")
        if value["operator"] not in {"NOT", "-"}:
            raise PolicyError("POLICY-SEMANTIC-001", "invalid unary operator")
        validate_expression(value["operand"])
    elif node == "binary":
        _keys(value, {"node", "operator", "left", "right"}, {"node", "operator", "left", "right"}, "binary")
        if value["operator"] not in ExpressionParser.PRECEDENCE:
            raise PolicyError("POLICY-SEMANTIC-001", "invalid binary operator")
        validate_expression(value["left"])
        validate_expression(value["right"])
    elif node in {"list", "sequence"}:
        _keys(value, {"node", "items"}, {"node", "items"}, node)
        if (
            not isinstance(value["items"], list)
            or len(value["items"]) > 256
            or (node == "sequence" and len(value["items"]) < 2)
        ):
            raise PolicyError("POLICY-SEMANTIC-001", f"invalid {node}")
        for item in value["items"]:
            validate_expression(item)
    else:
        raise PolicyError("POLICY-SEMANTIC-001", f"unknown expression node {node!r}")


def validate_ir(ir: Any) -> None:
    if not isinstance(ir, dict):
        raise PolicyError("POLICY-SEMANTIC-001", "Policy IR must be an object")
    root_keys = {"schema", "dialect", "language_version", "document", "environment", "bindings", "rules", "assertions", "states", "transitions"}
    _keys(ir, root_keys, root_keys, "Policy IR")
    if (ir["schema"], ir["dialect"], ir["language_version"]) != ("wellmanifest.policy/ir/v1", "wellmanifest.policy/v1", "1"):
        raise PolicyError("POLICY-SEMANTIC-001", "incompatible Policy IR identity")
    collection_limits = {
        "environment": 128,
        "bindings": 256,
        "rules": 4096,
        "assertions": 1024,
        "states": 256,
        "transitions": 1024,
    }
    for name, limit in collection_limits.items():
        if not isinstance(ir[name], list) or len(ir[name]) > limit:
            raise PolicyError("POLICY-SEMANTIC-001", f"invalid {name} collection")
    document_keys = {"name", "version", "language", "mode", "purpose", "policy"}
    _keys(ir["document"], document_keys, document_keys, "document")
    document = ir["document"]
    if not isinstance(document["name"], str) or not re.fullmatch(SYMBOL, document["name"]):
        raise PolicyError("POLICY-SEMANTIC-001", "invalid document name")
    if isinstance(document["version"], bool) or not isinstance(document["version"], int) or document["version"] < 1:
        raise PolicyError("POLICY-SEMANTIC-001", "invalid document version")
    if document["language"] is not None and (
        not isinstance(document["language"], str) or not re.fullmatch(SYMBOL, document["language"])
    ):
        raise PolicyError("POLICY-SEMANTIC-001", "invalid document language")
    if document["mode"] not in {"STRICT", "PROCEDURAL"}:
        raise PolicyError("POLICY-SEMANTIC-001", "invalid document mode")
    for name, limit in (("purpose", 1000), ("policy", 320)):
        if document[name] is not None and (not isinstance(document[name], str) or len(document[name]) > limit):
            raise PolicyError("POLICY-SEMANTIC-001", f"invalid document {name}")
    for environment in ir["environment"]:
        if not isinstance(environment, dict):
            raise PolicyError("POLICY-SEMANTIC-001", "environment binding must be an object")
        kind = environment.get("kind")
        if kind == "env_file":
            _keys(environment, {"kind", "path", "required"}, {"kind", "path", "required"}, "env_file")
            if not isinstance(environment["path"], str) or not environment["path"] or len(environment["path"]) > 320:
                raise PolicyError("POLICY-SEMANTIC-001", "invalid ENV_FILE path")
            if not isinstance(environment["required"], bool):
                raise PolicyError("POLICY-SEMANTIC-001", "invalid ENV_FILE requirement")
        elif kind == "variable":
            keys = {"kind", "name", "value_type", "required", "default"}
            _keys(environment, keys, keys, "variable")
            _validate_environment_name_type(environment)
            if not isinstance(environment["required"], bool):
                raise PolicyError("POLICY-SEMANTIC-001", "invalid VARIABLE requirement")
            if environment["default"] is not None:
                validate_expression({"node": "literal", "value": environment["default"]})
        elif kind == "secret":
            keys = {"kind", "name", "value_type", "required", "redact"}
            _keys(environment, keys, keys, "secret")
            _validate_environment_name_type(environment)
            if environment["required"] is not True or environment["redact"] is not True:
                raise PolicyError("POLICY-SEMANTIC-001", "SECRET must be required and redacted")
        else:
            raise PolicyError("POLICY-SEMANTIC-001", "unknown environment binding kind")
    for binding in ir["bindings"]:
        _keys(binding, {"name", "operator", "value"}, {"name", "operator", "value"}, "binding")
        if not isinstance(binding["name"], str) or not re.fullmatch(SYMBOL, binding["name"]):
            raise PolicyError("POLICY-SEMANTIC-001", "invalid binding name")
        if binding["operator"] not in {"=", "IN"}:
            raise PolicyError("POLICY-SEMANTIC-001", "invalid binding operator")
        validate_expression(binding["value"])
    for rule in ir["rules"]:
        rule_keys = {"id", "type", "condition", "actions", "forbidden", "assertions", "next"}
        _keys(rule, rule_keys, rule_keys, "rule")
        if not isinstance(rule["id"], str) or not re.fullmatch(STABLE_ID, rule["id"]):
            raise PolicyError("POLICY-SEMANTIC-001", "invalid rule identifier")
        if rule["type"] not in {"REQUIRED", "FORBIDDEN"}:
            raise PolicyError("POLICY-SEMANTIC-001", "invalid rule type")
        for name, limit in (("actions", 128), ("forbidden", 128), ("assertions", 128), ("next", 32)):
            if not isinstance(rule[name], list) or len(rule[name]) > limit:
                raise PolicyError("POLICY-SEMANTIC-001", f"invalid rule {name}")
        validate_expression(rule["condition"])
        for action in rule["actions"] + rule["forbidden"]:
            _keys(action, {"kind", "opcode", "payload", "guard"}, {"kind", "opcode", "payload", "guard"}, "action")
            if (
                action["kind"] != "action"
                or not isinstance(action["opcode"], str)
                or not re.fullmatch(r"[A-Z][A-Z0-9_]*", action["opcode"])
                or len(action["opcode"]) > 96
            ):
                raise PolicyError("POLICY-SEMANTIC-001", "invalid action identity")
            if action["payload"] is not None:
                validate_expression(action["payload"])
            if action["guard"] is not None:
                validate_expression(action["guard"])
        for assertion in rule["assertions"]:
            validate_expression(assertion)
        for target in rule["next"]:
            _keys(target, {"target", "condition"}, {"target", "condition"}, "next target")
            if not isinstance(target["target"], str) or not re.fullmatch(SYMBOL, target["target"]):
                raise PolicyError("POLICY-SEMANTIC-001", "invalid NEXT target")
            if target["condition"] is not None:
                validate_expression(target["condition"])
    if len({rule["id"] for rule in ir["rules"]}) != len(ir["rules"]):
        raise PolicyError("POLICY-SEMANTIC-001", "duplicate rule identifier")
    for assertion in ir["assertions"]:
        validate_expression(assertion)
    if any(not isinstance(state, str) or not re.fullmatch(SYMBOL, state) for state in ir["states"]):
        raise PolicyError("POLICY-SEMANTIC-001", "invalid state")
    if len(set(ir["states"])) != len(ir["states"]):
        raise PolicyError("POLICY-SEMANTIC-001", "duplicate state")
    for transition in ir["transitions"]:
        _keys(transition, {"from", "to", "condition"}, {"from", "to", "condition"}, "transition")
        if any(not isinstance(transition[name], str) or not re.fullmatch(SYMBOL, transition[name]) for name in ("from", "to")):
            raise PolicyError("POLICY-SEMANTIC-001", "invalid transition state")
        if transition["condition"] is not None:
            validate_expression(transition["condition"])


def _validate_environment_name_type(environment: dict[str, Any]) -> None:
    if not isinstance(environment["name"], str) or not re.fullmatch(SYMBOL, environment["name"]):
        raise PolicyError("POLICY-SEMANTIC-001", "invalid environment name")
    if environment["value_type"] not in SCALAR_TYPES:
        raise PolicyError("POLICY-SEMANTIC-001", "invalid environment scalar type")


def validate_candidate(candidate: Any) -> None:
    validate_ir(candidate)
    for rule in candidate["rules"]:
        for action in rule["actions"] + rule["forbidden"]:
            if action["opcode"] not in SAFE_CANDIDATE_OPCODES:
                raise PolicyError("POLICY-SECURITY-001", f"candidate opcode {action['opcode']} is not proposal-safe")


def schema_is_closed(schema: Any) -> bool:
    if isinstance(schema, dict):
        if schema.get("type") == "object" and schema.get("additionalProperties") is not False:
            return False
        return all(schema_is_closed(value) for value in schema.values())
    if isinstance(schema, list):
        return all(schema_is_closed(value) for value in schema)
    return True


def self_test() -> None:
    valid_path = ROOT / "examples/valid/contributing.policy"
    invalid_path = ROOT / "examples/invalid/shell-injection.policy"
    ir = parse(valid_path.read_text(encoding="utf-8"))
    assert ir["document"]["version"] == 13
    assert ir["language_version"] == "1"
    assert ir["rules"][0]["condition"]["node"] == "binary"
    assert ir["rules"][0]["actions"][0]["payload"]["node"] == "symbol"
    assert "text" not in json.dumps(ir, sort_keys=True)
    schema = json.loads((ROOT / "schemas/policy-ir.schema.json").read_text(encoding="utf-8"))
    assert schema_is_closed(schema)
    grammar = (ROOT / "spec/policy-dsl-candidate.v1.gbnf").read_text(encoding="utf-8")
    for forbidden in ('\"EXECUTE\"', '\"RUN\"', '\"approval_evidence\":', '\"execution_envelope\":', '\"credentials\":'):
        assert forbidden not in grammar
    try:
        parse(invalid_path.read_text(encoding="utf-8"))
    except PolicyError as error:
        assert error.code == "POLICY-SECURITY-001"
    else:
        raise AssertionError("invalid fixture was accepted")
    markdown = "before\n```dsl\n" + valid_path.read_text(encoding="utf-8") + "```\n```bash\nDO RUN evil\n```\n"
    assert parse_markdown(markdown)["document"]["name"] == "CONTRIBUTING"
    print("POLICY-CONFORMANCE-PASS")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_command = subparsers.add_parser("validate")
    validate_command.add_argument("path", type=Path)
    markdown_command = subparsers.add_parser("validate-markdown")
    markdown_command.add_argument("path", type=Path)
    ir_command = subparsers.add_parser("ir")
    ir_command.add_argument("path", type=Path)
    ir_command.add_argument("--check-schema", action="store_true")
    candidate_command = subparsers.add_parser("validate-candidate")
    candidate_command.add_argument("path", type=Path)
    subparsers.add_parser("self-test")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "self-test":
            self_test()
        elif args.command == "validate-candidate":
            validate_candidate(json.loads(args.path.read_text(encoding="utf-8")))
            print("POLICY-CANDIDATE-PASS")
        elif args.command == "validate-markdown":
            parse_markdown(args.path.read_text(encoding="utf-8"))
            print("POLICY-MARKDOWN-PASS")
        else:
            ir = parse(args.path.read_text(encoding="utf-8"))
            if args.command == "ir":
                if args.check_schema:
                    schema = json.loads((ROOT / "schemas/policy-ir.schema.json").read_text(encoding="utf-8"))
                    if not schema_is_closed(schema):
                        raise PolicyError("POLICY-SEMANTIC-001", "Policy IR Schema is not closed")
                    validate_ir(ir)
                print(json.dumps(ir, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print("POLICY-VALIDATION-PASS")
    except (OSError, json.JSONDecodeError, PolicyError, AssertionError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
