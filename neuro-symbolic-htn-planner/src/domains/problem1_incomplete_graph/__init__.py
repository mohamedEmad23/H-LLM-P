"""
Problem 1: Incomplete Knowledge Graph Traversal

Tests the system's ability to handle knowledge gaps and research missing information.

Problem Description:
- Find shortest path from A to D, must pass through B
- Edge(A,B) = 4, Edge(B,C) = UNKNOWN, Edge(C,D) = 5, Edge(A,C) = 15
- System must call research tool to discover weight(B,C) = 8
- Optimal path: A → B → C → D (total: 4+8+5=17)

Testing Purpose:
- Phase 1: Tests if single LLM can identify gap AND research value (likely fails/hallucinates)
- Phase 3: Tests modular planning - DecompositionAgent must create plan with explicit research step
- Phase 4B: Tests PlanningAgent identifying knowledge gap before decomposition
"""

from .state import GraphState, create_incomplete_graph
from .operators import GraphOperators
from .methods import GraphMethods

# Convenience exports for operators
research_unknown_edge = GraphOperators.research_unknown_edge
move_to_node = GraphOperators.move_to_node
check_for_unknown_edges = GraphOperators.check_for_unknown_edges

# Alias for consistency
IncompleteGraphMethods = GraphMethods

__all__ = [
    'GraphState', 'GraphOperators', 'GraphMethods', 'IncompleteGraphMethods',
    'create_incomplete_graph', 'research_unknown_edge', 'move_to_node',
    'check_for_unknown_edges'
]
