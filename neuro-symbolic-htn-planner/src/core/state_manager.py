"""
State Manager Module

This module provides the core state representation for the HTN planner.
States are represented as sets of ground predicates (strings) that describe
the world at any given time.

Author: H-LLM-P Project
Phase: 1 - Foundation (CoT + RAG)
"""

from typing import Set, Dict, Any, Optional
from dataclasses import dataclass, field
from copy import deepcopy
from loguru import logger


@dataclass
class State:
    """
    Represents the world state as a set of ground predicates.

    A predicate is a string representing a fact about the world.
    Examples:
        - "at(robot, kitchen)"
        - "holding(robot, cup)"
        - "clean(kitchen)"
        - "empty(robot_hand)"

    Attributes:
        predicates: Set of predicate strings that are true in this state
        metadata: Optional dictionary for storing additional state information
    """

    predicates: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize predicates"""
        if not isinstance(self.predicates, set):
            self.predicates = set(self.predicates)

        # Normalize predicates (remove extra whitespace)
        self.predicates = {p.strip() for p in self.predicates if p.strip()}

    def holds(self, predicate: str) -> bool:
        """
        Check if a predicate is true in this state.

        Args:
            predicate: The predicate string to check

        Returns:
            True if the predicate exists in the state, False otherwise
        """
        return predicate.strip() in self.predicates

    def holds_all(self, predicates: Set[str]) -> bool:
        """
        Check if all predicates in a set are true in this state.

        Args:
            predicates: Set of predicate strings to check

        Returns:
            True if all predicates exist in the state, False otherwise
        """
        return all(self.holds(p) for p in predicates)

    def apply_effects(self, add_list: Set[str], delete_list: Set[str]) -> "State":
        """
        Apply operator effects to produce a new state.

        This implements the STRIPS-style state transition:
        new_state = (current_state - delete_list) ∪ add_list

        Args:
            add_list: Set of predicates to add to the state
            delete_list: Set of predicates to remove from the state

        Returns:
            A new State object with the effects applied
        """
        new_predicates = (self.predicates - delete_list) | add_list
        new_metadata = deepcopy(self.metadata)

        logger.debug(f"State transition: Added {add_list}, Deleted {delete_list}")

        return State(predicates=new_predicates, metadata=new_metadata)

    def add_predicate(self, predicate: str) -> None:
        """Add a single predicate to the state (in-place)"""
        self.predicates.add(predicate.strip())

    def remove_predicate(self, predicate: str) -> None:
        """Remove a single predicate from the state (in-place)"""
        self.predicates.discard(predicate.strip())

    def to_natural_language(self) -> str:
        """
        Convert the state to a human-readable string.
        Useful for LLM prompts and debugging.

        Returns:
            Multi-line string with one predicate per line
        """
        if not self.predicates:
            return "Empty state (no predicates)"

        sorted_predicates = sorted(self.predicates)
        return "\n".join(f"- {pred}" for pred in sorted_predicates)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization"""
        return {"predicates": list(self.predicates), "metadata": self.metadata}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "State":
        """Create a State from a dictionary"""
        return cls(
            predicates=set(data.get("predicates", [])),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        """String representation for debugging"""
        pred_count = len(self.predicates)
        preview = list(self.predicates)[:3]
        preview_str = ", ".join(preview)
        suffix = "..." if pred_count > 3 else ""
        return f"State({pred_count} predicates: {preview_str}{suffix})"

    def __eq__(self, other: Any) -> bool:
        """Check equality of two states"""
        if not isinstance(other, State):
            return False
        return self.predicates == other.predicates

    def __hash__(self) -> int:
        """Make State hashable for use in sets/dicts"""
        return hash(frozenset(self.predicates))


class StateManager:
    """
    Manages state history and provides utilities for state manipulation.
    Useful for tracking execution traces and debugging.
    """

    def __init__(self):
        self.state_history: list[State] = []
        self.current_state: Optional[State] = None

    def initialize(self, initial_state: State) -> None:
        """Initialize the state manager with an initial state"""
        self.current_state = deepcopy(initial_state)
        self.state_history = [deepcopy(initial_state)]
        logger.info(
            f"State manager initialized with {len(initial_state.predicates)} predicates"
        )

    def transition(self, add_list: Set[str], delete_list: Set[str]) -> State:
        """
        Perform a state transition and record it in history.

        Args:
            add_list: Predicates to add
            delete_list: Predicates to delete

        Returns:
            The new current state
        """
        if self.current_state is None:
            raise ValueError("State manager not initialized")

        self.current_state = self.current_state.apply_effects(add_list, delete_list)
        self.state_history.append(deepcopy(self.current_state))

        return self.current_state

    def get_current_state(self) -> Optional[State]:
        """Get the current state"""
        return self.current_state

    def get_history(self) -> list[State]:
        """Get the full state history"""
        return self.state_history

    def reset(self) -> None:
        """Reset the state manager"""
        self.current_state = None
        self.state_history = []
        logger.info("State manager reset")
