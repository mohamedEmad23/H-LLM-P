"""
Core HTN Planning Module

This package contains the fundamental components for HTN planning:
- State representation and management
- Task definitions (primitive and compound)
- Operators (primitive actions)
- Methods (task decomposition rules)
- HTN planner implementation

Author: H-LLM-P Project
Phase: 1 - Foundation (CoT + RAG)
"""

from .state_manager import State, StateManager
from .task_manager import Task, PrimitiveTask, CompoundTask, TaskManager, TaskType
from .operator import Operator, OperatorLibrary
from .methods import Method, MethodLibrary
from .htn_planner import HTNPlanner, PlanningResult

__all__ = [
    # State management
    "State",
    "StateManager",
    # Task management
    "Task",
    "PrimitiveTask",
    "CompoundTask",
    "TaskManager",
    "TaskType",
    # Operators
    "Operator",
    "OperatorLibrary",
    # Methods
    "Method",
    "MethodLibrary",
    # Planner
    "HTNPlanner",
    "PlanningResult",
]
