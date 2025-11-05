"""
Operator Module

This module defines operators (primitive actions) for the HTN planner.
Operators represent actions that can be directly executed in the world,
with preconditions and effects specified in STRIPS-style.

Author: H-LLM-P Project
Phase: 1 - Foundation (CoT + RAG)
"""

from typing import Set, Callable, Any, Optional, Dict
from dataclasses import dataclass, field
from loguru import logger

from .state_manager import State


@dataclass
class Operator:
    """
    Defines the behavior of a primitive task.

    An operator specifies:
    - Preconditions: What must be true before execution
    - Add effects: What becomes true after execution
    - Delete effects: What becomes false after execution
    - Executor: Python function that performs the actual action

    Example:
        Operator(
            name="pick_up",
            preconditions={"at(robot, ?loc)", "at(?obj, ?loc)", "empty(robot_hand)"},
            add_effects={"holding(robot, ?obj)"},
            delete_effects={"at(?obj, ?loc)", "empty(robot_hand)"},
            executor=lambda state, params: print(f"Picking up {params['obj']}")
        )

    Attributes:
        name: Unique identifier for this operator
        preconditions: Set of predicates that must hold before execution
        add_effects: Set of predicates that become true after execution
        delete_effects: Set of predicates that become false after execution
        executor: Callable that simulates/executes the action
        cost: Optional cost metric for plan optimization
        duration: Optional duration for temporal planning
    """

    name: str
    preconditions: Set[str] = field(default_factory=set)
    add_effects: Set[str] = field(default_factory=set)
    delete_effects: Set[str] = field(default_factory=set)
    executor: Optional[Callable] = field(default=None, repr=False)
    cost: float = 1.0
    duration: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate operator definition"""
        # Ensure all fields are sets
        if not isinstance(self.preconditions, set):
            self.preconditions = set(self.preconditions)
        if not isinstance(self.add_effects, set):
            self.add_effects = set(self.add_effects)
        if not isinstance(self.delete_effects, set):
            self.delete_effects = set(self.delete_effects)

        # Normalize predicates (remove extra whitespace)
        self.preconditions = {p.strip() for p in self.preconditions if p.strip()}
        self.add_effects = {p.strip() for p in self.add_effects if p.strip()}
        self.delete_effects = {p.strip() for p in self.delete_effects if p.strip()}

        # Validation: Check for conflicts
        conflict = self.add_effects & self.delete_effects
        if conflict:
            logger.warning(
                f"Operator '{self.name}' has conflicting effects: {conflict}. "
                "Add effects take precedence."
            )

    def is_applicable(self, state: State) -> bool:
        """
        Check if all preconditions are satisfied in the given state.

        Args:
            state: The current world state

        Returns:
            True if the operator can be executed, False otherwise
        """
        return state.holds_all(self.preconditions)

    def apply(self, state: State, parameters: Optional[Dict[str, Any]] = None) -> State:
        """
        Execute the operator and return the resulting state.

        Args:
            state: The current world state
            parameters: Optional parameters for ground instantiation

        Returns:
            The new state after applying effects

        Raises:
            ValueError: If preconditions are not satisfied
        """
        if not self.is_applicable(state):
            missing = self.preconditions - state.predicates
            raise ValueError(
                f"Operator '{self.name}' not applicable. "
                f"Missing preconditions: {missing}"
            )

        # Apply effects to create new state
        new_state = state.apply_effects(self.add_effects, self.delete_effects)

        logger.info(f"✓ Executed operator: {self.name}")
        logger.debug(f"  Added: {self.add_effects}")
        logger.debug(f"  Deleted: {self.delete_effects}")

        return new_state

    def execute(
        self, state: State, parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Execute the actual action in the world (simulation).

        This calls the executor function if provided, which can perform
        side effects like controlling a robot or updating external systems.

        Args:
            state: The current world state
            parameters: Parameters for the action

        Returns:
            True if execution succeeded, False otherwise
        """
        if self.executor is None:
            logger.warning(f"No executor defined for operator '{self.name}'")
            return True  # Assume success if no executor

        try:
            params = parameters or {}
            result = self.executor(state, params)

            # If executor returns bool, use that; otherwise assume success
            success = result if isinstance(result, bool) else True

            if success:
                logger.info(f"✓ Executed '{self.name}' successfully")
            else:
                logger.error(f"✗ Execution of '{self.name}' failed")

            return success

        except Exception as e:
            logger.error(f"✗ Exception during execution of '{self.name}': {e}")
            return False

    def to_natural_language(self) -> str:
        """
        Convert operator to human-readable description.
        Useful for LLM prompts and documentation.

        Returns:
            Natural language description of the operator
        """
        desc = f"Action: {self.name.replace('_', ' ')}\n"

        if self.preconditions:
            desc += "  Requires:\n"
            for pre in sorted(self.preconditions):
                desc += f"    - {pre}\n"

        if self.add_effects:
            desc += "  Effects (added):\n"
            for eff in sorted(self.add_effects):
                desc += f"    + {eff}\n"

        if self.delete_effects:
            desc += "  Effects (removed):\n"
            for eff in sorted(self.delete_effects):
                desc += f"    - {eff}\n"

        return desc.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert operator to dictionary for serialization"""
        return {
            "name": self.name,
            "preconditions": list(self.preconditions),
            "add_effects": list(self.add_effects),
            "delete_effects": list(self.delete_effects),
            "cost": self.cost,
            "duration": self.duration,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Operator":
        """Create an Operator from a dictionary"""
        return cls(
            name=data["name"],
            preconditions=set(data.get("preconditions", [])),
            add_effects=set(data.get("add_effects", [])),
            delete_effects=set(data.get("delete_effects", [])),
            cost=data.get("cost", 1.0),
            duration=data.get("duration", 1.0),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"Operator(name={self.name}, preconditions={len(self.preconditions)}, effects={len(self.add_effects) + len(self.delete_effects)})"


class OperatorLibrary:
    """
    Manages a collection of operators for a planning domain.
    Provides registration, lookup, and validation utilities.
    """

    def __init__(self):
        self.operators: Dict[str, Operator] = {}

    def register(self, operator: Operator) -> None:
        """
        Register an operator in the library.

        Args:
            operator: The operator to register
        """
        if operator.name in self.operators:
            logger.warning(f"Overwriting existing operator: {operator.name}")

        self.operators[operator.name] = operator
        logger.debug(f"Registered operator: {operator.name}")

    def get(self, name: str) -> Optional[Operator]:
        """
        Retrieve an operator by name.

        Args:
            name: The operator name

        Returns:
            The operator if found, None otherwise
        """
        return self.operators.get(name)

    def get_all(self) -> Dict[str, Operator]:
        """Get all registered operators"""
        return self.operators

    def get_applicable_operators(self, state: State) -> list[Operator]:
        """
        Find all operators that can be executed in the given state.

        Args:
            state: The current world state

        Returns:
            List of applicable operators
        """
        return [op for op in self.operators.values() if op.is_applicable(state)]

    def to_natural_language(self) -> str:
        """
        Convert all operators to natural language descriptions.
        Useful for LLM prompts.

        Returns:
            Multi-line string describing all operators
        """
        if not self.operators:
            return "No operators defined."

        descriptions = []
        for operator in sorted(self.operators.values(), key=lambda op: op.name):
            descriptions.append(operator.to_natural_language())

        return "\n\n".join(descriptions)

    def __len__(self) -> int:
        """Return the number of registered operators"""
        return len(self.operators)

    def __contains__(self, name: str) -> bool:
        """Check if an operator is registered"""
        return name in self.operators
