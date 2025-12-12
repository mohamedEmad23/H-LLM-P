"""
Decomposition Agent Prompts
Specialized prompts for HTN task decomposition using LLMs
"""

DECOMPOSITION_SYSTEM_PROMPT = """You are an expert in Hierarchical Task Network (HTN) planning and task decomposition.

Your role is to break down high-level tasks into hierarchical subtasks following HTN principles:

1. **Recursive Decomposition**: Complex tasks should be decomposed into smaller subtasks
2. **Base Cases**: Identify when a task is primitive (cannot be decomposed further)
3. **Preconditions**: Ensure each subtask has valid preconditions
4. **Effects**: Define what state changes each subtask produces
5. **Constraints**: Respect domain-specific constraints

You must return structured HTN methods in valid JSON format."""

DECOMPOSITION_USER_PROMPT = """Task to decompose: {task}
Domain: {domain}

Available Operators:
{operators}

Domain Constraints:
{constraints}

{memory_hints}

Please generate HTN methods that decompose this task into valid subtasks.

Requirements:
1. Provide one or more decomposition methods
2. Each method should have:
   - task: The high-level task being decomposed
   - subtasks: List of subtasks (in execution order)
   - preconditions: What must be true before this method can be used
   - effects: What becomes true after this method succeeds
   - confidence: Your confidence in this decomposition (0.0-1.0)

3. Use recursive decomposition where appropriate
4. Ensure all subtasks are either primitive operators or decomposable tasks
5. Respect all domain constraints

Return ONLY valid JSON in this exact format:
{{
  "methods": [
    {{
      "task": "task_name(params)",
      "subtasks": ["subtask1(params)", "subtask2(params)", ...],
      "preconditions": ["condition1", "condition2", ...],
      "effects": ["effect1", "effect2", ...],
      "confidence": 0.95,
      "reasoning": "Brief explanation of why this decomposition works"
    }}
  ],
  "alternatives_considered": 2
}}"""

HANOI_DOMAIN_CONTEXT = """
Tower of Hanoi Domain:
- Goal: Move all disks from source peg to target peg
- Rules:
  1. Only one disk can be moved at a time
  2. A disk can only be moved if it's on top of its peg
  3. A larger disk cannot be placed on a smaller disk

- Operators:
  - move_disk(disk_num, from_peg, to_peg): Move disk from one peg to another

- Decomposition Strategy:
  - Base case: solve_hanoi(1, source, target, aux) = move_disk(1, source, target)
  - Recursive case for n disks:
    1. Move n-1 disks from source to auxiliary (using target as temporary)
    2. Move disk n from source to target
    3. Move n-1 disks from auxiliary to target (using source as temporary)
"""

GRAPH_DOMAIN_CONTEXT = """
Graph Traversal Domain:
- Goal: Find path from start node to goal node
- Rules:
  1. Can only traverse existing edges
  2. Cannot revisit nodes (for cycle-free paths)
  3. Must track visited nodes

- Operators:
  - traverse_edge(from_node, to_node): Move from one node to another
  - mark_visited(node): Mark node as visited

- Decomposition Strategy:
  - Base case: If at goal, return success
  - Recursive case:
    1. Mark current node as visited
    2. For each unvisited neighbor:
       - Traverse to neighbor
       - Recursively find path from neighbor to goal
"""

MEMORY_HINTS_TEMPLATE = """
Past Successful Plans (similar tasks):
{similar_plans}

Common Patterns:
{common_patterns}

Errors to Avoid:
{error_patterns}
"""

# ========== HDDL CORRECTION PROMPTS (for LLM feedback loop) ==========

HDDL_CORRECTION_SYSTEM_PROMPT = """You are an expert in HDDL (Hierarchical Domain Definition Language) syntax and semantics for HTN planning.

Your task is to FIX HDDL domain files that failed validation by the PANDA HTN planner.

HDDL Syntax Rules:
1. Domain structure: (define (domain name) (:requirements ...) (:types ...) (:predicates ...) (:task ...) (:method ...) (:action ...))
2. Task definitions: (:task task_name :parameters (?var1 - type1 ?var2 - type2))
3. Method definitions: (:method method_name :parameters (...) :task (task_name ?params) :precondition (and ...) :subtasks (and ...))
4. Action definitions: (:action action_name :parameters (...) :precondition (and ...) :effect (and ...))
5. Predicates must be defined before use
6. All variables must be declared in :parameters
7. Parentheses must be balanced

Common HDDL Errors:
- Undefined predicates (predicate used but not declared in :predicates)
- Type mismatches (variable type doesn't match predicate signature)
- Unbalanced parentheses
- Missing or extra keywords
- Invalid subtask ordering

Return ONLY the corrected HDDL domain file, nothing else."""

HDDL_CORRECTION_USER_PROMPT = """Original HDDL Domain that failed validation:
```hddl
{original_hddl}
```

PANDA Validation Errors:
{validation_errors}

Please analyze these errors and provide a CORRECTED version of the HDDL domain that:
1. Fixes ALL the validation errors listed above
2. Maintains the same domain semantics and planning intent
3. Uses proper HDDL syntax throughout
4. Ensures all predicates are declared before use
5. Ensures all variables are properly typed

Return ONLY the corrected HDDL code (no explanations, no markdown code blocks)."""

