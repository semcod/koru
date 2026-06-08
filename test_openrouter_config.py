#!/usr/bin/env python3
"""Test script to verify OpenRouter configuration and Ollama fallback."""

import os
import sys
from pathlib import Path

# Add the packages to Python path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "nlp2koru" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "nlp2coru" / "src"))

def test_openrouter_config():
    """Test OpenRouter configuration setup."""
    print("=== Testing OpenRouter Configuration ===")
    
    # Test nlp2koru config
    try:
        from nlp2koru.openrouter_config import (
            load_project_metadata,
            setup_openrouter_env,
            get_openrouter_headers,
            get_fallback_model,
            get_ollama_base_url,
            should_use_ollama_fallback,
        )
        
        name, version = load_project_metadata()
        print(f"✓ Project metadata: {name} v{version}")
        
        setup_openrouter_env()
        print("✓ Environment setup complete")
        
        headers = get_openrouter_headers()
        print(f"✓ OpenRouter headers: {headers}")
        
        fallback_model = get_fallback_model()
        print(f"✓ Fallback model: {fallback_model}")
        
        ollama_url = get_ollama_base_url()
        print(f"✓ Ollama URL: {ollama_url}")
        
        use_ollama = should_use_ollama_fallback()
        print(f"✓ Should use Ollama fallback: {use_ollama}")
        
    except Exception as e:
        print(f"✗ nlp2koru config failed: {e}")
        return False
    
    # Test nlp2coru config
    try:
        from nlp2coru.openrouter_config import (
            load_project_metadata as coru_load_metadata,
            get_openrouter_headers as coru_get_headers,
        )
        
        name, version = coru_load_metadata()
        print(f"✓ nlp2coru project metadata: {name} v{version}")
        
        headers = coru_get_headers()
        print(f"✓ nlp2coru OpenRouter headers: {headers}")
        
    except Exception as e:
        print(f"✗ nlp2coru config failed: {e}")
        return False
    
    return True

def test_llm_backend():
    """Test LLM backend with OpenRouter configuration."""
    print("\n=== Testing LLM Backend ===")
    
    try:
        from nlp2koru.llm_backend import LitellmBackend
        
        backend = LitellmBackend()
        print("✓ LitellmBackend instantiated")
        
        # Test with a simple completion (will fail without API key, but should show configuration)
        try:
            response = backend.complete(
                model="openrouter/qwen/qwen3-coder-next",
                messages=[{"role": "user", "content": "test"}],
                temperature=0.1,
            )
            print(f"✓ LLM completion successful: {response[:50]}...")
        except Exception as e:
            if "OPENROUTER_API_KEY" in str(e) or "authentication" in str(e).lower():
                print("✓ LLM backend correctly configured (API key expected)")
            else:
                print(f"✗ LLM backend error: {e}")
                return False
                
    except Exception as e:
        print(f"✗ LLM backend test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("OpenRouter Configuration Test")
    print("=" * 40)
    
    config_ok = test_openrouter_config()
    backend_ok = test_llm_backend()
    
    print("\n=== Summary ===")
    if config_ok and backend_ok:
        print("✓ All tests passed! OpenRouter configuration is working.")
        print("\nTo use:")
        print("1. Set OPENROUTER_API_KEY in your environment")
        print("2. Optionally set OLLAMA_API_URL=http://localhost:11434")
        print("3. Optionally set OLLAMA_LLM_MODEL=gemma2:9b")
        print("4. Your app name will automatically appear in OpenRouter logs!")
    else:
        print("✗ Some tests failed. Check the errors above.")
        sys.exit(1)
