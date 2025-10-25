"""
Comprehensive Test Suite for Graph Traversal HTN Domain

Tests all components:
- Domain initialization
- Graph creation and validation
- Operators and methods
- Initial state and goal creation
- Ground truth pathfinding algorithms
- Integration with symbolic validator
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from domains.graph_traversal.domain import GraphTraversalDomain, create_domain
from domains.graph_traversal.operators import GRAPH_OPERATORS, get_operator
from domains.graph_traversal.methods import GRAPH_METHODS, get_method


class TestDomainInitialization:
    """Test domain creation and basic properties"""
    
    def test_domain_creation(self):
        """Test basic domain instantiation"""
        domain = GraphTraversalDomain()
        assert domain is not None
        assert domain.domain_name == "graph_traversal"
        assert len(domain.operators) > 0
        assert len(domain.methods) > 0
    
    def test_convenience_function(self):
        """Test create_domain convenience function"""
        domain = create_domain()
        assert isinstance(domain, GraphTraversalDomain)
    
    def test_domain_statistics(self):
        """Test statistics retrieval"""
        domain = GraphTraversalDomain()
        stats = domain.get_statistics()
        
        assert stats["domain_name"] == "graph_traversal"
        assert stats["num_operators"] == 7
        assert stats["num_methods"] == 6
        assert "traverse_edge" in stats["operator_names"]
        assert "find_shortest_path" in stats["method_names"]


class TestGraphCreation:
    """Test graph creation utilities"""
    
    def test_create_simple_graph(self):
        """Test simple unweighted graph creation"""
        domain = GraphTraversalDomain()
        
        edges = [("A", "B"), ("B", "C"), ("A", "C")]
        graph = domain.create_simple_graph(edges)
        
        assert len(graph["nodes"]) == 3
        assert "A" in graph["nodes"]
        assert "B" in graph["nodes"]
        assert "C" in graph["nodes"]
        assert graph["edges"] == edges
        assert graph["type"] == "directed"
    
    def test_create_weighted_graph(self):
        """Test weighted graph creation"""
        domain = GraphTraversalDomain()
        
        edges = [("A", "B", 5.0), ("B", "C", 3.0), ("A", "C", 10.0)]
        graph = domain.create_weighted_graph(edges)
        
        assert len(graph["nodes"]) == 3
        assert graph["weighted"] == True
        assert graph["edges"] == edges


class TestInitialState:
    """Test initial state creation"""
    
    def test_initial_state_simple_graph(self):
        """Test initial state for simple graph"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B"), ("B", "C")])
        state = domain.get_initial_state(graph, "A")
        
        assert state["current_node"] == "A"
        assert state["visited"] == []
        assert state["path"] == ["A"]
        assert state["cycle_detected"] == False
        assert "A" in state["nodes"]
        assert "B" in state["nodes"]
        assert "C" in state["nodes"]
    
    def test_initial_state_shortest_distances(self):
        """Test shortest distances initialization"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B"), ("B", "C")])
        state = domain.get_initial_state(graph, "A")
        
        assert state["shortest_distances"]["A"] == float('inf')
        assert state["shortest_distances"]["B"] == float('inf')
        assert state["shortest_distances"]["C"] == float('inf')


class TestGoalCreation:
    """Test goal specification creation"""
    
    def test_reach_node_goal(self):
        """Test reach_node goal type"""
        domain = GraphTraversalDomain()
        goal = domain.create_goal("reach_node", target_node="C")
        
        assert goal["type"] == "reach_node"
        assert goal["target_node"] == "C"
        
        # Test goal satisfaction
        state_at_c = {"current_node": "C"}
        state_at_b = {"current_node": "B"}
        assert domain.is_goal_satisfied(state_at_c, goal) == True
        assert domain.is_goal_satisfied(state_at_b, goal) == False
    
    def test_find_shortest_path_goal(self):
        """Test find_shortest_path goal type"""
        domain = GraphTraversalDomain()
        goal = domain.create_goal("find_shortest_path", start_node="A", goal_node="C")
        
        assert goal["type"] == "find_shortest_path"
        assert goal["start_node"] == "A"
        assert goal["goal_node"] == "C"
        
        # Test goal satisfaction
        state_success = {"current_node": "C", "visited": ["A", "B", "C"]}
        state_not_visited = {"current_node": "C", "visited": ["A", "B"]}
        state_wrong_node = {"current_node": "B", "visited": ["A", "B"]}
        
        assert domain.is_goal_satisfied(state_success, goal) == True
        assert domain.is_goal_satisfied(state_not_visited, goal) == False
        assert domain.is_goal_satisfied(state_wrong_node, goal) == False
    
    def test_explore_all_goal(self):
        """Test explore_all goal type"""
        domain = GraphTraversalDomain()
        goal = domain.create_goal("explore_all", nodes=["A", "B", "C"])
        
        assert goal["type"] == "explore_all"
        
        state_complete = {"visited": ["A", "B", "C", "D"]}
        state_incomplete = {"visited": ["A", "B"]}
        
        assert domain.is_goal_satisfied(state_complete, goal) == True
        assert domain.is_goal_satisfied(state_incomplete, goal) == False
    
    def test_detect_cycle_goal(self):
        """Test detect_cycle goal type"""
        domain = GraphTraversalDomain()
        goal = domain.create_goal("detect_cycle")
        
        assert goal["type"] == "detect_cycle"
        
        state_with_cycle = {"cycle_detected": True}
        state_no_cycle = {"cycle_detected": False}
        
        assert domain.is_goal_satisfied(state_with_cycle, goal) == True
        assert domain.is_goal_satisfied(state_no_cycle, goal) == False


class TestApplicableOperators:
    """Test operator applicability"""
    
    def test_traverse_edge_applicable(self):
        """Test traverse_edge applicability"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B"), ("B", "C")])
        state = domain.get_initial_state(graph, "A")
        
        applicable = domain.get_applicable_operators(state)
        
        # Should be able to traverse to B and mark A as visited
        op_names = [op[0] for op in applicable]
        assert "traverse_edge" in op_names
        assert "mark_visited" in op_names
        
        # Check traverse_edge parameters
        traverse_ops = [op for op in applicable if op[0] == "traverse_edge"]
        assert len(traverse_ops) == 1
        assert traverse_ops[0][1] == ["A", "B"]
    
    def test_mark_visited_applicable(self):
        """Test mark_visited applicability"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B")])
        state = domain.get_initial_state(graph, "A")
        
        applicable = domain.get_applicable_operators(state)
        
        mark_ops = [op for op in applicable if op[0] == "mark_visited"]
        assert len(mark_ops) == 1
        assert mark_ops[0][1] == ["A"]
    
    def test_no_backtracking_to_visited(self):
        """Test that we don't traverse to visited nodes"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B"), ("B", "A")])
        state = domain.get_initial_state(graph, "B")
        state["visited"] = ["A"]
        
        applicable = domain.get_applicable_operators(state)
        
        # Should not be able to traverse to A (already visited)
        traverse_ops = [op for op in applicable if op[0] == "traverse_edge"]
        assert len(traverse_ops) == 0


