"""
Task Manager Module

This module defines the task hierarchy for HTN planning:
- PrimitiveTask: Directly executable actions
- CompoundTask: Abstract tasks that require decomposition

Author: H-LLM-P Project
Phase: 1 - Foundation (CoT + RAG)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger


class TaskType(Enum):
    """Enumeration of task types"""

    PRIMITIVE = "primitive"
    COMPOUND = "compound"


@dataclass
class Task(ABC):
    """
    Base class for all tasks in the HTN planner.

    A task represents an action or goal that needs to be accomplished.
    Tasks can be either primitive (directly executable) or compound
    (requiring decomposition into subtasks).

    Attributes:
        name: The name/identifier of the task
        parameters: Dictionary of parameter name -> value mappings
        metadata: Additional information about the task
    """

    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def is_primitive(self) -> bool:
        """Check if this is a primitive task"""
        pass

    @abstractmethod
    def get_type(self) -> TaskType:
        """Get the type of this task"""
        pass

    def get_signature(self) -> str:
        """
        Get a unique signature for this task instance.
        Useful for hashing and comparison.

        Returns:
            String representation: name(param1=value1, param2=value2, ...)
        """
        if not self.parameters:
            return f"{self.name}()"

        param_strs = [f"{k}={v}" for k, v in sorted(self.parameters.items())]
        return f"{self.name}({', '.join(param_strs)})"

    def to_natural_language(self) -> str:
        """
        Convert task to natural language description.
        Useful for LLM prompts.

        Returns:
            Human-readable task description
        """
        if not self.parameters:
            return f"{self.name.replace('_', ' ')}"

        # Format parameters nicely
        param_parts = []
        for key, value in self.parameters.items():
            param_parts.append(f"{key}: {value}")

        params_str = ", ".join(param_parts)
        return f"{self.name.replace('_', ' ')} ({params_str})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        return {
            "name": self.name,
            "type": self.get_type().value,
            "parameters": self.parameters,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"{self.__class__.__name__}({self.get_signature()})"

    def __eq__(self, other: Any) -> bool:
        """Check equality based on signature"""
        if not isinstance(other, Task):
            return False
        return self.get_signature() == other.get_signature()

    def __hash__(self) -> int:
        """Make Task hashable"""
        return hash(self.get_signature())


@dataclass
class PrimitiveTask(Task):
    """
    A primitive task that can be directly executed.

    Primitive tasks correspond to operators in classical planning.
    They have preconditions and effects, and can be executed directly
    in the world.

    Example:
        PrimitiveTask(
            name="pick_up",
            parameters={"object": "cup", "location": "table"}
        )
    """

    def is_primitive(self) -> bool:
        """Primitive tasks return True"""
        return True

    def get_type(self) -> TaskType:
        """Return the primitive task type"""
        return TaskType.PRIMITIVE


@dataclass
class CompoundTask(Task):
    """
    A compound (abstract) task that requires decomposition.

    Compound tasks represent high-level goals or abstract actions
    that must be broken down into simpler subtasks through HTN methods.

    Example:
        CompoundTask(
            name="prepare_coffee",
            parameters={"cup_type": "mug", "coffee_type": "espresso"}
        )
    """

    # Optional: Store the decomposition method used (filled during planning)
    decomposition_method: Optional[str] = field(default=None, repr=False)

    def is_primitive(self) -> bool:
        """Compound tasks return False"""
        return False

    def get_type(self) -> TaskType:
        """Return the compound task type"""
        return TaskType.COMPOUND


class TaskManager:
    """
    Manages task creation, validation, and tracking.
    Provides utilities for working with task hierarchies.
    """

    def __init__(self):
        self.task_registry: Dict[str, type] = {}
        self.task_history: List[Task] = []

    def register_task_type(self, task_name: str, task_class: type) -> None:
        """
        Register a task type for dynamic task creation.

        Args:
            task_name: Name of the task
            task_class: Either PrimitiveTask or CompoundTask class
        """
        if task_class not in [PrimitiveTask, CompoundTask]:
            raise ValueError("Task class must be PrimitiveTask or CompoundTask")

        self.task_registry[task_name] = task_class
        logger.debug(f"Registered task type: {task_name} as {task_class.__name__}")

    def create_task(
        self,
        name: str,
        parameters: Optional[Dict[str, Any]] = None,
        is_primitive: bool = False,
    ) -> Task:
        """
        Factory method to create tasks.

        Args:
            name: Task name
            parameters: Task parameters
            is_primitive: Whether this is a primitive task

        Returns:
            A PrimitiveTask or CompoundTask instance
        """
        params = parameters or {}

        # Check registry first
        if name in self.task_registry:
            task_class = self.task_registry[name]
            return task_class(name=name, parameters=params)

        # Otherwise create based on is_primitive flag
        if is_primitive:
            return PrimitiveTask(name=name, parameters=params)
        else:
            return CompoundTask(name=name, parameters=params)

    def log_task(self, task: Task) -> None:
        """Add a task to the execution history"""
        self.task_history.append(task)

    def get_history(self) -> List[Task]:
        """Get the full task execution history"""
        return self.task_history

    def clear_history(self) -> None:
        """Clear the task execution history"""
        self.task_history = []
        logger.debug("Task history cleared")

    @staticmethod
    def parse_task_string(task_str: str) -> tuple[str, Dict[str, Any]]:
        """
        Parse a task string into name and parameters.

        Args:
            task_str: String like "pick_up(object=cup, location=table)"

        Returns:
            Tuple of (task_name, parameters_dict)
        """
        task_str = task_str.strip()

        # Handle simple task with no parameters
        if "(" not in task_str:
            return task_str, {}

        # Extract name and parameters
        name = task_str[: task_str.index("(")]
        params_str = task_str[task_str.index("(") + 1 : task_str.rindex(")")]

        parameters = {}
        if params_str.strip():
            # Parse parameters
            for param in params_str.split(","):
                param = param.strip()
                if "=" in param:
                    key, value = param.split("=", 1)
                    parameters[key.strip()] = value.strip()

        return name, parameters
