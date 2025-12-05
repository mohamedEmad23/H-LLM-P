"""
Problem 3: Probabilistic Graph Traversal

Tests the system's ability to make optimal trade-off decisions under uncertainty.

Problem Description:
- Find path from Start to End with lowest EXPECTED time
- Path 1 (Safe): Start → A → End (guaranteed 30 min)
- Path 2 (Risky): Start → B → End (10 min base + 50% chance of +30 min penalty)

Testing Purpose:
- Phase 1 (CoT+HTN): Will see "10 min" vs "30 min", choose Path 2, ignoring probability → Low plan quality
- Phase 3 (3-Agent): DecompositionAgent not an analyst, will also fail → Low plan quality
- Phase 4B (5-Agent): PlanningAgent performs expected value calculation:
  * Path 1: 30 min
  * Path 2: 0.5*10 + 0.5*40 = 25 min
  * Should choose Path 2 (strategic analysis) → High plan quality
"""

from .state import ProbabilisticGraphState, create_probabilistic_graph
from .operators import ProbabilisticGraphOperators, get_applicable_operators
from .methods import ProbabilisticGraphMethods, get_decomposition_methods

# Expose operator methods as module-level functions for convenience
choose_path = ProbabilisticGraphOperators.choose_path
traverse_to_end = ProbabilisticGraphOperators.traverse_to_end
calculate_expected_values = ProbabilisticGraphOperators.calculate_expected_values
check_goal = ProbabilisticGraphOperators.check_goal

__all__ = [
    "ProbabilisticGraphState",
    "ProbabilisticGraphOperators",
    "ProbabilisticGraphMethods",
    "create_probabilistic_graph",
    "choose_path",
    "traverse_to_end",
    "calculate_expected_values",
    "check_goal",
    "get_applicable_operators",
    "get_decomposition_methods",
]
