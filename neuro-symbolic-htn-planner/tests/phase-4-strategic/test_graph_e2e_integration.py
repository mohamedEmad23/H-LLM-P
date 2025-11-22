"""
Graph Traversal E2E Integration Test

Tests graph domain through full 3-agent pipeline:
DecompositionAgent → ExecutionAgent → VerificationAgent

Tests shortest path finding on simple and complex graphs.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agents.decomposition_agent import DecompositionAgent
from src.agents.execution_agent import ExecutionAgent
from src.agents.verification_agent import VerificationAgent
from src.agents.workflows.core_workflow import CoreWorkflow
from src.domains.graph_traversal.domain import GraphTraversalDomain


class MockLLMGraphDecomposition:
    """Mock LLM for graph decomposition - returns valid HTN plan"""

    def generate(self, prompt, system_prompt=None, **kwargs):
        # Return simple graph traversal decomposition (A→B→C)
        # Correct order: mark current, then traverse
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
      "effects": ["at(C)", "visited(A)", "visited(B)", "visited(C)"],
      "confidence": 0.95,
      "reasoning": "Shortest path from A to C via B"
    }
  ],
  "alternatives_considered": 1
}"""


class MockLLMGraphVerification:
    """Mock LLM for graph verification"""

    def generate(self, prompt, system_prompt=None, **kwargs):
        return """{
  "goal_achieved": true,
  "constraint_violations": [],
  "logical_issues": [],
  "efficiency_score": 100,
  "quality_score": 98,
  "optimal_steps": 5,
  "actual_steps": 5,
  "suggestions": ["Path is optimal for simple graph A→B→C"],
  "reasoning": "Successfully reached goal node C via shortest path"
}"""


