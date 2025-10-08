"""
Prompt Builder for HTN Task Decomposition

This module provides prompt templates and builders specifically designed for
Hierarchical Task Network (HTN) planning. It uses Chain of Thought (CoT) prompting
to guide LLMs in decomposing complex tasks into executable sequences.

Features:
- Chain of Thought (CoT) prompting for HTN decomposition
- Few-shot learning examples
- Different strategies for different model types (fast vs reasoning models)
- Template variables for task context
- Method extraction format specifications
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class PromptStrategy(Enum):
    """Different prompting strategies for different use cases."""
    FAST = "fast"           # Minimal prompts for fast models (Groq, small models)
    REASONING = "reasoning"  # Detailed CoT for reasoning models (Gemini, Cohere)
    CODE_FOCUSED = "code"   # For code-specialized models (Codestral, CodeLLaMA)
    LOCAL = "local"         # Optimized for local models (Ollama)


@dataclass
class HTNTask:
    """Represents an HTN task to be decomposed."""
    name: str
    parameters: List[str]
    preconditions: List[str]
    effects: List[str]
    description: Optional[str] = None


@dataclass
class DomainContext:
    """Context about the HTN domain."""
    domain_name: str
    available_operators: List[str]
    available_methods: List[str]
    state_variables: List[str]
    examples: Optional[List[str]] = None


class PromptBuilder:
    """
    Builds prompts for LLM-based HTN task decomposition.
    
    Supports multiple prompting strategies and provides templates
    for different types of HTN reasoning tasks.
    """
    
    # Few-shot examples for HTN decomposition
    EXAMPLES = {
        "blocks_world": """
Example 1: Blocks World Domain
Task: move_block(block_a, table, block_b)
Description: Move block A from the table onto block B

Reasoning Steps:
1. Check preconditions: block_a must be clear, block_b must be clear
2. Decompose into subtasks:
   a. If block_a is on something else, remove it first (unstack)
   b. Pick up block_a from current location
   c. Place block_a onto block_b (stack)
3. Verify effects: block_a is now on block_b, block_a is not on table

Method Decomposition:
```
Method: move_block_to_block
  Task: move_block(?block, ?from, ?to)
  Preconditions:
    - clear(?block)
    - clear(?to)
    - on(?block, ?from)
  Subtasks:
    1. unstack(?block, ?from)
    2. stack(?block, ?to)
  Effects:
    - on(?block, ?to)
    - NOT on(?block, ?from)
    - clear(?from)
    - NOT clear(?to)
```
""",
        "logistics": """
Example 2: Logistics Domain
Task: deliver_package(pkg1, location_a, location_b, city1)
Description: Deliver package from location A to location B within the same city

Reasoning Steps:
1. Check preconditions: package exists, locations are valid, truck available
2. Decompose into subtasks:
   a. Load package onto truck at location_a
   b. Drive truck from location_a to location_b
   c. Unload package from truck at location_b
3. Verify effects: package is at location_b

Method Decomposition:
```
Method: deliver_within_city
  Task: deliver_package(?pkg, ?from, ?to, ?city)
  Preconditions:
    - at(?pkg, ?from)
    - in_city(?from, ?city)
    - in_city(?to, ?city)
    - truck_available(?truck, ?city)
  Subtasks:
    1. load_truck(?pkg, ?truck, ?from)
    2. drive_truck(?truck, ?from, ?to, ?city)
    3. unload_truck(?pkg, ?truck, ?to)
  Effects:
    - at(?pkg, ?to)
    - NOT at(?pkg, ?from)
```
""",
        "cooking": """
Example 3: Cooking Domain
Task: make_coffee()
Description: Make a cup of coffee

Reasoning Steps:
1. Check preconditions: coffee beans available, water available, coffee maker clean
2. Decompose into subtasks:
   a. Grind coffee beans
   b. Fill water reservoir
   c. Add coffee grounds to filter
   d. Start brewing
   e. Pour coffee into cup
3. Verify effects: coffee is ready in cup

