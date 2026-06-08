"""OpenRouter configuration with app name from pyproject.toml and Ollama fallback."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path


def load_project_metadata() -> tuple[str, str]:
    """Read name and version from pyproject.toml in the project root."""
    # Try to find pyproject.toml by going up from current directory
    current_path = Path.cwd()
    while current_path.parent != current_path:  # Stop at filesystem root
        pyproject_path = current_path / "pyproject.toml"
        if pyproject_path.exists():
            break
        current_path = current_path.parent
    else:
        return "unknown-app", "0.0.0"

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    # Try Poetry first
    name = data.get("tool", {}).get("poetry", {}).get("name")
    version = data.get("tool", {}).get("poetry", {}).get("version", "0.0.0")

    # Fallback to setuptools/project
    if not name:
        name = data.get("project", {}).get("name", "unknown-app")
        version = data.get("project", {}).get("version", "0.0.0")

    return name or "unknown-app", version or "0.0.0"


def setup_openrouter_env() -> None:
    """
    Set OR_SITE_URL and OR_APP_NAME environment variables if not already set,
    using values from pyproject.toml.
    """
    if os.getenv("OR_SITE_URL") is None:
        os.environ["OR_SITE_URL"] = "https://koru.semcode.pl"

    if os.getenv("OR_APP_NAME") is None:
        name, version = load_project_metadata()
        os.environ["OR_APP_NAME"] = f"{name} ({version})"


def get_openrouter_headers() -> dict[str, str]:
    """Get OpenRouter headers with app identification."""
    setup_openrouter_env()
    
    headers = {}
    if site_url := os.getenv("OR_SITE_URL"):
        headers["OR_SITE_URL"] = site_url
    if app_name := os.getenv("OR_APP_NAME"):
        headers["OR_APP_NAME"] = app_name
    
    return headers


def get_fallback_model() -> str:
    """Get fallback model (Ollama) when OpenRouter is unavailable."""
    return os.getenv("OLLAMA_LLM_MODEL", "gemma2:9b")


def get_ollama_base_url() -> str:
    """Get Ollama base URL."""
    return os.getenv("OLLAMA_API_URL", "http://localhost:11434")


def should_use_ollama_fallback() -> bool:
    """Check if Ollama fallback should be used."""
    return bool(os.getenv("OLLAMA_API_URL") and os.getenv("OLLAMA_LLM_MODEL"))
