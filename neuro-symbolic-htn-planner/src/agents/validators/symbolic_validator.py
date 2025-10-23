"""
Symbolic Validator - Fast rule-based constraint checking

Performs domain-specific symbolic validation without LLM overhead.
Used by ExecutionAgent for validating operator preconditions and
applying state transitions.
"""

import copy
from typing import Dict, List, Tuple, Any, Optional
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
        }
        
        # Domain-specific appliers
        self.appliers = {
            "tower_of_hanoi": self._apply_hanoi,
            "graph_traversal": self._apply_graph_traversal,
        }
    
    def validate_operator(self, operator: str, params: List, 
                          state: Dict) -> Tuple[bool, str]:
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
            is_valid, reason = self.validators[self.domain](
                operator, params, state
            )
            
            if not is_valid:
                self.validation_failures += 1
            
            return is_valid, reason
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            self.validation_failures += 1
            return False, f"Validation exception: {str(e)}"
    
    def apply_operator(self, operator: str, params: List, 
                       state: Dict) -> Optional[Dict]:
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
    
    def _validate_hanoi(self, operator: str, params: List, 
                        state: Dict) -> Tuple[bool, str]:
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
                f"(top disk is {pegs[source][-1]})"
            )
        
        # Check target constraint (empty or larger disk on top)
        if pegs[target] and pegs[target][-1] < disk:
            return (
                False,
                f"Cannot place disk {disk} on smaller disk "
                f"{pegs[target][-1]} on peg '{target}'"
            )
        
        return True, "Valid move"
    
    def _apply_hanoi(self, operator: str, params: List, 
                     state: Dict) -> Dict:
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
    
    def _validate_graph_traversal(self, operator: str, params: List,
                                   state: Dict) -> Tuple[bool, str]:
        """Validate graph traversal operation"""
        if operator == "traverse_edge":
            if len(params) != 2:
                return (
                    False,
                    f"traverse_edge requires 2 params, got {len(params)}"
                )
            
            from_node, to_node = params
            
            # Check current position
            if "current_node" not in state:
                return False, "State missing 'current_node'"
            
            if state["current_node"] != from_node:
                return (
                    False,
                    f"Not at node '{from_node}' "
                    f"(currently at '{state['current_node']}')"
                )
            
            # Check edge exists
            if "edges" not in state:
                return False, "State missing 'edges'"
            
            edge_exists = False
            for edge in state["edges"]:
                if len(edge) >= 2 and edge[0] == from_node and edge[1] == to_node:
                    edge_exists = True
                    break
            
            if not edge_exists:
                return False, f"No edge from '{from_node}' to '{to_node}'"
            
            # Check not already visited (if tracking)
            if "visited" in state and to_node in state["visited"]:
                return False, f"Node '{to_node}' already visited"
            
            return True, "Valid traversal"
        
        elif operator == "mark_visited":
            if len(params) != 1:
                return (
                    False,
                    f"mark_visited requires 1 param, got {len(params)}"
                )
            
            node = params[0]
            
            if "current_node" not in state:
                return False, "State missing 'current_node'"
            
            if state["current_node"] != node:
                return (
                    False,
                    f"Can only mark current node (at '{state['current_node']}', "
                    f"trying to mark '{node}')"
                )
            
            return True, "Valid mark"
        
        else:
            return False, f"Unknown operator: {operator}"
    
    def _apply_graph_traversal(self, operator: str, params: List,
                                state: Dict) -> Dict:
        """Apply graph traversal operation to state"""
        new_state = copy.deepcopy(state)
        
        if operator == "traverse_edge":
            from_node, to_node = params
            new_state["current_node"] = to_node
            
            # Initialize visited if not exists
            if "visited" not in new_state:
                new_state["visited"] = []
            
            if from_node not in new_state["visited"]:
                new_state["visited"].append(from_node)
        
        elif operator == "mark_visited":
            node = params[0]
            
            if "visited" not in new_state:
                new_state["visited"] = []
            
            if node not in new_state["visited"]:
                new_state["visited"].append(node)
        
        else:
            raise ValueError(f"Unknown operator: {operator}")
        
        return new_state
    
    def get_statistics(self) -> Dict:
        """Get validator statistics"""
        return {
            "validation_count": self.validation_count,
            "validation_failures": self.validation_failures,
            "success_rate": (
                (self.validation_count - self.validation_failures) /
                self.validation_count
            ) if self.validation_count > 0 else 0.0
        }