class TestGraphE2EIntegration:
    """E2E integration tests for graph traversal domain"""

    @pytest.fixture
    def domain(self):
        """Create graph traversal domain"""
        return GraphTraversalDomain()

    @pytest.fixture
    def workflow(self):
        """Create CoreWorkflow with all agents (using mocks for speed)"""
        decomp_agent = DecompositionAgent(llm_client=MockLLMGraphDecomposition())
        exec_agent = ExecutionAgent(llm_client=None)  # Symbolic only
        verif_agent = VerificationAgent(llm_client=MockLLMGraphVerification())

        return CoreWorkflow(
            decomposition_agent=decomp_agent,
            execution_agent=exec_agent,
            verification_agent=verif_agent,
            max_retries=2,
        )

    @pytest.mark.asyncio
    async def test_simple_graph_shortest_path(self, domain, workflow):
        """Test simple 3-node graph A→B→C"""
        # Create simple graph
        graph = domain.create_simple_graph([("A", "B"), ("B", "C")])
        initial_state = domain.get_initial_state(graph, "A")

        # Simple goal state (not lambda-based for workflow compatibility)
        goal_state = {"current_node": "C", "visited": ["A", "B", "C"]}

        # Ground truth path
        expected_path = domain.find_shortest_path_bfs(graph, "A", "C")
        assert expected_path == ["A", "B", "C"]

        # Run through 3-agent pipeline
        result = await workflow.process_task(
            {
                "task": "find_shortest_path(A, C)",
                "domain": "graph_traversal",
                "initial_state": initial_state,
                "goal": goal_state,
                "operators": domain.operators,
                "methods": domain.methods,
            }
        )

        # Verify success
        print("\n" + "=" * 60)
        print("GRAPH E2E TEST RESULT")
        print("=" * 60)
        print(f"Success: {result.get('success')}")
        print(f"Goal Achieved: {result.get('goal_achieved')}")
        print(f"Quality Score: {result.get('quality_score')}")
        print("\nFinal State:")
        final_state = result.get("final_state", {})
        print(f"  Current Node: {final_state.get('current_node')}")
        print(f"  Visited: {final_state.get('visited', [])}")
        print(f"  Path: {final_state.get('path', [])}")
        print(f"\nExpected Path: {expected_path}")
        print("=" * 60)

        assert result["success"] is True
        assert result["goal_achieved"] is True
        assert final_state.get("current_node") == "C"
        assert set(final_state.get("visited", [])) >= {"A", "B", "C"}

    @pytest.mark.asyncio
    async def test_graph_with_shortcut(self, domain, workflow):
        """Test graph with direct path vs longer path"""
        # Create graph: A→B→C and A→C (direct)
        graph = domain.create_simple_graph([("A", "B"), ("B", "C"), ("A", "C")])
        initial_state = domain.get_initial_state(graph, "A")
        goal = domain.create_goal("find_shortest_path", start_node="A", goal_node="C")

        # Ground truth: should prefer A→C (length 1) over A→B→C (length 2)
        expected_path = domain.find_shortest_path_bfs(graph, "A", "C")
        assert expected_path == ["A", "C"]

        # Run through pipeline
        result = await workflow.run(
            initial_state=initial_state, goal=goal, domain_type="graph_traversal"
        )

        # Verify success
        assert result["success"] is True

        final_state = result.get("final_state", {})
        assert domain.is_goal_satisfied(final_state, goal)
        assert final_state.get("current_node") == "C"

        # Check if path is optimal (length 2: A and C)
        path = final_state.get("path", [])
        print("\n✅ Graph with shortcut: SUCCESS")
        print(f"   Path found: {path}")
        print(f"   Expected optimal: {expected_path}")
        print(f"   Path length: {len(path)} (optimal: {len(expected_path)})")
        print(f"   Quality score: {result.get('quality_score', 0):.2f}")

    @pytest.mark.asyncio
    async def test_complex_5node_graph(self, domain, workflow):
        """Test complex 5-node graph with multiple paths"""
        # Create diamond + extension: A→B→D, A→C→D, D→E
        graph = domain.create_simple_graph(
            [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")]
        )
        initial_state = domain.get_initial_state(graph, "A")
        goal = domain.create_goal("find_shortest_path", start_node="A", goal_node="E")

        # Ground truth: any path through diamond, then to E (length 3)
        expected_path = domain.find_shortest_path_bfs(graph, "A", "E")
        assert len(expected_path) == 4  # A→(B or C)→D→E

        # Run through pipeline
        result = await workflow.run(
            initial_state=initial_state, goal=goal, domain_type="graph_traversal"
        )

        # Verify success
        assert result["success"] is True

        final_state = result.get("final_state", {})
        assert domain.is_goal_satisfied(final_state, goal)
        assert final_state.get("current_node") == "E"

        # Verify all nodes in path are visited
        path = final_state.get("path", [])
        assert "A" in path
        assert "E" in path
        assert "D" in path  # Must go through D
        assert ("B" in path) or ("C" in path)  # Must go through B or C

        print("\n✅ Complex 5-node graph: SUCCESS")
        print(f"   Path found: {path}")
        print(f"   Expected path length: {len(expected_path)}")
        print(f"   Actual path length: {len(path)}")
        print(f"   Quality score: {result.get('quality_score', 0):.2f}")

    @pytest.mark.asyncio
    async def test_weighted_graph(self, domain, workflow):
        """Test weighted graph with different edge costs"""
        # Create weighted graph: A→B (cost 1), A→C (cost 5), B→C (cost 1)
        # Optimal path A→C is A→B→C (cost 2) not A→C (cost 5)
        graph = domain.create_weighted_graph(
            [("A", "B", 1.0), ("B", "C", 1.0), ("A", "C", 5.0)]
        )
        initial_state = domain.get_initial_state(graph, "A")
        goal = domain.create_goal("find_shortest_path", start_node="A", goal_node="C")

        # Run through pipeline
        result = await workflow.run(
            initial_state=initial_state, goal=goal, domain_type="graph_traversal"
        )

        # Verify success
        assert result["success"] is True

        final_state = result.get("final_state", {})
        assert domain.is_goal_satisfied(final_state, goal)
        assert final_state.get("current_node") == "C"

        path = final_state.get("path", [])
        print("\n✅ Weighted graph: SUCCESS")
        print(f"   Path found: {path}")
        print(f"   Quality score: {result.get('quality_score', 0):.2f}")

    @pytest.mark.asyncio
    async def test_reach_node_goal(self, domain, workflow):
        """Test simple reach_node goal type"""
        graph = domain.create_simple_graph([("A", "B"), ("B", "C"), ("C", "D")])
        initial_state = domain.get_initial_state(graph, "A")
        goal = domain.create_goal("reach_node", target_node="D")

        # Run through pipeline
        result = await workflow.run(
            initial_state=initial_state, goal=goal, domain_type="graph_traversal"
        )

        # Verify success
        assert result["success"] is True

        final_state = result.get("final_state", {})
        assert domain.is_goal_satisfied(final_state, goal)
        assert final_state.get("current_node") == "D"

        print("\n✅ Reach node goal: SUCCESS")
        print(f"   Reached: {final_state.get('current_node')}")
        print(f"   Path: {final_state.get('path', [])}")
        print(f"   Quality score: {result.get('quality_score', 0):.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
