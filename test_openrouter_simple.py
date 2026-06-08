#!/usr/bin/env python3
"""Simple test to verify OpenRouter configuration modules work independently."""

import os
import sys
import tomllib
from pathlib import Path

def test_project_metadata():
    """Test loading project metadata from pyproject.toml."""
    print("=== Testing Project Metadata Loading ===")
    
    # Test nlp2koru
    nlp2koru_path = Path(__file__).parent / "packages" / "nlp2koru" / "pyproject.toml"
    if nlp2koru_path.exists():
        with nlp2koru_path.open("rb") as f:
            data = tomllib.load(f)
        
        name = data.get("project", {}).get("name", "unknown-app")
        version = data.get("project", {}).get("version", "0.0.0")
        print(f"✓ nlp2koru metadata: {name} v{version}")
    else:
        print("✗ nlp2koru pyproject.toml not found")
        return False
    
    # Test nlp2coru
    nlp2coru_path = Path(__file__).parent / "packages" / "nlp2coru" / "pyproject.toml"
    if nlp2coru_path.exists():
        with nlp2coru_path.open("rb") as f:
            data = tomllib.load(f)
        
        name = data.get("project", {}).get("name", "unknown-app")
        version = data.get("project", {}).get("version", "0.0.0")
        print(f"✓ nlp2coru metadata: {name} v{version}")
    else:
        print("✗ nlp2coru pyproject.toml not found")
        return False
    
    return True

def test_openrouter_config_module():
    """Test the OpenRouter configuration module directly."""
    print("\n=== Testing OpenRouter Config Module ===")
    
    config_path = Path(__file__).parent / "packages" / "nlp2koru" / "src" / "nlp2koru" / "openrouter_config.py"
    if not config_path.exists():
        print("✗ OpenRouter config module not found")
        return False
    
    # Read and execute the module code directly
    with open(config_path) as f:
        code = f.read()
    
    # Create a namespace to execute the code
    namespace = {}
    exec(code, namespace)
    
    # Test the functions
    try:
        load_project_metadata = namespace['load_project_metadata']
        setup_openrouter_env = namespace['setup_openrouter_env']
        get_openrouter_headers = namespace['get_openrouter_headers']
        get_fallback_model = namespace['get_fallback_model']
        get_ollama_base_url = namespace['get_ollama_base_url']
        should_use_ollama_fallback = namespace['should_use_ollama_fallback']
        
        name, version = load_project_metadata()
        print(f"✓ load_project_metadata: {name} v{version}")
        
        setup_openrouter_env()
        print("✓ setup_openrouter_env completed")
        
        headers = get_openrouter_headers()
        print(f"✓ get_openrouter_headers: {headers}")
        
        fallback_model = get_fallback_model()
        print(f"✓ get_fallback_model: {fallback_model}")
        
        ollama_url = get_ollama_base_url()
        print(f"✓ get_ollama_base_url: {ollama_url}")
        
        use_ollama = should_use_ollama_fallback()
        print(f"✓ should_use_ollama_fallback: {use_ollama}")
        
    except Exception as e:
        print(f"✗ Error executing config module: {e}")
        return False
    
    return True

def test_env_file():
    """Test that .env.example contains the required configuration."""
    print("\n=== Testing .env.example Configuration ===")
    
    env_path = Path(__file__).parent / ".env.example"
    if not env_path.exists():
        print("✗ .env.example not found")
        return False
    
    with open(env_path) as f:
        content = f.read()
    
    required_vars = [
        "OPENROUTER_API_KEY",
        "OLLAMA_API_URL",
        "OLLAMA_LLM_MODEL",
        "OR_SITE_URL",
        "OR_APP_NAME"
    ]
    
    for var in required_vars:
        if var in content:
            print(f"✓ {var} found in .env.example")
        else:
            print(f"✗ {var} missing from .env.example")
            return False
    
    return True

if __name__ == "__main__":
    print("Simple OpenRouter Configuration Test")
    print("=" * 50)
    
    # Set some test environment variables
    os.environ["OLLAMA_API_URL"] = "http://localhost:11434"
    os.environ["OLLAMA_LLM_MODEL"] = "gemma2:9b"
    
    metadata_ok = test_project_metadata()
    config_ok = test_openrouter_config_module()
    env_ok = test_env_file()
    
    print("\n=== Summary ===")
    if metadata_ok and config_ok and env_ok:
        print("✓ All tests passed!")
        print("\nImplementation Summary:")
        print("1. ✓ OpenRouter configuration modules created")
        print("2. ✓ Project metadata loading from pyproject.toml")
        print("3. ✓ App name and version auto-configuration")
        print("4. ✓ Ollama fallback configuration")
        print("5. ✓ .env.example updated with required variables")
        print("\nTo use:")
        print("- Set OPENROUTER_API_KEY in your environment")
        print("- Configure OLLAMA_API_URL and OLLAMA_LLM_MODEL for fallback")
        print("- App names will automatically appear in OpenRouter logs!")
    else:
        print("✗ Some tests failed. Check the errors above.")
        sys.exit(1)
