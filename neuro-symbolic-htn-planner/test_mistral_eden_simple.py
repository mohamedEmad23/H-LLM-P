#!/usr/bin/env python3
"""
Simplified test for Mistral and Eden AI - just test basic generation.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from llm.local_llm_interface import LLMConfig  # noqa: E402
from llm.mistral_client import MistralClient  # noqa: E402
from llm.eden_client import EdenClient  # noqa: E402


def test_mistral():
    """Test Mistral AI basic generation."""
    print("\n" + "=" * 80)
    print("🧪 TESTING MISTRAL AI")
    print("=" * 80)

    try:
        config = LLMConfig(
            model_name="mistral-small-latest", temperature=0.7, max_tokens=200
        )
        client = MistralClient(config=config)

        # Test 1: Simple math
        response = client.generate("What is 5+3? Answer with just the number.")
        print("\n✅ Test 1 - Simple Math:")
        print(f"   Response: {response.content}")
        print(
            f"   Tokens: {response.tokens_used.get('total_tokens') if response.tokens_used else 'N/A'}"
        )

        # Test 2: HTN planning task
        response2 = client.generate(
            "Decompose the task 'make coffee' into 2-3 subtasks. Be brief."
        )
        print("\n✅ Test 2 - Task Decomposition:")
        print(f"   Response: {response2.content[:150]}...")
        print(
            f"   Tokens: {response2.tokens_used.get('total_tokens') if response2.tokens_used else 'N/A'}"
        )

        print("\n" + "=" * 80)
        print("✅ MISTRAL PASSED - Working correctly!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ MISTRAL FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_eden():
    """Test Eden AI basic generation."""
    print("\n" + "=" * 80)
    print("🧪 TESTING EDEN AI (OpenAI Provider)")
    print("=" * 80)

    try:
        # Try with OpenAI provider instead of Google (might be more stable)
        config = LLMConfig(model_name="gpt-3.5-turbo", temperature=0.7, max_tokens=200)
        client = EdenClient(config=config, provider="openai")

        print("   Testing availability (timeout 10s)...")
        # Quick availability check with timeout
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Eden AI availability check timed out")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # 10 second timeout

        try:
            available = client.is_available()
            signal.alarm(0)  # Cancel alarm

            if not available:
                print("   ❌ Eden AI is not available")
                return False
        except TimeoutError:
            signal.alarm(0)
            print("   ❌ Eden AI availability check timed out (API may be slow/down)")
            return False

        print("   ✅ Eden AI is available")

        # Test generation with timeout
        signal.alarm(15)  # 15 second timeout for generation
        try:
            response = client.generate("What is 5+3? Answer with just the number.")
            signal.alarm(0)

            print("\n✅ Test 1 - Simple Math:")
            print(f"   Response: {response.content}")
            print(
                f"   Tokens: {response.tokens_used.get('total_tokens') if response.tokens_used else 'N/A'}"
            )

            print("\n" + "=" * 80)
            print("✅ EDEN AI PASSED - Working correctly!")
            print("=" * 80)
            return True

        except TimeoutError:
            signal.alarm(0)
            print("   ❌ Eden AI generation timed out (API may be slow/down)")
            return False

    except Exception as e:
        print(f"\n❌ EDEN AI FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("\n🚀 TESTING RENEWED API KEYS (MISTRAL + EDEN)")
    print("=" * 80)

    results = {"mistral": test_mistral(), "eden": test_eden()}

    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)

    for provider, passed in results.items():
        status = "✅ WORKING" if passed else "❌ NOT WORKING"
        print(f"   {provider.upper()}: {status}")

    working = sum(results.values())
    total = len(results)
    print(f"\n   Total Working: {working}/{total}")
    print("=" * 80 + "\n")

    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
