"""
HTN Planner Module

This module implements the core Hierarchical Task Network (HTN) planning algorithm.
It performs recursive task decomposition to generate executable plans.

The planner operates in two modes:
1. Symbolic mode: Uses only predefined methods from the method library
2. LLM-augmented mode: Queries LLM when no methods are found (Phase 2)

Author: H-LLM-P Project
Phase: 1 - Foundation (CoT + RAG)
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from copy import deepcopy
from loguru import logger

from .state_manager import State, StateManager
from .task_manager import Task, PrimitiveTask, CompoundTask, TaskManager
from .operator import Operator, OperatorLibrary
from .methods import Method, MethodLibrary


@dataclass
class PlanningResult:
    """
    Encapsulates the result of a planning attempt.
    
    Attributes:
        success: Whether planning succeeded
        plan: List of primitive tasks (if successful)
        final_state: The state after executing the plan
        message: Human-readable message about the result
        metadata: Additional information (decomposition trace, etc.)
    """
    success: bool
    plan: List[PrimitiveTask] = field(default_factory=list)
    final_state: Optional[State] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class HTNPlanner:
    """
    Hierarchical Task Network Planner
    
    Implements recursive task decomposition using HTN methods.
    This is the symbolic planning core that will be augmented with
    LLM capabilities in Phase 2.
    
    The planner uses depth-first search through the task network,
    trying methods in priority order until a valid plan is found.
    """
    
    def __init__(
        self,
        operators: Optional[OperatorLibrary] = None,
        methods: Optional[MethodLibrary] = None,
        use_llm: bool = False
    ):
        """
        Initialize the HTN planner.
        
        Args:
            operators: Library of primitive operators
            methods: Library of task decomposition methods
            use_llm: Whether to use LLM for knowledge gap filling (Phase 2)
        """
        self.operators = operators or OperatorLibrary()
        self.methods = methods or MethodLibrary()
        self.use_llm = use_llm
        
        # Planning statistics
        self.stats = {
            "decompositions": 0,
            "method_attempts": 0,
            "backtracking": 0,
            "llm_queries": 0
        }
        
        # Decomposition trace for debugging
        self.decomposition_trace: List[str] = []
        
        logger.info(f"HTN Planner initialized: {len(self.operators)} operators, {len(self.methods)} methods")
    
    def plan(
        self,
        initial_state: State,
        goals: List[Task],
        max_depth: int = 100
    ) -> PlanningResult:
        """
        Generate a plan to accomplish the given goals.
        
        Args:
            initial_state: The initial world state
            goals: List of tasks to accomplish
            max_depth: Maximum decomposition depth (prevents infinite recursion)
            
        Returns:
            PlanningResult containing the plan or failure information
        """
        logger.info(f"Starting planning with {len(goals)} goal(s)")
        logger.debug(f"Initial state: {initial_state.to_natural_language()}")
        
        # Reset statistics and trace
        self.stats = {key: 0 for key in self.stats}
        self.decomposition_trace = []
        
        # Attempt to plan
        try:
            plan = self._plan_tasks(goals, initial_state, depth=0, max_depth=max_depth)
            
            if plan is None:
                logger.warning("Planning failed: No valid plan found")
                return PlanningResult(
                    success=False,
                    message="No valid plan found",
                    metadata={"stats": self.stats, "trace": self.decomposition_trace}
                )
            
            # Simulate execution to get final state
            final_state = self._simulate_plan(plan, initial_state)
            
            logger.info(f"✓ Planning succeeded! Generated plan with {len(plan)} steps")
            logger.debug(f"Statistics: {self.stats}")
            
            return PlanningResult(
                success=True,
                plan=plan,
                final_state=final_state,
                message=f"Plan found with {len(plan)} steps",
                metadata={"stats": self.stats, "trace": self.decomposition_trace}
            )
            
        except RecursionError:
            logger.error("Planning failed: Maximum recursion depth exceeded")
            return PlanningResult(
                success=False,
                message="Maximum recursion depth exceeded",
                metadata={"stats": self.stats, "trace": self.decomposition_trace}
            )
        
        except Exception as e:
            logger.error(f"Planning failed with exception: {e}")
            return PlanningResult(
                success=False,
                message=f"Planning error: {str(e)}",
                metadata={"stats": self.stats, "trace": self.decomposition_trace}
            )
    
    def _plan_tasks(
        self,
        tasks: List[Task],
        state: State,
        depth: int,
        max_depth: int
    ) -> Optional[List[PrimitiveTask]]:
        """
        Recursively plan a list of tasks.
        
        Args:
            tasks: List of tasks to plan
            state: Current state
            depth: Current recursion depth
            max_depth: Maximum allowed depth
            
        Returns:
            List of primitive tasks if successful, None if planning fails
        """
        if depth > max_depth:
            logger.warning(f"Maximum depth ({max_depth}) exceeded")
            return None
        
        if not tasks:
            return []  # Empty task list - success
        
        # Plan the first task
        first_task = tasks[0]
        remaining_tasks = tasks[1:]
        
        # Get plan for the first task
        first_plan = self._plan_single_task(first_task, state, depth, max_depth)
        
        if first_plan is None:
            return None  # Failed to plan first task
        
        # Update state after first task
        new_state = self._apply_plan_to_state(first_plan, state)
        
        # Recursively plan remaining tasks
        remaining_plan = self._plan_tasks(remaining_tasks, new_state, depth, max_depth)
        
        if remaining_plan is None:
            return None  # Failed to plan remaining tasks
        
        # Combine plans
        return first_plan + remaining_plan
    
    def _plan_single_task(
        self,
        task: Task,
        state: State,
        depth: int,
        max_depth: int
    ) -> Optional[List[PrimitiveTask]]:
        """
        Plan a single task (either primitive or compound).
        
        Args:
            task: The task to plan
            state: Current state
            depth: Current recursion depth
            max_depth: Maximum allowed depth
            
        Returns:
            List of primitive tasks if successful, None if planning fails
        """
        indent = "  " * depth
        self.decomposition_trace.append(f"{indent}→ Planning: {task.get_signature()}")
        
        # BASE CASE: Primitive task
        if task.is_primitive():
            return self._handle_primitive_task(task, state, depth)
        
        # RECURSIVE CASE: Compound task
        return self._handle_compound_task(task, state, depth, max_depth)
    
    def _handle_primitive_task(
        self,
        task: PrimitiveTask,
        state: State,
        depth: int
    ) -> Optional[List[PrimitiveTask]]:
        """
        Handle a primitive task by checking if its operator is applicable.
        
        Args:
            task: The primitive task
            state: Current state
            depth: Current recursion depth
            
        Returns:
            List containing the task if applicable, None otherwise
        """
        indent = "  " * depth
        operator = self.operators.get(task.name)
        
        if operator is None:
            logger.warning(f"{indent}✗ No operator found for primitive task: {task.name}")
            self.decomposition_trace.append(f"{indent}  ✗ Operator not found")
            return None
        
        if not operator.is_applicable(state):
            logger.debug(f"{indent}✗ Operator not applicable: {task.name}")
            self.decomposition_trace.append(f"{indent}  ✗ Preconditions not met")
            return None
        
        logger.debug(f"{indent}✓ Primitive task applicable: {task.name}")
        self.decomposition_trace.append(f"{indent}  ✓ Executable")
        return [task]
    
    def _handle_compound_task(
        self,
        task: CompoundTask,
        state: State,
        depth: int,
        max_depth: int
    ) -> Optional[List[PrimitiveTask]]:
        """
        Handle a compound task by finding and applying an applicable method.
        
        Args:
            task: The compound task
            state: Current state
            depth: Current recursion depth
            max_depth: Maximum allowed depth
            
        Returns:
            List of primitive tasks if decomposition succeeds, None otherwise
        """
        indent = "  " * depth
        self.stats["decompositions"] += 1
        
        # Find applicable methods
        applicable_methods = self.methods.get_applicable_methods(task.name, state)
        
        if not applicable_methods:
            # KNOWLEDGE GAP DETECTED
            logger.debug(f"{indent}⚠ Knowledge gap: No methods for '{task.name}'")
            self.decomposition_trace.append(f"{indent}  ⚠ No applicable methods")
            
            if self.use_llm:
                # LLM integration point (Phase 2)
                logger.info(f"{indent}🤖 Would query LLM here (Phase 2)")
                self.stats["llm_queries"] += 1
                return None  # For now, return None
            else:
                return None
        
        # Try each applicable method in priority order
        for method in applicable_methods:
            self.stats["method_attempts"] += 1
            logger.debug(f"{indent}↓ Trying method: {method.name}")
            self.decomposition_trace.append(f"{indent}  ↓ Method: {method.name}")
            
            # Get subtasks from method
            subtasks = method.get_subtasks()
            
            # Recursively plan subtasks
            plan = self._plan_tasks(subtasks, state, depth + 1, max_depth)
            
            if plan is not None:
                logger.debug(f"{indent}✓ Method succeeded: {method.name}")
                self.decomposition_trace.append(f"{indent}  ✓ Decomposition successful")
                return plan
            
            # Method failed, try next one
            logger.debug(f"{indent}✗ Method failed: {method.name}")
            self.decomposition_trace.append(f"{indent}  ✗ Decomposition failed, backtracking...")
            self.stats["backtracking"] += 1
        
        # All methods failed
        logger.debug(f"{indent}✗ All methods failed for task: {task.name}")
        return None
    
    def _apply_plan_to_state(
        self,
        plan: List[PrimitiveTask],
        state: State
    ) -> State:
        """
        Apply a sequence of primitive tasks to a state.
        
        Args:
            plan: List of primitive tasks
            state: Initial state
            
        Returns:
            Resulting state after applying all tasks
        """
        current_state = state
        
        for task in plan:
            operator = self.operators.get(task.name)
            if operator:
                current_state = operator.apply(current_state, task.parameters)
        
        return current_state
    
    def _simulate_plan(
        self,
        plan: List[PrimitiveTask],
        initial_state: State
    ) -> State:
        """
        Simulate plan execution to compute the final state.
        
        Args:
            plan: The plan to simulate
            initial_state: Starting state
            
        Returns:
            Final state after plan execution
        """
        return self._apply_plan_to_state(plan, initial_state)
    
    def get_decomposition_trace(self) -> str:
        """
        Get a human-readable decomposition trace.
        
        Returns:
            Multi-line string showing the decomposition process
        """
        return "\n".join(self.decomposition_trace)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get planning statistics"""
        return self.stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset planning statistics"""
        self.stats = {key: 0 for key in self.stats}
        self.decomposition_trace = []
