"""
State representation for Probabilistic Graph Traversal problem.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random


@dataclass
class ProbabilisticEdge:
    """Edge with probabilistic cost"""
    source: str
    target: str
    base_time: int  # Base traversal time
    penalty_time: int = 0  # Additional time if penalty occurs
    penalty_probability: float = 0.0  # Probability of penalty (0.0 to 1.0)
    
    def get_expected_time(self) -> float:
        """Calculate expected value of traversal time"""
        return self.base_time + (self.penalty_probability * self.penalty_time)
    
    def get_worst_case_time(self) -> int:
        """Get worst-case traversal time"""
        return self.base_time + self.penalty_time
    
    def simulate_traversal(self, seed: Optional[int] = None) -> Tuple[int, bool]:
        """
        Simulate actual traversal (for testing/validation).
        
        Returns:
            (actual_time, penalty_occurred)
        """
        if seed is not None:
            random.seed(seed)
        
        penalty_occurred = random.random() < self.penalty_probability
        actual_time = self.base_time + (self.penalty_time if penalty_occurred else 0)
        
        return actual_time, penalty_occurred


@dataclass
class ProbabilisticGraphState:
    """State of the probabilistic graph traversal problem"""
    
    current_node: str
    target_node: str
    
    # Graph structure
    edges: List[ProbabilisticEdge] = field(default_factory=list)
    
    # Path tracking
    path_taken: List[str] = field(default_factory=list)
    chosen_route: Optional[str] = None  # "safe" or "risky"
    
    # Time tracking
    elapsed_time: int = 0
    simulated_time: Optional[int] = None  # Actual time after simulation
    penalty_occurred: Optional[bool] = None
    
    # Decision analysis
    expected_values_calculated: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize path with current node"""
        if not self.path_taken:
            self.path_taken = [self.current_node]
    
    def get_edge(self, source: str, target: str) -> Optional[ProbabilisticEdge]:
        """Get edge between two nodes"""
        for edge in self.edges:
            if edge.source == source and edge.target == target:
                return edge
        return None
    
    def get_outgoing_edges(self, node: str) -> List[ProbabilisticEdge]:
        """Get all outgoing edges from a node"""
        return [e for e in self.edges if e.source == node]
    
    def is_goal_reached(self) -> bool:
        """Check if reached target"""
        return self.current_node == self.target_node
    
    def to_dict(self) -> Dict:
        """Convert state to dictionary"""
        return {
            'current_node': self.current_node,
            'target_node': self.target_node,
            'path': self.path_taken,
            'chosen_route': self.chosen_route,
            'elapsed_time': self.elapsed_time,
            'simulated_time': self.simulated_time,
            'penalty_occurred': self.penalty_occurred,
            'expected_values': self.expected_values_calculated,
            'goal_reached': self.is_goal_reached()
        }


def create_probabilistic_graph() -> ProbabilisticGraphState:
    """
    Create the standard Problem 3 instance.
    
    Graph:
        Start → A → End (guaranteed 30 min)
        Start → B → End (10 min + 50% chance +30 min)
    
    Expected values:
        Path 1: 30 min
        Path 2: 0.5*10 + 0.5*40 = 25 min (OPTIMAL)
    """
    edges = [
        # Safe path
        ProbabilisticEdge("Start", "A", base_time=0, penalty_time=0, penalty_probability=0.0),
        ProbabilisticEdge("A", "End", base_time=30, penalty_time=0, penalty_probability=0.0),
        
        # Risky path
        ProbabilisticEdge("Start", "B", base_time=0, penalty_time=0, penalty_probability=0.0),
        ProbabilisticEdge("B", "End", base_time=10, penalty_time=30, penalty_probability=0.5),
    ]
    
    return ProbabilisticGraphState(
        current_node="Start",
        target_node="End",
        edges=edges
    )


def calculate_expected_value(edge: ProbabilisticEdge) -> float:
    """
    Calculate expected value for an edge.
    
    Formula: E[T] = base_time + (prob * penalty_time)
    """
    return edge.get_expected_time()


def analyze_paths(state: ProbabilisticGraphState) -> Dict[str, Dict]:
    """
    Analyze all paths and calculate expected values.
    
    Returns:
        Dictionary with path analysis
    """
    analysis = {}
    
    # Path 1: Safe route (Start → A → End)
    edge_a = state.get_edge("A", "End")
    if edge_a:
        analysis["safe_path"] = {
            "route": "Start → A → End",
            "expected_time": edge_a.get_expected_time(),
            "worst_case": edge_a.get_worst_case_time(),
            "risk": "None (guaranteed)",
            "calculation": f"{edge_a.base_time} min (no risk)"
        }
    
    # Path 2: Risky route (Start → B → End)
    edge_b = state.get_edge("B", "End")
    if edge_b:
        ev = edge_b.get_expected_time()
        analysis["risky_path"] = {
            "route": "Start → B → End",
            "expected_time": ev,
            "worst_case": edge_b.get_worst_case_time(),
            "risk": f"{edge_b.penalty_probability*100:.0f}% chance of +{edge_b.penalty_time} min penalty",
            "calculation": f"({1-edge_b.penalty_probability}*{edge_b.base_time}) + ({edge_b.penalty_probability}*{edge_b.get_worst_case_time()}) = {ev} min"
        }
    
    # Recommendation
    if "safe_path" in analysis and "risky_path" in analysis:
        safe_ev = analysis["safe_path"]["expected_time"]
        risky_ev = analysis["risky_path"]["expected_time"]
        
        if risky_ev < safe_ev:
            analysis["recommendation"] = {
                "optimal_path": "risky_path",
                "reason": f"Lower expected value ({risky_ev} < {safe_ev})",
                "savings": safe_ev - risky_ev
            }
        else:
            analysis["recommendation"] = {
                "optimal_path": "safe_path",
                "reason": f"Lower expected value ({safe_ev} <= {risky_ev})",
                "savings": risky_ev - safe_ev
            }
    
    return analysis
