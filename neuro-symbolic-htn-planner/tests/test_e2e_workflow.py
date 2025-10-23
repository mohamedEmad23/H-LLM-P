"""
End-to-End Integration Tests - Complete 3-Agent Workflow
"""

import pytest
import asyncio
from src.agents.decomposition_agent import DecompositionAgent
from src.agents.execution_agent import ExecutionAgent
from src.agents.verification_agent import VerificationAgent
from src.agents.workflows.core_workflow import CoreWorkflow


class MockLLMDecomposition:
    """Mock LLM for decomposition"""
    
    def generate(self, prompt, system_prompt=None, **kwargs):
        # Return optimal 3-disk Hanoi decomposition
        return """{
  "methods": [
    {
      "task": "solve_hanoi(3, A, C, B)",
      "subtasks": [
        "move_disk(1, A, C)",
        "move_disk(2, A, B)",
        "move_disk(1, C, B)",
        "move_disk(3, A, C)",
        "move_disk(1, B, A)",
        "move_disk(2, B, C)",
        "move_disk(1, A, C)"
      ],
      "preconditions": [],
      "effects": ["all_disks_on_C"],
      "confidence": 0.95,
      "reasoning": "Standard recursive decomposition for 3-disk Hanoi"
    }
  ],
  "alternatives_considered": 1
}"""


class MockLLMVerification:
    """Mock LLM for verification"""
    
    def generate(self, prompt, system_prompt=None, **kwargs):
        return """{
  "goal_achieved": true,
  "constraint_violations": [],
  "logical_issues": [],
  "efficiency_score": 100,
  "quality_score": 98,
  "optimal_steps": 7,
  "actual_steps": 7,
  "suggestions": ["Plan is optimal for 3-disk Tower of Hanoi"],
  "reasoning": "All disks successfully moved to target in optimal 7 moves"
}"""


@pytest.mark.asyncio
async def test_e2e_hanoi_3_disk():
    """Test complete workflow for 3-disk Tower of Hanoi"""
    
    # Create agents
    decomp_agent = DecompositionAgent(
        llm_client=MockLLMDecomposition()
    )
    
    exec_agent = ExecutionAgent(
        llm_client=None  # No LLM needed, symbolic validation only
    )
    
    verif_agent = VerificationAgent(
        llm_client=MockLLMVerification()
    )
    
    # Create workflow
    workflow = CoreWorkflow(
        decomposition_agent=decomp_agent,
        execution_agent=exec_agent,
        verification_agent=verif_agent,
        max_retries=3
    )
    
    # Run workflow
    result = await workflow.process_task({
        "task": "solve_hanoi(3, A, C, B)",
        "domain": "tower_of_hanoi",
        "initial_state": {
            "pegs": {"A": [3, 2, 1], "B": [], "C": []}
        },
        "goal": {
            "pegs": {"A": [], "B": [], "C": [3, 2, 1]}
        },
        "operators": {
            "move_disk": {
                "parameters": ["disk", "from", "to"],
                "preconditions": ["disk_on_top"],
                "effects": ["disk_moved"]
            }
        },
        "optimal_steps": 7
    })
    
    print("\n" + "="*60)
    print("  END-TO-END TEST: 3-Disk Tower of Hanoi")
    print("="*60)
    print(f"\n✓ Success: {result['success']}")
    print(f"✓ Goal Achieved: {result['goal_achieved']}")
    print(f"✓ Quality Score: {result['quality_score']:.1f}/100")
    print(f"✓ Total Time: {result['total_time_ms']:.1f}ms")
    print(f"\nBreakdown:")
    print(f"  - Decomposition: {result['decomposition_time_ms']:.1f}ms")
    print(f"  - Execution: {result['execution_time_ms']:.1f}ms")
    print(f"  - Verification: {result['verification_time_ms']:.1f}ms")
    print(f"\n✓ Plan Length: {len(result['plan'])} steps")
    print(f"✓ Final State: {result['final_state']['pegs']}")
    print(f"✓ Retries: {result['retry_count']}")
    print("="*60)
    
    # Assertions
    assert result["success"] is True
    assert result["goal_achieved"] is True
    assert result["quality_score"] > 90
    assert result["final_state"]["pegs"]["C"] == [3, 2, 1]
    assert result["final_state"]["pegs"]["A"] == []
    assert result["final_state"]["pegs"]["B"] == []
    assert len(result["plan"]) == 7
    assert result["retry_count"] == 0