class TestOperatorApplication:
    """Test operator application (planning lookahead)"""
    
    def test_apply_traverse_edge(self):
        """Test traverse_edge operator application"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B"), ("B", "C")])
        state = domain.get_initial_state(graph, "A")
        
        new_state = domain.apply_operator(state, "traverse_edge", ["A", "B"])
        
        assert new_state["current_node"] == "B"
        assert "A" in new_state["visited"]
        assert "B" in new_state["path"]
        
        # Original state should be unchanged
        assert state["current_node"] == "A"
    
    def test_apply_mark_visited(self):
        """Test mark_visited operator application"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B")])
        state = domain.get_initial_state(graph, "A")
        
        new_state = domain.apply_operator(state, "mark_visited", ["A"])
        
        assert "A" in new_state["visited"]
        assert state["visited"] == []  # Original unchanged


class TestOperatorCost:
    """Test operator cost calculation"""
    
    def test_unweighted_edge_cost(self):
        """Test cost for unweighted edges"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B")])
        state = domain.get_initial_state(graph, "A")
        
        cost = domain.get_operator_cost("traverse_edge", ["A", "B"], state)
        assert cost == 1.0
    
    def test_weighted_edge_cost(self):
        """Test cost for weighted edges"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_weighted_graph([("A", "B", 5.0)])
        state = domain.get_initial_state(graph, "A")
        
        cost = domain.get_operator_cost("traverse_edge", ["A", "B"], state)
        assert cost == 5.0
    
    def test_other_operator_cost(self):
        """Test cost for non-traversal operators"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B")])
        state = domain.get_initial_state(graph, "A")
        
        cost = domain.get_operator_cost("mark_visited", ["A"], state)
        assert cost == 0.1


class TestGroundTruthAlgorithms:
    """Test ground truth BFS and cycle detection"""
    
    def test_bfs_simple_path(self):
        """Test BFS finds simple path"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B"), ("B", "C")])
        path = domain.find_shortest_path_bfs(graph, "A", "C")
        
        assert path == ["A", "B", "C"]
    
    def test_bfs_direct_path(self):
        """Test BFS prefers direct path"""
        domain = GraphTraversalDomain()
        
        # Two paths: A->B->C (length 2) and A->C (length 1)
        graph = domain.create_simple_graph([("A", "B"), ("B", "C"), ("A", "C")])
        path = domain.find_shortest_path_bfs(graph, "A", "C")
        
        assert path == ["A", "C"]  # Shorter path
    
    def test_bfs_no_path(self):
        """Test BFS returns None when no path exists"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B"), ("C", "D")])
        path = domain.find_shortest_path_bfs(graph, "A", "D")
        
        assert path is None
    
    def test_bfs_same_start_goal(self):
        """Test BFS handles start==goal"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([("A", "B")])
        path = domain.find_shortest_path_bfs(graph, "A", "A")
        
        assert path == ["A"]
    
    def test_cycle_detection_positive(self):
        """Test cycle detection finds cycles"""
        domain = GraphTraversalDomain()
        
        # Graph with cycle: A->B->C->A
        graph = domain.create_simple_graph([("A", "B"), ("B", "C"), ("C", "A")])
        has_cycle = domain.has_cycle(graph)
        
        assert has_cycle == True
    
    def test_cycle_detection_negative(self):
        """Test cycle detection on acyclic graph"""
        domain = GraphTraversalDomain()
        
        # DAG: A->B->C
        graph = domain.create_simple_graph([("A", "B"), ("B", "C")])
        has_cycle = domain.has_cycle(graph)
        
        assert has_cycle == False
    
    def test_cycle_detection_self_loop(self):
        """Test cycle detection for self-loops"""
        domain = GraphTraversalDomain()
        
        # Self-loop: A->A
        graph = domain.create_simple_graph([("A", "A")])
        has_cycle = domain.has_cycle(graph)
        
        assert has_cycle == True


class TestComplexGraphScenarios:
    """Test complex graph scenarios"""
    
    def test_diamond_graph(self):
        """Test diamond-shaped graph"""
        domain = GraphTraversalDomain()
        
        # Diamond: A->B->D, A->C->D
        graph = domain.create_simple_graph([
            ("A", "B"), ("A", "C"),
            ("B", "D"), ("C", "D")
        ])
        
        path = domain.find_shortest_path_bfs(graph, "A", "D")
        assert len(path) == 3  # Either A->B->D or A->C->D
        assert path[0] == "A"
        assert path[-1] == "D"
    
    def test_disconnected_components(self):
        """Test graph with disconnected components"""
        domain = GraphTraversalDomain()
        
        graph = domain.create_simple_graph([
            ("A", "B"), ("B", "C"),  # Component 1
            ("D", "E"), ("E", "F")   # Component 2
        ])
        
        # Path within component should work
        path1 = domain.find_shortest_path_bfs(graph, "A", "C")
        assert path1 == ["A", "B", "C"]
        
        # Path across components should fail
        path2 = domain.find_shortest_path_bfs(graph, "A", "F")
        assert path2 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
