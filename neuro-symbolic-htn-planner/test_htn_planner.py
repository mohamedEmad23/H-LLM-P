"""
HTN Planner Test - Blocks World Domain

Tests the complete HTN planner with a classic blocks world domain.
This validates that symbolic planning works before adding LLM integration.

Author: H-LLM-P Project
Phase: 1 - Foundation (CoT + RAG)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import (
    State, PrimitiveTask, CompoundTask,
    Operator, OperatorLibrary,
    Method, MethodLibrary,
    HTNPlanner
)
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

console = Console()


def create_blocks_world_domain():
    """
    Create a simple blocks world domain.
    
    Operators:
    - pickup(block): Pick up a block from the table
    - putdown(block): Put a block on the table
    - stack(block, on_block): Stack a block on another
    - unstack(block, from_block): Unstack a block from another
    
    Methods:
    - move_block_to_table: Move a block to the table
    - move_block_to_block: Move a block onto another block
    """
    
    # === OPERATORS ===
    operators = OperatorLibrary()
    
    # Pickup operator
    operators.register(Operator(
        name="pickup",
        preconditions={"on_table(x)", "clear(x)", "hand_empty"},
        add_effects={"holding(x)"},
        delete_effects={"on_table(x)", "clear(x)", "hand_empty"}
    ))
    
    # Putdown operator
    operators.register(Operator(
        name="putdown",
        preconditions={"holding(x)"},
        add_effects={"on_table(x)", "clear(x)", "hand_empty"},
        delete_effects={"holding(x)"}
    ))
    
    # Stack operator
    operators.register(Operator(
        name="stack",
        preconditions={"holding(x)", "clear(y)"},
        add_effects={"on(x,y)", "clear(x)", "hand_empty"},
        delete_effects={"holding(x)", "clear(y)"}
    ))
    
    # Unstack operator
    operators.register(Operator(
        name="unstack",
        preconditions={"on(x,y)", "clear(x)", "hand_empty"},
        add_effects={"holding(x)", "clear(y)"},
        delete_effects={"on(x,y)", "clear(x)", "hand_empty"}
    ))
    
    # === METHODS ===
    methods = MethodLibrary()
    
    # Method: Move block to table
    methods.register(Method(
        name="move_to_table_from_table",
        task_name="move_to_table",
        preconditions={"on_table(x)", "clear(x)", "hand_empty"},
        subtasks=[],  # Already on table, nothing to do
        priority=10
    ))
    
    methods.register(Method(
        name="move_to_table_from_block",
        task_name="move_to_table",
        preconditions={"on(x,y)", "clear(x)", "hand_empty"},
        subtasks=[
            PrimitiveTask("unstack", {}),
            PrimitiveTask("putdown", {})
        ],
        priority=5
    ))
    
    # Method: Move block to another block
    methods.register(Method(
        name="move_to_block_already_on",
        task_name="move_to_block",
        preconditions={"on(x,y)"},
        subtasks=[],  # Already in position
        priority=10
    ))
    
    methods.register(Method(
        name="move_to_block_from_table",
        task_name="move_to_block",
        preconditions={"on_table(x)", "clear(x)", "clear(y)", "hand_empty"},
        subtasks=[
            PrimitiveTask("pickup", {}),
            PrimitiveTask("stack", {})
        ],
        priority=5
    ))
    
    methods.register(Method(
        name="move_to_block_from_block",
        task_name="move_to_block",
        preconditions={"on(x,z)", "clear(x)", "clear(y)", "hand_empty"},
        subtasks=[
            PrimitiveTask("unstack", {}),
            PrimitiveTask("stack", {})
        ],
        priority=5
    ))
    
    return operators, methods


def test_simple_pickup_putdown():
    """Test simple pickup and putdown"""
    console.print("\n[bold cyan]Test 1: Simple Pickup and Putdown[/bold cyan]")
    console.print("=" * 60)
    
    # Create domain
    operators, methods = create_blocks_world_domain()
    planner = HTNPlanner(operators=operators, methods=methods)
    
    # Initial state: block A on table, clear, hand empty
    initial_state = State(predicates={
        "on_table(a)",
        "clear(a)",
        "hand_empty"
    })
    
    # Goal: pickup block A
    goals = [PrimitiveTask("pickup", {})]
    
    # Plan
    result = planner.plan(initial_state, goals)
    
    # Display results
    if result.success:
        console.print("[green]✓ Planning succeeded![/green]")
        console.print(f"\nPlan ({len(result.plan)} steps):")
        for i, task in enumerate(result.plan, 1):
            console.print(f"  {i}. {task.get_signature()}")
        
        console.print(f"\n[dim]Statistics: {result.metadata['stats']}[/dim]")
    else:
        console.print(f"[red]✗ Planning failed: {result.message}[/red]")
    
    return result.success


def test_compound_task_decomposition():
    """Test decomposition of compound tasks"""
    console.print("\n[bold cyan]Test 2: Compound Task Decomposition[/bold cyan]")
    console.print("=" * 60)
    
    # Create domain
    operators, methods = create_blocks_world_domain()
    planner = HTNPlanner(operators=operators, methods=methods)
    
    # Initial state: block A on table
    initial_state = State(predicates={
        "on_table(a)",
        "clear(a)",
        "hand_empty"
    })
    
    # Goal: move block to table (should be no-op since already there)
    goals = [CompoundTask("move_to_table", {})]
    
    # Plan
    result = planner.plan(initial_state, goals)
    
    # Display results
    if result.success:
        console.print("[green]✓ Planning succeeded![/green]")
        console.print(f"\nPlan ({len(result.plan)} steps):")
        if result.plan:
            for i, task in enumerate(result.plan, 1):
                console.print(f"  {i}. {task.get_signature()}")
        else:
            console.print("  (empty plan - already satisfied)")
        
        console.print("\n[bold]Decomposition Trace:[/bold]")
        console.print(result.metadata['trace'])
        
        console.print(f"\n[dim]Statistics: {result.metadata['stats']}[/dim]")
    else:
        console.print(f"[red]✗ Planning failed: {result.message}[/red]")
    
    return result.success


def test_stacking_blocks():
    """Test stacking blocks"""
    console.print("\n[bold cyan]Test 3: Stacking Blocks[/bold cyan]")
    console.print("=" * 60)
    
    # Create domain
    operators, methods = create_blocks_world_domain()
    planner = HTNPlanner(operators=operators, methods=methods)
    
    # Initial state: blocks A and B on table
    initial_state = State(predicates={
        "on_table(a)",
        "on_table(b)",
        "clear(a)",
        "clear(b)",
        "hand_empty"
    })
    
    console.print("\n[bold]Initial State:[/bold]")
    console.print(initial_state.to_natural_language())
    
    # Goal: move block A onto block B
    goals = [CompoundTask("move_to_block", {})]
    
    # Plan
    result = planner.plan(initial_state, goals)
    
    # Display results
    if result.success:
        console.print("\n[green]✓ Planning succeeded![/green]")
        console.print(f"\nPlan ({len(result.plan)} steps):")
        for i, task in enumerate(result.plan, 1):
            console.print(f"  {i}. {task.get_signature()}")
        
        console.print("\n[bold]Decomposition Trace:[/bold]")
        for line in result.metadata['trace']:
            console.print(f"  {line}")
        
        console.print("\n[bold]Final State:[/bold]")
        if result.final_state:
            console.print(result.final_state.to_natural_language())
        
        console.print(f"\n[dim]Statistics: {result.metadata['stats']}[/dim]")
    else:
        console.print(f"\n[red]✗ Planning failed: {result.message}[/red]")
    
    return result.success


def test_knowledge_gap_detection():
    """Test detection of knowledge gaps (no applicable methods)"""
    console.print("\n[bold cyan]Test 4: Knowledge Gap Detection[/bold cyan]")
    console.print("=" * 60)
    
    # Create domain with limited methods
    operators, methods = create_blocks_world_domain()
    planner = HTNPlanner(operators=operators, methods=methods)
    
    # Initial state
    initial_state = State(predicates={
        "on_table(a)",
        "clear(a)",
        "hand_empty"
    })
    
    # Goal: unknown task (no methods defined)
    goals = [CompoundTask("fly_to_moon", {})]
    
    # Plan
    result = planner.plan(initial_state, goals)
    
    # Display results
    if not result.success:
        console.print("[yellow]✓ Knowledge gap detected correctly![/yellow]")
        console.print(f"\nMessage: {result.message}")
        console.print("\n[bold]Decomposition Trace:[/bold]")
        for line in result.metadata['trace']:
            console.print(f"  {line}")
        console.print("\n[dim]This is where LLM will be called in Phase 2[/dim]")
    else:
        console.print("[red]✗ Should have failed (no methods for this task)[/red]")
        return False
    
    return True


def main():
    """Run all tests"""
    console.print(Panel.fit(
        "[bold cyan]HTN Planner Test Suite[/bold cyan]\n"
        "[dim]Testing symbolic planning before LLM integration[/dim]",
        border_style="cyan"
    ))
    
    results = []
    
    try:
        results.append(("Simple Primitive Task", test_simple_pickup_putdown()))
        results.append(("Compound Task Decomposition", test_compound_task_decomposition()))
        results.append(("Stacking Blocks", test_stacking_blocks()))
        results.append(("Knowledge Gap Detection", test_knowledge_gap_detection()))
        
        # Summary
        console.print("\n" + "=" * 60)
        console.print("[bold]Test Summary:[/bold]")
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for name, success in results:
            status = "[green]✓ PASS[/green]" if success else "[red]✗ FAIL[/red]"
            console.print(f"  {status} - {name}")
        
        console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]")
        
        if passed == total:
            console.print("\n[bold green]🎉 All HTN planner tests passed![/bold green]")
            console.print("[dim]Ready for LLM integration (Phase 2)[/dim]")
            return 0
        else:
            console.print(f"\n[bold red]❌ {total - passed} test(s) failed[/bold red]")
            return 1
            
    except Exception as e:
        console.print(f"\n[bold red]❌ Test suite failed with exception:[/bold red]")
        console.print(f"[red]{e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
