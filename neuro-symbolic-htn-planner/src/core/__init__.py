"""
Core HTN Planning Module

This package contains the fundamental components for HTN planning:
- State representation and management
- Task definitions (primitive and compound)
- Operators (primitive actions)  
- HTN planner implementation

Author: H-LLM-P Project
Phase: 1 - Foundation (CoT + RAG)
"""

from .state_manager import State, StateManager
from .task_manager import Task, PrimitiveTask, CompoundTask, TaskManager, TaskType
from .operator import Operator, OperatorLibrary

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
]
