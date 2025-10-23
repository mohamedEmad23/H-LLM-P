"""
Test VerificationAgent
"""

import pytest
import asyncio
from src.agents.verification_agent import VerificationAgent


class MockLLMClient:
    """Mock LLM for testing"""
    
    def __init__(self, return_value=None):
        self.return_value = return_value or self._default_response()
        self.calls = []
    
    def generate(self, prompt, system_prompt=None, temperature=0.3,
                 max_tokens=1500):
        self.calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt
        })
        return self.return_value
    
    def _default_response(self):
        return """{
  "goal_achieved": true,
  "constraint_violations": [],
  "logical_issues": [],
  "efficiency_score": 95,
  "quality_score": 98,
  "optimal_steps": 7,
  "actual_steps": 7,
  "suggestions": ["Plan is optimal"],
  "reasoning": "All disks successfully moved to target peg in optimal 7 moves"
}"""


@pytest.mark.asyncio
async def test_verification_agent_basic():
    """Test basic verification functionality"""
    mock_client = MockLLMClient()
    agent = VerificationAgent(llm_client=mock_client)
    
    # Successful 3-disk Hanoi execution
    result = await agent.process({
        "execution_trace": [
            {"step": 1, "operator": "move_disk", "params": [1, "A", "C"],
             "status": "success"},
            {"step": 2, "operator": "move_disk", "params": [2, "A", "B"],
             "status": "success"},
            {"step": 3, "operator": "move_disk", "params": [1, "C", "B"],
             "status": "success"},
            {"step": 4, "operator": "move_disk", "params": [3, "A", "C"],
             "status": "success"},
            {"step": 5, "operator": "move_disk", "params": [1, "B", "A"],
             "status": "success"},
            {"step": 6, "operator": "move_disk", "params": [2, "B", "C"],
             "status": "success"},
            {"step": 7, "operator": "move_disk", "params": [1, "A", "C"],
             "status": "success"}
        ],
        "final_state": {
            "pegs": {"A": [], "B": [], "C": [3, 2, 1]}
        },
        "initial_state": {
            "pegs": {"A": [3, 2, 1], "B": [], "C": []}
        },
        "goal": {
            "pegs": {"A": [], "B": [], "C": [3, 2, 1]}
        },
        "domain": "tower_of_hanoi",
        "optimal_steps": 7
    })
    
    print("\n=== Verification Result ===")
    print(f"Success: {result['success']}")
    print(f"Goal achieved: {result['goal_achieved']}")
    print(f"Quality score: {result['quality_score']:.1f}")
    print(f"Efficiency score: {result['efficiency_score']}")
    print(f"Issues: {len(result['issues_found'])}")
    
    assert result["success"] is True
    assert result["goal_achieved"] is True
    assert result["quality_score"] > 80
    assert len(result["issues_found"]) == 0


@pytest.mark.asyncio
async def test_verification_agent_failed_plan():
    """Test verification of failed plan"""
    mock_response = """{
  "goal_achieved": false,
  "constraint_violations": ["Invalid move detected"],
  "logical_issues": ["Plan did not complete"],
  "efficiency_score": 20,
  "quality_score": 15,
  "actual_steps": 3,
  "suggestions": ["Fix constraint violations"],
  "reasoning": "Plan failed due to invalid moves"
}"""
    
    mock_client = MockLLMClient(return_value=mock_response)
    agent = VerificationAgent(llm_client=mock_client)
    
    # Failed execution
    result = await agent.process({
        "execution_trace": [
            {"step": 1, "operator": "move_disk", "params": [1, "A", "C"],
             "status": "success"},
            {"step": 2, "operator": "move_disk", "params": [2, "A", "C"],
             "status": "failed", "error": "Invalid move"}
        ],
        "final_state": {
            "pegs": {"A": [2], "B": [], "C": [1]}
        },
        "initial_state": {
            "pegs": {"A": [2, 1], "B": [], "C": []}
        },
        "goal": {
            "pegs": {"A": [], "B": [2, 1], "C": []}
        },
        "domain": "tower_of_hanoi"
    })
    
    assert result["success"] is True  # Verification succeeded
    assert result["goal_achieved"] is False  # But plan failed
    assert len(result["issues_found"]) > 0
    assert result["quality_score"] < 50


