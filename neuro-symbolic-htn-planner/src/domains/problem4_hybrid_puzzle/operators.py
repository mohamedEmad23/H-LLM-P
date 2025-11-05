"""
Primitive operators for Problem 4: Hybrid Hanoi-Graph Puzzle.
"""

from typing import Tuple
from copy import deepcopy
from .state import HybridPuzzleState, get_shortest_path


class HybridPuzzleOperators:
    """Primitive actions for hybrid puzzle"""

    @staticmethod
    def start_unlocking(
        state: HybridPuzzleState, peg: str
    ) -> Tuple[bool, HybridPuzzleState, str]:
        """
        Begin solving the unlock graph for a peg.

        This transitions from "Hanoi mode" to "graph mode".
        """
        if peg not in state.unlock_graphs:
            return False, state, f"No unlock graph for peg {peg}"

        if state.is_peg_unlocked(peg):
            return False, state, f"Peg {peg} already unlocked"

        graph = state.unlock_graphs[peg]

        new_state = deepcopy(state)
        new_state.solving_for_peg = peg
        new_state.current_location = graph.start_node

        return (
            True,
            new_state,
            f"Started solving unlock graph for peg {peg} at node {graph.start_node}",
        )

    @staticmethod
    def move_in_graph(
        state: HybridPuzzleState, to_node: str
    ) -> Tuple[bool, HybridPuzzleState, str]:
        """
        Move to a node in the unlock graph.
        """
        if state.solving_for_peg is None:
            return False, state, "Not currently solving an unlock graph"

        graph = state.unlock_graphs[state.solving_for_peg]
        current = state.current_location

        # Check if edge exists
        if to_node not in graph.edges.get(current, []):
            return False, state, f"No edge from {current} to {to_node}"

        new_state = deepcopy(state)
        new_state.current_location = to_node

        edge_cost = graph.edge_costs.get((current, to_node), 1)
        new_state.unlock_graphs[state.solving_for_peg].solution_path.append(to_node)
        new_state.unlock_graphs[state.solving_for_peg].solution_cost += edge_cost

        msg = f"Moved {current} → {to_node} (cost: {edge_cost})"

        # Check if reached goal
        if to_node == graph.goal_node:
            new_state.unlock_graphs[state.solving_for_peg].unlocked = True
            new_state.unlocked_pegs.add(state.solving_for_peg)
            new_state.solving_for_peg = None
            new_state.current_location = None

            total_cost = new_state.unlock_graphs[state.solving_for_peg].solution_cost
            msg += (
                f" → Unlocked peg {state.solving_for_peg}! (Total cost: {total_cost})"
            )

        return True, new_state, msg

    @staticmethod
    def solve_unlock_graph(
        state: HybridPuzzleState, peg: str, use_optimal: bool = True
    ) -> Tuple[bool, HybridPuzzleState, str]:
        """
        Solve the unlock graph for a peg in one step.

        Args:
            use_optimal: If True, find and use shortest path. If False, use direct path.

        This abstracts away the graph solving details, useful for testing.
        """
        if peg not in state.unlock_graphs:
            return False, state, f"No unlock graph for peg {peg}"

        if state.is_peg_unlocked(peg):
            return False, state, f"Peg {peg} already unlocked"

        graph = state.unlock_graphs[peg]

        if use_optimal:
            path, cost = get_shortest_path(graph)
            strategy = "optimal"
        else:
            # Use direct path (if exists)
            if graph.goal_node in graph.edges.get(graph.start_node, []):
                path = [graph.start_node, graph.goal_node]
                cost = graph.edge_costs.get((graph.start_node, graph.goal_node), 1)
                strategy = "direct (suboptimal)"
            else:
                path, cost = get_shortest_path(graph)
                strategy = "fallback to optimal"

        new_state = deepcopy(state)
        new_state.unlock_graphs[peg].solution_path = path
        new_state.unlock_graphs[peg].solution_cost = cost
        new_state.unlock_graphs[peg].unlocked = True
        new_state.unlocked_pegs.add(peg)

        path_str = " → ".join(path)
        return (
            True,
            new_state,
            f"Solved unlock graph for peg {peg} using {strategy} path: {path_str} (cost: {cost})",
        )

    @staticmethod
    def move_disk(
        state: HybridPuzzleState, from_peg: str, to_peg: str
    ) -> Tuple[bool, HybridPuzzleState, str]:
        """
        Move top disk from one peg to another.

        Preconditions checked via state.can_move_disk().
        """
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
    def check_goal(state: HybridPuzzleState) -> Tuple[bool, HybridPuzzleState, str]:
        """Check if goal reached"""
        if not state.is_goal_reached():
            return False, state, f"Goal not reached. Current: {state.to_dict()['pegs']}"

        total_moves = len(state.moves_history)
        unlock_cost = sum(
            g.solution_cost for g in state.unlock_graphs.values() if g.unlocked
        )

        msg = "✓ Goal reached!\n"
        msg += f"  Hanoi moves: {total_moves}\n"
        msg += f"  Unlock cost: {unlock_cost}\n"
        msg += f"  Total operations: {total_moves + unlock_cost}"

        return True, state, msg


def get_applicable_operators(state: HybridPuzzleState):
    """Get list of applicable operators"""
    applicable = []

    # If solving unlock graph
    if state.solving_for_peg:
        graph = state.unlock_graphs[state.solving_for_peg]
        current = state.current_location

        for neighbor in graph.edges.get(current, []):
            applicable.append(
                (
                    f"move_in_graph({neighbor})",
                    HybridPuzzleOperators.move_in_graph,
                    [neighbor],
                )
            )
    else:
        # Can start unlocking locked pegs
        for peg, graph in state.unlock_graphs.items():
            if not state.is_peg_unlocked(peg):
                applicable.append(
                    (
                        f"start_unlocking({peg})",
                        HybridPuzzleOperators.start_unlocking,
                        [peg],
                    )
                )
                applicable.append(
                    (
                        f"solve_unlock_graph({peg}, optimal)",
                        HybridPuzzleOperators.solve_unlock_graph,
                        [peg, True],
                    )
                )

        # Can move disks between unlocked pegs
        for from_peg in state.pegs:
            if state.pegs[from_peg] and state.is_peg_unlocked(from_peg):
                for to_peg in state.pegs:
                    if to_peg != from_peg:
                        can_move, _ = state.can_move_disk(from_peg, to_peg)
                        if can_move:
                            applicable.append(
                                (
                                    f"move_disk({from_peg}, {to_peg})",
                                    HybridPuzzleOperators.move_disk,
                                    [from_peg, to_peg],
                                )
                            )

    # Always can check goal
    applicable.append(("check_goal()", HybridPuzzleOperators.check_goal, []))

    return applicable
