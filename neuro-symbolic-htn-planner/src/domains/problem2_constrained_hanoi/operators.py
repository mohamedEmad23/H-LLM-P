"""
Primitive operators for Constrained Tower of Hanoi problem.
"""

from typing import Tuple
from copy import deepcopy
from .state import HanoiState


class HanoiOperators:
    """Primitive actions for constrained Hanoi"""

    @staticmethod
    def move_disk(
        state: HanoiState, disk: int, from_peg: str, to_peg: str
    ) -> Tuple[bool, HanoiState, str]:
        """
        Move a disk from one peg to another.

        Preconditions:
        - Disk must be on top of from_peg
        - Cannot place larger disk on smaller disk
        - CONSTRAINT: Disk 3 cannot be placed on fragile peg B

        Effects:
        - Removes disk from from_peg
        - Adds disk to to_peg
        - Records move in history
        - Records violation if constraint broken

        Returns:
            (success, new_state, message)
        """
        # Check if move is valid
        can_move, reason = state.can_move_disk(disk, from_peg, to_peg)

        if not can_move:
            # Check if this is a constraint violation
            if "CONSTRAINT VIOLATION" in reason:
                # Record violation but don't execute move
                new_state = deepcopy(state)
                new_state.violations.append(reason)
                return False, new_state, reason
            else:
                # Invalid move (Hanoi rules)
                return False, state, reason

        # Execute move
        new_state = deepcopy(state)

        # Remove from source peg
        new_state.pegs[from_peg].pop()

        # Add to target peg
        new_state.pegs[to_peg].append(disk)

        # Record move
        new_state.moves.append((disk, from_peg, to_peg))

        message = f"Moved disk {disk} from {from_peg} to {to_peg}"
        return True, new_state, message

    @staticmethod
    def check_constraint(state: HanoiState) -> Tuple[bool, HanoiState, str]:
        """
        Check if current state violates the fragile peg constraint.

        Returns:
            (constraint_satisfied, state, message)
        """
        # Check if forbidden disk is on fragile peg
        if state.forbidden_disk in state.pegs.get(state.fragile_peg, []):
            msg = f"⚠️  CONSTRAINT VIOLATED: Disk {state.forbidden_disk} is on fragile peg {state.fragile_peg}!"
            return False, state, msg

        msg = f"✓ Constraint satisfied: Disk {state.forbidden_disk} not on peg {state.fragile_peg}"
        return True, state, msg

    @staticmethod
    def check_goal(state: HanoiState) -> Tuple[bool, HanoiState, str]:
        """
        Check if goal is reached and constraints are satisfied.

        Returns:
            (goal_reached, state, message)
        """
        goal_reached = state.is_goal_reached()
        has_violations = state.has_violations()

        if goal_reached and not has_violations:
            msg = f"✓ Goal reached! All disks on peg {state.target_peg}. Moves: {len(state.moves)}"
            return True, state, msg

        if goal_reached and has_violations:
            msg = f"⚠️  Goal reached but with {len(state.violations)} constraint violations!"
            return False, state, msg

        if has_violations:
            msg = f"⚠️  Not at goal. {len(state.violations)} violations recorded."
            return False, state, msg

        # Not at goal
        disks_on_target = len(state.pegs[state.target_peg])
        msg = f"Not at goal. {disks_on_target}/3 disks on target peg {state.target_peg}"
        return False, state, msg

    @staticmethod
    def get_valid_moves(state: HanoiState) -> list:
        """
        Get all valid moves from current state.

        Returns:
            List of (disk, from_peg, to_peg) tuples
        """
        valid_moves = []

        for from_peg in ["A", "B", "C"]:
            top_disk = state.get_top_disk(from_peg)
            if top_disk is None:
                continue

            for to_peg in ["A", "B", "C"]:
                if from_peg == to_peg:
                    continue

                can_move, _ = state.can_move_disk(top_disk, from_peg, to_peg)
                if can_move:
                    valid_moves.append((top_disk, from_peg, to_peg))

        return valid_moves


def get_applicable_operators(state: HanoiState):
    """
    Get list of applicable operators for current state.

    Returns:
        List of (operator_name, operator_function, args)
    """
    applicable = []

    # Always can check constraint and goal
    applicable.append(("check_constraint", HanoiOperators.check_constraint, [state]))
    applicable.append(("check_goal", HanoiOperators.check_goal, [state]))

    # All valid moves
    for disk, from_peg, to_peg in HanoiOperators.get_valid_moves(state):
        applicable.append(
            (
                f"move_disk_{disk}_{from_peg}_to_{to_peg}",
                HanoiOperators.move_disk,
                [state, disk, from_peg, to_peg],
            )
        )

    return applicable
