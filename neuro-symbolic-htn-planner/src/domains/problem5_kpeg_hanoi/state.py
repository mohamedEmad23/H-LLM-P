"""
State representation for Problem 5: Generalized K-Peg Hanoi.

This is the classic multi-peg Tower of Hanoi problem. With 4+ pegs, the optimal
solution requires the Frame-Stewart algorithm, which is non-obvious.
"""

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class KPegHanoiState:
    """State for K-peg Tower of Hanoi"""

    pegs: Dict[str, List[int]]  # Peg name -> stack of disks (bottom to top)
    num_disks: int
    num_pegs: int
    source_peg: str
    target_peg: str
    auxiliary_pegs: List[str]
    moves_history: List[str] = field(default_factory=list)

    def can_move_disk(self, from_peg: str, to_peg: str) -> tuple[bool, str]:
        """
        Check if a disk can be moved.

        Preconditions:
        1. From peg has at least one disk
        2. Smaller-on-larger rule (if to peg has disks)
        """
        if not self.pegs.get(from_peg):
            return False, f"No disk on peg {from_peg}"

        disk_to_move = self.pegs[from_peg][-1]

        if self.pegs.get(to_peg) and disk_to_move > self.pegs[to_peg][-1]:
            return (
                False,
                f"Cannot place disk {disk_to_move} on smaller disk {self.pegs[to_peg][-1]}",
            )

        return True, "OK"

    def is_goal_reached(self) -> bool:
        """Check if all disks are on the target peg"""
        return len(self.pegs.get(self.target_peg, [])) == self.num_disks and all(
            len(self.pegs.get(p, [])) == 0 for p in self.pegs if p != self.target_peg
        )

    def to_dict(self) -> Dict:
        """Convert state to dictionary"""
        return {
            "pegs": {k: list(v) for k, v in self.pegs.items()},
            "num_disks": self.num_disks,
            "num_pegs": self.num_pegs,
            "moves": len(self.moves_history),
            "goal_reached": self.is_goal_reached(),
        }


def create_kpeg_hanoi(num_disks: int = 5, num_pegs: int = 4) -> KPegHanoiState:
    """
    Create standard K-peg Hanoi instance.

    Default: 5 disks, 4 pegs (A, B, C, D)
    - Source: A
    - Target: D
    - Auxiliary: B, C

    Optimal solution requires Frame-Stewart algorithm:
    - 3 pegs (standard): 2^n - 1 = 31 moves
    - 4 pegs (Frame-Stewart): 13 moves

    This demonstrates the HUGE advantage of knowing the algorithm.
    """
    peg_names = ["A", "B", "C", "D", "E", "F", "G", "H"][:num_pegs]

    pegs = {name: [] for name in peg_names}
    pegs["A"] = list(range(num_disks, 0, -1))  # [5, 4, 3, 2, 1]

    auxiliary = [p for p in peg_names if p not in ["A", "D"]]

    return KPegHanoiState(
        pegs=pegs,
        num_disks=num_disks,
        num_pegs=num_pegs,
        source_peg="A",
        target_peg="D",
        auxiliary_pegs=auxiliary,
    )


def frame_stewart_algorithm(n: int, k: int) -> int:
    """
    Calculate optimal number of moves for n disks and k pegs.

    Frame-Stewart Algorithm:
    - For k = 3: T(n, 3) = 2^n - 1
    - For k >= 4: T(n, k) = min over i in [1..n-1] of (2*T(i, k) + T(n-i, k-1))

    This is the KEY insight that Phase 4B should discover via "research".
    """
    # Use memoization for efficiency
    memo = {}

    def T(disks, pegs):
        if (disks, pegs) in memo:
            return memo[(disks, pegs)]

        # Base cases
        if disks == 0:
            return 0
        if disks == 1:
            return 1
        if pegs == 3:
            return 2**disks - 1

        # Frame-Stewart: try all split points
        min_moves = 999999  # Large number instead of inf
        for i in range(1, disks):
            moves = 2 * T(i, pegs) + T(disks - i, pegs - 1)
            min_moves = min(min_moves, moves)

        memo[(disks, pegs)] = min_moves
        return int(min_moves)

    return int(T(n, k))


def get_frame_stewart_explanation() -> str:
    """
    Return explanation of Frame-Stewart algorithm.

    This is what Phase 4B's PlanningAgent should "research" and discover.
    """
    explanation = """
FRAME-STEWART ALGORITHM (Multi-Peg Tower of Hanoi)

Problem: Move n disks from source to target using k pegs (k >= 4)

Key Insight:
  For 3 pegs: T(n) = 2^n - 1 (exponential)
  For 4+ pegs: Can do MUCH better by using auxiliary pegs strategically

Algorithm:
  1. Choose optimal split point i (where 1 <= i < n)
  2. Move top i disks to auxiliary peg (using all k pegs)
  3. Move bottom (n-i) disks to target (using k-1 pegs, excluding auxiliary)
  4. Move i disks from auxiliary to target (using all k pegs)

Recurrence:
  T(n, k) = min over i in [1..n-1] of (2*T(i, k) + T(n-i, k-1))

For 5 disks, 4 pegs:
  Optimal split: i = 3
  T(5, 4) = 2*T(3, 4) + T(2, 3)
          = 2*5 + 3
          = 13 moves

Compare to naive 3-peg approach:
  T(5, 3) = 2^5 - 1 = 31 moves

Efficiency gain: 13 vs 31 moves (58% reduction!)
"""
    return explanation


def calculate_frame_stewart_split(n: int, k: int) -> tuple[int, int]:
    """
    Calculate optimal split point for Frame-Stewart.

    Returns:
        (optimal_i, total_moves)
    """
    best_i = 1
    best_moves = 999999  # Large number instead of inf

    for i in range(1, n):
        moves_i = frame_stewart_algorithm(i, k)
        moves_rest = frame_stewart_algorithm(n - i, k - 1)
        total = 2 * moves_i + moves_rest

        if total < best_moves:
            best_moves = total
            best_i = i

    return best_i, int(best_moves)
