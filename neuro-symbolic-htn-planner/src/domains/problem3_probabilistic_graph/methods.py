"""
HTN methods for Probabilistic Graph Traversal problem.
"""

from typing import List, Dict
from .state import ProbabilisticGraphState, analyze_paths


class ProbabilisticGraphMethods:
    """HTN decomposition strategies for probabilistic graph"""
    
    @staticmethod
    def naive_shortest_time(state: ProbabilisticGraphState) -> List[str]:
        """
        Naive strategy: Choose path with lowest BASE time (ignores probability).
        
        This is what Phase 1 will likely do.
        Sees: Path 1 = 30 min, Path 2 = 10 min
        Chooses: Path 2 (risky) without considering 50% penalty
        
        Result: Accidentally optimal (but for wrong reasons)
        """
        plan = [
            "# Naive: Choose path with shortest BASE time",
            "# Sees risky path base time = 10 min < safe path 30 min",
            "choose_path(B)",  # Chooses risky
            "traverse_to_end()",
            "check_goal()"
        ]
        return plan
    
    @staticmethod
    def risk_averse(state: ProbabilisticGraphState) -> List[str]:
        """
        Risk-averse strategy: Always choose guaranteed path.
        
        This might be Phase 3 behavior - conservative decision.
        """
        plan = [
            "# Risk-averse: Choose guaranteed path",
            "choose_path(A)",  # Chooses safe
            "traverse_to_end()",
            "check_goal()"
        ]
        return plan
    
    @staticmethod
    def expected_value_optimization(state: ProbabilisticGraphState) -> List[str]:
        """
        Optimal strategy: Calculate expected values, choose minimum.
        
        This is what Phase 4B should do.
        PlanningAgent performs strategic analysis:
        1. Calculate E[T] for each path
        2. Choose path with minimum expected value
        3. Execute chosen path
        """
        plan = [
            "# Strategic: Calculate expected values first",
            "calculate_expected_values()",
            
            "# Expected Value Analysis:",
            "# Path 1 (Safe): E[T] = 30 min",
            "# Path 2 (Risky): E[T] = 0.5*10 + 0.5*40 = 25 min",
            
            "# Optimal choice: Path 2 (lower expected value)",
            "choose_path(B)",  # Risky but optimal
            "traverse_to_end()",
            "check_goal()"
        ]
        return plan
    
    @staticmethod
    def format_problem_for_llm(state: ProbabilisticGraphState) -> str:
        """
        Format problem description for LLM planning.
        """
        output = "PROBABILISTIC GRAPH TRAVERSAL PROBLEM\n"
        output += "=" * 50 + "\n\n"
        
        output += f"Goal: Travel from {state.current_node} to {state.target_node}\n"
        output += "Constraint: Once a path is chosen, you cannot turn back.\n\n"
        
        output += "Available Paths:\n\n"
        
        output += "1. SAFE PATH (Start → A → End):\n"
        output += "   - Guaranteed time: 30 minutes\n"
        output += "   - No risk, predictable outcome\n\n"
        
        output += "2. RISKY PATH (Start → B → End):\n"
        output += "   - Base time: 10 minutes\n"
        output += "   - Risk: 50% probability of +30 minute penalty\n"
        output += "   - Worst case: 10 + 30 = 40 minutes\n\n"
        
        output += "Current State:\n"
        output += f"  Location: {state.current_node}\n"
        output += f"  Path chosen: {state.chosen_route or 'Not yet decided'}\n"
        
        if state.expected_values_calculated:
            output += "\nExpected Value Analysis:\n"
            for path, ev in state.expected_values_calculated.items():
                output += f"  {path.capitalize()} path: E[T] = {ev} min\n"
        
        output += "\nQuestion: Which path minimizes the EXPECTED total time?\n\n"
        
        output += "Available Actions:\n"
        output += "  - calculate_expected_values() - Perform E[T] analysis\n"
        output += "  - choose_path(A) - Take safe path\n"
        output += "  - choose_path(B) - Take risky path\n"
        output += "  - traverse_to_end() - Complete journey\n"
        output += "  - check_goal() - Verify arrival\n"
        
        output += "\nHint for Expected Value:\n"
        output += "  E[T] = (prob_success × time_success) + (prob_penalty × time_with_penalty)\n"
        output += "  For risky path: E[T] = (0.5 × 10) + (0.5 × 40) = ?\n"
        
        return output
    
    @staticmethod
    def analyze_decision_quality(state: ProbabilisticGraphState) -> Dict:
        """
        Analyze the quality of the path choice decision.
        
        This is for post-hoc evaluation of each phase's performance.
        """
        analysis = analyze_paths(state)
        
        if state.chosen_route is None:
            return {
                "decision_made": False,
                "quality": "N/A"
            }
        
        optimal = analysis.get("recommendation", {}).get("optimal_path", "").replace("_path", "")
        
        quality = {
            "decision_made": True,
            "chosen_path": state.chosen_route,
            "optimal_path": optimal,
            "is_optimal": state.chosen_route == optimal
        }
        
        if "safe" in state.expected_values_calculated and "risky" in state.expected_values_calculated:
            safe_ev = state.expected_values_calculated["safe"]
            risky_ev = state.expected_values_calculated["risky"]
            
            quality["expected_value_calculated"] = True
            quality["safe_ev"] = safe_ev
            quality["risky_ev"] = risky_ev
            
            if state.chosen_route == "safe":
                quality["expected_time"] = safe_ev
                quality["opportunity_cost"] = safe_ev - risky_ev
            else:
                quality["expected_time"] = risky_ev
                quality["opportunity_cost"] = risky_ev - safe_ev
        else:
            quality["expected_value_calculated"] = False
        
        # Plan Quality Score (0-100)
        if quality["is_optimal"]:
            if quality.get("expected_value_calculated", False):
                quality["plan_quality_score"] = 100  # Perfect: calculated EV and chose optimally
            else:
                quality["plan_quality_score"] = 70  # Lucky: optimal but didn't calculate
        else:
            quality["plan_quality_score"] = 30  # Suboptimal choice
        
        return quality


def get_decomposition_methods() -> Dict[str, callable]:
    """Get dictionary of available decomposition strategies"""
    return {
        "naive": ProbabilisticGraphMethods.naive_shortest_time,
        "risk_averse": ProbabilisticGraphMethods.risk_averse,
        "optimal": ProbabilisticGraphMethods.expected_value_optimization
    }
