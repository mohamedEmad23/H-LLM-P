"""
Extended Workflow E2E Integration Tests - 5-Agent System

Tests the complete 5-agent workflow:
PlanningAgent → DecompositionAgent → ExecutionAgent → VerificationAgent → ContextAgent

Compares 3-agent baseline (CoreWorkflow) vs 5-agent extended (ExtendedWorkflow)
"""

import pytest
from src.agents import (
    PlanningAgent,
    DecompositionAgent,
    ExecutionAgent,
    VerificationAgent,
    ContextAgent,
    CoreWorkflow,
    ExtendedWorkflow,
)


# ============================================================================
# MOCK LLM CLIENTS
# ============================================================================


class MockLLMPlanning:
    """Mock LLM for PlanningAgent - returns strategic analysis"""

    def generate(self, prompt, system_prompt=None, **kwargs):
        # Return strategic planning response
        return """{
  "strategies": [
    {
      "name": "Optimal Recursive",
      "description": "Standard recursive decomposition for minimal moves",
      "trade_offs": {
        "optimality": "high",
        "complexity": "medium",
        "resource_usage": "low"
      },
      "suitability_score": 0.95,
      "reasoning": "Best for small-medium problems requiring optimal solution"
    },
    {
      "name": "Iterative Baseline",
      "description": "Iterative approach for simpler planning",
      "trade_offs": {
        "optimality": "medium",
        "complexity": "low",
        "resource_usage": "low"
      },
      "suitability_score": 0.75,
      "reasoning": "Simpler but may not find optimal path"
    }
  ],
  "recommended_strategy": "Optimal Recursive",
  "confidence": 0.95,
  "reasoning": "Optimal Recursive provides best balance for Tower of Hanoi with 3 disks"
}"""


