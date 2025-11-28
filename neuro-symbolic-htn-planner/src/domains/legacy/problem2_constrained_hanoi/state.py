"""
State representation for Constrained Tower of Hanoi problem.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class HanoiState:
    """State of the constrained Tower of Hanoi problem"""

    # Peg configurations (peg_name -> list of disks, bottom to top)
    pegs: Dict[str, List[int]] = field(default_factory=dict)

    # Source and target pegs
    source_peg: str = "A"
    target_peg: str = "C"

    # Constraint: Which disk cannot be placed on which peg
    fragile_peg: str = "B"
    forbidden_disk: int = 3  # Largest disk

    # Move history
    moves: List[Tuple[int, str, str]] = field(
        default_factory=list
    )  # (disk, from_peg, to_peg)

    # Constraint violation tracking
    violations: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate state after initialization"""
        if not self.pegs:
            # Default initialization: all disks on source peg
            self.pegs = {
                "A": [3, 2, 1],  # Bottom to top
                "B": [],
                "C": [],
            }

    def get_top_disk(self, peg: str) -> Optional[int]:
        """Get the top disk from a peg (None if empty)"""
        if peg not in self.pegs or not self.pegs[peg]:
            return None
        return self.pegs[peg][-1]

    def can_move_disk(self, disk: int, from_peg: str, to_peg: str) -> Tuple[bool, str]:
        """
        Check if a disk can be moved from one peg to another.

        Returns:
            (can_move, reason)
        """
        # Check if disk is on from_peg
        if from_peg not in self.pegs or disk not in self.pegs[from_peg]:
            return False, f"Disk {disk} is not on peg {from_peg}"

        # Check if disk is on top
        if self.pegs[from_peg][-1] != disk:
            return False, f"Disk {disk} is not on top of peg {from_peg}"

        # Check fragile peg constraint
        if disk == self.forbidden_disk and to_peg == self.fragile_peg:
            return (
                False,
                f"CONSTRAINT VIOLATION: Disk {disk} cannot be placed on fragile peg {to_peg}",
            )

        # Check Hanoi rule: larger disk cannot be on top of smaller disk
        top_disk = self.get_top_disk(to_peg)
        if top_disk is not None and disk > top_disk:
            return False, f"Cannot place larger disk {disk} on smaller disk {top_disk}"

        return True, "Move is valid"

    def is_goal_reached(self) -> bool:
        """Check if all disks are on target peg"""
        return self.pegs[self.target_peg] == [3, 2, 1]

    def has_violations(self) -> bool:
        """Check if any constraint violations occurred"""
        return len(self.violations) > 0

    def to_dict(self) -> Dict:
        """Convert state to dictionary"""
        return {
            "pegs": {k: list(v) for k, v in self.pegs.items()},
            "source": self.source_peg,
            "target": self.target_peg,
            "fragile_peg": self.fragile_peg,
            "forbidden_disk": self.forbidden_disk,
            "moves": [(d, f, t) for d, f, t in self.moves],
            "move_count": len(self.moves),
            "violations": self.violations,
            "goal_reached": self.is_goal_reached(),
        }

    def visualize(self) -> str:
        """ASCII visualization of current state"""
        output = "\n"
        output += "=" * 40 + "\n"
        output += "CONSTRAINED TOWER OF HANOI\n"
        output += "=" * 40 + "\n\n"

        for peg_name in ["A", "B", "C"]:
            marker = ""
            if peg_name == self.fragile_peg:
                marker = f" ⚠️  FRAGILE (Disk {self.forbidden_disk} forbidden)"
            output += f"Peg {peg_name}:{marker}\n"

            if self.pegs[peg_name]:
                for disk in reversed(self.pegs[peg_name]):  # Top to bottom
                    output += f"  {'─' * (disk * 2)} {disk} {'─' * (disk * 2)}\n"
            else:
                output += "  (empty)\n"
            output += "\n"

        output += f"Moves: {len(self.moves)}\n"
        if self.violations:
            output += f"⚠️  Violations: {len(self.violations)}\n"
        output += "=" * 40 + "\n"

        return output


def create_constrained_hanoi(num_disks: int = 3, fragile_peg: str = "B") -> HanoiState:
    """
    Create the standard Problem 2 instance.

    Args:
        num_disks: Number of disks (default 3)
        fragile_peg: The peg that largest disk cannot use (default "B")

    Returns:
        Initial state with all disks on peg A
    """
    pegs = {
        "A": list(range(num_disks, 0, -1)),  # [3, 2, 1] for num_disks=3
        "B": [],
        "C": [],
    }

    return HanoiState(
        pegs=pegs,
        source_peg="A",
        target_peg="C",
        fragile_peg=fragile_peg,
        forbidden_disk=num_disks,  # Largest disk
    )


def calculate_optimal_moves(num_disks: int, has_constraint: bool = False) -> int:
    """
    Calculate optimal number of moves for Tower of Hanoi.

    Standard Hanoi: 2^n - 1
    Constrained (disk 3 cannot use B):
        - Move sub-tower (disks 1,2) from A to B: 2^2 - 1 = 3 moves
        - Move disk 3 from A to C: 1 move
        - Move sub-tower (disks 1,2) from B to C: 2^2 - 1 = 3 moves
        - Total: 3 + 1 + 3 = 7 moves
    """
    if not has_constraint:
        return 2**num_disks - 1

    if num_disks == 3:
        return 7  # Special case for constrained 3-disk

    # General formula for constrained case
    sub_tower = num_disks - 1
    return 2 * (2**sub_tower - 1) + 1
