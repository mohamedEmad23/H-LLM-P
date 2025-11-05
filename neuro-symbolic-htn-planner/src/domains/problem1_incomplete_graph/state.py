"""
State representation for Incomplete Knowledge Graph problem.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Edge:
    """Directed weighted edge in graph"""

    source: str
    target: str
    weight: Optional[int]  # None = UNKNOWN

    def is_known(self) -> bool:
        """Check if edge weight is known"""
        return self.weight is not None


@dataclass
class GraphState:
    """State of the incomplete knowledge graph traversal problem"""

    # Current position
    current_node: str
    target_node: str
    required_waypoint: str  # Must pass through this node

    # Graph structure
    edges: List[Edge] = field(default_factory=list)

    # Path history
    path: List[str] = field(default_factory=list)
    total_cost: int = 0

    # Knowledge tracking
    researched_edges: Dict[Tuple[str, str], int] = field(default_factory=dict)
    unknown_edges_found: List[Tuple[str, str]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize path with current node"""
        if not self.path:
            self.path = [self.current_node]

    def get_edge(self, source: str, target: str) -> Optional[Edge]:
        """Get edge between two nodes"""
        for edge in self.edges:
            if edge.source == source and edge.target == target:
                return edge
        return None

    def get_edge_weight(self, source: str, target: str) -> Optional[int]:
        """
        Get edge weight, checking researched edges first.
        Returns None if unknown and not researched.
        """
        # Check if we researched this edge
        if (source, target) in self.researched_edges:
            return self.researched_edges[(source, target)]

        # Check original graph
        edge = self.get_edge(source, target)
        return edge.weight if edge else None

    def is_edge_unknown(self, source: str, target: str) -> bool:
        """Check if edge weight is unknown"""
        edge = self.get_edge(source, target)
        return edge is not None and edge.weight is None

    def get_outgoing_edges(self, node: str) -> List[Edge]:
        """Get all outgoing edges from a node"""
        return [e for e in self.edges if e.source == node]

    def has_visited_waypoint(self) -> bool:
        """Check if required waypoint has been visited"""
        return self.required_waypoint in self.path

    def is_goal_reached(self) -> bool:
        """Check if goal conditions met"""
        return self.current_node == self.target_node and self.has_visited_waypoint()

    def get_unknown_edges(self) -> List[Tuple[str, str]]:
        """Get all edges with unknown weights"""
        unknown = []
        for edge in self.edges:
            if edge.weight is None:
                if (edge.source, edge.target) not in self.researched_edges:
                    unknown.append((edge.source, edge.target))
        return unknown

    def to_dict(self) -> Dict:
        """Convert state to dictionary"""
        return {
            "current_node": self.current_node,
            "target_node": self.target_node,
            "required_waypoint": self.required_waypoint,
            "path": self.path,
            "total_cost": self.total_cost,
            "researched_edges": {
                f"{s}->{t}": w for (s, t), w in self.researched_edges.items()
            },
            "unknown_edges": [f"{s}->{t}" for s, t in self.get_unknown_edges()],
            "goal_reached": self.is_goal_reached(),
        }


def create_incomplete_graph() -> GraphState:
    """
    Create the standard Problem 1 graph.

    Graph:
        A --[4]--> B --[UNKNOWN]--> C --[5]--> D
        |                                       ^
        +---------------[15]-------------------+

    Constraint: Must pass through B
    Hidden value: weight(B,C) = 8
    Optimal path: A → B → C → D (4+8+5=17)
    """
    edges = [
        Edge("A", "B", 4),
        Edge("B", "C", None),  # UNKNOWN
        Edge("C", "D", 5),
        Edge("A", "C", 15),
    ]

    return GraphState(
        current_node="A", target_node="D", required_waypoint="B", edges=edges
    )


# Hidden knowledge base (simulates external research tool)
HIDDEN_KNOWLEDGE = {("B", "C"): 8}


def research_edge_weight(source: str, target: str) -> Optional[int]:
    """
    Simulates calling an external knowledge base / research tool.

    This represents what the system must discover through LLM reasoning.
    In Phase 4B, the PlanningAgent should identify this need.
    """
    return HIDDEN_KNOWLEDGE.get((source, target))