Method Decomposition:
```
Method: make_brewed_coffee
  Task: make_coffee()
  Preconditions:
    - has_ingredient(coffee_beans)
    - has_ingredient(water)
    - clean(coffee_maker)
    - has_equipment(cup)
  Subtasks:
    1. grind_beans(coffee_beans, grounds)
    2. fill_reservoir(water, coffee_maker)
    3. add_coffee(grounds, coffee_maker)
    4. brew_coffee(coffee_maker)
    5. pour_coffee(coffee_maker, cup)
  Effects:
    - coffee_ready(cup)
    - NOT has_ingredient(coffee_beans)
    - NOT has_ingredient(water)
```
"""
    }
    
    def __init__(self, strategy: PromptStrategy = PromptStrategy.REASONING):
        """
        Initialize the prompt builder.
        
        Args:
            strategy: The prompting strategy to use
        """
        self.strategy = strategy
    
    def build_task_decomposition_prompt(
        self,
        task: HTNTask,
        domain_context: DomainContext,
        include_examples: bool = True
    ) -> str:
        """
        Build a prompt for decomposing an HTN task.
        
        Args:
            task: The task to decompose
            domain_context: Context about the HTN domain
            include_examples: Whether to include few-shot examples
            
        Returns:
            The complete prompt string
        """
        if self.strategy == PromptStrategy.FAST:
            return self._build_fast_prompt(task, domain_context)
        elif self.strategy == PromptStrategy.REASONING:
            return self._build_reasoning_prompt(task, domain_context, include_examples)
        elif self.strategy == PromptStrategy.CODE_FOCUSED:
            return self._build_code_prompt(task, domain_context)
        else:  # LOCAL
            return self._build_local_prompt(task, domain_context, include_examples)
    
    def _build_fast_prompt(self, task: HTNTask, domain_context: DomainContext) -> str:
        """Build a minimal prompt for fast models."""
        return f"""Decompose this HTN task into subtasks:

Task: {task.name}({', '.join(task.parameters)})
{f'Description: {task.description}' if task.description else ''}

Available operators: {', '.join(domain_context.available_operators)}

Provide the method decomposition in this format:
Method: <method_name>
  Task: {task.name}({', '.join('?' + p for p in task.parameters)})
  Subtasks:
    1. <subtask_1>
    2. <subtask_2>
    ...
"""
    
    def _build_reasoning_prompt(
        self,
        task: HTNTask,
        domain_context: DomainContext,
        include_examples: bool
    ) -> str:
        """Build a detailed Chain of Thought prompt for reasoning models."""
        prompt = f"""You are an expert in Hierarchical Task Network (HTN) planning. Your task is to decompose complex tasks into sequences of subtasks that can be executed to achieve a goal.

## Domain Context
Domain: {domain_context.domain_name}
Available Operators: {', '.join(domain_context.available_operators)}
Existing Methods: {', '.join(domain_context.available_methods) if domain_context.available_methods else 'None'}
State Variables: {', '.join(domain_context.state_variables)}

"""
        
        if include_examples and domain_context.domain_name.lower() in self.EXAMPLES:
            prompt += f"""## Learning Examples
{self.EXAMPLES.get(domain_context.domain_name.lower(), self.EXAMPLES['blocks_world'])}

"""
        
        prompt += f"""## Task to Decompose
Task: {task.name}({', '.join(task.parameters)})
{f'Description: {task.description}' if task.description else ''}

Preconditions:
{self._format_list(task.preconditions)}

Expected Effects:
{self._format_list(task.effects)}

## Instructions
Please think step-by-step and provide:

1. **Reasoning**: Explain your thought process for decomposing this task
2. **Method Decomposition**: Provide the formal method structure
3. **Verification**: Explain why this decomposition achieves the goal

Use this format for the method:
```
Method: <method_name>
  Task: {task.name}({', '.join('?' + p for p in task.parameters)})
  Preconditions:
{self._format_list(['- ' + p for p in task.preconditions])}
  Subtasks:
    1. <subtask_name>(<parameters>)
    2. <subtask_name>(<parameters>)
    ...
  Effects:
{self._format_list(['- ' + e for e in task.effects])}
```

Begin your response with your reasoning, then provide the method decomposition.
"""
        return prompt
    
    def _build_code_prompt(self, task: HTNTask, domain_context: DomainContext) -> str:
        """Build a prompt optimized for code-focused models."""
        return f"""# HTN Method Generation

Generate a Python-like HTN method for the following task:

## Domain: {domain_context.domain_name}

## Task Specification
```python
class Task:
    name = "{task.name}"
    parameters = {task.parameters}
    preconditions = {task.preconditions}
    effects = {task.effects}
```

## Available Operators
{chr(10).join(f'- {op}' for op in domain_context.available_operators)}

## Required Output Format
```python
class Method:
    name = "<method_name>"
    task = "{task.name}"
    parameters = {[f"?{p}" for p in task.parameters]}
    
    preconditions = [
        # List precondition predicates
    ]
    
    subtasks = [
        # List of (task_name, [parameters]) tuples
        ("<subtask_1>", ["?param1", "?param2"]),
        ("<subtask_2>", ["?param3"]),
    ]
    
    effects = [
        # List effect predicates
    ]
```

