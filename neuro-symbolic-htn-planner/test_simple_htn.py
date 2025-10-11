"""
Simple HTN Planner Test

A minimal test with concrete predicates to validate the core planning algorithm.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import (
    State, PrimitiveTask, CompoundTask,
    Operator, OperatorLibrary,
    Method, MethodLibrary,
    HTNPlanner
)
from loguru import logger
from rich.console import Console

logger.remove()
logger.add(sys.stdout, level="INFO")
console = Console()

def test_simple_planning():
    """Test with fully concrete predicates"""
    
    # === Create operators with concrete predicates ===
    operators = OperatorLibrary()
    
    # Pickup block A
    operators.register(Operator(
        name="pickup_a",
        preconditions={"on_table(a)", "clear(a)", "hand_empty"},
        add_effects={"holding(a)"},
        delete_effects={"on_table(a)", "clear(a)", "hand_empty"}
    ))
    
    # Putdown block A
    operators.register(Operator(
        name="putdown_a",
        preconditions={"holding(a)"},
        add_effects={"on_table(a)", "clear(a)", "hand_empty"},
        delete_effects={"holding(a)"}
    ))
    
    # Stack A on B
    operators.register(Operator(
        name="stack_a_on_b",
        preconditions={"holding(a)", "clear(b)"},
        add_effects={"on(a,b)", "clear(a)", "hand_empty"},
        delete_effects={"holding(a)", "clear(b)"}
    ))
    
    # === Create methods ===
    methods = MethodLibrary()
    
    # Method: Move A to B from table
    methods.register(Method(
        name="move_a_to_b_from_table",
        task_name="move_a_to_b",
        preconditions={"on_table(a)", "clear(a)", "clear(b)", "hand_empty"},
        subtasks=[
            PrimitiveTask("pickup_a", {}),
            PrimitiveTask("stack_a_on_b", {})
        ]
    ))
    
    # === Create planner ===
    planner = HTNPlanner(operators=operators, methods=methods)
    
    # === Test 1: Simple primitive task ===
    console.print("\n[bold cyan]Test 1: Execute Primitive Task[/bold cyan]")
    console.print("=" * 60)
    
    initial_state = State(predicates={
        "on_table(a)",
        "clear(a)",
        "hand_empty"
    })
    
    result = planner.plan(initial_state, [PrimitiveTask("pickup_a", {})])
    
    if result.success:
        console.print("[green]✓ Test 1 PASSED[/green]")
        console.print(f"Plan: {[t.name for t in result.plan]}")
    else:
        console.print(f"[red]✗ Test 1 FAILED: {result.message}[/red]")
        return False
    
    # === Test 2: Compound task decomposition ===
    console.print("\n[bold cyan]Test 2: Compound Task Decomposition[/bold cyan]")
    console.print("=" * 60)
    
    initial_state2 = State(predicates={
        "on_table(a)",
        "on_table(b)",
        "clear(a)",
        "clear(b)",
        "hand_empty"
    })
    
    console.print("\n[bold]Initial State:[/bold]")
    console.print(initial_state2.to_natural_language())
    
    result2 = planner.plan(initial_state2, [CompoundTask("move_a_to_b", {})])
    
    if result2.success:
        console.print("\n[green]✓ Test 2 PASSED[/green]")
        console.print(f"\nGenerated Plan ({len(result2.plan)} steps):")
        for i, task in enumerate(result2.plan, 1):
            console.print(f"  {i}. {task.name}")
        
        console.print("\n[bold]Decomposition Trace:[/bold]")
        for line in result2.metadata['trace']:
            console.print(f"  {line}")
        
        console.print("\n[bold]Final State:[/bold]")
        console.print(result2.final_state.to_natural_language())
        
        console.print(f"\n[dim]Stats: {result2.metadata['stats']}[/dim]")
    else:
        console.print(f"[red]✗ Test 2 FAILED: {result2.message}[/red]")
        console.print("\nTrace:")
        for line in result2.metadata['trace']:
            console.print(f"  {line}")
        return False
    
    # === Test 3: Knowledge gap ===
    console.print("\n[bold cyan]Test 3: Knowledge Gap Detection[/bold cyan]")
    console.print("=" * 60)
    
    result3 = planner.plan(initial_state2, [CompoundTask("unknown_task", {})])
    
    if not result3.success:
        console.print("[yellow]✓ Test 3 PASSED - Knowledge gap detected[/yellow]")
    else:
        console.print("[red]✗ Test 3 FAILED - Should have failed[/red]")
        return False
    
    console.print("\n[bold green]🎉 All tests passed![/bold green]")
    console.print("[dim]HTN planner core is working correctly[/dim]")
    return True

if __name__ == "__main__":
    try:
        success = test_simple_planning()
        sys.exit(0 if success else 1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
