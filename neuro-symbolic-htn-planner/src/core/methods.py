"""
Methods Module

This module defines HTN methods - the knowledge for decomposing compound tasks
into subtasks. Methods are the core of hierarchical planning, encoding
procedural knowledge about how to accomplish abstract goals.

Author: H-LLM-P Project
Phase: 1 - Foundation (CoT + RAG)
"""

from typing import List, Set, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger

from .task_manager import Task, CompoundTask
from .state_manager import State


@dataclass
class Method:
    """
    Defines one way to decompose a compound task into subtasks.

    A method specifies:
    - Which compound task it decomposes
    - Preconditions that must hold for this method to be applicable
    - An ordered list of subtasks to accomplish the compound task

    Example:
        Method(
            name="get_coffee_from_kitchen",
            task_name="get_coffee",
            preconditions={"at(robot, office)", "coffee_in(kitchen)"},
            subtasks=[
                CompoundTask("navigate_to", {"location": "kitchen"}),
                PrimitiveTask("pick_up", {"object": "coffee"}),
                CompoundTask("navigate_to", {"location": "office"})
            ]
        )

    Attributes:
        name: Unique identifier for this method
        task_name: Name of the compound task this method decomposes
        preconditions: Set of predicates that must hold for applicability
        subtasks: Ordered list of tasks to execute
        priority: Optional priority for method selection (higher = preferred)
        metadata: Additional information about the method
    """

    name: str
    task_name: str  # Which compound task this decomposes
    preconditions: Set[str] = field(default_factory=set)
    subtasks: List[Task] = field(default_factory=list)
    priority: int = 0  # Higher priority methods are tried first
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate method definition"""
        if not isinstance(self.preconditions, set):
            self.preconditions = set(self.preconditions)

        # Normalize predicates
        self.preconditions = {p.strip() for p in self.preconditions if p.strip()}

        if not isinstance(self.subtasks, list):
            self.subtasks = list(self.subtasks)

        if not self.subtasks:
            logger.warning(f"Method '{self.name}' has no subtasks")

    def is_applicable(self, state: State) -> bool:
        """
        Check if this method can be applied in the given state.

        Args:
            state: The current world state

        Returns:
            True if all preconditions are satisfied, False otherwise
        """
        return state.holds_all(self.preconditions)

    def get_subtasks(self) -> List[Task]:
        """
        Get the ordered list of subtasks for this method.

        Returns:
            List of subtasks to execute
        """
        return self.subtasks.copy()

    def to_natural_language(self) -> str:
        """
        Convert method to human-readable description.
        Useful for LLM prompts and documentation.

        Returns:
            Natural language description of the method
        """
        desc = f"Method: {self.name}\n"
        desc += f"  Decomposes: {self.task_name}\n"

        if self.preconditions:
            desc += "  Requires:\n"
            for pre in sorted(self.preconditions):
                desc += f"    - {pre}\n"

        if self.subtasks:
            desc += "  Subtasks:\n"
            for i, subtask in enumerate(self.subtasks, 1):
                desc += f"    {i}. {subtask.to_natural_language()}\n"

        return desc.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert method to dictionary for serialization"""
        return {
            "name": self.name,
            "task_name": self.task_name,
            "preconditions": list(self.preconditions),
            "subtasks": [task.to_dict() for task in self.subtasks],
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Method":
        """Create a Method from a dictionary"""
        from .task_manager import PrimitiveTask

        # Reconstruct subtasks
        subtasks = []
        for task_data in data.get("subtasks", []):
            task_type = task_data.get("type")
            if task_type == "primitive":
                subtasks.append(
                    PrimitiveTask(
                        name=task_data["name"],
                        parameters=task_data.get("parameters", {}),
                    )
                )
            else:
                subtasks.append(
                    CompoundTask(
                        name=task_data["name"],
                        parameters=task_data.get("parameters", {}),
                    )
                )

        return cls(
            name=data["name"],
            task_name=data["task_name"],
            preconditions=set(data.get("preconditions", [])),
            subtasks=subtasks,
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"Method(name={self.name}, task={self.task_name}, subtasks={len(self.subtasks)})"

    def __eq__(self, other: Any) -> bool:
        """Check equality based on name"""
        if not isinstance(other, Method):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        """Make Method hashable"""
        return hash(self.name)


class MethodLibrary:
    """
    Manages a collection of methods for a planning domain.
    Provides registration, lookup, and method selection utilities.
    """

    def __init__(self):
        # Maps task_name -> list of methods that decompose it
        self.methods: Dict[str, List[Method]] = {}
        self._all_methods: Dict[str, Method] = {}  # For lookup by method name

    def register(self, method: Method) -> None:
        """
        Register a method in the library.

        Args:
            method: The method to register
        """
        if method.name in self._all_methods:
            logger.warning(f"Overwriting existing method: {method.name}")

        # Add to task-specific methods
        if method.task_name not in self.methods:
            self.methods[method.task_name] = []

        self.methods[method.task_name].append(method)
        self._all_methods[method.name] = method

        logger.debug(f"Registered method: {method.name} for task: {method.task_name}")

    def get_methods_for_task(self, task_name: str) -> List[Method]:
        """
        Get all methods that can decompose a given task.

        Args:
            task_name: The name of the compound task

        Returns:
            List of methods (sorted by priority, highest first)
        """
        methods = self.methods.get(task_name, [])
        # Sort by priority (highest first)
        return sorted(methods, key=lambda m: m.priority, reverse=True)

    def get_applicable_methods(self, task_name: str, state: State) -> List[Method]:
        """
        Get all applicable methods for a task in the given state.

        Args:
            task_name: The name of the compound task
            state: The current world state

        Returns:
            List of applicable methods (sorted by priority)
        """
        methods = self.get_methods_for_task(task_name)
        applicable = [m for m in methods if m.is_applicable(state)]

        logger.debug(
            f"Found {len(applicable)}/{len(methods)} applicable methods for '{task_name}'"
        )

        return applicable

    def get_method_by_name(self, name: str) -> Optional[Method]:
        """
        Retrieve a specific method by its name.

        Args:
            name: The method name

        Returns:
            The method if found, None otherwise
        """
        return self._all_methods.get(name)

    def has_methods_for(self, task_name: str) -> bool:
        """
        Check if any methods exist for a given task.

        Args:
            task_name: The task name to check

        Returns:
            True if methods exist, False otherwise
        """
        return task_name in self.methods and len(self.methods[task_name]) > 0

    def get_all_task_names(self) -> Set[str]:
        """Get all task names that have registered methods"""
        return set(self.methods.keys())

    def to_natural_language(self) -> str:
        """
        Convert all methods to natural language descriptions.
        Useful for LLM prompts.

        Returns:
            Multi-line string describing all methods
        """
        if not self._all_methods:
            return "No methods defined."

        descriptions = []
        for method in sorted(
            self._all_methods.values(), key=lambda m: (m.task_name, m.name)
        ):
            descriptions.append(method.to_natural_language())

        return "\n\n".join(descriptions)

    def __len__(self) -> int:
        """Return the total number of registered methods"""
        return len(self._all_methods)

    def __contains__(self, name: str) -> bool:
        """Check if a method is registered"""
        return name in self._all_methods

    def __repr__(self) -> str:
        """String representation for debugging"""
        task_count = len(self.methods)
        method_count = len(self._all_methods)
        return f"MethodLibrary({method_count} methods for {task_count} tasks)"
