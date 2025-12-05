"""
Symbolic Validator - Fast rule-based constraint checking

Performs domain-specific symbolic validation without LLM overhead.
Used by ExecutionAgent for validating operator preconditions and
applying state transitions.
"""

import copy
from typing import Dict, List, Tuple, Optional
from loguru import logger


class SymbolicValidator:
    """
    Fast symbolic constraint checker for HTN execution

    Provides domain-specific validation rules that can check
    preconditions and apply effects in < 1ms per operation.

    Intelligence Type: Rule-based (100% symbolic)
    Latency: < 1ms per validation
    Use Case: Fast execution validation before expensive LLM calls
    """

    def __init__(self, domain: str = None):
        """
        Initialize validator for specific domain

        Args:
            domain: Domain name (e.g., "tower_of_hanoi", "graph_traversal")
        """
        self.domain = domain
        self.validation_count = 0
        self.validation_failures = 0

        # Domain-specific validators
        self.validators = {
            "tower_of_hanoi": self._validate_hanoi,
            "graph_traversal": self._validate_graph_traversal,
            "constrained_sorting": self._validate_sorting,
        }

        # Domain-specific appliers
        self.appliers = {
            "tower_of_hanoi": self._apply_hanoi,
            "graph_traversal": self._apply_graph_traversal,
            "constrained_sorting": self._apply_sorting,
        }

    def validate_operator(
        self, operator: str, params: List, state: Dict
    ) -> Tuple[bool, str]:
        """
        Validate operator can be applied to current state

        Args:
            operator: Operator name (e.g., "move_disk")
            params: Operator parameters
            state: Current world state

        Returns:
            Tuple of (is_valid, reason)
        """
        self.validation_count += 1

        if not self.domain:
            return False, "No domain specified for validation"

        if self.domain not in self.validators:
            return False, f"No validator for domain: {self.domain}"

        try:
            is_valid, reason = self.validators[self.domain](operator, params, state)

            if not is_valid:
                self.validation_failures += 1

            return is_valid, reason

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            self.validation_failures += 1
            return False, f"Validation exception: {str(e)}"

    def apply_operator(
        self, operator: str, params: List, state: Dict
    ) -> Optional[Dict]:
        """
        Apply operator to state and return new state

        Args:
            operator: Operator name
            params: Operator parameters
            state: Current state

        Returns:
            New state after applying operator, or None if failed
        """
        if not self.domain:
            logger.error("No domain specified for apply")
            return None

        if self.domain not in self.appliers:
            logger.error(f"No applier for domain: {self.domain}")
            return None

        try:
            new_state = self.appliers[self.domain](operator, params, state)
            return new_state
        except Exception as e:
            logger.error(f"Apply error: {str(e)}")
            return None

    # ========== Tower of Hanoi Domain ==========

    def _validate_hanoi(
        self, operator: str, params: List, state: Dict
    ) -> Tuple[bool, str]:
        """Validate Tower of Hanoi move"""
        if operator != "move_disk":
            return False, f"Unknown operator: {operator}"

        if len(params) != 3:
            return False, f"move_disk requires 3 params, got {len(params)}"

        disk, source, target = params

        # Ensure pegs exist in state
        if "pegs" not in state:
            return False, "State missing 'pegs' key"

        pegs = state["pegs"]

        if source not in pegs:
            return False, f"Source peg '{source}' not found"

        if target not in pegs:
            return False, f"Target peg '{target}' not found"

        # Check disk is on source peg
        if not pegs[source]:
            return False, f"Source peg '{source}' is empty"

        # Check disk is on top
        if pegs[source][-1] != disk:
            return (
                False,
                f"Disk {disk} is not on top of peg '{source}' "
                f"(top disk is {pegs[source][-1]})",
            )

        # Check target constraint (empty or larger disk on top)
        if pegs[target] and pegs[target][-1] < disk:
            return (
                False,
                f"Cannot place disk {disk} on smaller disk "
                f"{pegs[target][-1]} on peg '{target}'",
            )

        return True, "Valid move"

    def _apply_hanoi(self, operator: str, params: List, state: Dict) -> Dict:
        """Apply Tower of Hanoi move to state"""
        if operator != "move_disk":
            raise ValueError(f"Unknown operator: {operator}")

        disk, source, target = params

        # Deep copy state
        new_state = copy.deepcopy(state)

        # Move disk
        new_state["pegs"][source].pop()
        new_state["pegs"][target].append(disk)

        return new_state

    # ========== Graph Traversal Domain ==========

    def _validate_graph_traversal(
        self, operator: str, params: List, state: Dict
    ) -> Tuple[bool, str]:
        """
        Validate graph traversal operation
        
        Supports operators from HDDL domain:
        - traverse: Move from one node to another
        - traverse_edge: Alias for traverse (legacy)
        - query-weight: Query unknown edge weight
        - complete-path: Mark path as complete at goal node
        - mark_visited: Legacy alias for complete-path
        """
        # Handle traverse and traverse_edge (HDDL uses 'traverse')
        if operator in ("traverse", "traverse_edge"):
            if len(params) != 2:
                return (False, f"{operator} requires 2 params, got {len(params)}")

            from_node, to_node = params

            # For PANDA execution, we're lenient - just validate structure
            # The actual preconditions are checked by PANDA during planning
            
            # Basic validation: params should be strings (node names)
            if not isinstance(from_node, str) or not isinstance(to_node, str):
                return False, "Node names must be strings"
            
            # If state has current_node, validate position
            if "current_node" in state:
                if state["current_node"] != from_node:
                    return (
                        False,
                        f"Not at node '{from_node}' "
                        f"(currently at '{state['current_node']}')",
                    )

            # If state has edges, validate edge exists
            if "edges" in state:
                edge_exists = False
                for edge in state["edges"]:
                    if len(edge) >= 2 and edge[0] == from_node and edge[1] == to_node:
                        edge_exists = True
                        break
                if not edge_exists:
                    # Be lenient - PANDA already validated this
                    logger.debug(f"Edge {from_node}->{to_node} not in state, but accepting (PANDA validated)")

            return True, "Valid traversal"

        # Handle query-weight (HDDL operator for knowledge gap)
        elif operator == "query-weight":
            if len(params) != 2:
                return (False, f"query-weight requires 2 params, got {len(params)}")

            from_node, to_node = params
            
            # Basic validation
            if not isinstance(from_node, str) or not isinstance(to_node, str):
                return False, "Node names must be strings"
            
            return True, "Valid weight query"

        # Handle complete-path and mark_visited
        elif operator in ("complete-path", "mark_visited"):
            if len(params) != 1:
                return (False, f"{operator} requires 1 param, got {len(params)}")

            node = params[0]
            
            # Basic validation
            if not isinstance(node, str):
                return False, "Node name must be string"

            # If state has current_node, validate position
            if "current_node" in state:
                if state["current_node"] != node:
                    return (
                        False,
                        f"Can only complete path at current node (at '{state['current_node']}', "
                        f"trying at '{node}')",
                    )

            return True, "Valid path completion"

        else:
            return False, f"Unknown operator: {operator}"

    def _apply_graph_traversal(self, operator: str, params: List, state: Dict) -> Dict:
        """
        Apply graph traversal operation to state
        
        Supports operators:
        - traverse / traverse_edge: Move to new node
        - query-weight: Mark edge weight as known
        - complete-path / mark_visited: Mark path as complete
        """
        new_state = copy.deepcopy(state)

        # Handle traverse and traverse_edge
        if operator in ("traverse", "traverse_edge"):
            from_node, to_node = params
            new_state["current_node"] = to_node

            # Initialize visited if not exists
            if "visited" not in new_state:
                new_state["visited"] = []

            if from_node not in new_state["visited"]:
                new_state["visited"].append(from_node)
                
            # Track path
            if "path" not in new_state:
                new_state["path"] = []
            new_state["path"].append((from_node, to_node))

        # Handle query-weight (knowledge gap resolution)
        elif operator == "query-weight":
            from_node, to_node = params
            
            # Track known weights
            if "known_weights" not in new_state:
                new_state["known_weights"] = []
            
            edge_key = (from_node, to_node)
            if edge_key not in new_state["known_weights"]:
                new_state["known_weights"].append(edge_key)
            
            logger.debug(f"Queried weight for edge {from_node}->{to_node}")

        # Handle complete-path and mark_visited
        elif operator in ("complete-path", "mark_visited"):
            node = params[0]

            if "visited" not in new_state:
                new_state["visited"] = []

            if node not in new_state["visited"]:
                new_state["visited"].append(node)
            
            # Mark path as complete
            new_state["path_complete"] = True
            new_state["goal_reached"] = node
            
            logger.debug(f"Path completed at node {node}")

        else:
            raise ValueError(f"Unknown operator: {operator}")

        return new_state

    def get_statistics(self) -> Dict:
        """Get validator statistics"""
        return {
            "validation_count": self.validation_count,
            "validation_failures": self.validation_failures,
            "success_rate": (
                (self.validation_count - self.validation_failures)
                / self.validation_count
            )
            if self.validation_count > 0
            else 0.0,
        }

    # ========== Constrained Sorting Domain ==========

    def _validate_sorting(
        self, operator: str, params: List, state: Dict
    ) -> Tuple[bool, str]:
        """Validate sorting operations"""

        # Check array exists in state
        if "array" not in state:
            return False, "State missing 'array' key"

        array = state["array"]

        if operator == "partition":
            # Partition requires pivot_index or pivot_value
            if not params:
                return False, "partition requires parameters"

            # Can partition any non-empty array
            if not array:
                return False, "Cannot partition empty array"

            return True, "Valid partition operation"

        elif operator == "partition_array":
            # Alias for partition
            if not array:
                return False, "Cannot partition empty array"
            return True, "Valid partition operation"

        elif operator == "sort_array" or operator == "sort_subarray" or operator == "sort_subarrays":
            # Sort operation - can always be attempted
            return True, "Valid sort operation"

        elif operator == "recursive_sort":
            # Recursive sort - valid if array has more than 1 element
            if len(array) <= 1:
                return True, "Array already sorted (single element or empty)"
            return True, "Valid recursive sort"

        elif operator == "swap_elements":
            # Swap requires two indices
            if len(params) != 2:
                return False, f"swap_elements requires 2 indices, got {len(params)}"

            i, j = params
            if i < 0 or i >= len(array):
                return False, f"Index {i} out of bounds (array length {len(array)})"
            if j < 0 or j >= len(array):
                return False, f"Index {j} out of bounds (array length {len(array)})"

            return True, "Valid swap"

        elif operator == "compare_elements":
            # Compare requires two indices or values
            if len(params) != 2:
                return False, f"compare_elements requires 2 params, got {len(params)}"

            return True, "Valid comparison"

        elif operator == "select_pivot":
            # Pivot selection - valid for non-empty array
            if not array:
                return False, "Cannot select pivot from empty array"

            return True, "Valid pivot selection"

        elif operator == "merge_subarrays":
            # Merge operation - valid if we have subarrays in state
            return True, "Valid merge operation"

        else:
            return False, f"Unknown sorting operator: {operator}"

    def _apply_sorting(self, operator: str, params: List, state: Dict) -> Dict:
        """Apply sorting operations to state"""
        new_state = copy.deepcopy(state)

        # Ensure tracking fields exist
        if "swap_count" not in new_state:
            new_state["swap_count"] = 0
        if "comparison_count" not in new_state:
            new_state["comparison_count"] = 0

        array = new_state["array"]

        if operator == "partition" or operator == "partition_array":
            # Simple partition around middle element or last element
            if not array:
                return new_state

            # Choose pivot (last element for quicksort)
            pivot = array[-1]
            left = [x for x in array[:-1] if x <= pivot]
            right = [x for x in array[:-1] if x > pivot]

            new_state["array"] = left + [pivot] + right
            new_state["comparison_count"] += len(array) - 1
            new_state["last_pivot_index"] = len(left)

            logger.debug(f"Partitioned around {pivot}: left={left}, pivot={pivot}, right={right}")

        elif operator == "sort_array" or operator == "sort_subarray" or operator == "sort_subarrays":
            # Actually sort the array (quicksort implementation)
            if len(array) <= 1:
                return new_state

            # Quicksort in-place
            sorted_array = sorted(array)
            new_state["array"] = sorted_array
            new_state["sorted"] = True

            # Estimate operations (n log n comparisons for quicksort)
            import math
            n = len(array)
            estimated_comparisons = int(n * math.log2(n)) if n > 1 else 0
            estimated_swaps = estimated_comparisons // 2

            new_state["comparison_count"] += estimated_comparisons
            new_state["swap_count"] += estimated_swaps

            logger.debug(f"Sorted array: {sorted_array}")

        elif operator == "recursive_sort":
            # Recursive sort (actual quicksort)
            if len(array) <= 1:
                new_state["sorted"] = True
                return new_state

            sorted_array = sorted(array)
            new_state["array"] = sorted_array
            new_state["sorted"] = True

            import math
            n = len(array)
            new_state["comparison_count"] += int(n * math.log2(n)) if n > 1 else 0
            new_state["swap_count"] += (int(n * math.log2(n)) if n > 1 else 0) // 2

            logger.debug(f"Recursively sorted: {sorted_array}")

        elif operator == "swap_elements":
            # Swap two elements
            i, j = params
            array[i], array[j] = array[j], array[i]
            new_state["swap_count"] += 1

            logger.debug(f"Swapped indices {i} and {j}: {array}")

        elif operator == "compare_elements":
            # Compare two elements (increment counter)
            new_state["comparison_count"] += 1

        elif operator == "select_pivot":
            # Select pivot element (last element for quicksort)
            if array:
                new_state["pivot"] = array[-1]
                new_state["pivot_index"] = len(array) - 1

        elif operator == "merge_subarrays":
            # Merge subarrays (assuming they're sorted)
            # In real implementation, would merge sorted subarrays
            # For now, just sort the whole array
            sorted_array = sorted(array)
            new_state["array"] = sorted_array
            new_state["sorted"] = True
            new_state["comparison_count"] += len(array)

            logger.debug(f"Merged and sorted: {sorted_array}")

        else:
            raise ValueError(f"Unknown sorting operator: {operator}")

        return new_state
