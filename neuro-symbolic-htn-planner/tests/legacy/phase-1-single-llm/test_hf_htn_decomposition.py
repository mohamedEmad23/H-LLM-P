"""
Test Hugging Face Models on HTN Task Decomposition

Tests multiple HF models on actual HTN planning tasks.
"""

import os
import sys
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from llm.huggingface_client import HuggingFaceClient
from llm.local_llm_interface import LLMConfig


def test_hf_htn_decomposition():
    """Test Hugging Face models on HTN task decomposition."""
    print("=" * 80)
    print("🤗 HUGGING FACE - HTN TASK DECOMPOSITION TEST")
    print("=" * 80)

    if not os.getenv("HF_TOKEN") and not os.getenv("HUGGINGFACE_API_KEY"):
        print("\n❌ No API key found!")
        print("Set HF_TOKEN environment variable")
        return

    # Models to test
    models_to_test = [
        ("Qwen/Qwen2.5-7B-Instruct", "Qwen 2.5 7B - Fast"),
        ("meta-llama/Llama-3.1-8B-Instruct", "Llama 3.1 8B - Balanced"),
        ("meta-llama/Llama-3.3-70B-Instruct", "Llama 3.3 70B - Best"),
    ]

    # HTN Task to decompose
    htn_prompt = """Decompose this HTN task into subtasks:

Task: make_coffee()
Description: Make a cup of brewed coffee

Available operators:
- grind_beans(beans, grounds)
- fill_water(amount, container)
- add_coffee(grounds, filter)
- brew(coffee_maker)
- pour(source, destination)

Provide the method decomposition in this format:
Method: make_brewed_coffee
  Task: make_coffee()
  Subtasks:
    1. <subtask>(<params>)
    2. <subtask>(<params>)
    ...

Be concise and logical."""

    system_prompt = (
        "You are an expert in HTN planning. Provide clear task decompositions."
    )

    results = []

    for model_id, model_name in models_to_test:
        print(f"\n{'=' * 80}")
        print(f"Testing: {model_name}")
        print(f"Model: {model_id}")
        print("-" * 80)

        try:
            client = HuggingFaceClient(
                config=LLMConfig(model_name=model_id, temperature=0.7, max_tokens=400)
            )

            # Check availability
            print("Checking availability...", end=" ", flush=True)
            if not client.is_available():
                print("❌ Not available")
                continue
            print("✅")

            # Generate decomposition
            print("Generating HTN decomposition...", end=" ", flush=True)
            import time

            start_time = time.time()

            response = client.generate(prompt=htn_prompt, system_prompt=system_prompt)

            elapsed = time.time() - start_time
            print(f"✅ ({elapsed:.2f}s)")

            # Display result
            print("\n📝 HTN Decomposition:\n")
            print(response.content)
            print(f"\n📊 Tokens: {response.tokens_used.get('total_tokens', 'N/A')}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"🤖 Model: {response.model}")

            results.append(
                {
                    "model": model_name,
                    "success": True,
                    "time": elapsed,
                    "tokens": response.tokens_used.get("total_tokens", 0),
                    "content_length": len(response.content),
                }
            )

        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.exception(f"Failed to test {model_name}")
            results.append({"model": model_name, "success": False, "error": str(e)})

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    for result in results:
        if result["success"]:
            print(f"✅ {result['model']}")
            print(f"   Time: {result['time']:.2f}s")
            print(f"   Tokens: {result['tokens']}")
            print(f"   Output: {result['content_length']} chars")
        else:
            print(f"❌ {result['model']}: {result.get('error', 'Unknown')}")

    print("\n" + "=" * 80)
    print("✅ HUGGING FACE HTN DECOMPOSITION TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_hf_htn_decomposition()
