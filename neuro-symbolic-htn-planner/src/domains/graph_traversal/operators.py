"""
Graph Traversal HTN Operators

Primitive operators for graph traversal tasks.
These operators are executed by the ExecutionAgent with symbolic validation.
"""

from typing import Dict, List, Any


GRAPH_OPERATORS = {
    "traverse_edge": {
        "name": "traverse_edge",
        "parameters": ["from_node", "to_node"],
        "preconditions": [
            "current_node == from_node",
            "edge_exists(from_node, to_node)",
            "not_visited(to_node) OR allow_revisit"
        ],
        "effects": [
            "current_node = to_node",
            "add_to_path(to_node)",
            "mark_visited(from_node)"
        ],
        "description": "Traverse from one node to an adjacent node"
    },
    
    "mark_visited": {
        "name": "mark_visited",
        "parameters": ["node"],
        "preconditions": [
            "current_node == node"
        ],
        "effects": [
            "visited(node) = True"
        ],
        "description": "Mark current node as visited"
    },
    
    "find_neighbors": {
        "name": "find_neighbors",
        "parameters": ["node"],
        "preconditions": [
            "node_exists(node)"
        ],
        "effects": [
            "neighbors_list = get_neighbors(node)"
        ],
        "description": "Get list of neighboring nodes"
    },
    
    "calculate_distance": {
        "name": "calculate_distance",
        "parameters": ["from_node", "to_node"],
        "preconditions": [
            "edge_exists(from_node, to_node)"
        ],
        "effects": [
            "distance = get_edge_weight(from_node, to_node)"
        ],
        "description": "Calculate distance between two adjacent nodes"
    },
    
    "update_shortest_distance": {
        "name": "update_shortest_distance",
        "parameters": ["node", "distance"],
        "preconditions": [
            "node_exists(node)"
        ],
        "effects": [
            "shortest_distance[node] = min(shortest_distance[node], distance)"
        ],
        "description": "Update shortest known distance to a node"
    },
    
    "detect_cycle": {
        "name": "detect_cycle",
        "parameters": ["node"],
        "preconditions": [
            "node_exists(node)",
            "in_current_path(node)"
        ],
        "effects": [
            "cycle_detected = True"
        ],
        "description": "Detect if visiting this node creates a cycle"
    },
    
    "backtrack": {
        "name": "backtrack",
        "parameters": [],
        "preconditions": [
            "path_length > 0"
        ],
        "effects": [
            "current_node = previous_node",
            "remove_from_path(current_node)"
        ],
        "description": "Backtrack to previous node in path"
    }
}


def get_operator(operator_name: str) -> Dict[str, Any]:
    """Get operator definition by name"""
    return GRAPH_OPERATORS.get(operator_name, None)


def list_operators() -> List[str]:
    """List all available operator names"""
    return list(GRAPH_OPERATORS.keys())


def validate_operator_params(operator_name: str, params: List[Any]) -> bool:
    """Validate operator parameters"""
    operator = get_operator(operator_name)
    if not operator:
        return False
    
    expected_params = operator["parameters"]
    return len(params) == len(expected_params)
