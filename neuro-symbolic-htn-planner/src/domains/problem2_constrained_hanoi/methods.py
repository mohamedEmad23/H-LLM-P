"""
HTN methods for Constrained Tower of Hanoi problem.
"""

from typing import List, Dict
from .state import HanoiState


class HanoiMethods:
    """HTN decomposition strategies for constrained Hanoi"""

    @staticmethod
    def standard_hanoi(state: HanoiState) -> List[str]:
        """
        Standard Tower of Hanoi algorithm (WILL VIOLATE CONSTRAINT).

        This is what Phase 1 will likely generate.
        It follows the classic recursive pattern without considering the fragile peg.

        For 3 disks A→C:
        1. Move sub-tower (1,2) from A to B (uses B as auxiliary)
        2. Move disk 3 from A to C
        3. Move sub-tower (1,2) from B to C (uses A as auxiliary)

        This FAILS because step 1 requires moving disk 3's sub-tower to B,
        which means disk 3 must go through B in standard algorithm.
        """
        plan = [
            "# Standard Hanoi Algorithm (WILL FAIL)",
            "move_disk(1, A, C)",
            "move_disk(2, A, B)",
            "move_disk(1, C, B)",
            "move_disk(3, A, C)",  # This is OK
            "# But we needed to clear B first, which violated constraint",
            "move_disk(1, B, A)",
            "move_disk(2, B, C)",
            "move_disk(1, A, C)",
            "check_goal()",
        ]
        return plan

    @staticmethod
    def constraint_aware_hanoi(state: HanoiState) -> List[str]:
        """
        Constraint-aware algorithm (CORRECT).

        This is what Phase 4B should generate after PlanningAgent analyzes constraint.

        Strategy:
        1. Move 2-disk sub-tower from A to B (allowed, since disk 3 stays on A)
        2. Move disk 3 directly from A to C (bypasses fragile B)
        3. Move 2-disk sub-tower from B to C

        This satisfies the constraint: disk 3 never touches peg B.
        """
        plan = [
            "# Phase 1: Move sub-tower (1,2) from A to B",
            "move_disk(1, A, B)",
            "move_disk(2, A, C)",  # Using C as auxiliary
            "move_disk(1, B, C)",
            "move_disk(2, C, B)",  # Now 2-disk tower is on B
            "move_disk(1, C, B)",  # Complete: both disks 1,2 on B
            "# Phase 2: Move disk 3 from A to C (bypasses fragile B!)",
            "move_disk(3, A, C)",
            "# Phase 3: Move sub-tower (1,2) from B to C",
            "move_disk(1, B, A)",  # Using A as auxiliary
            "move_disk(2, B, C)",
            "move_disk(1, A, C)",
            "check_goal()",
        ]
        return plan

    @staticmethod
    def brute_force_search(state: HanoiState) -> List[str]:
        """
        Simulated breadth-first search approach.

        Phase 3 might use this - try to search through valid moves
        without strategic planning.
        """
        plan = [
            "# BFS-style exploration",
            "check_constraint()",
            "# ... explore valid moves avoiding constraint violations ...",
            "# This would eventually find a solution but inefficiently",
        ]
        return plan

    @staticmethod
    def format_problem_for_llm(state: HanoiState) -> str:
        """
        Format problem description for LLM planning.

        This is what gets sent to LLM in each phase.
        """
        output = "CONSTRAINED TOWER OF HANOI PROBLEM\n"
        output += "=" * 50 + "\n\n"

        output += f"Goal: Move all disks from Peg {state.source_peg} to Peg {state.target_peg}\n\n"

        output += "⚠️  CRITICAL CONSTRAINT:\n"
        output += f"  Disk {state.forbidden_disk} (largest) can NEVER be placed on Peg {state.fragile_peg}\n"
        output += f"  Peg {state.fragile_peg} is FRAGILE and cannot support disk {state.forbidden_disk}\n"
        output += f"  All other disks can use Peg {state.fragile_peg} normally.\n\n"

        output += "Current State:\n"
        for peg in ["A", "B", "C"]:
            marker = " ⚠️  FRAGILE" if peg == state.fragile_peg else ""
            output += f"  Peg {peg}{marker}: {state.pegs[peg]}\n"

        output += f"\nMoves so far: {len(state.moves)}\n"

        if state.violations:
            output += f"\n⚠️  Constraint Violations: {len(state.violations)}\n"
            for v in state.violations:
                output += f"  - {v}\n"

        output += "\nHanoi Rules:\n"
        output += "  1. Only one disk can be moved at a time\n"
        output += "  2. Only the top disk from a peg can be moved\n"
        output += "  3. A larger disk cannot be placed on a smaller disk\n"
        output += f"  4. CONSTRAINT: Disk {state.forbidden_disk} cannot use Peg {state.fragile_peg}\n"

        output += "\nAvailable Actions:\n"
        output += "  - move_disk(disk_number, from_peg, to_peg)\n"
        output += "  - check_constraint() - Verify constraint satisfaction\n"
        output += "  - check_goal() - Check if all disks on target peg\n"

        output += "\nOptimal Solution Hints:\n"
        output += "  Standard Hanoi: 2^n - 1 = 7 moves (but violates constraint!)\n"
        output += "  Constraint-aware: Requires modified strategy\n"
        output += "  Hint: Move sub-tower to B first, then disk 3 directly to C\n"

        return output

    @staticmethod
    def analyze_constraint(state: HanoiState) -> Dict[str, any]:
        """
        Strategic analysis of the constraint.

        This is what Phase 4B's PlanningAgent should do.

        Returns:
            Analysis dictionary with strategy recommendation
        """
        analysis = {
            "problem_type": "Constrained Tower of Hanoi",
            "constraint": f"Disk {state.forbidden_disk} cannot use Peg {state.fragile_peg}",
            "standard_algorithm_valid": False,
            "reason": "Standard Hanoi uses all pegs as auxiliary, will violate constraint",
            "recommended_strategy": "constraint_aware_hanoi",
            "strategic_insight": [
                f"Phase 1: Move smaller disks to {state.fragile_peg} (allowed)",
                f"Phase 2: Move disk {state.forbidden_disk} directly to target (bypasses fragile peg)",
                f"Phase 3: Move smaller disks from {state.fragile_peg} to target",
            ],
            "expected_moves": 7,  # For 3-disk constrained case
            "complexity": "Requires strategic planning before decomposition",
        }
        return analysis


def get_decomposition_methods() -> Dict[str, callable]:
    """
    Get dictionary of available decomposition strategies.

    Returns:
        Dict mapping strategy name to method function
    """
    return {
        "standard_hanoi": HanoiMethods.standard_hanoi,
        "constraint_aware": HanoiMethods.constraint_aware_hanoi,
        "brute_force": HanoiMethods.brute_force_search,
    }