HDDL_GENERATION_SYSTEM_PROMPT = """You are an expert HDDL (Hierarchical Domain Definition Language) generator for HTN planning.

Generate valid HDDL domain files that can be processed by the PANDA HTN planner.

HDDL Structure:
```
(define (domain domain_name)
  (:requirements :hierarchy :typing)
  
  (:types type1 type2 - object)
  
  (:predicates 
    (predicate1 ?arg1 - type1)
    (predicate2 ?arg1 - type1 ?arg2 - type2)
  )
  
  (:task task_name :parameters (?var1 - type1 ?var2 - type2))
  
  (:method method_name
    :parameters (?var1 - type1 ?var2 - type2)
    :task (task_name ?var1 ?var2)
    :precondition (and (predicate1 ?var1))
    :subtasks (and
      (subtask1 ?var1)
      (subtask2 ?var2)
    )
  )
  
  (:action action_name
    :parameters (?var1 - type1 ?var2 - type2)
    :precondition (and (predicate1 ?var1))
    :effect (and 
      (not (predicate1 ?var1))
      (predicate2 ?var1 ?var2)
    )
  )
)
```

Rules:
1. ALL predicates must be declared in :predicates before use
2. ALL variables must have types declared in :parameters  
3. Parentheses must be perfectly balanced
4. Use (and ...) for multiple preconditions/effects/subtasks
5. Tasks define the abstract goals, methods decompose them, actions are primitive

Return ONLY valid HDDL code."""

HDDL_GENERATION_USER_PROMPT = """Generate an HDDL domain for:

Domain: {domain_name}
Task: {task_description}

Available Operators (convert to :action blocks):
{operators}

Methods to implement (convert to :method blocks):
{methods_json}

Objects and Types:
{objects}

Initial State Predicates (declare these in :predicates):
{initial_predicates}

Goal Tasks:
{goal_tasks}

{strategy_hints}

Generate a complete, valid HDDL domain file that:
1. Defines all necessary types
2. Declares all predicates used
3. Defines task schemas for each abstract task
4. Implements methods that decompose tasks into subtasks
5. Implements actions for primitive operations

Return ONLY the HDDL code (no markdown, no explanations)."""


def build_hddl_correction_prompt(original_hddl: str, validation_errors: list) -> tuple:
    """
    Build prompt for correcting invalid HDDL based on PANDA errors
    
    Args:
        original_hddl: The HDDL text that failed validation
        validation_errors: List of error messages from PANDA
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    errors_str = "\n".join([f"- {error}" for error in validation_errors])
    
    user_prompt = HDDL_CORRECTION_USER_PROMPT.format(
        original_hddl=original_hddl,
        validation_errors=errors_str
    )
    
    return HDDL_CORRECTION_SYSTEM_PROMPT, user_prompt


def build_hddl_generation_prompt(
    domain_name: str,
    task_description: str,
    operators: list,
    methods_json: str,
    objects: dict,
    initial_predicates: list,
    goal_tasks: list,
    strategy_hints: list = None
) -> tuple:
    """
    Build prompt for generating HDDL domain from scratch
    
    Args:
        domain_name: Name of the domain
        task_description: Description of the main task
        operators: List of operator definitions
        methods_json: JSON string of method definitions from LLM
        objects: Dict of objects {name: type}
        initial_predicates: List of initial state predicates
        goal_tasks: List of goal task tuples
        strategy_hints: Optional list of strategy hints
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Format operators
    operators_str = ""
    for op in operators:
        if hasattr(op, 'name'):
            op_name = op.name
            params = getattr(op, 'parameters', {})
            precond = getattr(op, 'preconditions', [])
            effects = getattr(op, 'effects', [])
        elif isinstance(op, dict):
            op_name = op.get('name', 'unknown')
            params = op.get('parameters', {})
            precond = op.get('preconditions', [])
            effects = op.get('effects', [])
        else:
            continue
            
        operators_str += f"\n- {op_name}:\n"
        operators_str += f"    Parameters: {params}\n"
        operators_str += f"    Preconditions: {precond}\n"
        operators_str += f"    Effects: {effects}\n"
    
    # Format objects
    objects_str = "\n".join([f"- {name}: {obj_type}" for name, obj_type in objects.items()]) if objects else "No objects defined"
    
    # Format initial predicates
    init_str = "\n".join([f"- {pred}" for pred in initial_predicates]) if initial_predicates else "No initial predicates"
    
    # Format goal tasks
    goals_str = "\n".join([f"- {task[0]}({', '.join(task[1]) if len(task) > 1 else ''})" for task in goal_tasks]) if goal_tasks else "No goal tasks"
    
    # Format strategy hints
    hints_str = ""
    if strategy_hints:
        hints_str = "\nStrategy Hints from Similar Problems:\n"
        for hint in strategy_hints:
            if isinstance(hint, dict):
                hints_str += f"- {hint.get('name', 'unnamed')}: {hint.get('approach', hint.get('description', ''))}\n"
            else:
                hints_str += f"- {hint}\n"
    
    user_prompt = HDDL_GENERATION_USER_PROMPT.format(
        domain_name=domain_name,
        task_description=task_description,
        operators=operators_str or "No operators defined",
        methods_json=methods_json,
        objects=objects_str,
        initial_predicates=init_str,
        goal_tasks=goals_str,
        strategy_hints=hints_str
    )
    
    return HDDL_GENERATION_SYSTEM_PROMPT, user_prompt


