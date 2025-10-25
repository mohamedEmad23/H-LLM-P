"""
Graph Traversal HTN Methods

HTN decomposition methods for high-level graph tasks.
Methods decompose tasks into subtasks or primitive operators.
"""

from typing import Dict, List, Any


GRAPH_METHODS = {
    "find_shortest_path": {
        "name": "find_shortest_path",
        "task": "find_shortest_path(start, goal)",
        "parameters": ["start", "goal"],
        "preconditions": [
            "node_exists(start)",
            "node_exists(goal)",
            "path_exists(start, goal)"
        ],
        "decompositions": [
            {
                "name": "direct_path",
                "condition": "adjacent(start, goal)",
                "subtasks": [
                    "traverse_edge(start, goal)"
                ],
                "description": "Direct path when nodes are adjacent"
            },
            {
                "name": "multi_hop_path",
                "condition": "not adjacent(start, goal)",
                "subtasks": [
                    "explore_from(start, goal)",
                    "construct_path(start, goal)"
                ],
                "description": "Multi-hop pathfor non-adjacent nodes"
            }
        ],
        "description": "Find shortest path from start to goal node"
    },
    
    "explore_graph": {
        "name": "explore_graph",
        "task": "explore_graph(start)",
        "parameters": ["start"],
        "preconditions": [
            "node_exists(start)"
        ],
        "decompositions": [
            {
                "name": "dfs_exploration",
                "condition": "depth_first_preferred",
                "subtasks": [
                    "mark_visited(start)",
                    "explore_neighbors_dfs(start)"
                ],
                "description": "Depth-first exploration"
            },
            {
                "name": "bfs_exploration",
                "condition": "breadth_first_preferred",
                "subtasks": [
                    "mark_visited(start)",
                    "explore_neighbors_bfs(start)"
                ],
                "description": "Breadth-first exploration"
            }
        ],
        "description": "Explore graph starting from a node"
    },
    
    "detect_cycles": {
        "name": "detect_cycles",
        "task": "detect_cycles(graph)",
        "parameters": ["graph"],
        "preconditions": [
            "graph_has_edges"
        ],
        "decompositions": [
            {
                "name": "dfs_cycle_detection",
                "condition": "directed_graph",
                "subtasks": [
                    "initialize_visited()",
                    "dfs_cycle_check_all_nodes()"
                ],
                "description": "DFS-based cycle detection for directed graphs"
            }
        ],
        "description": "Detect if graph contains cycles"
    },
    
    "traverse_simple_path": {
        "name": "traverse_simple_path",
        "task": "traverse_path(node_list)",
        "parameters": ["node_list"],
        "preconditions": [
            "valid_path(node_list)"
        ],
        "decompositions": [
            {
                "name": "sequential_traversal",
                "condition": "path_length > 1",
                "subtasks": [
                    "traverse_edge(node_list[i], node_list[i+1]) for each i"
                ],
                "description": "Traverse each edge in sequence"
            },
            {
                "name": "single_node",
                "condition": "path_length == 1",
                "subtasks": [
                    "mark_visited(node_list[0])"
                ],
                "description": "Path with single node"
            }
        ],
        "description": "Traverse a given path"
    },
    
    "find_all_paths": {
        "name": "find_all_paths",
        "task": "find_all_paths(start, goal)",
        "parameters": ["start", "goal"],
        "preconditions": [
            "node_exists(start)",
            "node_exists(goal)"
        ],
        "decompositions": [
            {
                "name": "backtracking_search",
                "condition": "allow_exploration",
                "subtasks": [
                    "explore_path(start, goal, [])",
                    "collect_all_solutions()"
                ],
                "description": "Find all possible paths using backtracking"
            }
        ],
        "description": "Find all paths from start to goal"
    },
    
    "verify_path": {
        "name": "verify_path",
        "task": "verify_path(path)",
        "parameters": ["path"],
        "preconditions": [
            "path_specified"
        ],
        "decompositions": [
            {
                "name": "check_connectivity",
                "condition": "True",
                "subtasks": [
                    "verify_all_edges_exist(path)",
                    "verify_no_duplicates(path)"
                ],
                "description": "Verify path is valid and connected"
            }
        ],
        "description": "Verify if a path is valid"
    }
}


def get_method(method_name: str) -> Dict[str, Any]:
    """Get method definition by name"""
    return GRAPH_METHODS.get(method_name, None)


def list_methods() -> List[str]:
    """List all available method names"""
    return list(GRAPH_METHODS.keys())


def get_methods_for_task(task_pattern: str) -> List[Dict[str, Any]]:
    """Get all methods that can handle a task pattern"""
    matching_methods = []
    for method in GRAPH_METHODS.values():
        if task_pattern in method["task"] or method["name"] in task_pattern:
            matching_methods.append(method)
    return matching_methods
