"""
ExecutionAgent - HTN Plan Execution with Hybrid Validation

Executes plan steps using fast symbolic validation (rule-based)
with LLM fallback for edge cases.
"""

import asyncio
import copy
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent
from .validators.symbolic_validator import SymbolicValidator


class ExecutionAgent(BaseAgent):
    """
    Agent specialized in executing HTN plans
    
    Uses hybrid approach:
    - Fast symbolic validation for well-defined constraints (70%)
    - LLM fallback for ambiguous/complex cases (30%)
    
    Intelligence Type: Hybrid (30% LLM, 70% rules)
    Primary: Rule-based SymbolicValidator (< 1ms)
    Fallback LLM: Qwen 2.5 7B (HF) - 1.9s
    """
    
    def __init__(self, name: str = "ExecutionAgent",
                 llm_client=None, config: dict = None):
        """
        Initialize ExecutionAgent
        
        Args:
            name: Agent name
            llm_client: Fallback LLM client (Qwen 7B)
            config: Configuration dict
        """
        super().__init__(name, llm_client, config or {})
        
        # Symbolic validator (primary validation)
        self.validator = SymbolicValidator()
        
        # Agent-specific config
        self.use_llm_fallback = config.get("use_llm_fallback", True) if config else True
        self.max_retries = config.get("max_retries", 3) if config else 3
        
        # Statistics
        self.stats = {
            "plans_executed": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_steps_executed": 0,
            "validation_failures": 0,
            "llm_fallback_used": 0,
            "avg_execution_time_ms": 0.0
        }
    
    async def process(self, input_data: Dict) -> Dict:
        """
        Execute HTN plan
        
        Args:
            input_data: {
                "plan": ["move_disk(1, A, C)", ...],
                "initial_state": {...},
                "operators": {...},
                "domain": "tower_of_hanoi"
            }
        
        Returns:
            {
                "success": bool,
                "execution_trace": [...],
                "final_state": {...},
                "errors": [...],
                "execution_time_ms": float
            }
        """
        start_time = datetime.now()
        
        # Validate input
        if not self.validate_input(input_data):
            return {
                "success": False,
                "error": "Invalid input data",
                "agent": self.name
            }
        
        plan = input_data["plan"]
        initial_state = input_data["initial_state"]
        domain = input_data.get("domain", "unknown")
        operators_def = input_data.get("operators", {})
        
        logger.info(
            f"Executing plan with {len(plan)} steps in domain: {domain}"
        )
        
        # Set validator domain
        self.validator.domain = domain
        
        # Execute plan step by step
        execution_trace = []
        current_state = copy.deepcopy(initial_state)
        errors = []
        
        for step_num, step in enumerate(plan, 1):
            # Parse step
            operator, params = self._parse_step(step)
            
            if operator is None:
                error_msg = f"Failed to parse step: {step}"
                logger.error(error_msg)
                errors.append({
                    "step": step_num,
                    "error": error_msg,
                    "step_str": step
                })
                break
            
            # Validate step
            is_valid, reason = self.validator.validate_operator(
                operator, params, current_state
            )
            
            # Try LLM fallback if validation failed and fallback enabled
            if not is_valid and self.use_llm_fallback and self.llm_client:
                logger.warning(
                    f"Symbolic validation failed ({reason}), "
                    f"trying LLM fallback"
                )
                is_valid, reason = await self._llm_validate(
                    operator, params, current_state, domain
                )
                if is_valid:
                    self.stats["llm_fallback_used"] += 1
            
            if not is_valid:
                error_msg = f"Step {step_num} validation failed: {reason}"
                logger.error(error_msg)
                errors.append({
                    "step": step_num,
                    "operator": operator,
                    "params": params,
                    "error": reason,
                    "state_at_failure": copy.deepcopy(current_state)
                })
                self.stats["validation_failures"] += 1
                break
            
            # Apply operator
            state_before = copy.deepcopy(current_state)
            new_state = self.validator.apply_operator(
                operator, params, current_state
            )
            
            if new_state is None:
                error_msg = f"Failed to apply operator: {operator}"
                logger.error(error_msg)
                errors.append({
                    "step": step_num,
                    "operator": operator,
                    "params": params,
                    "error": error_msg
                })
                break
            
            # Record trace
            execution_trace.append({
                "step": step_num,
                "operator": operator,
                "params": params,
                "state_before": state_before,
                "state_after": new_state,
                "validation_result": reason,
                "status": "success"
            })
            
            current_state = new_state
            self.stats["total_steps_executed"] += 1
        
        # Determine overall success
        success = len(errors) == 0 and len(execution_trace) == len(plan)
        
        # Update statistics
        self.stats["plans_executed"] += 1
        if success:
            self.stats["successful_executions"] += 1
        else:
            self.stats["failed_executions"] += 1
        
        # Calculate execution time
        execution_time_ms = (
            datetime.now() - start_time
        ).total_seconds() * 1000
        
        # Update running average
        n = self.stats["plans_executed"]
        self.stats["avg_execution_time_ms"] = (
            (self.stats["avg_execution_time_ms"] * (n - 1) + execution_time_ms) / n
        )
        
        result = {
            "success": success,
            "execution_trace": execution_trace,
            "final_state": current_state,
            "errors": errors,
            "execution_time_ms": execution_time_ms,
            "steps_completed": len(execution_trace),
            "steps_total": len(plan),
            "agent": self.name
        }
        
        # Log interaction
        self.log_interaction({
            "input": input_data,
            "output": result,
            "timestamp": datetime.now().isoformat()
        })
        
        return result
    
    def _parse_step(self, step: str) -> tuple:
        """
        Parse step string into operator and parameters
        
        Args:
            step: "move_disk(1, A, C)"
        
        Returns:
            Tuple of (operator_name, [params]) or (None, None)
        """
        try:
            # Simple parser: operator(param1, param2, ...)
            if '(' not in step or ')' not in step:
                return None, None
            
            operator = step[:step.index('(')].strip()
            params_str = step[step.index('(') + 1:step.rindex(')')].strip()
            
            if not params_str:
                params = []
            else:
                # Split by comma, strip whitespace, convert types
                params = []
                for p in params_str.split(','):
                    p = p.strip()
                    # Try to convert to int
                    try:
                        params.append(int(p))
                    except ValueError:
                        params.append(p)
            
            return operator, params
        
        except Exception as e:
            logger.error(f"Error parsing step '{step}': {str(e)}")
            return None, None
    
    async def _llm_validate(self, operator: str, params: List,
                            state: Dict, domain: str) -> tuple:
        """
        Use LLM to validate ambiguous cases
        
        Args:
            operator: Operator name
            params: Parameters
            state: Current state
            domain: Domain name
        
        Returns:
            Tuple of (is_valid, reason)
        """
        if not self.llm_client:
            return False, "No LLM client available for fallback"
        
        prompt = f"""You are validating an HTN operator application.

Domain: {domain}
Operator: {operator}
Parameters: {params}
Current State: {state}

Question: Is this operator valid given the current state?

Respond with EXACTLY:
VALID: <brief reason>
or
INVALID: <brief reason>

Keep your response concise (one line).
"""
        
        try:
            response = await asyncio.to_thread(
                self.llm_client.generate,
                prompt,
                temperature=0.3,
                max_tokens=100
            )
            
            response = response.strip().upper()
            
            if response.startswith("VALID"):
                reason = response.replace("VALID:", "").strip()
                return True, reason or "LLM validated"
            elif response.startswith("INVALID"):
                reason = response.replace("INVALID:", "").strip()
                return False, reason or "LLM rejected"
            else:
                return False, f"Unexpected LLM response: {response}"
        
        except Exception as e:
            logger.error(f"LLM validation error: {str(e)}")
            return False, f"LLM validation failed: {str(e)}"
    
    def validate_input(self, input_data: Dict) -> bool:
        """Validate input data structure"""
        if not isinstance(input_data, dict):
            return False
        
        required_keys = ["plan", "initial_state"]
        for key in required_keys:
            if key not in input_data:
                logger.error(f"Missing required key: {key}")
                return False
        
        if not isinstance(input_data["plan"], list):
            logger.error("Plan must be a list")
            return False
        
        if not isinstance(input_data["initial_state"], dict):
            logger.error("Initial state must be a dict")
            return False
        
        return True
    
    def get_statistics(self) -> Dict:
        """Get agent performance statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_executions"] /
                self.stats["plans_executed"]
            ) if self.stats["plans_executed"] > 0 else 0.0,
            "validation_failure_rate": (
                self.stats["validation_failures"] /
                self.stats["total_steps_executed"]
            ) if self.stats["total_steps_executed"] > 0 else 0.0,
            "llm_fallback_rate": (
                self.stats["llm_fallback_used"] /
                self.stats["total_steps_executed"]
            ) if self.stats["total_steps_executed"] > 0 else 0.0,
            "validator_stats": self.validator.get_statistics()
        }
