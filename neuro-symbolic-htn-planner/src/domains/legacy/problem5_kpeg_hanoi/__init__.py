"""
Problem 5: Generalized K-Peg Tower of Hanoi

Tests strategic synthesis and algorithm discovery.

Problem Description:
- Move 5 disks from peg A to peg D using 4 pegs (A, B, C, D)
- Standard 3-peg solution: 2^5 - 1 = 31 moves
- Optimal (Frame-Stewart): 13 moves (58% reduction!)

Testing Purpose:
- Phase 1: Uses naive 3-peg algorithm (ignores extra pegs) → 31 moves, 30/100 quality
- Phase 3: Still uses naive approach (doesn't know Frame-Stewart exists) → 31 moves, 30/100 quality
- Phase 4B: PlanningAgent "researches" Frame-Stewart algorithm, applies it → 13 moves, 100/100 quality
"""

from .state import (
    KPegHanoiState,
    create_kpeg_hanoi,
    frame_stewart_algorithm,
    get_frame_stewart_explanation,
)
from .operators import KPegHanoiOperators, get_applicable_operators
from .methods import (
    KPegHanoiMethods,
    get_decomposition_methods,
    generate_frame_stewart_moves,
)

# Expose operator methods
move_disk = KPegHanoiOperators.move_disk
check_goal = KPegHanoiOperators.check_goal

__all__ = [
    "KPegHanoiState",
    "KPegHanoiOperators",
    "KPegHanoiMethods",
    "create_kpeg_hanoi",
    "frame_stewart_algorithm",
    "get_frame_stewart_explanation",
    "move_disk",
    "check_goal",
    "get_applicable_operators",
    "get_decomposition_methods",
    "generate_frame_stewart_moves",
]
