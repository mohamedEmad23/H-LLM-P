"""
State representation for Problem 4: Hybrid Hanoi-Graph Puzzle.

Combines Tower of Hanoi with unlock graphs. Pegs are locked initially and require
solving small graph traversal problems to unlock them before disks can be moved.
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class UnlockGraph:
    """Represents a graph that must be traversed to unlock a peg"""
    peg_name: str
    start_node: str
    goal_node: str
    edges: Dict[str, List[str]]  # Adjacency list
    edge_costs: Dict[tuple, int]  # (from, to) -> cost
    unlocked: bool = False
    solution_path: List[str] = field(default_factory=list)
    solution_cost: int = 0
    
    def is_solved(self) -> bool:
        """Check if this unlock graph has been solved"""
        return self.unlocked


@dataclass
class HybridPuzzleState:
    """State for hybrid Hanoi-Graph puzzle"""
    pegs: Dict[str, List[int]]  # Peg name -> stack of disks
    unlock_graphs: Dict[str, UnlockGraph]  # Peg name -> unlock graph
    current_location: Optional[str] = None  # Current graph node (if solving unlock)
    solving_for_peg: Optional[str] = None  # Which peg we're unlocking
    moves_history: List[str] = field(default_factory=list)
    unlocked_pegs: Set[str] = field(default_factory=set)
    
    def is_peg_unlocked(self, peg: str) -> bool:
        """Check if a peg is unlocked"""
        return peg in self.unlocked_pegs
    
    def can_move_disk(self, from_peg: str, to_peg: str) -> tuple[bool, str]:
        """
        Check if a disk can be moved from one peg to another.
        
        Preconditions:
        1. From peg is unlocked
        2. From peg has at least one disk
        3. To peg is unlocked
        4. Smaller-on-larger rule (if to peg has disks)
        """
        # Check if from peg is unlocked
        if not self.is_peg_unlocked(from_peg):
            return False, f"Peg {from_peg} is locked! Must solve unlock graph first."
        
        # Check if from peg has disks
        if not self.pegs.get(from_peg):
            return False, f"No disk on peg {from_peg}"
        
        # Check if to peg is unlocked
        if not self.is_peg_unlocked(to_peg):
            return False, f"Peg {to_peg} is locked! Must solve unlock graph first."
        
        # Check smaller-on-larger rule
        disk_to_move = self.pegs[from_peg][-1]
        if self.pegs.get(to_peg) and disk_to_move > self.pegs[to_peg][-1]:
            return False, f"Cannot place disk {disk_to_move} on smaller disk {self.pegs[to_peg][-1]}"
        
        return True, "OK"
    
    def is_goal_reached(self) -> bool:
        """Check if all disks are on the target peg"""
        # Goal: All disks on peg C
        return len(self.pegs.get("C", [])) == 2 and not self.pegs.get("A") and not self.pegs.get("B")
    
    def to_dict(self) -> Dict:
        """Convert state to dictionary"""
        return {
            'pegs': {k: list(v) for k, v in self.pegs.items()},
            'unlocked_pegs': list(self.unlocked_pegs),
            'moves_history': self.moves_history,
            'solving_for_peg': self.solving_for_peg,
            'goal_reached': self.is_goal_reached()
        }


def create_hybrid_puzzle() -> HybridPuzzleState:
    """
    Create the standard Problem 4 instance.
    
    Setup:
    - 2 disks on peg A
    - Pegs A, B unlocked initially
    - Peg C is LOCKED - requires solving unlock graph
    
    Unlock Graph for Peg C:
        N1 --5--> N2 --5--> N3 (Goal)
        |                   ^
        +--------15---------+
    
    Optimal solution: N1 → N2 → N3 (cost 10)
    Naive solution: N1 → N3 (cost 15)
    
    Expected Behavior:
    - Phase 1: May try to move disks to locked peg C → fail → 0% success
    - Phase 3: DecompositionAgent separates tasks (solve graph, then Hanoi) → linear plan
    - Phase 4B: PlanningAgent creates hierarchical strategy:
      1. Solve unlock graph optimally (N1→N2→N3)
      2. Then solve Hanoi (A→C)
    """
    # Unlock graph for peg C
    unlock_graph_c = UnlockGraph(
        peg_name="C",
        start_node="N1",
        goal_node="N3",
        edges={
            "N1": ["N2", "N3"],
            "N2": ["N3"],
            "N3": []
        },
        edge_costs={
            ("N1", "N2"): 5,
            ("N1", "N3"): 15,  # Direct path (suboptimal)
            ("N2", "N3"): 5
        }
    )
    
    return HybridPuzzleState(
        pegs={
            "A": [2, 1],  # Disk 2 (bottom), Disk 1 (top)
            "B": [],
            "C": []
        },
        unlock_graphs={
            "C": unlock_graph_c
        },
        unlocked_pegs={"A", "B"}  # A and B start unlocked
    )


def get_shortest_path(graph: UnlockGraph) -> tuple[List[str], int]:
    """
    Find shortest path in unlock graph using BFS.
    
    Returns:
        (path, cost)
    """
    from collections import deque
    
    if graph.start_node == graph.goal_node:
        return [graph.start_node], 0
    
    queue = deque([(graph.start_node, [graph.start_node], 0)])
    visited = {graph.start_node}
    best_path = None
    best_cost = float('inf')
    
    while queue:
        current, path, cost = queue.popleft()
        
        for neighbor in graph.edges.get(current, []):
            edge_cost = graph.edge_costs.get((current, neighbor), 1)
            new_cost = cost + edge_cost
            new_path = path + [neighbor]
            
            if neighbor == graph.goal_node:
                if new_cost < best_cost:
                    best_cost = new_cost
                    best_path = new_path
            elif neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, new_path, new_cost))
    
    return best_path if best_path else [], best_cost if best_path else float('inf')
