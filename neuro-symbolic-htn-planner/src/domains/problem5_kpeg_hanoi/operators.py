"""
Primitive operators for Problem 5: Generalized K-Peg Hanoi.
"""

from typing import Tuple
from copy import deepcopy
from .state import KPegHanoiState


class KPegHanoiOperators:
    """Primitive actions for K-peg Hanoi"""

    @staticmethod
    def move_disk(
        state: KPegHanoiState, from_peg: str, to_peg: str
    ) -> Tuple[bool, KPegHanoiState, str]:
        """Move top disk from one peg to another"""
        can_move, reason = state.can_move_disk(from_peg, to_peg)

        if not can_move:
            return False, state, reason

        new_state = deepcopy(state)
        disk = new_state.pegs[from_peg].pop()
        new_state.pegs.setdefault(to_peg, []).append(disk)

        move_desc = f"Move disk {disk}: {from_peg} → {to_peg}"
        new_state.moves_history.append(move_desc)

        return True, new_state, move_desc

    @staticmethod
    def check_goal(state: KPegHanoiState) -> Tuple[bool, KPegHanoiState, str]:
        """Check if goal reached"""
        if not state.is_goal_reached():
            return False, state, f"Goal not reached. Current: {state.to_dict()['pegs']}"

        total_moves = len(state.moves_history)

        # Calculate optimal moves using Frame-Stewart
        from .state import frame_stewart_algorithm

        optimal_moves = frame_stewart_algorithm(state.num_disks, state.num_pegs)

        # For comparison, calculate 3-peg solution
        naive_moves = 2**state.num_disks - 1

        msg = "✓ Goal reached!\n"
        msg += f"  Total moves: {total_moves}\n"
        msg += f"  Optimal (Frame-Stewart): {optimal_moves}\n"
        msg += f"  Naive (3-peg): {naive_moves}\n"

        if total_moves == optimal_moves:
            msg += "  ⭐ OPTIMAL SOLUTION!"
        elif total_moves <= optimal_moves + 5:
            msg += "  Good (within 5 of optimal)"
        elif total_moves == naive_moves:
            msg += "  Used naive 3-peg approach (suboptimal)"
        else:
            msg += "  Suboptimal"

        return True, state, msg


def get_applicable_operators(state: KPegHanoiState):
    """Get list of applicable operators"""
    applicable = []

    # Can move any disk between pegs (if legal)
    for from_peg in state.pegs:
        if state.pegs[from_peg]:  # Has disks
            for to_peg in state.pegs:
                if to_peg != from_peg:
                    can_move, _ = state.can_move_disk(from_peg, to_peg)
                    if can_move:
                        applicable.append(
                            (
                                f"move_disk({from_peg}, {to_peg})",
                                KPegHanoiOperators.move_disk,
                                [from_peg, to_peg],
                            )
                        )

    # Always can check goal
    applicable.append(("check_goal()", KPegHanoiOperators.check_goal, []))

    return applicable
