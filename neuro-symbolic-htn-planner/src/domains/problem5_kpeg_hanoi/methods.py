"""
HTN methods for Problem 5: Generalized K-Peg Hanoi.
"""

from typing import List, Dict
from .state import (
    KPegHanoiState,
    frame_stewart_algorithm,
    calculate_frame_stewart_split,
    get_frame_stewart_explanation,
)


class KPegHanoiMethods:
    """HTN decomposition strategies for K-peg Hanoi"""

    @staticmethod
    def naive_3peg_approach(state: KPegHanoiState) -> List[str]:
        """
        Naive approach: Ignore extra pegs, use standard 3-peg algorithm.

        This is what Phase 1/3 might do - doesn't know Frame-Stewart exists.
        Uses exponential 2^n-1 moves instead of optimal.

        For 5 disks: 31 moves (vs optimal 13)
        """
        # Simplified representation - would generate actual moves
        plan = [
            "# Naive: Use standard 3-peg algorithm (ignores auxiliary pegs)",
            "# This is highly suboptimal for 4+ pegs",
            "# Would require 2^5 - 1 = 31 moves",
            "# (Implementation would recursively generate all moves)",
            "# ... 31 move_disk operations ...",
            "check_goal()",
        ]
        return plan

    @staticmethod
    def frame_stewart_optimal(state: KPegHanoiState) -> List[str]:
        """
        Optimal approach: Use Frame-Stewart algorithm.

        This is what Phase 4B should do after "researching" the algorithm.

        Key steps:
        1. Calculate optimal split point
        2. Recursively apply Frame-Stewart strategy
        3. Use all available pegs efficiently

        For 5 disks, 4 pegs: 13 moves (optimal)
        """
        n = state.num_disks
        k = state.num_pegs

        optimal_i, optimal_moves = calculate_frame_stewart_split(n, k)

        plan = [
            "# Phase 4B: Frame-Stewart Algorithm",
            "",
            "# RESEARCH PHASE:",
            "# PlanningAgent discovers Frame-Stewart algorithm exists",
            "# Key insight: With 4+ pegs, can do MUCH better than 2^n-1",
            "",
            f"# For {n} disks, {k} pegs:",
            f"#   Naive (3-peg): {2**n - 1} moves",
            f"#   Optimal (Frame-Stewart): {optimal_moves} moves",
            f"#   Efficiency gain: {((2**n - 1 - optimal_moves) / (2**n - 1) * 100):.1f}%",
            "",
            "# STRATEGIC DECOMPOSITION:",
            f"#   Optimal split point: i = {optimal_i}",
            f"#   Strategy: Move top {optimal_i} disks → aux, bottom {n-optimal_i} → target, top {optimal_i} → target",
            "",
            "# EXECUTION:",
            f"# Step 1: Move top {optimal_i} disks to auxiliary (using all {k} pegs)",
            "# ... (recursive Frame-Stewart) ...",
            "",
            f"# Step 2: Move bottom {n-optimal_i} disks to target (using {k-1} pegs)",
            "# ... (recursive Frame-Stewart with k-1 pegs) ...",
            "",
            f"# Step 3: Move {optimal_i} disks from auxiliary to target (using all {k} pegs)",
            "# ... (recursive Frame-Stewart) ...",
            "",
            "check_goal()",
        ]
        return plan

    @staticmethod
    def format_problem_for_llm(state: KPegHanoiState) -> str:
        """Format problem description for LLM planning"""
        output = "GENERALIZED K-PEG TOWER OF HANOI\n"
        output += "=" * 50 + "\n\n"

        output += f"Configuration: {state.num_disks} disks, {state.num_pegs} pegs\n"
        output += f"Goal: Move all disks from peg {state.source_peg} to peg {state.target_peg}\n\n"

        output += "Current State:\n"
        for peg, disks in sorted(state.pegs.items()):
            output += f"  Peg {peg}: {disks}\n"

        output += "\nRules:\n"
        output += "  1. Can only move one disk at a time\n"
        output += "  2. Cannot place larger disk on smaller disk\n"
        output += "  3. Can use ANY of the available pegs\n\n"

        output += "Available Actions:\n"
        output += "  - move_disk(from_peg, to_peg)\n"
        output += "  - check_goal()\n\n"

        output += "Challenge:\n"
        output += f"  Standard 3-peg solution: {2**state.num_disks - 1} moves\n"
        output += f"  With {state.num_pegs} pegs, can do MUCH better!\n"
        output += "  Hint: Look up 'Frame-Stewart algorithm'\n\n"

        output += "Key Question:\n"
        output += "  How can you leverage the extra pegs to minimize moves?\n"
        output += "  This requires strategic decomposition - not obvious!\n"

        return output

    @staticmethod
    def provide_algorithm_hint() -> str:
        """
        Provide Frame-Stewart algorithm explanation.

        This simulates what PlanningAgent would find via "research".
        """
        return get_frame_stewart_explanation()

    @staticmethod
    def analyze_solution_quality(state: KPegHanoiState) -> Dict:
        """
        Analyze the quality of the solution.
        """
        if not state.is_goal_reached():
            return {"success": False, "plan_quality_score": 0}

        actual_moves = len(state.moves_history)
        optimal_moves = frame_stewart_algorithm(state.num_disks, state.num_pegs)
        naive_moves = 2**state.num_disks - 1

        analysis = {
            "success": True,
            "actual_moves": actual_moves,
            "optimal_moves": optimal_moves,
            "naive_moves": naive_moves,
            "efficiency_vs_optimal": f"{(actual_moves / optimal_moves * 100):.1f}%",
            "efficiency_vs_naive": f"{(actual_moves / naive_moves * 100):.1f}%",
        }

        # Plan Quality Score (0-100)
        if actual_moves == optimal_moves:
            analysis["plan_quality_score"] = 100  # Perfect - used Frame-Stewart
            analysis["strategy"] = "Frame-Stewart (optimal)"
        elif actual_moves <= optimal_moves + 5:
            analysis["plan_quality_score"] = 80  # Good
            analysis["strategy"] = "Near-optimal"
        elif actual_moves == naive_moves:
            analysis["plan_quality_score"] = 30  # Suboptimal - used 3-peg approach
            analysis["strategy"] = "Naive 3-peg (ignored extra pegs)"
        elif actual_moves < naive_moves:
            # Somewhere between optimal and naive
            ratio = (naive_moves - actual_moves) / (naive_moves - optimal_moves)
            analysis["plan_quality_score"] = int(30 + ratio * 50)
            analysis["strategy"] = "Partial optimization"
        else:
            analysis["plan_quality_score"] = 10  # Worse than naive
            analysis["strategy"] = "Inefficient"

        return analysis