Provide the method implementation:
"""
    
    def _build_local_prompt(
        self,
        task: HTNTask,
        domain_context: DomainContext,
        include_examples: bool
    ) -> str:
        """Build a prompt optimized for local models (shorter context)."""
        prompt = f"""Decompose this HTN task into executable subtasks.

Domain: {domain_context.domain_name}
Operators: {', '.join(domain_context.available_operators[:10])}  # Limit for context

Task: {task.name}({', '.join(task.parameters)})
{f'Description: {task.description}' if task.description else ''}

"""
        
        if include_examples:
            prompt += """Example Method:
```
Method: example_method
  Task: example_task(?obj)
  Subtasks:
    1. subtask_1(?obj)
    2. subtask_2(?obj)
```

"""
        
        prompt += f"""Your Task Method:
```
Method: <name>
  Task: {task.name}({', '.join('?' + p for p in task.parameters)})
  Subtasks:
    1. <subtask>(<params>)
    2. ...
```
"""
        return prompt
    
    def build_method_refinement_prompt(
        self,
        original_method: str,
        failure_reason: str,
        execution_trace: List[str]
    ) -> str:
        """
        Build a prompt for refining a failed method.
        
        Args:
            original_method: The method that failed
            failure_reason: Why it failed
            execution_trace: Trace of execution steps
            
        Returns:
            Prompt for method refinement
        """
        return f"""The following HTN method failed during execution. Please refine it to fix the issue.

## Original Method
```
{original_method}
```

## Failure Information
Reason: {failure_reason}

Execution Trace:
{self._format_list(execution_trace)}

## Instructions
1. Analyze why the method failed
2. Identify the problematic subtask(s)
3. Provide a corrected version of the method

Focus on:
- Checking preconditions are satisfied before subtasks
- Ensuring subtasks are in correct order
- Verifying all parameters are bound correctly
- Making sure effects are achievable

Provide the refined method in the same format:
```
Method: <refined_method_name>
  Task: ...
  Preconditions: ...
  Subtasks: ...
  Effects: ...
```
"""
    
    def build_gap_analysis_prompt(
        self,
        current_state: Dict[str, Any],
        goal_state: Dict[str, Any],
        attempted_methods: List[str]
    ) -> str:
        """
        Build a prompt for analyzing knowledge gaps in HTN planning.
        
        Args:
            current_state: Current world state
            goal_state: Desired goal state
            attempted_methods: Methods that were tried
            
        Returns:
            Prompt for gap analysis
        """
        return f"""Analyze the knowledge gap in this HTN planning scenario.

## Current State
{self._format_dict(current_state)}

## Goal State
{self._format_dict(goal_state)}

## Attempted Methods
{self._format_list(attempted_methods)}

## Task
The planner cannot find a path from the current state to the goal state using existing methods.

Please:
1. Identify what's missing (operators, methods, or preconditions)
2. Suggest new methods or operators needed
3. Explain how they would bridge the gap

Format your response as:
1. **Gap Analysis**: What's preventing progress?
2. **Missing Knowledge**: What methods/operators are needed?
3. **Proposed Solution**: Detailed method or operator definition
"""
    
    def build_validation_prompt(
        self,
        method: str,
        domain_constraints: List[str]
    ) -> str:
        """
        Build a prompt for validating a generated method.
        
        Args:
            method: The method to validate
            domain_constraints: Constraints from the domain
            
        Returns:
            Prompt for validation
        """
        return f"""Validate this HTN method against domain constraints.

## Method to Validate
```
{method}
```

## Domain Constraints
{self._format_list(domain_constraints)}

## Validation Checklist
Please verify:
1. ✓ All preconditions are checkable
2. ✓ Subtasks use valid operators or known methods
3. ✓ Parameters are correctly bound
4. ✓ Effects are consistent with subtasks
5. ✓ No circular dependencies
6. ✓ Ordering constraints are logical

Provide:
- **Valid**: Yes/No
- **Issues Found**: List of problems (if any)
- **Corrected Method**: Fixed version (if needed)
"""
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list with proper indentation."""
        if not items:
            return "  - None"
        return '\n'.join(f"  - {item}" for item in items)
    
    def _format_dict(self, d: Dict[str, Any]) -> str:
        """Format a dictionary as a readable string."""
        return '\n'.join(f"  {k}: {v}" for k, v in d.items())
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for HTN planning.
        
        Returns:
            System prompt to set LLM behavior
        """
        if self.strategy == PromptStrategy.FAST:
            return "You are an HTN planning expert. Provide concise, direct method decompositions."
        elif self.strategy == PromptStrategy.REASONING:
            return """You are an expert in Hierarchical Task Network (HTN) planning with deep knowledge of:
