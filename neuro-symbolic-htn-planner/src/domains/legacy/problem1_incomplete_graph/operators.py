"""
Primitive operators for Incomplete Knowledge Graph problem.
"""

from typing import Tuple
from .state import GraphState, research_edge_weight


class GraphOperators:
    """Primitive actions for graph traversal with knowledge gaps"""

    @staticmethod
    def move_to_node(
        state: GraphState, target_node: str
    ) -> Tuple[bool, GraphState, str]:
        """
        Move from current node to target node.

        Preconditions:
        - Edge must exist
        - Edge weight must be known (either originally or via research)

        Effects:
        - Updates current_node
        - Adds to path
        - Increments total_cost

        Returns:
            (success, new_state, message)
        """
        # Check if edge exists
        edge = state.get_edge(state.current_node, target_node)
        if not edge:
            return False, state, f"No edge from {state.current_node} to {target_node}"

        # Check if weight is known
        weight = state.get_edge_weight(state.current_node, target_node)
        if weight is None:
            return (
                False,
                state,
                f"Edge weight ({state.current_node}, {target_node}) is UNKNOWN. Must research first.",
            )

        # Execute move
        new_state = GraphState(
            current_node=target_node,
            target_node=state.target_node,
            required_waypoint=state.required_waypoint,
            edges=state.edges,
            path=state.path + [target_node],
            total_cost=state.total_cost + weight,
            researched_edges=state.researched_edges.copy(),
            unknown_edges_found=state.unknown_edges_found.copy(),
        )

        return (
            True,
            new_state,
            f"Moved from {state.current_node} to {target_node} (cost: {weight})",
        )

    @staticmethod
    def research_unknown_edge(
        state: GraphState, source: str, target: str
    ) -> Tuple[bool, GraphState, str]:
        """
        Research tool: Discover the weight of an unknown edge.

        This simulates calling an LLM/knowledge base to find missing information.

        Preconditions:
        - Edge must exist and be unknown

        Effects:
        - Adds discovered weight to researched_edges
        - Records unknown edge was found

        Returns:
            (success, new_state, message)
        """
        # Check if edge exists and is unknown
        if not state.is_edge_unknown(source, target):
            return (
                False,
                state,
                f"Edge ({source}, {target}) is not unknown or doesn't exist",
            )

        # Check if already researched
        if (source, target) in state.researched_edges:
            return False, state, f"Edge ({source}, {target}) already researched"

        # Call research tool (simulated)
        discovered_weight = research_edge_weight(source, target)

        if discovered_weight is None:
            return (
                False,
                state,
                f"Research failed: No information found for edge ({source}, {target})",
            )

        # Update state with discovered knowledge
        new_researched = state.researched_edges.copy()
        new_researched[(source, target)] = discovered_weight

        new_unknown_found = state.unknown_edges_found.copy()
        new_unknown_found.append((source, target))

        new_state = GraphState(
            current_node=state.current_node,
            target_node=state.target_node,
            required_waypoint=state.required_waypoint,
            edges=state.edges,
            path=state.path.copy(),
            total_cost=state.total_cost,
            researched_edges=new_researched,
            unknown_edges_found=new_unknown_found,
        )

        return (
            True,
            new_state,
            f"Research successful: weight({source}, {target}) = {discovered_weight}",
        )

    @staticmethod
    def check_for_unknown_edges(state: GraphState) -> Tuple[bool, GraphState, str]:
        """
        Scan graph for unknown edges on potential paths.

        This is a meta-action that helps identify knowledge gaps.

        Returns:
            (success, new_state, message with list of unknown edges)
        """
        unknown = state.get_unknown_edges()

        if not unknown:
            return True, state, "No unknown edges found. Graph is complete."

        unknown_str = ", ".join([f"({s}, {t})" for s, t in unknown])
        return True, state, f"Found {len(unknown)} unknown edge(s): {unknown_str}"

    @staticmethod
    def check_goal(state: GraphState) -> Tuple[bool, GraphState, str]:
        """
        Check if goal conditions are met.

        Returns:
            (success, state, message)
        """
        if state.is_goal_reached():
            return (
                True,
                state,
                f"Goal reached! Path: {' → '.join(state.path)}, Total cost: {state.total_cost}",
            )

        if state.current_node == state.target_node:
            return (
                False,
                state,
                f"At target but did not pass through waypoint {state.required_waypoint}",
            )

        if not state.has_visited_waypoint():
            return (
                False,
                state,
                f"Not at goal. Waypoint {state.required_waypoint} not visited yet.",
            )

        return (
            False,
            state,
            f"Not at goal. Current node: {state.current_node}, Target: {state.target_node}",
        )


def get_applicable_operators(state: GraphState):
    """
    Get list of applicable operators for current state.

    Returns:
        List of (operator_name, operator_function, args)
    """
    applicable = []

    # Check goal
    applicable.append(("check_goal", GraphOperators.check_goal, [state]))

    # Check for unknown edges
    applicable.append(
        ("check_for_unknown_edges", GraphOperators.check_for_unknown_edges, [state])
    )

    # Research unknown edges
    for source, target in state.get_unknown_edges():
        applicable.append(
            (
                f"research_edge_{source}_{target}",
                GraphOperators.research_unknown_edge,
                [state, source, target],
            )
        )

    # Move actions
    for edge in state.get_outgoing_edges(state.current_node):
        weight = state.get_edge_weight(edge.source, edge.target)
        if weight is not None:  # Only suggest moves with known weights
            applicable.append(
                (
                    f"move_to_{edge.target}",
                    GraphOperators.move_to_node,
                    [state, edge.target],
                )
            )

    return applicable
