"""
Graph Traversal HTN Domain

Complete HTN domain for graph-based planning problems.
Integrates operators, methods, and provides utility functions for graph manipulation.
"""

from typing import Dict, List, Any, Tuple, Optional
from .operators import GRAPH_OPERATORS, get_operator, list_operators
from .methods import GRAPH_METHODS, get_method, list_methods


class GraphTraversalDomain:
    """
    HTN Domain for graph traversal and pathfinding problems.
    
    Supports:
    - Shortest path finding (Dijkstra-style)
    - Cycle detection
    - Graph exploration (DFS/BFS)
    - Path validation
    """
    
    def __init__(self):
        """Initialize the graph traversal domain"""
        self.operators = GRAPH_OPERATORS
        self.methods = GRAPH_METHODS
        self.domain_name = "graph_traversal"
    
    def get_initial_state(self, graph: Dict[str, Any], start_node: str) -> Dict[str, Any]:
        """
        Create initial state for graph traversal problem.
        
        Args:
            graph: Graph definition with nodes and edges
            start_node: Starting node
            
        Returns:
            Initial state dictionary
        """
        return {
            "current_node": start_node,
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
            "visited": [],
            "path": [start_node],
            "cycle_detected": False,
            "shortest_distances": {node: float('inf') for node in graph.get("nodes", [])},
            "graph_type": graph.get("type", "directed")
        }
    
    def create_goal(self, goal_type: str, **kwargs) -> Dict[str, Any]:
        """
        Create goal specification for graph problems.
        
        Args:
            goal_type: Type of goal ("reach_node", "find_path", "detect_cycle", etc.)
            **kwargs: Goal-specific parameters
            
        Returns:
            Goal dictionary
        """
        if goal_type == "reach_node":
            return {
                "type": "reach_node",
                "target_node": kwargs.get("target_node"),
                "condition": lambda state: state.get("current_node") == kwargs.get("target_node")
            }
        
        elif goal_type == "find_shortest_path":
            return {
                "type": "find_shortest_path",
                "start_node": kwargs.get("start_node"),
                "goal_node": kwargs.get("goal_node"),
                "condition": lambda state: (
                    state.get("current_node") == kwargs.get("goal_node") and
                    kwargs.get("goal_node") in state.get("visited", [])
                )
            }
        
        elif goal_type == "explore_all":
            return {
                "type": "explore_all",
                "nodes_to_visit": kwargs.get("nodes", []),
                "condition": lambda state: all(
                    node in state.get("visited", []) 
                    for node in kwargs.get("nodes", [])
                )
            }
        
        elif goal_type == "detect_cycle":
            return {
                "type": "detect_cycle",
                "condition": lambda state: state.get("cycle_detected", False)
            }
        
        else:
            raise ValueError(f"Unknown goal type: {goal_type}")
    
    def is_goal_satisfied(self, state: Dict[str, Any], goal: Dict[str, Any]) -> bool:
        """Check if goal is satisfied in current state"""
        if "condition" in goal:
            return goal["condition"](state)
        return False
    
    def get_applicable_operators(self, state: Dict[str, Any]) -> List[Tuple[str, List[Any]]]:
        """
        Get list of applicable operators in current state.
        
        Returns:
            List of (operator_name, parameters) tuples
        """
        applicable = []
        current_node = state.get("current_node")
        
        if not current_node:
            return applicable
        
        # traverse_edge operators
        for edge in state.get("edges", []):
            if len(edge) >= 2 and edge[0] == current_node:
                to_node = edge[1]
                # Only traverse if not visited (for simple paths)
                if to_node not in state.get("visited", []):
                    applicable.append(("traverse_edge", [current_node, to_node]))
        
        # mark_visited operator
        if current_node not in state.get("visited", []):
            applicable.append(("mark_visited", [current_node]))
        
        return applicable
    
    def apply_operator(self, state: Dict[str, Any], operator_name: str, 
                      params: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Apply operator to state (used for planning, not execution).
        
        Note: For actual execution, use SymbolicValidator in ExecutionAgent.
        This is for HTN planning lookahead only.
        """
        import copy
        new_state = copy.deepcopy(state)
        
        if operator_name == "traverse_edge":
            from_node, to_node = params
            new_state["current_node"] = to_node
            if from_node not in new_state["visited"]:
                new_state["visited"].append(from_node)
            if to_node not in new_state["path"]:
                new_state["path"].append(to_node)
        
        elif operator_name == "mark_visited":
            node = params[0]
            if node not in new_state["visited"]:
                new_state["visited"].append(node)
        
        else:
            return None  # Unknown operator
        
        return new_state
    
    def get_operator_cost(self, operator_name: str, params: List[Any], 
                         state: Dict[str, Any]) -> float:
        """
        Get cost of applying an operator.
        
        For weighted graphs, returns edge weight.
        For unweighted graphs, returns 1.0.
        """
        if operator_name == "traverse_edge":
            from_node, to_node = params
            
            # Check if edges have weights (3-tuple: [from, to, weight])
            for edge in state.get("edges", []):
                if len(edge) >= 3 and edge[0] == from_node and edge[1] == to_node:
                    return float(edge[2])
            
            # Default cost for unweighted edges
            return 1.0
        
        # Other operators have minimal cost
        return 0.1
    
    def create_simple_graph(self, edges: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Create a simple graph from edge list.
        
        Args:
            edges: List of (from_node, to_node) tuples
            
        Returns:
            Graph dictionary
        """
        nodes = set()
        for edge in edges:
            nodes.add(edge[0])
            nodes.add(edge[1])
        
        return {
            "nodes": list(nodes),
            "edges": edges,
            "type": "directed"
        }
    
    def create_weighted_graph(self, edges: List[Tuple[str, str, float]]) -> Dict[str, Any]:
        """
        Create a weighted graph from edge list with weights.
        
        Args:
            edges: List of (from_node, to_node, weight) tuples
            
        Returns:
            Graph dictionary
        """
        nodes = set()
        for edge in edges:
            nodes.add(edge[0])
            nodes.add(edge[1])
        
        return {
            "nodes": list(nodes),
            "edges": edges,
            "type": "directed",
            "weighted": True
        }
    
    def find_shortest_path_bfs(self, graph: Dict[str, Any], start: str, 
                                goal: str) -> Optional[List[str]]:
        """
        Find shortest path using BFS (for comparison/validation).
        
        This is the ground truth for testing the HTN planner.
        """
        from collections import deque
        
        if start == goal:
            return [start]
        
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            for edge in graph.get("edges", []):
                if len(edge) >= 2 and edge[0] == current:
                    next_node = edge[1]
                    
                    if next_node == goal:
                        return path + [next_node]
                    
                    if next_node not in visited:
                        visited.add(next_node)
                        queue.append((next_node, path + [next_node]))
        
        return None  # No path found
    
    def has_cycle(self, graph: Dict[str, Any]) -> bool:
        """
        Detect if graph has cycles using DFS (for validation).
        
        This is the ground truth for testing cycle detection.
        """
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for edge in graph.get("edges", []):
                if len(edge) >= 2 and edge[0] == node:
                    neighbor = edge[1]
                    
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph.get("nodes", []):
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get domain statistics"""
        return {
            "domain_name": self.domain_name,
            "num_operators": len(self.operators),
            "num_methods": len(self.methods),
            "operator_names": list(self.operators.keys()),
            "method_names": list(self.methods.keys())
        }
    
    def __repr__(self) -> str:
        return (
            f"GraphTraversalDomain("
            f"operators={len(self.operators)}, "
            f"methods={len(self.methods)})"
        )


# Convenience function for creating domain instance
def create_domain() -> GraphTraversalDomain:
    """Create and return a GraphTraversalDomain instance"""
    return GraphTraversalDomain()