# Helper function to actually generate Frame-Stewart moves (for testing)
def generate_frame_stewart_moves(
    n: int, source: str, target: str, pegs: List[str]
) -> List[str]:
    """
    Generate actual move sequence using Frame-Stewart algorithm.

    Args:
        n: Number of disks
        source: Source peg
        target: Target peg
        pegs: List of all available pegs

    Returns:
        List of move commands
    """
    if n == 0:
        return []

    k = len(pegs)

    if k == 3:
        # Standard 3-peg Hanoi
        if n == 1:
            return [f"move_disk({source}, {target})"]

        # Find auxiliary peg
        aux = [p for p in pegs if p not in [source, target]][0]

        moves = []
        moves.extend(generate_frame_stewart_moves(n - 1, source, aux, pegs))
        moves.append(f"move_disk({source}, {target})")
        moves.extend(generate_frame_stewart_moves(n - 1, aux, target, pegs))
        return moves

    # Frame-Stewart for k >= 4
    if n == 1:
        return [f"move_disk({source}, {target})"]

    # Calculate optimal split
    optimal_i, _ = calculate_frame_stewart_split(n, k)

    # Choose auxiliary peg for top i disks
    aux = [p for p in pegs if p not in [source, target]][0]

    # Remaining pegs for bottom (n-i) disks
    remaining_pegs = [p for p in pegs if p != aux]

    moves = []

    # Move top i disks to auxiliary (using all k pegs)
    moves.extend(generate_frame_stewart_moves(optimal_i, source, aux, pegs))

    # Move bottom (n-i) disks to target (using k-1 pegs, excluding aux)
    moves.extend(
        generate_frame_stewart_moves(n - optimal_i, source, target, remaining_pegs)
    )

    # Move i disks from auxiliary to target (using all k pegs)
    moves.extend(generate_frame_stewart_moves(optimal_i, aux, target, pegs))

    return moves


def get_decomposition_methods() -> Dict[str, callable]:
    """Get dictionary of available decomposition strategies"""
    return {
        "naive": KPegHanoiMethods.naive_3peg_approach,
        "optimal": KPegHanoiMethods.frame_stewart_optimal,
    }
