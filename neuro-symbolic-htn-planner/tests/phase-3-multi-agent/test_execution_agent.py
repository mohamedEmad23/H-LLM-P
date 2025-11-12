"""
Test ExecutionAgent and SymbolicValidator
"""

import pytest
import asyncio
from src.agents.execution_agent import ExecutionAgent
from src.agents.validators.symbolic_validator import SymbolicValidator


def test_symbolic_validator_hanoi():
    """Test symbolic validator for Tower of Hanoi"""
    validator = SymbolicValidator(domain="tower_of_hanoi")

    # Valid state
    state = {"pegs": {"A": [3, 2, 1], "B": [], "C": []}}

    # Valid move: disk 1 from A to C
    is_valid, reason = validator.validate_operator("move_disk", [1, "A", "C"], state)
    assert is_valid is True
    assert "valid" in reason.lower()

    # Invalid move: disk 2 (not on top)
    is_valid, reason = validator.validate_operator("move_disk", [2, "A", "C"], state)
    assert is_valid is False
    assert "not on top" in reason.lower()

    # Invalid move: larger on smaller
    state2 = {"pegs": {"A": [2], "B": [], "C": [1]}}
    is_valid, reason = validator.validate_operator("move_disk", [2, "A", "C"], state2)
    assert is_valid is False
    assert "smaller disk" in reason.lower()


def test_symbolic_validator_apply_hanoi():
    """Test applying Tower of Hanoi moves"""
    validator = SymbolicValidator(domain="tower_of_hanoi")

    state = {"pegs": {"A": [3, 2, 1], "B": [], "C": []}}

    # Apply move
    new_state = validator.apply_operator("move_disk", [1, "A", "C"], state)

    assert new_state is not None
    assert new_state["pegs"]["A"] == [3, 2]
    assert new_state["pegs"]["C"] == [1]

    # Original state unchanged
    assert state["pegs"]["A"] == [3, 2, 1]


def test_symbolic_validator_graph():
    """Test symbolic validator for graph traversal"""
    validator = SymbolicValidator(domain="graph_traversal")

    state = {"current_node": "A", "edges": [("A", "B"), ("B", "C")], "visited": []}

    # Valid traversal
    is_valid, reason = validator.validate_operator("traverse_edge", ["A", "B"], state)
    assert is_valid is True

    # Invalid traversal (no edge)
    is_valid, reason = validator.validate_operator("traverse_edge", ["A", "C"], state)
    assert is_valid is False
    assert "no edge" in reason.lower()

    # Invalid traversal (not at node)
    is_valid, reason = validator.validate_operator("traverse_edge", ["B", "C"], state)
    assert is_valid is False


@pytest.mark.asyncio
async def test_execution_agent_basic():
    """Test basic execution agent functionality"""
    agent = ExecutionAgent(llm_client=None)

    # Simple Hanoi plan
    result = await agent.process(
        {
            "plan": ["move_disk(1, A, C)", "move_disk(2, A, B)", "move_disk(1, C, B)"],
            "initial_state": {"pegs": {"A": [2, 1], "B": [], "C": []}},
            "domain": "tower_of_hanoi",
        }
    )

    print("\n=== Execution Result ===")
    print(f"Success: {result['success']}")
    print(f"Steps completed: {result['steps_completed']}/{result['steps_total']}")
    print(f"Execution time: {result['execution_time_ms']:.2f}ms")

    assert result["success"] is True
    assert result["steps_completed"] == 3
    assert result["final_state"]["pegs"]["B"] == [2, 1]
    assert len(result["execution_trace"]) == 3


@pytest.mark.asyncio
async def test_execution_agent_invalid_move():
    """Test execution agent catches invalid moves"""
    agent = ExecutionAgent(llm_client=None, config={"use_llm_fallback": False})

    # Invalid plan: try to move disk not on top
    result = await agent.process(
        {
            "plan": [
                "move_disk(2, A, C)",  # Invalid: disk 2 not on top
            ],
            "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
            "domain": "tower_of_hanoi",
        }
    )

    assert result["success"] is False
    assert len(result["errors"]) > 0
    assert "not on top" in result["errors"][0]["error"].lower()


@pytest.mark.asyncio
async def test_execution_agent_full_hanoi_3():
    """Test execution of full 3-disk Hanoi solution"""
    agent = ExecutionAgent()

    # Optimal 3-disk solution (7 moves)
    result = await agent.process(
        {
            "plan": [
                "move_disk(1, A, C)",
                "move_disk(2, A, B)",
                "move_disk(1, C, B)",
                "move_disk(3, A, C)",
                "move_disk(1, B, A)",
                "move_disk(2, B, C)",
                "move_disk(1, A, C)",
            ],
            "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
            "domain": "tower_of_hanoi",
        }
    )

    print("\n=== Full 3-Disk Hanoi Execution ===")
    print(f"Success: {result['success']}")
    print(f"Steps: {result['steps_completed']}/{result['steps_total']}")
    print(f"Final state: {result['final_state']['pegs']}")
    print(f"Execution time: {result['execution_time_ms']:.2f}ms")

    assert result["success"] is True
    assert result["steps_completed"] == 7
    assert result["final_state"]["pegs"]["C"] == [3, 2, 1]
    assert result["final_state"]["pegs"]["A"] == []
    assert result["final_state"]["pegs"]["B"] == []


@pytest.mark.asyncio
async def test_execution_agent_graph_traversal():
    """Test graph traversal execution"""
    agent = ExecutionAgent()

    result = await agent.process(
        {
            "plan": ["traverse_edge(A, B)", "traverse_edge(B, C)"],
            "initial_state": {
                "current_node": "A",
                "edges": [("A", "B"), ("B", "C"), ("A", "C")],
                "visited": [],
            },
            "domain": "graph_traversal",
        }
    )

    print("\n=== Graph Traversal Execution ===")
    print(f"Success: {result['success']}")
    print(f"Final state: {result['final_state']}")

    assert result["success"] is True
    assert result["final_state"]["current_node"] == "C"
    assert "A" in result["final_state"]["visited"]
    assert "B" in result["final_state"]["visited"]


@pytest.mark.asyncio
async def test_execution_agent_statistics():
    """Test agent tracks statistics"""
    agent = ExecutionAgent()

    # Execute multiple plans
    for i in range(3):
        await agent.process(
            {
                "plan": ["move_disk(1, A, C)"],
                "initial_state": {"pegs": {"A": [1], "B": [], "C": []}},
                "domain": "tower_of_hanoi",
            }
        )

    stats = agent.get_statistics()
    print("\n=== Execution Statistics ===")
    print(f"Plans executed: {stats['plans_executed']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    print(f"Total steps: {stats['total_steps_executed']}")
    print(f"Avg time: {stats['avg_execution_time_ms']:.2f}ms")

    assert stats["plans_executed"] == 3
    assert stats["successful_executions"] == 3
    assert stats["total_steps_executed"] == 3


if __name__ == "__main__":
    # Run tests
    print("Testing SymbolicValidator...")
    test_symbolic_validator_hanoi()
    test_symbolic_validator_apply_hanoi()
    test_symbolic_validator_graph()
    print("✅ SymbolicValidator tests passed!\n")

    print("Testing ExecutionAgent...")
    asyncio.run(test_execution_agent_basic())
    asyncio.run(test_execution_agent_invalid_move())
    asyncio.run(test_execution_agent_full_hanoi_3())
    asyncio.run(test_execution_agent_graph_traversal())
    asyncio.run(test_execution_agent_statistics())
    print("✅ ExecutionAgent tests passed!")
