"""
HTN methods for Incomplete Knowledge Graph problem.
"""

from typing import List, Optional, Dict
from .state import GraphState
from .operators import GraphOperators


class GraphMethods:
    """HTN decomposition strategies for incomplete knowledge graph"""
    
    @staticmethod
    def solve_incomplete_graph(state: GraphState) -> Optional[List[str]]:
        """
        High-level method: Solve incomplete knowledge graph problem.
        
        Strategy:
        1. Check for unknown edges
        2. Research all unknown edges
        3. Plan optimal path through waypoint
        4. Execute path
        
        This tests if the system can decompose the problem correctly.
        """
        plan = []
        
        # Step 1: Identify knowledge gaps
        plan.append("check_for_unknown_edges()")
        
        # Step 2: Research unknown edges
        unknown_edges = state.get_unknown_edges()
        for source, target in unknown_edges:
            plan.append(f"research_unknown_edge({source}, {target})")
        
        # Step 3: Plan path (requires waypoint)
        # Optimal: A → B → C → D
        plan.append(f"move_to_node({state.required_waypoint})")  # A → B
        plan.append(f"move_to_node(C)")  # B → C (after research)
        plan.append(f"move_to_node({state.target_node})")  # C → D
        
        # Step 4: Verify goal
        plan.append("check_goal()")
        
        return plan
    
    @staticmethod
    def naive_shortest_path(state: GraphState) -> Optional[List[str]]:
        """
        Naive strategy: Try to find shortest path without checking for unknowns.
        
        This simulates Phase 1 behavior - may fail if it encounters unknown edge.
        """
        plan = []
        
        # Direct path A → C → D (ignoring waypoint requirement)
        plan.append("move_to_node(C)")  # This has cost 15
        plan.append("move_to_node(D)")
        plan.append("check_goal()")
        
        return plan
    
    @staticmethod
    def research_then_plan(state: GraphState) -> Optional[List[str]]:
        """
        Improved strategy: Research first, then plan.
        
        This tests Phase 3's ability to separate concerns:
        - DecompositionAgent creates research step
        - ExecutionAgent then solves with complete knowledge
        """
        plan = []
        
        # Phase 1: Research
        plan.append("check_for_unknown_edges()")
        for source, target in state.get_unknown_edges():
            plan.append(f"research_unknown_edge({source}, {target})")
        
        # Phase 2: Plan with complete knowledge
        # Now we know weight(B,C) = 8, so A→B→C→D (4+8+5=17) < A→C→D (15+5=20)
        plan.append(f"move_to_node({state.required_waypoint})")
        plan.append("move_to_node(C)")
        plan.append(f"move_to_node({state.target_node})")
        plan.append("check_goal()")
        
        return plan
    
    @staticmethod
    def format_problem_for_llm(state: GraphState) -> str:
        """
        Format problem description for LLM planning.
        
        This is what gets sent to the LLM in each phase.
        """
        output = "INCOMPLETE KNOWLEDGE GRAPH PROBLEM\n"
        output += "="*50 + "\n\n"
        
        output += f"Goal: Find shortest path from {state.current_node} to {state.target_node}\n"
        output += f"Constraint: Path MUST pass through node {state.required_waypoint}\n\n"
        
        output += "Graph Edges:\n"
        for edge in state.edges:
            weight_str = str(edge.weight) if edge.weight is not None else "UNKNOWN"
            output += f"  {edge.source} → {edge.target}: weight = {weight_str}\n"
        
        output += f"\nCurrent State:\n"
        output += f"  Location: {state.current_node}\n"
        output += f"  Path so far: {' → '.join(state.path)}\n"
        output += f"  Total cost: {state.total_cost}\n"
        
        unknown = state.get_unknown_edges()
        if unknown:
            output += f"\n⚠️  Unknown Edges Found:\n"
            for s, t in unknown:
                output += f"  - weight({s}, {t}) is UNKNOWN\n"
            output += "\n  You can call: research_unknown_edge(source, target) to discover the weight.\n"
        
        if state.researched_edges:
            output += f"\nResearched Edges:\n"
            for (s, t), w in state.researched_edges.items():
                output += f"  - weight({s}, {t}) = {w} (discovered)\n"
        
        output += f"\nAvailable Actions:\n"
        output += f"  1. check_for_unknown_edges() - Scan for knowledge gaps\n"
        output += f"  2. research_unknown_edge(source, target) - Discover unknown weight\n"
        output += f"  3. move_to_node(target) - Move along edge (if weight known)\n"
        output += f"  4. check_goal() - Verify goal conditions\n"
        
        return output


def get_decomposition_methods() -> Dict[str, callable]:
    """
    Get dictionary of available decomposition strategies.
    
    Returns:
        Dict mapping strategy name to method function
    """
    return {
        "complete_solution": GraphMethods.solve_incomplete_graph,
        "naive_shortest": GraphMethods.naive_shortest_path,
        "research_first": GraphMethods.research_then_plan
    }
