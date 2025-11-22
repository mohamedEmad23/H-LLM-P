"""Domain representation for HTN planning.

Simple domain class to hold tasks, methods, and operators for the Problem Ingestion Layer.
"""

from typing import Any


class Domain:
    """Lightweight domain representation for HTN planning."""

    def __init__(self, name: str):
        """Initialize domain.

        Args:
            name: Domain name (typically matches problem_type)
        """
        self.name = name
        self.description = ""
        self.tasks = []
        self.methods = []
        self.operators = []

    def add_task(self, task: Any) -> None:
        """Add a task to the domain.

        Args:
            task: Task object (simplified or full Task class)
        """
        self.tasks.append(task)

    def add_method(self, method: Any) -> None:
        """Add a method to the domain.

        Args:
            method: Method object (simplified or full Method class)
        """
        self.methods.append(method)

    def add_operator(self, operator: Any) -> None:
        """Add an operator to the domain.

        Args:
            operator: Operator object (simplified or full Operator class)
        """
        self.operators.append(operator)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Domain(name='{self.name}', "
            f"tasks={len(self.tasks)}, "
            f"methods={len(self.methods)}, "
            f"operators={len(self.operators)})"
        )