@pytest.mark.asyncio
async def test_verification_agent_rule_based():
    """Test rule-based verification without LLM"""
    agent = VerificationAgent(llm_client=None)
    
    # Successful Hanoi execution
    result = await agent.process({
        "execution_trace": [
            {"step": 1, "operator": "move_disk", "params": [1, "A", "C"],
             "status": "success"}
        ],
        "final_state": {
            "pegs": {"A": [], "B": [], "C": [1]}
        },
        "initial_state": {
            "pegs": {"A": [1], "B": [], "C": []}
        },
        "goal": {
            "pegs": {"A": [], "B": [], "C": [1]}
        },
        "domain": "tower_of_hanoi"
    })
    
    print("\n=== Rule-Based Verification ===")
    print(f"Goal achieved: {result['goal_achieved']}")
    print(f"Quality score: {result['quality_score']:.1f}")
    
    assert result["success"] is True
    assert result["goal_achieved"] is True


@pytest.mark.asyncio
async def test_verification_agent_graph_domain():
    """Test verification for graph traversal"""
    mock_client = MockLLMClient()
    agent = VerificationAgent(llm_client=mock_client)
    
    result = await agent.process({
        "execution_trace": [
            {"step": 1, "operator": "traverse_edge", "params": ["A", "B"],
             "status": "success"},
            {"step": 2, "operator": "traverse_edge", "params": ["B", "C"],
             "status": "success"}
        ],
        "final_state": {
            "current_node": "C",
            "visited": ["A", "B"]
        },
        "initial_state": {
            "current_node": "A",
            "visited": []
        },
        "goal": {
            "current_node": "C"
        },
        "domain": "graph_traversal"
    })
    
    assert result["success"] is True
    assert result["goal_achieved"] is True


@pytest.mark.asyncio
async def test_verification_agent_statistics():
    """Test statistics tracking"""
    mock_client = MockLLMClient()
    agent = VerificationAgent(llm_client=mock_client)
    
    # Verify multiple plans
    for i in range(3):
        await agent.process({
            "execution_trace": [{"step": 1, "status": "success"}],
            "final_state": {"pegs": {"A": [], "B": [], "C": [1]}},
            "initial_state": {"pegs": {"A": [1], "B": [], "C": []}},
            "goal": {"pegs": {"A": [], "B": [], "C": [1]}},
            "domain": "tower_of_hanoi"
        })
    
    stats = agent.get_statistics()
    print("\n=== Verification Statistics ===")
    print(f"Verifications: {stats['verifications_performed']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    print(f"Avg quality: {stats['avg_quality_score']:.1f}")
    
    assert stats["verifications_performed"] == 3
    assert stats["plans_verified_successful"] >= 0


@pytest.mark.asyncio
async def test_verification_quality_metrics():
    """Test quality metrics calculation"""
    from src.agents.prompts.verification_prompts import (
        calculate_quality_metrics
    )
    
    metrics = calculate_quality_metrics(
        goal_achieved=True,
        constraint_violations=[],
        logical_issues=[],
        efficiency_score=90,
        actual_steps=7,
        optimal_steps=7
    )
    
    print("\n=== Quality Metrics ===")
    print(f"Goal achievement: {metrics['goal_achievement']}")
    print(f"Constraint compliance: {metrics['constraint_compliance']}")
    print(f"Logical soundness: {metrics['logical_soundness']}")
    print(f"Efficiency: {metrics['efficiency']}")
    print(f"Optimality ratio: {metrics['optimality_ratio']}")
    print(f"Overall quality: {metrics['overall_quality']:.1f}")
    
    assert metrics["goal_achievement"] == 100
    assert metrics["constraint_compliance"] == 100
    assert metrics["optimality_ratio"] == 1.0
    assert metrics["overall_quality"] > 90


if __name__ == "__main__":
    print("Testing VerificationAgent...\n")
    asyncio.run(test_verification_agent_basic())
    asyncio.run(test_verification_agent_failed_plan())
    asyncio.run(test_verification_agent_rule_based())
    asyncio.run(test_verification_agent_graph_domain())
    asyncio.run(test_verification_agent_statistics())
    asyncio.run(test_verification_quality_metrics())
    print("\n✅ All VerificationAgent tests passed!")
