# Memory Management System (MMS) - Complete Integration Guide
## Step-by-Step Implementation for Thesis Research

**Target Audience**: Developers implementing MMS for HTN planning thesis
**Estimated Time**: 6-8 weeks
**Prerequisites**: Python 3.9+, existing HTN planner codebase

---

## Table of Contents
1. [Environment Setup](#1-environment-setup)
2. [Gibson AI Memori Integration](#2-gibson-ai-memori-integration)
3. [MMS Core Implementation](#3-mms-core-implementation)
4. [Clue Generator (MemoRAG Pattern)](#4-clue-generator-memorag-pattern)
5. [HTN Planner Integration](#5-htn-planner-integration)
6. [Multi-Agent Coordination](#6-multi-agent-coordination)
7. [Testing & Validation](#7-testing--validation)
8. [Benchmarking](#8-benchmarking)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Environment Setup

### Step 1.1: Install Dependencies

```bash
# Navigate to project root
cd /home/mohammed-emad/VS-CODE/B.Sc\ Thesis/gpt-htn-thesis/neuro-symbolic-htn-planner

# Install Gibson AI Memori SDK
pip install memorisdk

# Verify installation
python -c "from memori import Memori; print('Memori installed successfully!')"
```

**Expected Output**:
```
Memori installed successfully!
```

### Step 1.2: Update `requirements.txt`

```bash
# Add to requirements.txt
echo "memorisdk>=0.1.0  # Gibson AI Memori - SQL-native memory layer" >> requirements.txt
```

### Step 1.3: Create MMS Directory Structure

```bash
mkdir -p src/memory
touch src/memory/__init__.py
touch src/memory/mms_core.py
touch src/memory/clue_generator.py
touch src/memory/memory_types.py
```

**Directory Structure After Setup**:
```
src/memory/
├── __init__.py           # Module exports
├── mms_core.py          # Core MMS class
├── clue_generator.py    # MemoRAG-inspired query decomposer
└── memory_types.py      # Type definitions for memory entries
```

---

## 2. Gibson AI Memori Integration

### Step 2.1: Create `mms_core.py` (Foundation)

```python
# src/memory/mms_core.py
"""Core Memory Management System using Gibson AI Memori.

This module provides a thin wrapper around Memori SDK to manage
HTN planner state, rules, and long-term memory.
"""

from typing import Dict, List, Any, Optional
from memori import Memori
import json
import logging

logger = logging.getLogger(__name__)


class MemoryManagementSystem:
    """Memory Management System for HTN planning.

    Uses Gibson AI Memori's SQL-native storage with 4 memory types:
    - short_term: Current world state (disk positions, agent locations)
    - long_term: Past successful plans for reuse
    - rules: Static knowledge (agent capabilities, domain constraints)
    - entity: Object properties (disks, pegs, nodes, edges)
    """

    def __init__(
        self,
        database_path: str = "sqlite:///mms_thesis.db",
        conscious_ingest: bool = False,  # Disable LLM auto-ingestion
        auto_ingest: bool = False        # We control memory explicitly
    ):
        """Initialize MMS with SQLite backend.

        Args:
            database_path: SQLite connection string (default: local file)
            conscious_ingest: Enable LLM-based memory parsing (not needed for HTN)
            auto_ingest: Enable automatic memory ingestion (we control manually)
        """
        logger.info(f"Initializing MMS with database: {database_path}")

        self.memori = Memori(
            database_connect=database_path,
            conscious_ingest=conscious_ingest,
            auto_ingest=auto_ingest
        )

        # Enable Memori (required for activation)
        self.memori.enable()

        logger.info("MMS initialized successfully")

    # -------------------------------------------------------------------------
    # Short-Term Memory (Current World State)
    # -------------------------------------------------------------------------

    def query_state(self, clues: List[str]) -> Dict[str, Any]:
        """Query short-term memory using clues.

        Args:
            clues: List of query strings (e.g., ["disk_1_position", "peg_A_disks"])

        Returns:
            Dictionary mapping clue -> retrieved value

        Example:
            >>> mms = MemoryManagementSystem()
            >>> mms.update_state({"disk_1_position": "peg_A"})
            >>> result = mms.query_state(["disk_1_position"])
            >>> print(result)
            {'disk_1_position': 'peg_A'}
        """
        results = {}

        for clue in clues:
            try:
                # Memori retrieve returns the stored value
                value = self.memori.retrieve(clue)
                results[clue] = value
                logger.debug(f"Retrieved clue '{clue}': {value}")
            except Exception as e:
                logger.warning(f"Failed to retrieve clue '{clue}': {e}")
                results[clue] = None

        return results

    def update_state(self, changes: Dict[str, Any]) -> bool:
        """Update short-term memory with state changes.

        Args:
            changes: Dictionary of {key: value} updates

        Returns:
            True if all updates succeeded, False otherwise

        Example:
            >>> mms.update_state({
            ...     "disk_1_position": "peg_B",
            ...     "disk_2_position": "peg_C"
            ... })
            True
        """
        try:
            for key, value in changes.items():
                # Memori stores as natural language statements
                statement = f"{key} is {value}"
                self.memori.remember(statement)
                logger.debug(f"Updated state: {statement}")

            return True

        except Exception as e:
            logger.error(f"Failed to update state: {e}")
            return False

    def get_full_state(self) -> Dict[str, Any]:
        """Retrieve all short-term memory (current world state).

        WARNING: This can be slow for large state spaces. Prefer query_state() with specific clues.

        Returns:
            Dictionary of all current state variables
        """
        # Memori doesn't have a "get all" method, so we need to track keys
        # This is a simplified version - in production, maintain a key index
        logger.warning("get_full_state() is expensive. Use query_state() with specific clues.")

        # For thesis, we'll implement this later if needed
        raise NotImplementedError("Full state retrieval not yet implemented. Use query_state().")

    # -------------------------------------------------------------------------
    # Rules Memory (Static Knowledge)
    # -------------------------------------------------------------------------

    def query_rules(self, key: str) -> Optional[str]:
        """Query rules memory for static knowledge.

        Args:
            key: Rule identifier (e.g., "agent_red_capability", "peg_B_max_size")

        Returns:
            Rule value or None if not found

        Example:
            >>> mms.store_rule("agent_red_capability", "traverse_red_edges")
            >>> capability = mms.query_rules("agent_red_capability")
            >>> print(capability)
            'traverse_red_edges'
        """
        try:
            query = f"rule for {key}"
            result = self.memori.retrieve(query)
            logger.debug(f"Retrieved rule '{key}': {result}")
            return result

        except Exception as e:
            logger.warning(f"Failed to retrieve rule '{key}': {e}")
            return None

    def store_rule(self, key: str, value: str) -> bool:
        """Store a rule in rules memory.

        Args:
            key: Rule identifier
            value: Rule value

        Returns:
            True if storage succeeded

        Example:
            >>> mms.store_rule("frame_stewart_formula", "optimal_moves = 2^n - 1")
            True
        """
        try:
            statement = f"rule for {key} is {value}"
            self.memori.remember(statement)
            logger.info(f"Stored rule: {statement}")
            return True

        except Exception as e:
            logger.error(f"Failed to store rule '{key}': {e}")
            return False

    # -------------------------------------------------------------------------
    # Long-Term Memory (Plan Reuse)
    # -------------------------------------------------------------------------

    def store_plan(self, problem_id: str, plan: Dict[str, Any]) -> Optional[str]:
        """Store a successful plan in long-term memory.

        Args:
            problem_id: Unique identifier (e.g., "hanoi_n4_pegs3")
            plan: Plan data structure (will be JSON-serialized)

        Returns:
            problem_id if storage succeeded, None otherwise

        Example:
            >>> plan = {
            ...     "problem": "hanoi_n4",
            ...     "steps": ["move(disk1, A, B)", "move(disk2, A, C)"],
            ...     "cost": 15
            ... }
            >>> mms.store_plan("hanoi_n4_pegs3", plan)
            'hanoi_n4_pegs3'
        """
        try:
            plan_json = json.dumps(plan)
            statement = f"plan for {problem_id}: {plan_json}"
            self.memori.remember(statement)
            logger.info(f"Stored plan for '{problem_id}'")
            return problem_id

        except Exception as e:
            logger.error(f"Failed to store plan '{problem_id}': {e}")
            return None

    def retrieve_plan(self, problem_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored plan from long-term memory.

        Args:
            problem_id: Unique identifier for the plan

        Returns:
            Plan dictionary or None if not found

        Example:
            >>> plan = mms.retrieve_plan("hanoi_n4_pegs3")
            >>> print(plan["cost"])
            15
        """
        try:
            query = f"plan for {problem_id}"
            result = self.memori.retrieve(query)

            if result:
                # Parse JSON from retrieved string
                plan = json.loads(result)
                logger.debug(f"Retrieved plan for '{problem_id}'")
                return plan
            else:
                logger.debug(f"No plan found for '{problem_id}'")
                return None

        except Exception as e:
            logger.warning(f"Failed to retrieve plan '{problem_id}': {e}")
            return None

    # -------------------------------------------------------------------------
    # Entity Memory (Object Properties)
    # -------------------------------------------------------------------------

    def store_entity(self, entity_id: str, properties: Dict[str, Any]) -> bool:
        """Store entity properties in entity memory.

        Args:
            entity_id: Entity identifier (e.g., "disk_3", "node_5")
            properties: Dictionary of properties (e.g., {"size": 40, "color": "red"})

        Returns:
            True if storage succeeded

        Example:
            >>> mms.store_entity("disk_3", {"size": 40, "color": "blue"})
            True
        """
        try:
            props_json = json.dumps(properties)
            statement = f"entity {entity_id} has properties: {props_json}"
            self.memori.remember(statement)
            logger.debug(f"Stored entity '{entity_id}': {properties}")
            return True

        except Exception as e:
            logger.error(f"Failed to store entity '{entity_id}': {e}")
            return False

    def query_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Query entity properties from entity memory.

        Args:
            entity_id: Entity identifier

        Returns:
            Dictionary of properties or None if not found

        Example:
            >>> props = mms.query_entity("disk_3")
            >>> print(props["size"])
            40
        """
        try:
            query = f"entity {entity_id} properties"
            result = self.memori.retrieve(query)

            if result:
                properties = json.loads(result)
                logger.debug(f"Retrieved entity '{entity_id}': {properties}")
                return properties
            else:
                logger.debug(f"No entity found for '{entity_id}'")
                return None

        except Exception as e:
            logger.warning(f"Failed to query entity '{entity_id}': {e}")
            return None

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def clear_all_memory(self) -> bool:
        """Clear all memory (for testing/debugging).

        WARNING: This is irreversible!

        Returns:
            True if successful
        """
        logger.warning("Clearing all memory!")

        try:
            # Memori doesn't have a clear_all method yet
            # For thesis, we can just delete the SQLite file and reinitialize
            # This is a TODO for future improvement
            raise NotImplementedError("Memory clearing not yet implemented")

        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            return False

    def get_memory_stats(self) -> Dict[str, int]:
        """Get statistics about memory usage.

        Returns:
            Dictionary with counts for each memory type

        Example:
            >>> stats = mms.get_memory_stats()
            >>> print(stats)
            {'short_term': 15, 'rules': 8, 'long_term': 3, 'entity': 12}
        """
        # TODO: Implement once Memori SDK supports stats API
        logger.warning("Memory stats not yet implemented")
        return {
            "short_term": 0,
            "rules": 0,
            "long_term": 0,
            "entity": 0
        }


# Module-level convenience functions
def create_mms(database_path: str = "sqlite:///mms_thesis.db") -> MemoryManagementSystem:
    """Factory function to create MMS instance.

    Args:
        database_path: SQLite connection string

    Returns:
        Initialized MemoryManagementSystem

    Example:
        >>> from memory import create_mms
        >>> mms = create_mms()
        >>> mms.update_state({"test": "value"})
    """
    return MemoryManagementSystem(database_path=database_path)
```

### Step 2.2: Test Memori Integration

```python
# tests/test_mms_basic.py
"""Basic MMS integration tests."""

import pytest
from src.memory.mms_core import MemoryManagementSystem


def test_mms_initialization():
    """Test that MMS initializes correctly."""
    mms = MemoryManagementSystem(database_path="sqlite:///test_mms.db")
    assert mms.memori is not None


def test_short_term_memory():
    """Test short-term memory storage and retrieval."""
    mms = MemoryManagementSystem(database_path="sqlite:///test_mms.db")

    # Update state
    success = mms.update_state({
        "disk_1_position": "peg_A",
        "disk_2_position": "peg_B"
    })
    assert success

    # Query state
    result = mms.query_state(["disk_1_position", "disk_2_position"])
    assert result["disk_1_position"] == "peg_A"
    assert result["disk_2_position"] == "peg_B"


def test_rules_memory():
    """Test rules storage and retrieval."""
    mms = MemoryManagementSystem(database_path="sqlite:///test_mms.db")

    # Store rule
    success = mms.store_rule("agent_red_capability", "traverse_red_edges")
    assert success

    # Query rule
    capability = mms.query_rules("agent_red_capability")
    assert capability == "traverse_red_edges"


def test_long_term_memory():
    """Test plan storage and retrieval."""
    mms = MemoryManagementSystem(database_path="sqlite:///test_mms.db")

    # Store plan
    plan = {
        "problem": "hanoi_n3",
        "steps": ["move(1, A, C)", "move(2, A, B)"],
        "cost": 7
    }
    plan_id = mms.store_plan("hanoi_n3_test", plan)
    assert plan_id == "hanoi_n3_test"

    # Retrieve plan
    retrieved = mms.retrieve_plan("hanoi_n3_test")
    assert retrieved["cost"] == 7
    assert len(retrieved["steps"]) == 2


def test_entity_memory():
    """Test entity storage and retrieval."""
    mms = MemoryManagementSystem(database_path="sqlite:///test_mms.db")

    # Store entity
    success = mms.store_entity("disk_3", {"size": 40, "color": "blue"})
    assert success

    # Query entity
    props = mms.query_entity("disk_3")
    assert props["size"] == 40
    assert props["color"] == "blue"
```

**Run Tests**:
```bash
pytest tests/test_mms_basic.py -v
```

---

## 3. MMS Core Implementation

### Step 3.1: Define Memory Types

```python
# src/memory/memory_types.py
"""Type definitions for MMS memory entries."""

from typing import TypedDict, Any, List, Dict
from dataclasses import dataclass
from enum import Enum


class MemoryType(Enum):
    """Four types of memory in MMS."""
    SHORT_TERM = "short_term"  # Current world state
    LONG_TERM = "long_term"    # Past successful plans
    RULES = "rules"            # Static knowledge
    ENTITY = "entity"          # Object properties


@dataclass
class StateUpdate:
    """Represents a state change to short-term memory."""
    key: str
    value: Any
    timestamp: float = None  # Optional for tracking updates

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp
        }


@dataclass
class Rule:
    """Represents a static rule in rules memory."""
    key: str
    value: str
    description: str = ""  # Optional human-readable description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description
        }


class PlanDict(TypedDict):
    """Type definition for stored plans."""
    problem: str
    steps: List[str]
    cost: int
    metadata: Dict[str, Any]  # Optional: solver, timestamp, etc.


@dataclass
class Entity:
    """Represents an object with properties."""
    entity_id: str
    properties: Dict[str, Any]
    entity_type: str  # e.g., "disk", "peg", "node", "edge"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "properties": self.properties,
            "entity_type": self.entity_type
        }
```

### Step 3.2: Create `__init__.py` for Module Exports

```python
# src/memory/__init__.py
"""Memory Management System (MMS) module.

This module provides SQL-native memory for HTN planning using Gibson AI Memori.
"""

from .mms_core import MemoryManagementSystem, create_mms
from .memory_types import (
    MemoryType,
    StateUpdate,
    Rule,
    PlanDict,
    Entity
)

__all__ = [
    "MemoryManagementSystem",
    "create_mms",
    "MemoryType",
    "StateUpdate",
    "Rule",
    "PlanDict",
    "Entity"
]
```

---

## 4. Clue Generator (MemoRAG Pattern)

### Step 4.1: Implement Clue Generator

```python
# src/memory/clue_generator.py
"""MemoRAG-inspired query decomposer for HTN preconditions.

This module implements the "clue generation" pattern from MemoRAG:
instead of complex single queries, decompose into multiple simple clues.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ClueGenerator:
    """Decomposes HTN preconditions into simple memory queries.

    Inspired by MemoRAG's clue generation paradigm:
    - Complex queries are hard to retrieve accurately
    - Decompose into multiple simple clues
    - Synthesize results to evaluate precondition

    Example:
        >>> cg = ClueGenerator()
        >>> clues = cg.generate_clues(
        ...     "can_move_tower",
        ...     {"size": 3, "target_peg": "B", "agent_id": "red"}
        ... )
        >>> print(clues)
        ['current_disks_on_B', 'constraint_B_max_size', 'disk_sizes_in_tower', 'agent_red_capabilities']
    """

    # Precondition patterns mapped to clue templates
    PATTERNS = {
        # Tower of Hanoi Patterns
        "can_move_tower": [
            "current_disks_on_{target_peg}",
            "constraint_{target_peg}_max_size",
            "disk_sizes_in_tower_{size}",
            "agent_{agent_id}_capabilities"
        ],

        "is_peg_clear": [
            "disks_on_{peg_id}"
        ],

        "can_move_disk": [
            "disk_{disk_id}_current_location",
            "disk_{disk_id}_size",
            "disks_on_{target_peg}",
            "constraint_{target_peg}_max_size"
        ],

        # Graph Traversal Patterns
        "agent_can_traverse": [
            "agent_{agent_id}_capabilities",
            "edge_{edge_id}_color",
            "edge_{edge_id}_weight"
        ],

        "is_node_reachable": [
            "agent_{agent_id}_current_location",
            "path_from_{from_node}_to_{to_node}",
            "agent_{agent_id}_capabilities"
        ],

        # Multi-Agent Coordination Patterns
        "agent_available": [
            "agent_{agent_id}_status",
            "agent_{agent_id}_current_task"
        ],

        "resource_available": [
            "resource_{resource_id}_status",
            "resource_{resource_id}_current_owner"
        ]
    }

    def generate_clues(
        self,
        precondition_type: str,
        params: Dict[str, Any]
    ) -> List[str]:
        """Generate clue list for a precondition type.

        Args:
            precondition_type: Type of precondition (e.g., "can_move_tower")
            params: Parameters to fill templates (e.g., {"size": 3, "target_peg": "B"})

        Returns:
            List of clue strings ready for MMS query

        Raises:
            ValueError: If precondition_type is unknown

        Example:
            >>> clues = cg.generate_clues("is_peg_clear", {"peg_id": "A"})
            >>> print(clues)
            ['disks_on_A']
        """
        template = self.PATTERNS.get(precondition_type)

        if not template:
            logger.error(f"Unknown precondition type: {precondition_type}")
            raise ValueError(f"Unknown precondition type: {precondition_type}")

        # Fill templates with parameters
        try:
            clues = [clue.format(**params) for clue in template]
            logger.debug(f"Generated clues for '{precondition_type}': {clues}")
            return clues

        except KeyError as e:
            logger.error(f"Missing parameter for template: {e}")
            raise ValueError(f"Missing parameter: {e}")

    def add_pattern(
        self,
        precondition_type: str,
        clue_templates: List[str]
    ) -> None:
        """Add a new precondition pattern (for domain-specific preconditions).

        Args:
            precondition_type: Name of the precondition
            clue_templates: List of template strings with {param} placeholders

        Example:
            >>> cg.add_pattern("custom_precondition", [
            ...     "param_{x}_value",
            ...     "constraint_{y}_max"
            ... ])
        """
        if precondition_type in self.PATTERNS:
            logger.warning(f"Overwriting existing pattern: {precondition_type}")

        self.PATTERNS[precondition_type] = clue_templates
        logger.info(f"Added pattern '{precondition_type}' with {len(clue_templates)} clues")

    def list_supported_preconditions(self) -> List[str]:
        """List all supported precondition types.

        Returns:
            List of precondition type names

        Example:
            >>> cg.list_supported_preconditions()
            ['can_move_tower', 'is_peg_clear', 'can_move_disk', ...]
        """
        return list(self.PATTERNS.keys())


# Example usage for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    cg = ClueGenerator()

    # Example 1: Tower of Hanoi
    clues = cg.generate_clues(
        "can_move_tower",
        {"size": 3, "target_peg": "B", "agent_id": "red"}
    )
    print(f"Hanoi clues: {clues}")

    # Example 2: Graph Traversal
    clues = cg.generate_clues(
        "agent_can_traverse",
        {"agent_id": "blue", "edge_id": "e1"}
    )
    print(f"Graph clues: {clues}")

    # Example 3: Custom pattern
    cg.add_pattern("custom_check", ["value_{x}", "threshold_{y}"])
    clues = cg.generate_clues("custom_check", {"x": "temp", "y": "max"})
    print(f"Custom clues: {clues}")
```

### Step 4.2: Test Clue Generator

```python
# tests/test_clue_generator.py
"""Tests for clue generator."""

import pytest
from src.memory.clue_generator import ClueGenerator


def test_generate_hanoi_clues():
    """Test Tower of Hanoi clue generation."""
    cg = ClueGenerator()

    clues = cg.generate_clues(
        "can_move_tower",
        {"size": 4, "target_peg": "C", "agent_id": "agent1"}
    )

    assert "current_disks_on_C" in clues
    assert "constraint_C_max_size" in clues
    assert "disk_sizes_in_tower_4" in clues
    assert "agent_agent1_capabilities" in clues


def test_generate_graph_clues():
    """Test graph traversal clue generation."""
    cg = ClueGenerator()

    clues = cg.generate_clues(
        "agent_can_traverse",
        {"agent_id": "red", "edge_id": "edge_5"}
    )

    assert "agent_red_capabilities" in clues
    assert "edge_edge_5_color" in clues


def test_custom_pattern():
    """Test adding custom patterns."""
    cg = ClueGenerator()

    cg.add_pattern("my_precondition", ["value_{x}", "limit_{y}"])
    clues = cg.generate_clues("my_precondition", {"x": "temp", "y": "max"})

    assert "value_temp" in clues
    assert "limit_max" in clues


def test_unknown_precondition():
    """Test that unknown preconditions raise ValueError."""
    cg = ClueGenerator()

    with pytest.raises(ValueError):
        cg.generate_clues("unknown_type", {})


def test_missing_parameter():
    """Test that missing parameters raise ValueError."""
    cg = ClueGenerator()

    with pytest.raises(ValueError):
        # Missing 'peg_id' parameter
        cg.generate_clues("is_peg_clear", {})
```

---

## 5. HTN Planner Integration

### Step 5.1: Modify Precondition Functions

**Before (stateless)**:
```python
# src/core/htn_planner.py (OLD VERSION)
def is_peg_clear(state, peg_id):
    """Check if peg is clear (no disks on it)."""
    return state.get(f"{peg_id}_disks", []) == []
```

**After (MMS-integrated)**:
```python
# src/core/htn_planner.py (NEW VERSION)
from src.memory import MemoryManagementSystem
from src.memory.clue_generator import ClueGenerator

def is_peg_clear(mms: MemoryManagementSystem, peg_id: str) -> bool:
    """Check if peg is clear (no disks on it) via MMS.

    Args:
        mms: Memory Management System instance
        peg_id: Peg identifier (e.g., "A", "B", "C")

    Returns:
        True if peg has no disks, False otherwise
    """
    cg = ClueGenerator()
    clues = cg.generate_clues("is_peg_clear", {"peg_id": peg_id})

    # Query MMS
    result = mms.query_state(clues)
    disks = result.get(f"disks_on_{peg_id}", [])

    return len(disks) == 0
```

### Step 5.2: Update HTN Planner Class

```python
# src/core/htn_planner.py
"""HTN Planner with Memory Management System integration."""

from typing import List, Dict, Any, Optional
from src.memory import MemoryManagementSystem
from src.memory.clue_generator import ClueGenerator
import logging

logger = logging.getLogger(__name__)


class HTNPlanner:
    """Hierarchical Task Network planner with MMS integration."""

    def __init__(self, mms: MemoryManagementSystem):
        """Initialize HTN planner with MMS.

        Args:
            mms: Memory Management System instance
        """
        self.mms = mms
        self.clue_generator = ClueGenerator()
        logger.info("HTN Planner initialized with MMS")

    def check_precondition(
        self,
        precondition_type: str,
        params: Dict[str, Any]
    ) -> bool:
        """Check if a precondition is satisfied via MMS.

        Args:
            precondition_type: Type of precondition (e.g., "can_move_tower")
            params: Parameters for clue generation

        Returns:
            True if precondition is satisfied, False otherwise
        """
        # Generate clues
        clues = self.clue_generator.generate_clues(precondition_type, params)

        # Query MMS
        results = self.mms.query_state(clues)

        # Evaluate precondition based on results
        # (Domain-specific logic goes here)

        # Example for "can_move_tower":
        if precondition_type == "can_move_tower":
            current_disks = results.get(f"current_disks_on_{params['target_peg']}", [])
            max_size = results.get(f"constraint_{params['target_peg']}_max_size", float('inf'))
            tower_size = results.get(f"disk_sizes_in_tower_{params['size']}", 0)

            total_size = sum(current_disks) + tower_size
            return total_size <= max_size

        # Default: assume satisfied if all clues returned values
        return all(v is not None for v in results.values())

    def apply_action(
        self,
        action: str,
        params: Dict[str, Any]
    ) -> bool:
        """Apply an action and update MMS state.

        Args:
            action: Action name (e.g., "move_disk")
            params: Action parameters

        Returns:
            True if action succeeded
        """
        logger.info(f"Applying action: {action} with params {params}")

        # Compute state changes (domain-specific)
        state_changes = self._compute_state_changes(action, params)

        # Update MMS
        success = self.mms.update_state(state_changes)

        if success:
            logger.info(f"Action {action} applied successfully")
        else:
            logger.error(f"Failed to apply action {action}")

        return success

    def _compute_state_changes(
        self,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute state changes for an action (domain-specific).

        Args:
            action: Action name
            params: Action parameters

        Returns:
            Dictionary of state changes
        """
        # Example for "move_disk" action:
        if action == "move_disk":
            disk_id = params["disk_id"]
            from_peg = params["from_peg"]
            to_peg = params["to_peg"]

            return {
                f"disk_{disk_id}_position": to_peg,
                f"peg_{from_peg}_top_disk": None,  # Update after disk removal
                f"peg_{to_peg}_top_disk": disk_id  # Update after disk placement
            }

        # Add more action types as needed
        return {}
```

---

## 6. Multi-Agent Coordination

### Step 6.1: Create Orchestrator Agent

```python
# src/agents/orchestrator.py
"""Orchestrator agent for multi-agent HTN planning."""

from typing import List, Dict, Any
from src.memory import MemoryManagementSystem
from src.core.htn_planner import HTNPlanner
from src.agents.worker_agent import WorkerAgent
import logging

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Coordinates multiple worker agents via shared MMS.

    Responsibilities:
    - Decompose HTN tasks into primitive actions
    - Delegate actions to worker agents
    - Update MMS after each action
    - Handle backtracking on failures
    """

    def __init__(
        self,
        mms: MemoryManagementSystem,
        worker_agents: List[WorkerAgent]
    ):
        """Initialize orchestrator.

        Args:
            mms: Shared Memory Management System
            worker_agents: List of worker agents
        """
        self.mms = mms
        self.htn_planner = HTNPlanner(mms)
        self.worker_agents = {agent.agent_id: agent for agent in worker_agents}
        logger.info(f"Orchestrator initialized with {len(worker_agents)} workers")

    def execute_plan(self, goal: Dict[str, Any]) -> bool:
        """Execute an HTN plan to achieve a goal.

        Args:
            goal: Goal specification (e.g., {"type": "hanoi", "n": 4})

        Returns:
            True if goal achieved, False otherwise
        """
        logger.info(f"Executing plan for goal: {goal}")

        # Generate HTN plan
        plan = self.htn_planner.plan(goal)

        # Execute each action in the plan
        for action in plan:
            success = self._execute_action(action)

            if not success:
                logger.warning(f"Action {action} failed. Backtracking...")
                # TODO: Implement backtracking logic
                return False

        logger.info("Plan executed successfully!")
        return True

    def _execute_action(self, action: Dict[str, Any]) -> bool:
        """Execute a single action via worker delegation.

        Args:
            action: Action specification

        Returns:
            True if action succeeded
        """
        # Check preconditions via MMS
        precondition_satisfied = self.htn_planner.check_precondition(
            action["precondition_type"],
            action["params"]
        )

        if not precondition_satisfied:
            logger.warning(f"Precondition not satisfied for {action}")
            return False

        # Delegate to appropriate worker agent
        agent_id = action.get("assigned_agent")
        worker = self.worker_agents.get(agent_id)

        if not worker:
            logger.error(f"No worker found for agent_id: {agent_id}")
            return False

        # Execute action via worker
        result = worker.execute(action)

        # Update MMS with result
        if result["success"]:
            self.mms.update_state(result["state_changes"])
            logger.info(f"Action {action['name']} completed by {agent_id}")
            return True
        else:
            logger.error(f"Action {action['name']} failed: {result['error']}")
            return False
```

### Step 6.2: Create Worker Agent Template

```python
# src/agents/worker_agent.py
"""Worker agent template for HTN execution."""

from typing import Dict, Any
from src.memory import MemoryManagementSystem
import logging

logger = logging.getLogger(__name__)


class WorkerAgent:
    """Worker agent that executes primitive actions.

    Worker agents:
    - Read current state from MMS (read-only)
    - Execute assigned actions
    - Report results to orchestrator
    - Do NOT directly update MMS (orchestrator does this)
    """

    def __init__(
        self,
        agent_id: str,
        capabilities: List[str],
        mms: MemoryManagementSystem
    ):
        """Initialize worker agent.

        Args:
            agent_id: Unique agent identifier
            capabilities: List of actions this agent can perform
            mms: Memory Management System (read-only access)
        """
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.mms = mms
        logger.info(f"Worker {agent_id} initialized with capabilities: {capabilities}")

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action.

        Args:
            action: Action specification

        Returns:
            Result dictionary with:
                - success: bool
                - state_changes: dict (if success=True)
                - error: str (if success=False)
        """
        action_name = action["name"]

        # Check if agent can perform this action
        if action_name not in self.capabilities:
            return {
                "success": False,
                "error": f"Agent {self.agent_id} cannot perform {action_name}"
            }

        # Read current state from MMS
        current_state = self._read_relevant_state(action)

        # Execute action (domain-specific logic)
        try:
            state_changes = self._perform_action(action, current_state)

            return {
                "success": True,
                "state_changes": state_changes
            }

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _read_relevant_state(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Read state relevant to this action from MMS.

        Args:
            action: Action specification

        Returns:
            Dictionary of relevant state variables
        """
        # Generate clues for required state
        clues = action.get("required_state_clues", [])

        # Query MMS
        state = self.mms.query_state(clues)

        return state

    def _perform_action(
        self,
        action: Dict[str, Any],
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform the actual action (domain-specific).

        Args:
            action: Action specification
            current_state: Current state from MMS

        Returns:
            Dictionary of state changes
        """
        # TODO: Implement domain-specific action logic
        # This is a placeholder
        logger.info(f"Agent {self.agent_id} performing {action['name']}")

        return {
            "action_completed": True,
            "timestamp": "2025-01-15T10:00:00"
        }
```

---

## 7. Testing & Validation

### Step 7.1: Create End-to-End Test

```python
# tests/test_mms_integration.py
"""End-to-end integration test for MMS with HTN planner."""

import pytest
from src.memory import MemoryManagementSystem
from src.core.htn_planner import HTNPlanner
from src.agents.orchestrator import OrchestratorAgent
from src.agents.worker_agent import WorkerAgent


def test_tower_of_hanoi_with_mms():
    """Test Tower of Hanoi problem with MMS integration."""

    # Initialize MMS
    mms = MemoryManagementSystem(database_path="sqlite:///test_hanoi.db")

    # Initialize world state
    mms.update_state({
        "disk_1_position": "peg_A",
        "disk_2_position": "peg_A",
        "disk_3_position": "peg_A",
        "peg_A_disks": [1, 2, 3],
        "peg_B_disks": [],
        "peg_C_disks": []
    })

    # Store rules
    mms.store_rule("peg_A_max_size", "1000")
    mms.store_rule("peg_B_max_size", "1000")
    mms.store_rule("peg_C_max_size", "1000")

    # Create worker agents
    worker_1 = WorkerAgent("agent_1", ["move_disk"], mms)

    # Create orchestrator
    orchestrator = OrchestratorAgent(mms, [worker_1])

    # Execute plan
    goal = {"type": "hanoi", "n": 3, "target_peg": "C"}
    success = orchestrator.execute_plan(goal)

    assert success

    # Verify final state
    final_state = mms.query_state(["peg_C_disks"])
    assert final_state["peg_C_disks"] == [1, 2, 3]
```

### Step 7.2: Run All Tests

```bash
# Run all MMS tests
pytest tests/test_mms_*.py -v

# Run integration tests
pytest tests/test_*_integration.py -v

# Check coverage
pytest --cov=src/memory --cov-report=html
```

---

## 8. Benchmarking

### Step 8.1: Create Benchmark Script

```python
# benchmarks/benchmark_mms_performance.py
"""Benchmark MMS query latency and state update performance."""

import time
from src.memory import MemoryManagementSystem


def benchmark_query_latency():
    """Measure query latency."""
    mms = MemoryManagementSystem(database_path="sqlite:///benchmark.db")

    # Populate with 1000 state variables
    for i in range(1000):
        mms.update_state({f"var_{i}": f"value_{i}"})

    # Measure query time
    start = time.time()

    for i in range(100):
        mms.query_state([f"var_{i}"])

    end = time.time()

    avg_latency = (end - start) / 100 * 1000  # ms per query
    print(f"Average query latency: {avg_latency:.2f} ms")

    assert avg_latency < 100, "Query latency exceeds 100ms threshold!"


def benchmark_state_updates():
    """Measure state update throughput."""
    mms = MemoryManagementSystem(database_path="sqlite:///benchmark.db")

    start = time.time()

    for i in range(1000):
        mms.update_state({f"var_{i}": f"updated_value_{i}"})

    end = time.time()

    throughput = 1000 / (end - start)  # updates/second
    print(f"Update throughput: {throughput:.2f} updates/sec")


if __name__ == "__main__":
    benchmark_query_latency()
    benchmark_state_updates()
```

**Run Benchmark**:
```bash
python benchmarks/benchmark_mms_performance.py
```

---

## 9. Troubleshooting

### Common Issue 1: "ModuleNotFoundError: No module named 'memori'"

**Solution**:
```bash
pip install memorisdk --upgrade
```

### Common Issue 2: SQLite Database Locked

**Cause**: Multiple processes accessing the same SQLite file.

**Solution**:
- Use separate database files for tests: `sqlite:///test_{test_name}.db`
- Close MMS instances after tests: `del mms`

### Common Issue 3: Memori Retrieve Returns None

**Cause**: Query string doesn't match stored statement format.

**Solution**:
- Check stored format: `"disk_1_position is peg_A"`
- Query should match: `"disk_1_position"`
- Use exact key names in clues

### Common Issue 4: Plan Reuse Not Working

**Cause**: JSON parsing fails on retrieval.

**Solution**:
```python
# Ensure JSON is properly escaped when storing
import json
plan_json = json.dumps(plan)  # Use json.dumps, not str(plan)
mms.memori.remember(f"plan for {problem_id}: {plan_json}")
```

---

## 🎉 Integration Complete!

You now have a fully integrated Memory Management System using:
- ✅ Gibson AI Memori (SQL-native backend)
- ✅ SQLite (zero-config database)
- ✅ MemoRAG pattern (clue generation)
- ✅ HTN Planner integration
- ✅ Multi-agent coordination

**Next Steps**:
1. Run all tests: `pytest tests/ -v`
2. Benchmark performance: `python benchmarks/benchmark_mms_performance.py`
3. Update OpenSpec proposal (see next section)
4. Start implementing domain-specific action logic

**Thesis Timeline**:
- Weeks 1-2: Foundation + Testing (DONE after this guide)
- Weeks 3-4: HTN Integration
- Weeks 5-6: Multi-Agent Coordination
- Weeks 7-8: Benchmarking + Documentation

Good luck! 🚀
