"""
Primitive operators for Probabilistic Graph Traversal problem.
"""

from typing import Tuple
from copy import deepcopy
from .state import ProbabilisticGraphState, analyze_paths


class ProbabilisticGraphOperators:
    """Primitive actions for probabilistic graph traversal"""

    @staticmethod
    def choose_path(
        state: ProbabilisticGraphState, intermediate_node: str
    ) -> Tuple[bool, ProbabilisticGraphState, str]:
        """
        Choose a path (safe or risky).

        This is the KEY decision point. Once chosen, cannot go back.

        Args:
            intermediate_node: Either "A" (safe) or "B" (risky)

        Returns:
            (success, new_state, message)
        """
        if state.chosen_route is not None:
            return False, state, "Path already chosen! Cannot change decision."

        if intermediate_node not in ["A", "B"]:
            return False, state, f"Invalid intermediate node: {intermediate_node}"

        new_state = deepcopy(state)

        if intermediate_node == "A":
            new_state.chosen_route = "safe"
            new_state.current_node = "A"
            new_state.path_taken.append("A")
            msg = "Chose SAFE path (Start → A → End)"
        else:  # "B"
            new_state.chosen_route = "risky"
            new_state.current_node = "B"
            new_state.path_taken.append("B")
            msg = "Chose RISKY path (Start → B → End)"

        return True, new_state, msg

    @staticmethod
    def traverse_to_end(
        state: ProbabilisticGraphState, simulate: bool = False, seed: int = 42
    ) -> Tuple[bool, ProbabilisticGraphState, str]:
        """
        Complete the journey to End node.

        Args:
            simulate: If True, simulates actual traversal time (for validation)
            seed: Random seed for simulation

        Returns:
            (success, new_state, message)
        """
        if state.chosen_route is None:
            return False, state, "Must choose a path first!"

        if state.current_node not in ["A", "B"]:
            return False, state, f"Invalid current node: {state.current_node}"

        edge = state.get_edge(state.current_node, "End")
        if not edge:
            return False, state, f"No edge from {state.current_node} to End"

        new_state = deepcopy(state)
        new_state.current_node = "End"
        new_state.path_taken.append("End")

        # Calculate expected time
        expected = edge.get_expected_time()
        new_state.elapsed_time = int(expected)

        msg = f"Traveled from {state.current_node} to End"

        if simulate:
            actual_time, penalty = edge.simulate_traversal(seed)
            new_state.simulated_time = actual_time
            new_state.penalty_occurred = penalty

            if penalty:
                msg += f" - Penalty occurred! Actual time: {actual_time} min"
            else:
                msg += f" - No penalty. Actual time: {actual_time} min"
        else:
            msg += f" - Expected time: {expected} min"

        return True, new_state, msg

    @staticmethod
    def calculate_expected_values(
        state: ProbabilisticGraphState,
    ) -> Tuple[bool, ProbabilisticGraphState, str]:
        """
        Perform expected value calculation for all paths.

        This is what Phase 4B's PlanningAgent should do BEFORE choosing.

        Returns:
            (success, new_state_with_analysis, message)
        """
        analysis = analyze_paths(state)

        new_state = deepcopy(state)

        if "safe_path" in analysis:
            new_state.expected_values_calculated["safe"] = analysis["safe_path"][
                "expected_time"
            ]

        if "risky_path" in analysis:
            new_state.expected_values_calculated["risky"] = analysis["risky_path"][
                "expected_time"
            ]

        msg = "Expected Value Analysis:\n"
        if "safe_path" in analysis:
            msg += f"  Safe Path: {analysis['safe_path']['calculation']} = {analysis['safe_path']['expected_time']} min\n"
        if "risky_path" in analysis:
            msg += f"  Risky Path: {analysis['risky_path']['calculation']} = {analysis['risky_path']['expected_time']} min\n"

        if "recommendation" in analysis:
            rec = analysis["recommendation"]
            optimal = "Safe" if rec["optimal_path"] == "safe_path" else "Risky"
            msg += f"  → OPTIMAL: {optimal} path ({rec['reason']})"

        return True, new_state, msg

    @staticmethod
    def check_goal(
        state: ProbabilisticGraphState,
    ) -> Tuple[bool, ProbabilisticGraphState, str]:
        """Check if goal reached and evaluate decision quality"""
        if not state.is_goal_reached():
            return False, state, f"Not at goal. Current: {state.current_node}"

        # Calculate decision quality
        analysis = analyze_paths(state)

        msg = f"✓ Goal reached via {state.chosen_route} path!\n"
        msg += f"  Path: {' → '.join(state.path_taken)}\n"

        if state.simulated_time is not None:
            msg += f"  Actual time: {state.simulated_time} min\n"
        else:
            msg += f"  Expected time: {state.elapsed_time} min\n"

        # Evaluate decision quality
        if "recommendation" in analysis:
            rec = analysis["recommendation"]
            optimal_choice = rec["optimal_path"]

            if state.chosen_route == "safe" and optimal_choice == "safe_path":
                msg += (
                    "  ⭐ Optimal decision (chose safe when expected values favored it)"
                )
            elif state.chosen_route == "risky" and optimal_choice == "risky_path":
                msg += "  ⭐ Optimal decision (chose risky based on expected value analysis)"
            else:
                msg += f"  ⚠️  Suboptimal decision (chose {state.chosen_route}, but {optimal_choice.replace('_path', '')} was optimal)"

        return True, state, msg


def get_applicable_operators(state: ProbabilisticGraphState):
    """
    Get list of applicable operators for current state.

    Returns:
        List of (operator_name, operator_function, args)
    """
    applicable = []

    # Always can calculate expected values
    applicable.append(
        (
            "calculate_expected_values",
            ProbabilisticGraphOperators.calculate_expected_values,
            [state],
        )
    )

    # If no path chosen yet, can choose
    if state.chosen_route is None:
        applicable.append(
            ("choose_safe_path", ProbabilisticGraphOperators.choose_path, [state, "A"])
        )
        applicable.append(
            ("choose_risky_path", ProbabilisticGraphOperators.choose_path, [state, "B"])
        )

    # If path chosen but not at end, can traverse
    if state.chosen_route is not None and state.current_node in ["A", "B"]:
        applicable.append(
            (
                "traverse_to_end",
                ProbabilisticGraphOperators.traverse_to_end,
                [state, True],  # With simulation
            )
        )

    # Can always check goal
    applicable.append(("check_goal", ProbabilisticGraphOperators.check_goal, [state]))

    return applicable
