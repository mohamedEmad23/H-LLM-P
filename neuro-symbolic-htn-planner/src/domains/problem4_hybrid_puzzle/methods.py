"""
HTN methods for Problem 4: Hybrid Hanoi-Graph Puzzle.
"""

from typing import List, Dict
from .state import HybridPuzzleState


class HybridPuzzleMethods:
    """HTN decomposition strategies for hybrid puzzle"""

    @staticmethod
    def naive_sequential(state: HybridPuzzleState) -> List[str]:
        """
        Naive approach: Try Hanoi moves first, fail, then unlock.

        This is what Phase 1 might do - doesn't recognize dependencies.
        Will fail immediately when trying to move to locked peg C.

        Expected result: 0% success (blocked by locked peg)
        """
        plan = [
            "# Naive: Try to move directly to C (FAILS - locked)",
            "move_disk(A, C)",  # Will fail
            "# Then realize need to unlock",
            "solve_unlock_graph(C, optimal=True)",
            "# Try again",
            "move_disk(A, C)",
            "check_goal()",
        ]
        return plan

    @staticmethod
    def linear_decomposition(state: HybridPuzzleState) -> List[str]:
        """
        Linear approach: Solve tasks sequentially.

        This is what Phase 3 might do:
        1. Identify locked pegs
        2. Unlock them
        3. Then solve Hanoi

        Works but no optimization of graph solving.
        """
        plan = [
            "# Phase 3 Linear: Decompose into subtasks",
            "# Task 1: Unlock all locked pegs",
            "solve_unlock_graph(C, optimal=False)",  # Uses direct path (suboptimal)
            "# Task 2: Solve 2-disk Hanoi (A → C)",
            "move_disk(A, B)",  # Disk 1: A → B
            "move_disk(A, C)",  # Disk 2: A → C
            "move_disk(B, C)",  # Disk 1: B → C
            "check_goal()",
        ]
        return plan

    @staticmethod
    def hierarchical_planning(state: HybridPuzzleState) -> List[str]:
        """
        Hierarchical approach: Strategic decomposition with optimization.

        This is what Phase 4B should do:
        1. PlanningAgent analyzes dependencies
        2. Finds optimal unlock strategy (shortest path in graph)
        3. Integrates unlock + Hanoi optimally

        Expected: Unlock C optimally (N1→N2→N3, cost 10), then Hanoi
        """
        plan = [
            "# Phase 4B Hierarchical: Strategic analysis",
            "# Strategic Step 1: Analyze unlock graph",
            "# Graph has two paths:",
            "#   Direct: N1 → N3 (cost 15)",
            "#   Optimal: N1 → N2 → N3 (cost 10)",
            "# PlanningAgent chooses optimal",
            "solve_unlock_graph(C, optimal=True)",  # Optimal path
            "# Strategic Step 2: Solve Hanoi with unlocked pegs",
            "# Standard 2-disk solution (3 moves)",
            "move_disk(A, B)",  # Disk 1: A → B
            "move_disk(A, C)",  # Disk 2: A → C
            "move_disk(B, C)",  # Disk 1: B → C
            "check_goal()",
        ]
        return plan

    @staticmethod
    def format_problem_for_llm(state: HybridPuzzleState) -> str:
        """Format problem description for LLM planning"""
        output = "HYBRID HANOI-GRAPH PUZZLE\n"
        output += "=" * 50 + "\n\n"

        output += "Goal: Move all disks from peg A to peg C\n\n"

        output += "Current State:\n"
        for peg, disks in sorted(state.pegs.items()):
            status = "UNLOCKED" if state.is_peg_unlocked(peg) else "LOCKED"
            output += f"  Peg {peg}: {disks} ({status})\n"

        output += "\nRules:\n"
        output += "  1. Can only move one disk at a time\n"
        output += "  2. Cannot place larger disk on smaller disk\n"
        output += "  3. LOCKED pegs cannot be used until unlocked\n\n"

        output += "Unlock Graphs:\n"
        for peg, graph in state.unlock_graphs.items():
            if not state.is_peg_unlocked(peg):
                output += f"\n  Peg {peg} Unlock Graph:\n"
                output += f"    Start: {graph.start_node}\n"
                output += f"    Goal: {graph.goal_node}\n"
                output += "    Edges:\n"
                for from_node, neighbors in graph.edges.items():
                    for to_node in neighbors:
                        cost = graph.edge_costs.get((from_node, to_node), 1)
                        output += f"      {from_node} --{cost}--> {to_node}\n"

                # Show path options
                output += "\n    Path Options:\n"
                output += f"      Direct: {graph.start_node} → {graph.goal_node} "
                direct_cost = graph.edge_costs.get(
                    (graph.start_node, graph.goal_node), "N/A"
                )
                output += f"(cost: {direct_cost})\n"

                if "N2" in graph.edges.get(graph.start_node, []):
                    via_cost = graph.edge_costs.get(
                        (graph.start_node, "N2"), 0
                    ) + graph.edge_costs.get(("N2", graph.goal_node), 0)
                    output += (
                        f"      Via N2: {graph.start_node} → N2 → {graph.goal_node} "
                    )
                    output += f"(cost: {via_cost})\n"

        output += "\n\nAvailable Actions:\n"
        output += "  - solve_unlock_graph(peg, optimal=True/False)\n"
        output += "  - move_disk(from_peg, to_peg)\n"
        output += "  - check_goal()\n"

        output += "\nKey Challenge:\n"
        output += "  Must FIRST unlock peg C before moving disks to it.\n"
        output += "  Choose optimal path in unlock graph to minimize cost.\n"

        return output

    @staticmethod
    def analyze_solution_quality(state: HybridPuzzleState) -> Dict:
        """
        Analyze the quality of the solution.

        Optimal solution:
        - Unlock cost: 10 (optimal path N1→N2→N3)
        - Hanoi moves: 3
        - Total: 13 operations
        """
        if not state.is_goal_reached():
            return {"success": False, "plan_quality_score": 0}

        hanoi_moves = len(state.moves_history)
        unlock_cost = sum(
            g.solution_cost for g in state.unlock_graphs.values() if g.unlocked
        )
        total_cost = hanoi_moves + unlock_cost

        # Optimal solution analysis
        # optimal_unlock = 10  # N1 → N2 → N3
        # optimal_hanoi = 3  # Standard 2-disk solution
        optimal_total = 13

        analysis = {
            "success": True,
            "hanoi_moves": hanoi_moves,
            "unlock_cost": unlock_cost,
            "total_cost": total_cost,
            "optimal_total": optimal_total,
            "unlock_strategy": "optimal" if unlock_cost == 10 else "suboptimal",
        }

        # Plan Quality Score (0-100)
        if total_cost == optimal_total:
            analysis["plan_quality_score"] = 100  # Perfect
        elif total_cost <= optimal_total + 5:
            analysis["plan_quality_score"] = 80  # Good
        elif total_cost <= optimal_total + 10:
            analysis["plan_quality_score"] = 60  # Acceptable
        else:
            analysis["plan_quality_score"] = 30  # Suboptimal

        return analysis


def get_decomposition_methods() -> Dict[str, callable]:
    """Get dictionary of available decomposition strategies"""
    return {
        "naive": HybridPuzzleMethods.naive_sequential,
        "linear": HybridPuzzleMethods.linear_decomposition,
        "hierarchical": HybridPuzzleMethods.hierarchical_planning,
    }