class MockLLMDecomposition:
    """Mock LLM for DecompositionAgent"""

    def __init__(self, problem_size=3):
        self.problem_size = problem_size

    def generate(self, prompt, system_prompt=None, **kwargs):
        # Return optimal decomposition based on problem size
        if self.problem_size == 3:
            # 3-disk Hanoi: 7 moves
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
      "reasoning": "Standard optimal decomposition for 3-disk Hanoi"
    }
  ],
  "alternatives_considered": 1
}"""
        elif self.problem_size == 4:
            # 4-disk Hanoi: 15 moves (properly formatted JSON)
            return """{
  "methods": [
    {
      "task": "solve_hanoi(4, A, C, B)",
      "subtasks": [
        "move_disk(1, A, B)", "move_disk(2, A, C)", "move_disk(1, B, C)",
        "move_disk(3, A, B)", "move_disk(1, C, A)", "move_disk(2, C, B)",
        "move_disk(1, A, B)", "move_disk(4, A, C)", "move_disk(1, B, C)",
        "move_disk(2, B, A)", "move_disk(1, C, A)", "move_disk(3, B, C)",
        "move_disk(1, A, B)", "move_disk(2, A, C)", "move_disk(1, B, C)"
      ],
      "preconditions": [],
      "effects": ["all_disks_on_C"],
      "confidence": 0.95,
      "reasoning": "Optimal decomposition for 4-disk Hanoi"
    }
  ],
  "alternatives_considered": 1
}"""
        else:
            # Graph traversal
            return """{
  "methods": [
    {
      "task": "find_shortest_path(A, C)",
      "subtasks": [
        "mark_visited(A)",
        "traverse_edge(A, B)",
        "mark_visited(B)",
        "traverse_edge(B, C)",
        "mark_visited(C)"
      ],
      "preconditions": ["at(A)"],
      "effects": ["at(C)"],
      "confidence": 0.95,
      "reasoning": "Shortest path from A to C"
    }
  ],
  "alternatives_considered": 1
}"""


class MockLLMVerification:
    """Mock LLM for VerificationAgent"""

    def __init__(self, quality=98):
        self.quality = quality

    def generate(self, prompt, system_prompt=None, **kwargs):
        return f"""{{
  "goal_achieved": true,
  "constraint_violations": [],
  "logical_issues": [],
  "efficiency_score": 100,
  "quality_score": {self.quality},
  "optimal_steps": 7,
  "actual_steps": 7,
  "suggestions": ["Plan is optimal"],
  "reasoning": "All goals achieved optimally"
}}"""


class MockLLMContext:
    """Mock LLM for ContextAgent (only used for complex queries)"""

    def generate(self, prompt, system_prompt=None, **kwargs):
        # Return context analysis for complex queries
        return """{
  "relevant_context": [
    {
      "phase": "planning",
      "agent": "PlanningAgent",
      "key_info": "Selected Optimal Recursive strategy"
    },
    {
      "phase": "execution",
      "agent": "ExecutionAgent",
      "key_info": "Executed 7 steps successfully"
    }
  ],
  "summary": "Workflow executed successfully with optimal strategy",
  "insights": ["Strategy selection was effective", "No retries needed"]
}"""


# ============================================================================
# TEST CLASS
# ============================================================================


class TestExtendedWorkflowE2E:
    """E2E integration tests for 5-agent ExtendedWorkflow"""

    # ========================================================================
    # FIXTURES
    # ========================================================================

    @pytest.fixture
    def planning_agent(self):
        """Create PlanningAgent with mock LLM"""
        return PlanningAgent(llm_client=MockLLMPlanning(), fallback_client=None)

    @pytest.fixture
    def decomposition_agent_3disk(self):
        """DecompositionAgent for 3-disk Hanoi"""
        return DecompositionAgent(llm_client=MockLLMDecomposition(problem_size=3))

    @pytest.fixture
    def decomposition_agent_4disk(self):
        """DecompositionAgent for 4-disk Hanoi"""
        return DecompositionAgent(llm_client=MockLLMDecomposition(problem_size=4))

    @pytest.fixture
    def decomposition_agent_graph(self):
        """DecompositionAgent for graph traversal"""
        return DecompositionAgent(llm_client=MockLLMDecomposition(problem_size="graph"))

    @pytest.fixture
    def execution_agent(self):
        """ExecutionAgent (symbolic only, no LLM needed)"""
        return ExecutionAgent(llm_client=None)

    @pytest.fixture
    def verification_agent(self):
        """VerificationAgent with mock LLM"""
        return VerificationAgent(llm_client=MockLLMVerification())

    @pytest.fixture
    def context_agent(self):
        """ContextAgent with mock LLM"""
        return ContextAgent(
            llm_client=MockLLMContext(),
            fallback_client=None,
            config={"max_history": 100},
        )

    @pytest.fixture
    def core_workflow_3disk(
        self, decomposition_agent_3disk, execution_agent, verification_agent
    ):
        """3-agent baseline workflow for 3-disk Hanoi"""
        return CoreWorkflow(
            decomposition_agent=decomposition_agent_3disk,
            execution_agent=execution_agent,
            verification_agent=verification_agent,
            max_retries=2,
        )

    @pytest.fixture
    def extended_workflow_3disk(
        self,
        planning_agent,
        decomposition_agent_3disk,
        execution_agent,
        verification_agent,
        context_agent,
    ):
        """5-agent extended workflow for 3-disk Hanoi"""
        return ExtendedWorkflow(
            planning_agent=planning_agent,
            decomposition_agent=decomposition_agent_3disk,
            execution_agent=execution_agent,
            verification_agent=verification_agent,
            context_agent=context_agent,
            max_retries=2,
        )

    @pytest.fixture
    def extended_workflow_4disk(
        self,
        planning_agent,
        decomposition_agent_4disk,
        execution_agent,
        verification_agent,
        context_agent,
    ):
        """5-agent extended workflow for 4-disk Hanoi"""
        return ExtendedWorkflow(
            planning_agent=planning_agent,
            decomposition_agent=decomposition_agent_4disk,
            execution_agent=execution_agent,
            verification_agent=verification_agent,
            context_agent=context_agent,
            max_retries=2,
        )

    # ========================================================================
    # TOWER OF HANOI E2E TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_hanoi_3disk_with_planning(self, extended_workflow_3disk):
        """Test 3-disk Hanoi with full 5-agent workflow"""

        result = await extended_workflow_3disk.process_task(
            {
                "task": "solve_hanoi(3, A, C, B)",
                "domain": "tower_of_hanoi",
                "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
                "goal": {"pegs": {"A": [], "B": [], "C": [3, 2, 1]}},
                "operators": {
                    "move_disk": {
                        "parameters": ["disk", "from", "to"],
                        "preconditions": ["disk_on_top"],
                        "effects": ["disk_moved"],
                    }
                },
                "optimal_steps": 7,
            }
        )

        # Print comprehensive results
        print("\n" + "=" * 70)
        print("  E2E TEST: 3-Disk Hanoi with 5-Agent Workflow")
        print("=" * 70)
        print(f"\n✅ Success: {result['success']}")
        print(f"✅ Goal Achieved: {result['goal_achieved']}")
        print(f"✅ Quality Score: {result['quality_score']:.1f}/100")
        print("\n⏱️  Performance:")
        print(f"   Total Time: {result['total_time_ms']:.1f}ms")
        print(f"   - Planning: {result['planning_time_ms']:.1f}ms")
        print(f"   - Decomposition: {result['decomposition_time_ms']:.1f}ms")
        print(f"   - Execution: {result['execution_time_ms']:.1f}ms")
        print(f"   - Verification: {result['verification_time_ms']:.1f}ms")
        print(f"   - Context Summary: {result['context_time_ms']:.1f}ms")

        planning = result.get("planning", {})
        print("\n🧠 Strategic Planning:")
        print(f"   Strategies Evaluated: {len(planning.get('strategies', []))}")
        print(f"   Recommended: {planning.get('recommended_strategy')}")
        print(f"   Confidence: {planning.get('confidence', 0):.2f}")

        print("\n📊 Execution:")
        print(f"   Plan Length: {len(result['plan'])} steps")
        print(f"   Final State: {result['final_state']['pegs']}")
        print(f"   Retry Count: {result['retry_count']}")

        context_summary = result.get("context", {})
        print("\n📝 Context Tracking:")
        print(
            f"   Interactions Logged: {context_summary.get('interaction_count', 'N/A')}"
        )
        print(
            f"   States Tracked: {context_summary.get('agent_statistics', {}).get('history_size', 'N/A')}"
        )
        print("=" * 70)

        # Assertions
        assert result["success"] is True
        assert result["goal_achieved"] is True
        assert result["quality_score"] >= 90
        assert result["final_state"]["pegs"]["C"] == [3, 2, 1]
        assert len(result["plan"]) == 7

        # Verify planning stage executed
        assert "planning" in result
        assert planning.get("recommended_strategy") is not None
        assert len(planning.get("strategies", [])) >= 1

        # Verify context tracking
        assert "context" in result

    @pytest.mark.asyncio
    async def test_hanoi_4disk_with_planning(self, extended_workflow_4disk):
        """Test 4-disk Hanoi with 5-agent workflow"""

        result = await extended_workflow_4disk.process_task(
            {
                "task": "solve_hanoi(4, A, C, B)",
                "domain": "tower_of_hanoi",
                "initial_state": {"pegs": {"A": [4, 3, 2, 1], "B": [], "C": []}},
                "goal": {"pegs": {"A": [], "B": [], "C": [4, 3, 2, 1]}},
                "operators": {
                    "move_disk": {
                        "parameters": ["disk", "from", "to"],
                        "preconditions": ["disk_on_top"],
                        "effects": ["disk_moved"],
                    }
                },
                "optimal_steps": 15,
            }
        )

        print("\n" + "=" * 70)
        print("  E2E TEST: 4-Disk Hanoi with 5-Agent Workflow")
        print("=" * 70)
        print(f"\n✅ Success: {result['success']}")
        print(f"✅ Goal Achieved: {result['goal_achieved']}")
        print(f"✅ Quality Score: {result['quality_score']:.1f}/100")
        print(f"✅ Plan Length: {len(result['plan'])} steps (optimal: 15)")
        print(f"✅ Final State: {result['final_state']['pegs']}")
        print("=" * 70)

        assert result["success"] is True
        assert result["goal_achieved"] is True
        assert len(result["plan"]) == 15
        assert result["final_state"]["pegs"]["C"] == [4, 3, 2, 1]

    # ========================================================================
    # PERFORMANCE COMPARISON TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_3agent_vs_5agent_comparison(
        self, core_workflow_3disk, extended_workflow_3disk
    ):
        """Compare 3-agent baseline vs 5-agent extended workflow"""

        task_input = {
            "task": "solve_hanoi(3, A, C, B)",
            "domain": "tower_of_hanoi",
            "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
            "goal": {"pegs": {"A": [], "B": [], "C": [3, 2, 1]}},
            "operators": {
                "move_disk": {
                    "parameters": ["disk", "from", "to"],
                    "preconditions": ["disk_on_top"],
                    "effects": ["disk_moved"],
                }
            },
            "optimal_steps": 7,
        }

        # Run 3-agent workflow
        result_3agent = await core_workflow_3disk.process_task(task_input)

        # Run 5-agent workflow
        result_5agent = await extended_workflow_3disk.process_task(task_input)

        print("\n" + "=" * 70)
        print("  PERFORMANCE COMPARISON: 3-Agent vs 5-Agent")
        print("=" * 70)

        print("\n📊 3-Agent Workflow (CoreWorkflow):")
        print(f"   Success: {result_3agent['success']}")
        print(f"   Quality: {result_3agent['quality_score']:.1f}")
        print(f"   Total Time: {result_3agent['total_time_ms']:.1f}ms")
        print("   Breakdown:")
        print(f"     - Decomposition: {result_3agent['decomposition_time_ms']:.1f}ms")
        print(f"     - Execution: {result_3agent['execution_time_ms']:.1f}ms")
        print(f"     - Verification: {result_3agent['verification_time_ms']:.1f}ms")

        print("\n📊 5-Agent Workflow (ExtendedWorkflow):")
        print(f"   Success: {result_5agent['success']}")
        print(f"   Quality: {result_5agent['quality_score']:.1f}")
        print(f"   Total Time: {result_5agent['total_time_ms']:.1f}ms")
        print("   Breakdown:")
        print(f"     - Planning: {result_5agent['planning_time_ms']:.1f}ms")
        print(f"     - Decomposition: {result_5agent['decomposition_time_ms']:.1f}ms")
        print(f"     - Execution: {result_5agent['execution_time_ms']:.1f}ms")
        print(f"     - Verification: {result_5agent['verification_time_ms']:.1f}ms")
        print(f"     - Context: {result_5agent['context_time_ms']:.1f}ms")

        overhead = result_5agent["total_time_ms"] - result_3agent["total_time_ms"]
        overhead_pct = (overhead / result_3agent["total_time_ms"]) * 100

        print("\n📈 Analysis:")
        print(f"   Overhead: +{overhead:.1f}ms (+{overhead_pct:.1f}%)")
        print(f"   Planning Cost: {result_5agent['planning_time_ms']:.1f}ms")
        print(f"   Context Cost: {result_5agent['context_time_ms']:.1f}ms")
        print(
            f"   Both Successful: {result_3agent['success'] and result_5agent['success']}"
        )
        print("=" * 70)

        # Both should succeed
        assert result_3agent["success"] is True
        assert result_5agent["success"] is True

        # 5-agent has planning stage
        assert "planning" in result_5agent
        assert "context" in result_5agent

        # 3-agent does NOT have planning/context
        assert "planning" not in result_3agent
        assert "context" not in result_3agent

    # ========================================================================
    # CONTEXT TRACKING TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_context_tracking_verification(self, extended_workflow_3disk):
        """Verify context agent tracks all workflow stages"""

        result = await extended_workflow_3disk.process_task(
            {
                "task": "solve_hanoi(3, A, C, B)",
                "domain": "tower_of_hanoi",
                "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
                "goal": {"pegs": {"A": [], "B": [], "C": [3, 2, 1]}},
                "operators": {
                    "move_disk": {
                        "parameters": ["disk", "from", "to"],
                        "preconditions": ["disk_on_top"],
                        "effects": ["disk_moved"],
                    }
                },
            }
        )

        context_summary = result.get("context", {})

        print("\n" + "=" * 70)
        print("  CONTEXT TRACKING VERIFICATION")
        print("=" * 70)
        print(f"\nContext Summary: {context_summary}")
        print("=" * 70)

        # Verify context summary exists
        assert "context" in result

        # Context agent should have tracked multiple stages
        # (The exact structure depends on ContextAgent implementation)
        assert context_summary is not None

    # ========================================================================
    # STATISTICS TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_extended_workflow_statistics(self, extended_workflow_3disk):
        """Test comprehensive statistics from 5-agent workflow"""

        # Process multiple tasks
        for i in range(3):
            await extended_workflow_3disk.process_task(
                {
                    "task": f"solve_hanoi(3, A, C, B)_{i}",
                    "domain": "tower_of_hanoi",
                    "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
                    "goal": {"pegs": {"A": [], "B": [], "C": [3, 2, 1]}},
                    "operators": {
                        "move_disk": {
                            "parameters": ["disk", "from", "to"],
                            "preconditions": ["disk_on_top"],
                            "effects": ["disk_moved"],
                        }
                    },
                }
            )

        stats = extended_workflow_3disk.get_statistics()

        print("\n" + "=" * 70)
        print("  EXTENDED WORKFLOW STATISTICS (3 tasks)")
        print("=" * 70)
        print("\nWorkflow Stats:")
        print(f"  Tasks Processed: {stats['tasks_processed']}")
        print(f"  Success Rate: {stats['success_rate']:.1%}")
        print(f"  Avg Total Time: {stats['avg_total_time_ms']:.1f}ms")
        print(f"  Avg Planning Time: {stats.get('avg_planning_time_ms', 0):.1f}ms")
        print(f"  Avg Context Time: {stats.get('avg_context_time_ms', 0):.1f}ms")

        print("\nPlanning Agent Stats:")
        planning_stats = stats.get("planning_agent_stats", {})
        print(f"  Plans Generated: {planning_stats.get('plans_generated', 0)}")
        print(f"  Avg Confidence: {planning_stats.get('avg_confidence', 0):.2f}")

        print("\nContext Agent Stats:")
        context_stats = stats.get("context_agent_stats", {})
        print(f"  Interactions Logged: {context_stats.get('interactions_logged', 0)}")
        print(f"  States Tracked: {context_stats.get('states_tracked', 0)}")
        print(f"  LLM Usage Rate: {context_stats.get('llm_usage_rate', 0):.1%}")
        print("=" * 70)

        # Verify stats structure
        assert stats["tasks_processed"] == 3
        assert stats["success_rate"] > 0
        assert "planning_agent_stats" in stats
        assert "context_agent_stats" in stats

    # ========================================================================
    # FULL REPORT TEST
    # ========================================================================

    @pytest.mark.asyncio
    async def test_extended_workflow_full_report(self, extended_workflow_3disk):
        """Test full report generation from extended workflow"""

        # Process task
        await extended_workflow_3disk.process_task(
            {
                "task": "solve_hanoi(3, A, C, B)",
                "domain": "tower_of_hanoi",
                "initial_state": {"pegs": {"A": [3, 2, 1], "B": [], "C": []}},
                "goal": {"pegs": {"A": [], "B": [], "C": [3, 2, 1]}},
                "operators": {
                    "move_disk": {
                        "parameters": ["disk", "from", "to"],
                        "preconditions": ["disk_on_top"],
                        "effects": ["disk_moved"],
                    }
                },
            }
        )

        # Get full report
        report = extended_workflow_3disk.get_full_report()

        print("\n" + "=" * 70)
        print("  FULL WORKFLOW REPORT")
        print("=" * 70)
        print(report)
        print("=" * 70)

        # Verify report structure
        assert isinstance(report, str)
        assert len(report) > 100
        assert "EXTENDED MULTI-AGENT WORKFLOW REPORT" in report or "5-AGENT" in report
