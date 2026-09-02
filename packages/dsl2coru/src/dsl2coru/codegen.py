"""Compatibility aliases for canonical schema model generation."""

from dsl2koru import codegen as _canonical
from dsl2koru.codegen import build_model_registry, main, render_models_module, validate_payload


def __getattr__(name: str):
    return getattr(_canonical, name)


__all__ = ["build_model_registry", "main", "render_models_module", "validate_payload"]


if __name__ == "__main__":
    raise SystemExit(main())
