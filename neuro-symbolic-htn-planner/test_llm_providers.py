"""Quick diagnostic script to test all LLM providers."""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm.local_llm_interface import LLMConfig

print("="*80)
print("LLM Provider Diagnostic Test")
print("="*80)

# Test 1: Ollama (local)
print("\n[1/7] Testing Ollama (local)...")
try:
    from llm.ollama_client import OllamaClient
    client = OllamaClient(config=LLMConfig(model_name="llama3.1:8b"))
    if client.is_available():
        print("✅ Ollama: AVAILABLE")
        response = client.generate("Say 'Hello'", max_tokens=10)
        print(f"   Response: {response.content[:50]}...")
    else:
        print("❌ Ollama: NOT AVAILABLE (server not running)")
except Exception as e:
    print(f"❌ Ollama: ERROR - {e}")

# Test 2: Groq
print("\n[2/7] Testing Groq...")
if not os.getenv("GROQ_API_KEY"):
    print("❌ Groq: NO API KEY (GROQ_API_KEY not set)")
else:
    try:
        from llm.groq_client import GroqClient
        client = GroqClient(config=LLMConfig(model_name="llama-3.3-70b-versatile"))
        if client.is_available():
            print("✅ Groq: AVAILABLE")
            response = client.generate("Say 'Hello'", max_tokens=10)
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ Groq: NOT AVAILABLE")
    except Exception as e:
        print(f"❌ Groq: ERROR - {str(e)[:100]}")

# Test 3: GitHub Models
print("\n[3/7] Testing GitHub Models...")
if not os.getenv("GITHUB_TOKEN"):
    print("❌ GitHub Models: NO TOKEN (GITHUB_TOKEN not set)")
else:
    try:
        from llm.github_models_client import GitHubModelsClient
        # Try GPT-4o (most likely to work)
        client = GitHubModelsClient(config=LLMConfig(model_name="openai/gpt-4o"))
        if client.is_available():
            print("✅ GitHub Models (GPT-4o): AVAILABLE")
            response = client.generate("Say 'Hello'", max_tokens=10)
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ GitHub Models: NOT AVAILABLE")
    except Exception as e:
        print(f"❌ GitHub Models: ERROR - {str(e)[:100]}")

# Test 4: Gemini
print("\n[4/7] Testing Gemini...")
api_key = os.getenv("GOOGLE_GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ Gemini: NO API KEY")
else:
    try:
        from llm.gemini_client import GeminiClient
        client = GeminiClient(config=LLMConfig(model_name="gemini-2.0-flash-exp"))
        if client.is_available():
            print("✅ Gemini: AVAILABLE")
            response = client.generate("Say 'Hello'", max_tokens=10)
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ Gemini: NOT AVAILABLE")
    except Exception as e:
        print(f"❌ Gemini: ERROR - {str(e)[:100]}")

# Test 5: Cohere
print("\n[5/7] Testing Cohere...")
if not os.getenv("COHERE_API_KEY"):
    print("❌ Cohere: NO API KEY")
else:
    try:
        from llm.cohere_client import CohereClient
        client = CohereClient(config=LLMConfig(model_name="command-r-plus-08-2024"))
        if client.is_available():
            print("✅ Cohere: AVAILABLE")
            response = client.generate("Say 'Hello'", max_tokens=10)
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ Cohere: NOT AVAILABLE")
    except Exception as e:
        print(f"❌ Cohere: ERROR - {str(e)[:100]}")

# Test 6: Mistral
print("\n[6/7] Testing Mistral...")
if not os.getenv("MISTRAL_API_KEY"):
    print("❌ Mistral: NO API KEY")
else:
    try:
        from llm.mistral_client import MistralClient
        client = MistralClient(config=LLMConfig(model_name="mistral-large-latest"))
        if client.is_available():
            print("✅ Mistral: AVAILABLE")
            response = client.generate("Say 'Hello'", max_tokens=10)
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ Mistral: NOT AVAILABLE")
    except Exception as e:
        print(f"❌ Mistral: ERROR - {str(e)[:100]}")

# Test 7: Eden AI
print("\n[7/7] Testing Eden AI...")
if not os.getenv("EDEN_API_KEY"):
    print("❌ Eden AI: NO API KEY")
else:
    try:
        from llm.eden_client import EdenClient
        client = EdenClient(config=LLMConfig(model_name="openai/gpt-4"))
        if client.is_available():
            print("✅ Eden AI: AVAILABLE")
            response = client.generate("Say 'Hello'", max_tokens=10)
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ Eden AI: NOT AVAILABLE")
    except Exception as e:
        print(f"❌ Eden AI: ERROR - {str(e)[:100]}")

print("\n" + "="*80)
print("Diagnostic Complete")
print("="*80)
