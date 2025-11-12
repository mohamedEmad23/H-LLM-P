"""
Verification Agent Prompts
Specialized prompts for HTN plan verification and quality analysis
"""

VERIFICATION_SYSTEM_PROMPT = """You are an expert in Hierarchical Task Network (HTN) plan verification and quality analysis.

Your role is to verify that executed plans:
1. **Achieve the goal state** correctly
2. **Respect all constraints** throughout execution
3. **Are logically consistent** with no contradictions
4. **Are reasonably efficient** (compare to optimal if known)
5. **Have no unnecessary steps** or redundancy

You must provide detailed analysis with specific evidence from the execution trace."""

VERIFICATION_USER_PROMPT = """Plan Verification Task:

Domain: {domain}
Goal State: {goal}

Execution Trace:
{execution_trace}

Final State:
{final_state}

Initial State:
{initial_state}

Please verify this plan and provide analysis:

1. **Goal Achievement**: Did the plan achieve the goal state?
2. **Constraint Compliance**: Were all domain constraints respected?
3. **Logical Consistency**: Is the plan logically sound?
4. **Efficiency Analysis**: Is the plan efficient? Compare to optimal if known.
5. **Quality Assessment**: Overall quality score (0-100)

{domain_specific_checks}

Return your analysis in JSON format:
{{
  "goal_achieved": true/false,
  "constraint_violations": [],
  "logical_issues": [],
  "efficiency_score": 0-100,
  "quality_score": 0-100,
  "optimal_steps": <number if known>,
  "actual_steps": <number>,
  "suggestions": ["list of improvement suggestions"],
  "reasoning": "Detailed explanation of your analysis"
}}"""

HANOI_VERIFICATION_CONTEXT = """
Domain-Specific Checks for Tower of Hanoi:
1. All disks moved from source to target peg
2. Disks are in correct order (largest at bottom)
3. No invalid moves (larger on smaller)
4. Optimal moves = 2^n - 1 (where n = number of disks)
   - 3 disks: 7 moves optimal
   - 4 disks: 15 moves optimal
   - 5 disks: 31 moves optimal
"""

GRAPH_VERIFICATION_CONTEXT = """
Domain-Specific Checks for Graph Traversal:
1. Path exists from start to goal
2. All edges in path are valid
3. No invalid node traversals
4. For shortest path: Compare to known optimal (if available)
"""


def build_verification_prompt(
    domain: str,
    goal: dict,
    execution_trace: list,
    final_state: dict,
    initial_state: dict,
    optimal_steps: int = None,
) -> tuple:
    """
    Build verification prompt

    Args:
        domain: Domain name
        goal: Goal state
        execution_trace: List of execution steps
        final_state: Final state after execution
        initial_state: Initial state
        optimal_steps: Known optimal steps (if available)

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Format execution trace
    trace_str = format_execution_trace(execution_trace)

    # Domain-specific checks
    if domain == "tower_of_hanoi":
        domain_checks = HANOI_VERIFICATION_CONTEXT
    elif domain == "graph_traversal":
        domain_checks = GRAPH_VERIFICATION_CONTEXT
    else:
        domain_checks = "No domain-specific checks available."

    # Add optimal steps info if available
    if optimal_steps:
        domain_checks += f"\n\nKnown Optimal: {optimal_steps} steps"

    user_prompt = VERIFICATION_USER_PROMPT.format(
        domain=domain,
        goal=str(goal),
        execution_trace=trace_str,
        final_state=str(final_state),
        initial_state=str(initial_state),
        domain_specific_checks=domain_checks,
    )

    return VERIFICATION_SYSTEM_PROMPT, user_prompt


def format_execution_trace(trace: list) -> str:
    """Format execution trace for prompt"""
    if not trace:
        return "No execution trace available"

    lines = []
    for step in trace:
        step_num = step.get("step", "?")
        operator = step.get("operator", "unknown")
        params = step.get("params", [])
        status = step.get("status", "unknown")

        lines.append(
            f"Step {step_num}: {operator}({', '.join(map(str, params))}) - {status}"
        )

    return "\n".join(lines)


def parse_verification_response(response_text: str) -> dict:
    """
    Parse LLM verification response

    Args:
        response_text: Raw LLM response

    Returns:
        Dict with verification results or error
    """
    import json
    import re

    try:
        # Try direct JSON parse
        result = json.loads(response_text)

        # Validate required keys
        required = ["goal_achieved", "quality_score", "reasoning"]

        for key in required:
            if key not in result:
                return {
                    "error": f"Missing required key: {key}",
                    "raw_response": response_text,
                }

        # Set defaults for optional keys
        result.setdefault("constraint_violations", [])
        result.setdefault("logical_issues", [])
        result.setdefault("efficiency_score", 50)
        result.setdefault("suggestions", [])
        result.setdefault("actual_steps", 0)
        result.setdefault("optimal_steps", None)

        return result

    except json.JSONDecodeError:
        # Try to extract JSON from markdown
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                return result
            except (json.JSONDecodeError, ValueError):
                pass

        return {"error": "Failed to parse JSON response", "raw_response": response_text}


def calculate_quality_metrics(
    goal_achieved: bool,
    constraint_violations: list,
    logical_issues: list,
    efficiency_score: int,
    actual_steps: int,
    optimal_steps: int = None,
) -> dict:
    """
    Calculate detailed quality metrics

    Args:
        goal_achieved: Whether goal was achieved
        constraint_violations: List of violations
        logical_issues: List of logical problems
        efficiency_score: Efficiency score (0-100)
        actual_steps: Actual number of steps
        optimal_steps: Optimal number of steps (if known)

    Returns:
        Dict with quality metrics
    """
    metrics = {
        "goal_achievement": 100 if goal_achieved else 0,
        "constraint_compliance": (
            100
            if len(constraint_violations) == 0
            else max(0, 100 - len(constraint_violations) * 20)
        ),
        "logical_soundness": (
            100 if len(logical_issues) == 0 else max(0, 100 - len(logical_issues) * 20)
        ),
        "efficiency": efficiency_score,
    }

    # Calculate optimality ratio if optimal known
    if optimal_steps and optimal_steps > 0:
        optimality_ratio = optimal_steps / actual_steps
        metrics["optimality_ratio"] = min(1.0, optimality_ratio)
        metrics["optimality_percentage"] = min(100, optimality_ratio * 100)
    else:
        metrics["optimality_ratio"] = None
        metrics["optimality_percentage"] = None

    # Overall quality (weighted average)
    weights = {
        "goal_achievement": 0.4,
        "constraint_compliance": 0.3,
        "logical_soundness": 0.2,
        "efficiency": 0.1,
    }

    overall = sum(
        metrics[key] * weight for key, weight in weights.items() if key in metrics
    )

    metrics["overall_quality"] = overall

    return metrics
