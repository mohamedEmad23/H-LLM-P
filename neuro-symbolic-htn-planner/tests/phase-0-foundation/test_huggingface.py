"""
Test Hugging Face Inference API Client

Tests multiple models from small to large to verify the client works correctly.
"""

import os
import sys
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from llm.huggingface_client import HuggingFaceClient
from llm.local_llm_interface import LLMConfig


def test_huggingface_simple():
    """Test Hugging Face with a simple prompt."""
    print("=" * 80)
    print("�� HUGGING FACE INFERENCE API - SIMPLE TEST")
    print("=" * 80)

    # Check for API key
    if not os.getenv("HF_TOKEN") and not os.getenv("HUGGINGFACE_API_KEY"):
        print("\n❌ No HuggingFace API key found!")
        print("💡 Get your free token at: https://huggingface.co/settings/tokens")
        print("💡 Then set: export HF_TOKEN='your_token_here'")
        return

    # Test with small, fast model
    print("\n1️⃣ Testing Llama 3.3 70B (Default Model)")
    print("-" * 80)

    try:
        client = HuggingFaceClient(
            config=LLMConfig(
                model_name="meta-llama/Llama-3.3-70B-Instruct",
                temperature=0.7,
                max_tokens=100,
            )
        )

        # Check availability
        if not client.is_available():
            print("⚠️ Model not available (may be loading)")
            return

        # Simple math test
        response = client.generate(
            prompt="What is 7 + 8? Answer with just the number.",
            system_prompt="You are a helpful assistant.",
        )

        print(f"✅ Response: {response.content}")
        print(f"📊 Tokens: {response.tokens_used}")
        print(f"⏱️ Model: {response.model}")

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Test failed")


def test_huggingface_models():
    """Test multiple Hugging Face models."""
    print("\n" + "=" * 80)
    print("🤗 TESTING MULTIPLE HUGGING FACE MODELS")
    print("=" * 80)

    if not os.getenv("HF_TOKEN") and not os.getenv("HUGGINGFACE_API_KEY"):
        print("\n❌ No API key found!")
        return

    # Models to test (small to large)
    models = [
        ("Qwen/Qwen2.5-7B-Instruct", "Qwen 2.5 7B"),
        ("meta-llama/Llama-3.1-8B-Instruct", "Llama 3.1 8B"),
        ("meta-llama/Llama-3.3-70B-Instruct", "Llama 3.3 70B (default)"),
    ]

    prompt = "Explain what HTN planning is in one sentence."

    for model_id, model_name in models:
        print(f"\n{'=' * 80}")
        print(f"Testing: {model_name}")
        print(f"Model ID: {model_id}")
        print("-" * 80)

        try:
            client = HuggingFaceClient(
                config=LLMConfig(model_name=model_id, temperature=0.7, max_tokens=100)
            )

            # Quick availability check
            print("Checking availability...", end=" ")
            if not client.is_available():
                print("⚠️ Not available (may be loading)")
                continue
            print("✅")

            # Generate
            print("Generating response...", end=" ")
            response = client.generate(prompt)
            print("✅")

            print(f"\n📝 Response:\n{response.content}")
            print(f"\n📊 Tokens: ~{response.tokens_used.get('total_tokens', 'N/A')}")

        except Exception as e:
            print(f"\n❌ Error: {e}")


def test_huggingface_htn_task():
    """Test Hugging Face on an HTN task decomposition."""
    print("\n" + "=" * 80)
    print("🤗 HTN TASK DECOMPOSITION TEST")
    print("=" * 80)

    if not os.getenv("HF_TOKEN") and not os.getenv("HUGGINGFACE_API_KEY"):
        print("\n❌ No API key found!")
        return

    print("\nTask: Make Coffee")
    print("-" * 80)

    try:
        # Use Llama 3.3 70B for reasoning (best quality)
        client = HuggingFaceClient(
            config=LLMConfig(
                model_name="meta-llama/Llama-3.3-70B-Instruct",
                temperature=0.7,
                max_tokens=300,
            )
        )

        if not client.is_available():
            print("⚠️ Llama 3.3 70B not available, trying Qwen 2.5 7B...")
            client = HuggingFaceClient(
                config=LLMConfig(
                    model_name="Qwen/Qwen2.5-7B-Instruct",
                    temperature=0.7,
                    max_tokens=300,
                )
            )

        prompt = """Decompose this HTN task into subtasks:

Task: make_coffee()
Description: Make a cup of coffee

Available operators: grind_beans, fill_water, brew, pour

Provide the method decomposition:
Method: make_brewed_coffee
  Task: make_coffee()
  Subtasks:
    1. ...
"""

        response = client.generate(
            prompt=prompt,
            system_prompt="You are an expert in HTN planning. Provide clear, logical task decompositions.",
        )

        print(f"✅ HTN Decomposition:\n{response.content}")
        print(f"\n📊 Tokens used: ~{response.tokens_used.get('total_tokens', 'N/A')}")
        print(f"🤖 Model: {response.model}")

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("HTN test failed")


if __name__ == "__main__":
    # Run tests
    test_huggingface_simple()

    # Uncomment to test multiple models (takes longer)
    # test_huggingface_models()

    # Uncomment to test HTN decomposition
    # test_huggingface_htn_task()

    print("\n" + "=" * 80)
    print("✅ HUGGING FACE CLIENT TESTS COMPLETE")
    print("=" * 80)
    print("\n💡 Recommended models for HTN planning:")
    print("  - Small/Fast: meta-llama/Llama-3.2-3B-Instruct")
    print("  - Medium: mistralai/Mistral-7B-Instruct-v0.3")
    print("  - Large: meta-llama/Llama-3.1-70B-Instruct")
    print("=" * 80)
