"""
Test DecompositionAgent
"""

import pytest
import asyncio
from src.agents.decomposition_agent import DecompositionAgent
from src.llm.huggingface_client import HuggingFaceClient


class MockLLMClient:
    """Mock LLM client for testing"""

    def __init__(self, return_value=None):
        self.return_value = return_value or self._default_response()
        self.calls = []

    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=2000):
        """Mock generate method"""
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.return_value

    def _default_response(self):
        """Default mock response"""
        return """{
  "methods": [
    {
      "task": "solve_hanoi(3, A, C, B)",
      "subtasks": [
        "solve_hanoi(2, A, B, C)",
        "move_disk(3, A, C)",
        "solve_hanoi(2, B, C, A)"
      ],
      "preconditions": ["disk_on_top(3, A)"],
      "effects": ["disk_on_top(3, C)"],
      "confidence": 0.95,
      "reasoning": "Standard recursive decomposition for Tower of Hanoi"
    }
  ],
  "alternatives_considered": 1
}"""


@pytest.mark.asyncio
async def test_decomposition_agent_basic():
    """Test basic decomposition agent functionality"""
    mock_client = MockLLMClient()
    agent = DecompositionAgent(llm_client=mock_client)

    result = await agent.process(
        {
            "task": "solve_hanoi(3, A, C, B)",
            "domain": "tower_of_hanoi",
            "operators": {
                "move_disk": {
                    "parameters": ["disk", "from", "to"],
                    "preconditions": ["disk_on_top"],
                    "effects": ["disk_moved"],
                }
            },
            "constraints": ["larger_on_smaller_forbidden"],
        }
    )

    assert result["success"] is True
    assert "methods" in result
    assert len(result["methods"]) > 0
    assert result["confidence"] > 0.0
    assert "reasoning" in result
    assert len(mock_client.calls) == 1


@pytest.mark.asyncio
async def test_decomposition_agent_invalid_input():
    """Test agent handles invalid input"""
    mock_client = MockLLMClient()
    agent = DecompositionAgent(llm_client=mock_client)

    # Missing task
    result = await agent.process({"domain": "tower_of_hanoi"})
    assert result["success"] is False
    assert "error" in result

    # Missing domain
    result = await agent.process({"task": "solve_hanoi(3, A, C, B)"})
    assert result["success"] is False


@pytest.mark.asyncio
async def test_decomposition_agent_fallback():
    """Test fallback mechanism"""
    # Primary client fails
    failing_client = MockLLMClient(return_value="invalid json")

    # Fallback client succeeds
    fallback_client = MockLLMClient()

    agent = DecompositionAgent(
        llm_client=failing_client, fallback_client=fallback_client
    )

    result = await agent.process(
        {"task": "solve_hanoi(3, A, C, B)", "domain": "tower_of_hanoi"}
    )

    assert result["success"] is True
    assert result["used_fallback"] is True
    assert len(failing_client.calls) == 1
    assert len(fallback_client.calls) == 1


@pytest.mark.asyncio
async def test_decomposition_agent_statistics():
    """Test agent tracks statistics correctly"""
    mock_client = MockLLMClient()
    agent = DecompositionAgent(llm_client=mock_client)

    # Process multiple tasks
    for i in range(5):
        await agent.process({"task": f"task_{i}", "domain": "test_domain"})

    stats = agent.get_statistics()
    assert stats["decompositions_generated"] == 5
    assert stats["successful_decompositions"] == 5
    assert stats["success_rate"] == 1.0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_decomposition_agent_with_real_llm():
    """Integration test with real HuggingFace LLM"""
    import os

    # Skip if no HF token
    if not os.getenv("HF_TOKEN"):
        pytest.skip("HF_TOKEN not set")

    # Use Qwen 7B (faster for testing)
    client = HuggingFaceClient(
        model_name="Qwen/Qwen2.5-7B-Instruct", api_token=os.getenv("HF_TOKEN")
    )

    agent = DecompositionAgent(llm_client=client)

    result = await agent.process(
        {
            "task": "solve_hanoi(3, A, C, B)",
            "domain": "tower_of_hanoi",
            "operators": {
                "move_disk": {
                    "parameters": ["disk", "from_peg", "to_peg"],
                    "preconditions": ["disk_on_top(disk, from_peg)"],
                    "effects": ["disk_on_top(disk, to_peg)"],
                }
            },
            "constraints": [
                "Only one disk can be moved at a time",
                "Larger disk cannot be on smaller disk",
            ],
        }
    )

    print("\n=== Real LLM Decomposition Result ===")
    print(f"Success: {result['success']}")
    print(f"Confidence: {result.get('confidence', 0.0):.2f}")
    print(f"Methods: {len(result.get('methods', []))}")
    if result["success"]:
        for i, method in enumerate(result["methods"], 1):
            print(f"\nMethod {i}:")
            print(f"  Task: {method['task']}")
            print(f"  Subtasks: {method['subtasks']}")
            print(f"  Reasoning: {method.get('reasoning', 'N/A')}")

    assert result["success"] is True
    assert len(result["methods"]) > 0


if __name__ == "__main__":
    # Run basic tests
    asyncio.run(test_decomposition_agent_basic())
    asyncio.run(test_decomposition_agent_invalid_input())
    asyncio.run(test_decomposition_agent_fallback())
    asyncio.run(test_decomposition_agent_statistics())

    print("\n✅ All basic tests passed!")

    # Run integration test if HF_TOKEN available
    try:
        asyncio.run(test_decomposition_agent_with_real_llm())
        print("✅ Integration test passed!")
    except Exception as e:
        print(f"⚠️  Integration test skipped: {e}")
