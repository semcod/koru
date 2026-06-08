"""Schema → Pydantic models (Phase 5)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Literal

from dsl2coru.schema_registry import _load_schemas, all_verbs, normalize_verb


def _python_type(prop: dict[str, Any], *, required: bool) -> tuple[Any, Any]:
    if "const" in prop:
        const = prop["const"]
        return Literal[const], const  # type: ignore[valid-type]
    json_type = prop.get("type", "string")
    if json_type == "string":
        default = ... if required else prop.get("default", None)
        return str, default
    if json_type == "integer":
        default = ... if required else prop.get("default", 0)
        return int, default
    if json_type == "boolean":
        default = ... if required else prop.get("default", False)
        return bool, default
    default = ... if required else None
    return Any, default


def build_model_registry() -> dict[str, type]:
    from pydantic import create_model

    registry: dict[str, type] = {}
    for verb, schema in _load_schemas().items():
        required = set(schema.get("required", []))
        fields: dict[str, tuple[Any, Any]] = {}
        for name, prop in schema.get("properties", {}).items():
            fields[name] = _python_type(prop, required=name in required)
        class_name = re.sub(r"[^A-Za-z0-9]", "", verb.title()) + "Command"
        registry[verb] = create_model(class_name, **fields)  # type: ignore[call-overload]
    return registry


def validate_payload(payload: dict[str, Any]) -> Any:
    verb = normalize_verb(str(payload.get("verb", "")))
    models = build_model_registry()
    model = models.get(verb)
    if model is None:
        raise KeyError(f"unknown verb model: {verb}")
    return model.model_validate(payload)


def render_models_module() -> str:
    lines = [
        '"""Auto-generated Pydantic command models — do not edit by hand."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Literal",
        "",
        "from pydantic import BaseModel",
        "",
    ]
    for verb in all_verbs():
        schema = _load_schemas()[verb]
        class_name = re.sub(r"[^A-Za-z0-9]", "", verb.title()) + "Command"
        lines.append(f"class {class_name}(BaseModel):")
        required = set(schema.get("required", []))
        for name, prop in schema.get("properties", {}).items():
            if "const" in prop:
                lines.append(f"    {name}: Literal[{prop['const']!r}] = {prop['const']!r}")
            elif prop.get("type") == "boolean":
                default = prop.get("default", False)
                lines.append(f"    {name}: bool = {default!r}")
            elif name in required:
                lines.append(f"    {name}: str")
            else:
                default = prop.get("default")
                if default is not None:
                    lines.append(f"    {name}: str = {default!r}")
                else:
                    lines.append(f"    {name}: str | None = None")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m dsl2coru.codegen")
    parser.add_argument("--write", type=Path, help="Write models.py to this path")
    parser.add_argument("--check", action="store_true", help="Validate all schemas build models")
    args = parser.parse_args(argv)

    if args.check:
        registry = build_model_registry()
        for verb, schema in _load_schemas().items():
            sample: dict[str, Any] = {"verb": verb}
            for name, prop in schema.get("properties", {}).items():
                if name == "verb":
                    continue
                if "const" in prop:
                    sample[name] = prop["const"]
                elif prop.get("type") == "boolean":
                    sample[name] = prop.get("default", False)
                elif name in schema.get("required", []):
                    sample[name] = "test"
            registry[verb].model_validate(sample)
        print(f"OK: {len(registry)} models")
        return 0

    source = render_models_module()
    if args.write:
        args.write.write_text(source, encoding="utf-8")
        print(f"wrote {args.write}")
    else:
        print(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
