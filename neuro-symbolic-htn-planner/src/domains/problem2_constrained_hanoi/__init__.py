"""
Problem 2: Constrained Tower of Hanoi

Tests the system's ability to modify known algorithms based on hard constraints.

Problem Description:
- Standard 3-disk Tower of Hanoi: Move from Peg A to Peg C
- Constraint: Disk 3 (largest) can NEVER be placed on Peg B (fragile peg)
- Disks 1 and 2 can use Peg B normally

Testing Purpose:
- Phase 1 (CoT+HTN): Will generate standard Hanoi algorithm, violating constraint → 0% success
- Phase 3 (3-Agent): DecompositionAgent might fail, trying to solve recursion + constraint together
- Phase 4B (5-Agent): PlanningAgent analyzes constraint BEFORE decomposition, creates modified strategy

Expected Phase 4B Strategy:
1. Move 2-disk sub-tower from A → B (allowed)
2. Move disk 3 from A → C (direct, bypasses fragile B)
3. Move 2-disk sub-tower from B → C (allowed)
"""

from .state import HanoiState, create_constrained_hanoi
from .operators import HanoiOperators
from .methods import HanoiMethods

# Convenience exports for operators
move_disk = HanoiOperators.move_disk

# Alias for consistency
ConstrainedHanoiMethods = HanoiMethods

__all__ = [
    'HanoiState', 'HanoiOperators', 'HanoiMethods', 'ConstrainedHanoiMethods',
    'create_constrained_hanoi', 'move_disk'
]