def format_memory_hints(similar_plans=None, common_patterns=None, error_patterns=None):
    """Format memory hints section for the prompt"""
    if not any([similar_plans, common_patterns, error_patterns]):
        return "No memory hints available (first time solving this type of task)."

    hints = []

    if similar_plans:
        plans_str = "\n".join([f"  - {plan}" for plan in similar_plans])
        hints.append(f"Past Successful Plans:\n{plans_str}")

    if common_patterns:
        patterns_str = "\n".join([f"  - {pattern}" for pattern in common_patterns])
        hints.append(f"Common Patterns:\n{patterns_str}")

    if error_patterns:
        errors_str = "\n".join([f"  - {error}" for error in error_patterns])
        hints.append(f"Errors to Avoid:\n{errors_str}")

    return "\n\n".join(hints)


def format_operators(operators):
    """Format operators dict into readable string"""
    if not operators:
        return "No operators defined"

    lines = []
    for op_name, op_def in operators.items():
        params = op_def.get("parameters", [])
        precond = op_def.get("preconditions", [])
        effects = op_def.get("effects", [])

        lines.append(f"- {op_name}({', '.join(params)})")
        if precond:
            lines.append(f"    Preconditions: {', '.join(precond)}")
        if effects:
            lines.append(f"    Effects: {', '.join(effects)}")

    return "\n".join(lines)


def format_constraints(constraints):
    """Format constraints into readable string"""
    if not constraints:
        return "No specific constraints"

    if isinstance(constraints, list):
        return "\n".join([f"- {c}" for c in constraints])
    elif isinstance(constraints, dict):
        lines = []
        for key, value in constraints.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    else:
        return str(constraints)


def build_decomposition_prompt(
    task,
    domain,
    operators=None,
    constraints=None,
    memory_hints=None,
    domain_context=None,
):
    """
    Build complete decomposition prompt with all context

    Args:
        task: Task string to decompose (e.g., "solve_hanoi(3, A, C, B)")
        domain: Domain name (e.g., "tower_of_hanoi")
        operators: Dict of available operators
        constraints: List or dict of domain constraints
        memory_hints: Dict with similar_plans, common_patterns, error_patterns
        domain_context: Optional domain-specific context string

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Format operators
    operators_str = format_operators(operators or {})

    # Format constraints
    constraints_str = format_constraints(constraints or [])

    # Format memory hints
    if memory_hints:
        memory_str = format_memory_hints(
            similar_plans=memory_hints.get("similar_plans"),
            common_patterns=memory_hints.get("common_patterns"),
            error_patterns=memory_hints.get("error_patterns"),
        )
    else:
        memory_str = "No memory hints available."

    # Add domain-specific context
    if domain_context:
        constraints_str = f"{constraints_str}\n\nDomain Context:\n{domain_context}"
    elif domain == "tower_of_hanoi":
        constraints_str = f"{constraints_str}\n\n{HANOI_DOMAIN_CONTEXT}"
    elif domain == "graph_traversal":
        constraints_str = f"{constraints_str}\n\n{GRAPH_DOMAIN_CONTEXT}"

    # Build user prompt
    user_prompt = DECOMPOSITION_USER_PROMPT.format(
        task=task,
        domain=domain,
        operators=operators_str,
        constraints=constraints_str,
        memory_hints=memory_str,
    )

    return DECOMPOSITION_SYSTEM_PROMPT, user_prompt


def parse_decomposition_response(response_text):
    """
    Parse LLM response into structured decomposition

    Args:
        response_text: Raw text response from LLM

    Returns:
        Dict with parsed methods or error dict
    """
    import json
    import re

    try:
        # Try direct JSON parse
        result = json.loads(response_text)

        # Validate structure
        if "methods" not in result:
            return {
                "error": "Missing 'methods' key in response",
                "raw_response": response_text,
            }

        if not isinstance(result["methods"], list):
            return {"error": "'methods' must be a list", "raw_response": response_text}

        # Validate each method
        for i, method in enumerate(result["methods"]):
            required_keys = [
                "task",
                "subtasks",
                "preconditions",
                "effects",
                "confidence",
            ]
            for key in required_keys:
                if key not in method:
                    return {
                        "error": f"Method {i} missing required key: {key}",
                        "raw_response": response_text,
                    }

        return result

    except json.JSONDecodeError as e:
        # Try to extract JSON from markdown code blocks
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                return result
            except (json.JSONDecodeError, ValueError):
                pass

        return {
            "error": f"Failed to parse JSON: {str(e)}",
            "raw_response": response_text,
        }
