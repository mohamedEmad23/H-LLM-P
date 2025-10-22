#!/usr/bin/env python3
"""
Test script for Mistral and Eden AI clients with renewed API keys.
Tests each provider individually before integration.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm.local_llm_interface import LLMConfig
from llm.mistral_client import MistralClient
from llm.eden_client import EdenClient


def test_mistral():
    """Test Mistral AI client with renewed API key."""
    print("\n" + "="*80)
    print("🧪 TESTING MISTRAL AI CLIENT")
    print("="*80)
    
    try:
        # Initialize client
        print("\n1️⃣ Initializing Mistral client...")
        config = LLMConfig(
            model_name="mistral-small-latest",  # Use smaller model for faster testing
            temperature=0.7,
            max_tokens=500
        )
        client = MistralClient(config=config)
        print(f"   ✅ Client initialized: {config.model_name}")
        
        # Test availability
        print("\n2️⃣ Testing availability...")
        if client.is_available():
            print("   ✅ Mistral API is available!")
        else:
            print("   ❌ Mistral API is NOT available")
            return False
        
        # Test simple generation
        print("\n3️⃣ Testing text generation...")
        test_prompt = "What is 2+2? Answer in one sentence."
        response = client.generate(test_prompt)
        
        print(f"   📝 Prompt: {test_prompt}")
        print(f"   💬 Response: {response.content}")
        tokens = response.tokens_used.get('total_tokens', 'N/A') if response.tokens_used else 'N/A'
        print(f"   🔢 Tokens used: {tokens}")
        print(f"   ⏱️  Time: {response.metadata.get('response_time', 'N/A')}s")
        
        if response.content and len(response.content) > 0:
            print("   ✅ Generation successful!")
        else:
            print("   ❌ Generation returned empty response")
            return False
        
        # Test with history
        print("\n4️⃣ Testing conversation with history...")
        history = [
            {"role": "user", "content": "My name is Alice."},
            {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
        ]
        response_with_history = client.generate_with_history(
            "What is my name?",
            history
        )
        
        print(f"   💬 Response: {response_with_history.content}")
        
        if "alice" in response_with_history.content.lower():
            print("   ✅ History tracking works!")
        else:
            print("   ⚠️  History tracking may not be working correctly")
        
        print("\n" + "="*80)
        print("✅ MISTRAL TEST PASSED")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n❌ MISTRAL TEST FAILED: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def test_eden():
    """Test Eden AI client with renewed API key."""
    print("\n" + "="*80)
    print("🧪 TESTING EDEN AI CLIENT")
    print("="*80)
    
    try:
        # Initialize client with Google provider (free tier)
        print("\n1️⃣ Initializing Eden AI client (Google provider)...")
        config = LLMConfig(
            model_name="gemini-2.0-flash-exp",
            temperature=0.7,
            max_tokens=500
        )
        client = EdenClient(config=config, provider="google")
        print(f"   ✅ Client initialized: google/{config.model_name}")
        
        # Test availability
        print("\n2️⃣ Testing availability...")
        if client.is_available():
            print("   ✅ Eden AI (Google) is available!")
        else:
            print("   ❌ Eden AI (Google) is NOT available")
            return False
        
        # Test simple generation
        print("\n3️⃣ Testing text generation...")
        test_prompt = "What is 2+2? Answer in one sentence."
        response = client.generate(test_prompt)
        
        print(f"   📝 Prompt: {test_prompt}")
        print(f"   💬 Response: {response.content}")
        tokens = response.tokens_used.get('total_tokens', 'N/A') if response.tokens_used else 'N/A'
        print(f"   🔢 Tokens used: {tokens}")
        print(f"   ⏱️  Time: {response.metadata.get('response_time', 'N/A')}s")
        
        if response.content and len(response.content) > 0:
            print("   ✅ Generation successful!")
        else:
            print("   ❌ Generation returned empty response")
            return False
        
        # Test with history
        print("\n4️⃣ Testing conversation with history...")
        history = [
            {"role": "user", "content": "My name is Bob."},
            {"role": "assistant", "content": "Hello Bob! Nice to meet you."},
        ]
        response_with_history = client.generate_with_history(
            "What is my name?",
            history
        )
        
        print(f"   💬 Response: {response_with_history.content}")
        
        if "bob" in response_with_history.content.lower():
            print("   ✅ History tracking works!")
        else:
            print("   ⚠️  History tracking may not be working correctly")
        
        print("\n" + "="*80)
        print("✅ EDEN AI TEST PASSED")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n❌ EDEN AI TEST FAILED: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n🚀 STARTING LLM PROVIDER TESTS (MISTRAL + EDEN)")
    print("=" * 80)
    
    results = {}
    
    # Test Mistral
    results['mistral'] = test_mistral()
    
    # Test Eden AI
    results['eden'] = test_eden()
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    for provider, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {provider.upper()}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\n   Total: {total_passed}/{total_tests} providers working")
    print("="*80 + "\n")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