- Task decomposition strategies
- Precondition and effect reasoning
- Operator sequencing
- Planning domain modeling

Provide detailed, well-reasoned method decompositions using Chain of Thought reasoning."""
        elif self.strategy == PromptStrategy.CODE_FOCUSED:
            return """You are a code generation expert specializing in HTN planning systems. 
Generate clean, well-structured method definitions in a Python-like format."""
        else:  # LOCAL
            return "You are an HTN planning assistant. Break down tasks into clear subtasks."


# Convenience functions for common use cases

def build_decomposition_prompt(
    task_name: str,
    task_params: List[str],
    domain_name: str,
    operators: List[str],
    strategy: PromptStrategy = PromptStrategy.REASONING,
    task_description: Optional[str] = None,
    preconditions: Optional[List[str]] = None,
    effects: Optional[List[str]] = None
) -> tuple[str, str]:
    """
    Build a task decomposition prompt (convenience function).
    
    Args:
        task_name: Name of the task
        task_params: Task parameters
        domain_name: Domain name
        operators: Available operators
        strategy: Prompting strategy
        task_description: Optional task description
        preconditions: Optional preconditions
        effects: Optional effects
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    builder = PromptBuilder(strategy)
    
    task = HTNTask(
        name=task_name,
        parameters=task_params,
        preconditions=preconditions or [],
        effects=effects or [],
        description=task_description
    )
    
    domain = DomainContext(
        domain_name=domain_name,
        available_operators=operators,
        available_methods=[],
        state_variables=[]
    )
    
    system_prompt = builder.get_system_prompt()
    user_prompt = builder.build_task_decomposition_prompt(task, domain)
    
    return system_prompt, user_prompt


def build_quick_prompt(task_name: str, description: str, operators: List[str]) -> str:
    """
    Build a quick decomposition prompt for fast iteration.
    
    Args:
        task_name: Task to decompose
        description: Task description
        operators: Available operators
        
    Returns:
        Complete prompt string
    """
    return f"""Decompose: {task_name}
Description: {description}
Operators: {', '.join(operators)}

Method:
  Task: {task_name}
  Subtasks:
"""


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("HTN Prompt Builder - Example Usage")
    print("="*80)
    
    # Example 1: Reasoning strategy
    print("\n### Example 1: Detailed Reasoning Prompt ###\n")
    builder = PromptBuilder(PromptStrategy.REASONING)
    
    task = HTNTask(
        name="move_block",
        parameters=["block", "from_loc", "to_loc"],
        preconditions=["clear(block)", "clear(to_loc)", "on(block, from_loc)"],
        effects=["on(block, to_loc)", "NOT on(block, from_loc)"],
        description="Move a block from one location to another"
    )
    
    domain = DomainContext(
        domain_name="blocks_world",
        available_operators=["pickup", "putdown", "stack", "unstack"],
        available_methods=["move_to_table", "move_to_block"],
        state_variables=["on", "clear", "holding"]
    )
    
    system_prompt = builder.get_system_prompt()
    user_prompt = builder.build_task_decomposition_prompt(task, domain, include_examples=True)
    
    print("SYSTEM PROMPT:")
    print(system_prompt)
    print("\nUSER PROMPT:")
    print(user_prompt[:500] + "...\n[truncated for display]")
    
    # Example 2: Fast strategy
    print("\n### Example 2: Fast Prompt (for Groq) ###\n")
    fast_builder = PromptBuilder(PromptStrategy.FAST)
    fast_prompt = fast_builder.build_task_decomposition_prompt(task, domain)
    print(fast_prompt)
    
    # Example 3: Using convenience function
    print("\n### Example 3: Convenience Function ###\n")
    sys_prompt, usr_prompt = build_decomposition_prompt(
        task_name="make_coffee",
        task_params=[],
        domain_name="cooking",
        operators=["grind_beans", "fill_water", "brew", "pour"],
        strategy=PromptStrategy.LOCAL,
        task_description="Make a cup of coffee",
        preconditions=["has(coffee_beans)", "has(water)", "clean(maker)"],
        effects=["coffee_ready(cup)"]
    )
    print("SYSTEM:", sys_prompt)
    print("\nUSER:", usr_prompt)
    
    print("\n" + "="*80)
    print("✅ Prompt Builder Examples Complete")
    print("="*80)
