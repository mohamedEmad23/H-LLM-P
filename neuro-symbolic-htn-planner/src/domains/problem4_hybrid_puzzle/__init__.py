"""
Problem 4: Hybrid Hanoi-Graph Puzzle

Tests task specialization and hierarchical planning.

Problem Description:
- Solve 2-disk Tower of Hanoi (A → C)
- BUT peg C is LOCKED - requires solving unlock graph first
- Unlock graph has optimal path (cost 10) and suboptimal path (cost 15)

Testing Purpose:
- Phase 1: Tries to move to locked peg, fails → 0% success
- Phase 3: Decomposes into tasks (unlock, then Hanoi) but uses suboptimal unlock → Linear plan
- Phase 4B: Hierarchical planning - analyzes unlock graph, chooses optimal path → High quality
"""

from .state import HybridPuzzleState, create_hybrid_puzzle, UnlockGraph, get_shortest_path
from .operators import HybridPuzzleOperators, get_applicable_operators
from .methods import HybridPuzzleMethods, get_decomposition_methods

# Expose operator methods
solve_unlock_graph = HybridPuzzleOperators.solve_unlock_graph
move_disk = HybridPuzzleOperators.move_disk
start_unlocking = HybridPuzzleOperators.start_unlocking
move_in_graph = HybridPuzzleOperators.move_in_graph
check_goal = HybridPuzzleOperators.check_goal

__all__ = [
    'HybridPuzzleState',
    'HybridPuzzleOperators',
    'HybridPuzzleMethods',
    'create_hybrid_puzzle',
    'UnlockGraph',
    'get_shortest_path',
    'solve_unlock_graph',
    'move_disk',
    'start_unlocking',
    'move_in_graph',
    'check_goal',
    'get_applicable_operators',
    'get_decomposition_methods'
]