@pytest.mark.asyncio
async def test_e2e_workflow_statistics():
    """Test workflow statistics tracking"""
    
    decomp_agent = DecompositionAgent(llm_client=MockLLMDecomposition())
    exec_agent = ExecutionAgent(llm_client=None)
    verif_agent = VerificationAgent(llm_client=MockLLMVerification())
    
    workflow = CoreWorkflow(
        decomposition_agent=decomp_agent,
        execution_agent=exec_agent,
        verification_agent=verif_agent
    )
    
    # Process multiple tasks
    for i in range(3):
        await workflow.process_task({
            "task": f"solve_hanoi(3, A, C, B)_{i}",
            "domain": "tower_of_hanoi",
            "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
            "goal": {"pegs": {"A": [], "B": [], "C": [3, 2, 1]}},
            "optimal_steps": 7
        })
    
    stats = workflow.get_statistics()
    
    print("\n" + "="*60)
    print("  WORKFLOW STATISTICS")
    print("="*60)
    print(f"\nTasks Processed: {stats['tasks_processed']}")
    print(f"Success Rate: {stats['success_rate']:.1%}")
    print(f"Avg Total Time: {stats['avg_total_time_ms']:.1f}ms")
    print(f"Avg Decomposition Time: {stats['avg_decomposition_time_ms']:.1f}ms")
    print(f"Avg Execution Time: {stats['avg_execution_time_ms']:.1f}ms")
    print(f"Avg Verification Time: {stats['avg_verification_time_ms']:.1f}ms")
    print("="*60)
    
    assert stats["tasks_processed"] == 3
    assert stats["successful_tasks"] >= 2
    assert stats["success_rate"] >= 0.5


@pytest.mark.asyncio
async def test_e2e_full_report():
    """Test full workflow report generation"""
    
    decomp_agent = DecompositionAgent(llm_client=MockLLMDecomposition())
    exec_agent = ExecutionAgent(llm_client=None)
    verif_agent = VerificationAgent(llm_client=MockLLMVerification())
    
    workflow = CoreWorkflow(
        decomposition_agent=decomp_agent,
        execution_agent=exec_agent,
        verification_agent=verif_agent
    )
    
    # Process a task
    await workflow.process_task({
        "task": "solve_hanoi(3, A, C, B)",
        "domain": "tower_of_hanoi",
        "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
        "goal": {"pegs": {"A": [], "B": [], "C": [3, 2, 1]}},
        "optimal_steps": 7
    })
    
    report = workflow.get_full_report()
    
    print("\n" + report)
    
    assert "MULTI-AGENT HTN WORKFLOW REPORT" in report
    assert "Tasks Processed" in report
    assert "DecompositionAgent" in report
    assert "ExecutionAgent" in report
    assert "VerificationAgent" in report


@pytest.mark.asyncio
async def test_e2e_hanoi_2_disk():
    """Test workflow with 2-disk Hanoi (simpler case)"""
    
    class MockLLMDecomp2Disk:
        def generate(self, prompt, system_prompt=None, **kwargs):
            return """{
  "methods": [{
    "task": "solve_hanoi(2, A, C, B)",
    "subtasks": [
      "move_disk(1, A, B)",
      "move_disk(2, A, C)",
      "move_disk(1, B, C)"
    ],
    "preconditions": [],
    "effects": ["all_disks_on_C"],
    "confidence": 0.98,
    "reasoning": "Optimal 2-disk solution"
  }],
  "alternatives_considered": 1
}"""
    
    decomp_agent = DecompositionAgent(llm_client=MockLLMDecomp2Disk())
    exec_agent = ExecutionAgent(llm_client=None)
    verif_agent = VerificationAgent(llm_client=MockLLMVerification())
    
    workflow = CoreWorkflow(
        decomposition_agent=decomp_agent,
        execution_agent=exec_agent,
        verification_agent=verif_agent
    )
    
    result = await workflow.process_task({
        "task": "solve_hanoi(2, A, C, B)",
        "domain": "tower_of_hanoi",
        "initial_state": {"pegs": {"A": [2, 1], "B": [], "C": []}},
        "goal": {"pegs": {"A": [], "B": [], "C": [2, 1]}},
        "optimal_steps": 3
    })
    
    print("\n" + "="*60)
    print("  2-DISK HANOI TEST")
    print("="*60)
    print(f"Success: {result['success']}")
    print(f"Plan Length: {len(result['plan'])} (optimal: 3)")
    print(f"Final State: {result['final_state']['pegs']}")
    print("="*60)
    
    assert result["success"] is True
    assert len(result["plan"]) == 3
    assert result["final_state"]["pegs"]["C"] == [2, 1]


if __name__ == "__main__":
    print("\n🧪 Running End-to-End Integration Tests...\n")
    
    asyncio.run(test_e2e_hanoi_3_disk())
    asyncio.run(test_e2e_workflow_statistics())
    asyncio.run(test_e2e_full_report())
    asyncio.run(test_e2e_hanoi_2_disk())
    
    print("\n✅ All End-to-End Tests Passed!")
    print("\n🎉 Phase 4A Core Implementation Complete!")
