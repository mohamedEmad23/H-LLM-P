"""
VerificationAgent - HTN Plan Verification and Quality Analysis with PANDA Integration

Verifies executed plans for correctness, efficiency, and quality.
Enhanced with 4-layer PANDA validation.
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent
from .prompts.verification_prompts import (
    build_verification_prompt,
    parse_verification_response,
    calculate_quality_metrics,
)
from ..integrations.panda_wrapper import PANDAWrapper


class VerificationAgent(BaseAgent):
    """
    Agent specialized in plan verification and quality analysis

    Uses LLM to perform deep analysis of executed plans:
    - Goal achievement verification
    - Constraint compliance checking
    - Logical consistency analysis
    - Efficiency assessment
    - Quality scoring and suggestions

    Intelligence Type: LLM-Medium (60% LLM, 40% rules)
    Primary LLM: Llama 3.1 8B (HF) - 3.7s latency
    Fallback LLM: Gemini 2.0 - 4-6s latency
    """

    def __init__(
        self,
        name: str = "VerificationAgent",
        llm_client=None,
        fallback_client=None,
        config: dict = None,
    ):
        """
        Initialize VerificationAgent with PANDA integration

        Args:
            name: Agent name
            llm_client: Primary LLM (Llama 8B HF)
            fallback_client: Fallback LLM (Gemini)
            config: Configuration dict
        """
        super().__init__(name, llm_client, config or {})
        self.fallback_client = fallback_client

        # PANDA integration for plan validation
        # Note: Workflow will inject the wrapper, this is just for standalone usage
        panda_root = config.get("panda_root", "../PANDA-HTN") if config else "../PANDA-HTN"
        self.panda_wrapper: Optional[PANDAWrapper] = None
        try:
            self.panda_wrapper = PANDAWrapper(panda_root=panda_root)
        except Exception as e:
            logger.warning(f"PANDA wrapper initialization failed: {e}")

        # Config
        self.temperature = config.get("temperature", 0.3) if config else 0.3
        self.max_tokens = config.get("max_tokens", 1500) if config else 1500

        # Statistics
        self.stats = {
            "verifications_performed": 0,
            "plans_verified_successful": 0,
            "plans_verified_failed": 0,
            "avg_quality_score": 0.0,
            "fallback_used": 0,
            "panda_validations": 0,
            "panda_validation_failures": 0,
        }

    async def process(self, input_data: Dict) -> Dict:
        """
        Verify executed plan

        Args:
            input_data: {
                "execution_trace": [...],
                "final_state": {...},
                "initial_state": {...},
                "goal": {...},
                "domain": "tower_of_hanoi",
                "optimal_steps": 7 (optional)
            }

        Returns:
            {
                "success": bool,
                "goal_achieved": bool,
                "quality_score": 0-100,
                "efficiency_score": 0-100,
                "issues_found": [...],
                "suggestions": [...],
                "quality_metrics": {...},
                "reasoning": str
            }
        """
        start_time = datetime.now()

        # Validate input
        if not self.validate_input(input_data):
            return {"success": False, "error": "Invalid input data", "agent": self.name}

        execution_trace = input_data["execution_trace"]
        final_state = input_data["final_state"]
        initial_state = input_data["initial_state"]
        goal = input_data["goal"]
        domain = input_data.get("domain", "unknown")
        optimal_steps = input_data.get("optimal_steps")

        logger.info(
            f"Verifying plan with {len(execution_trace)} steps in domain: {domain}"
        )

        # Quick rule-based checks first
        rule_based_result = self._rule_based_verification(
            execution_trace, final_state, goal, domain
        )

        # Build verification prompt
        system_prompt, user_prompt = build_verification_prompt(
            domain=domain,
            goal=goal,
            execution_trace=execution_trace,
            final_state=final_state,
            initial_state=initial_state,
            optimal_steps=optimal_steps,
        )

        # Get LLM verification
        llm_result = await self._llm_verification(
            system_prompt, user_prompt, is_fallback=False
        )

        # Try fallback if primary failed
        if not llm_result["success"] and self.fallback_client:
            logger.warning(
                f"Primary LLM failed, trying fallback: {llm_result.get('error')}"
            )
            llm_result = await self._llm_verification(
                system_prompt, user_prompt, is_fallback=True
            )
            if llm_result["success"]:
                self.stats["fallback_used"] += 1

        # Combine rule-based and LLM results
        if llm_result["success"]:
            verification_data = llm_result["verification"]

            # Override with rule-based checks if more strict
            if not rule_based_result["goal_achieved"]:
                verification_data["goal_achieved"] = False

            # Merge issues
            all_violations = list(
                set(
                    verification_data.get("constraint_violations", [])
                    + rule_based_result.get("constraint_violations", [])
                )
            )
            all_issues = list(
                set(
                    verification_data.get("logical_issues", [])
                    + rule_based_result.get("logical_issues", [])
                )
            )

            verification_data["constraint_violations"] = all_violations
            verification_data["logical_issues"] = all_issues

        else:
            # Fall back to rule-based only
            verification_data = rule_based_result
            verification_data["reasoning"] = (
                "LLM verification failed, using rule-based checks only"
            )

        # Calculate quality metrics
        quality_metrics = calculate_quality_metrics(
            goal_achieved=verification_data.get("goal_achieved", False),
            constraint_violations=verification_data.get("constraint_violations", []),
            logical_issues=verification_data.get("logical_issues", []),
            efficiency_score=verification_data.get("efficiency_score", 50),
            actual_steps=len(execution_trace),
            optimal_steps=optimal_steps,
        )

        # Update statistics
        self.stats["verifications_performed"] += 1
        if verification_data.get("goal_achieved"):
            self.stats["plans_verified_successful"] += 1
        else:
            self.stats["plans_verified_failed"] += 1

        # Update running average quality score
        n = self.stats["verifications_performed"]
        quality = quality_metrics.get("overall_quality", 0)
        self.stats["avg_quality_score"] = (
            self.stats["avg_quality_score"] * (n - 1) + quality
        ) / n

        # Build result
        result = {
            "success": True,
            "goal_achieved": verification_data.get("goal_achieved", False),
            "quality_score": quality_metrics.get("overall_quality", 0),
            "efficiency_score": verification_data.get("efficiency_score", 50),
            "issues_found": (
                verification_data.get("constraint_violations", [])
                + verification_data.get("logical_issues", [])
            ),
            "suggestions": verification_data.get("suggestions", []),
            "quality_metrics": quality_metrics,
            "reasoning": verification_data.get("reasoning", ""),
            "constraint_violations": verification_data.get("constraint_violations", []),
            "logical_issues": verification_data.get("logical_issues", []),
            "verification_time_ms": (datetime.now() - start_time).total_seconds()
            * 1000,
            "agent": self.name,
        }

        # Log interaction
        self.log_interaction(
            {
                "input": input_data,
                "output": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return result

    def _rule_based_verification(
        self, execution_trace: list, final_state: dict, goal: dict, domain: str
    ) -> dict:
        """
        Fast rule-based verification checks

        Args:
            execution_trace: Execution trace
            final_state: Final state
            goal: Goal state
            domain: Domain name

        Returns:
            Dict with verification results
        """
        violations = []
        issues = []

        # Check if any execution errors
        for step in execution_trace:
            if step.get("status") != "success":
                issues.append(
                    f"Step {step.get('step')} failed: "
                    f"{step.get('error', 'unknown error')}"
                )

        # Domain-specific checks
        if domain == "tower_of_hanoi":
            goal_achieved = self._verify_hanoi_goal(final_state, goal)
        elif domain == "graph_traversal":
            goal_achieved = self._verify_graph_goal(final_state, goal)
        else:
            # Generic check: deep equality
            goal_achieved = final_state == goal

        return {
            "goal_achieved": goal_achieved and len(issues) == 0,
            "constraint_violations": violations,
            "logical_issues": issues,
            "efficiency_score": 50,
            "quality_score": 75 if goal_achieved else 25,
            "suggestions": [],
            "reasoning": "Rule-based verification",
        }

    def _verify_hanoi_goal(self, final_state: dict, goal: dict) -> bool:
        """Verify Tower of Hanoi goal state"""
        if "pegs" not in final_state or "pegs" not in goal:
            return False

        final_pegs = final_state["pegs"]
        goal_pegs = goal["pegs"]

        # Check each peg
        for peg in goal_pegs:
            if peg not in final_pegs:
                return False
            if final_pegs[peg] != goal_pegs[peg]:
                return False

        return True

    def _verify_graph_goal(self, final_state: dict, goal: dict) -> bool:
        """Verify graph traversal goal"""
        if "current_node" not in final_state or "current_node" not in goal:
            return False

        return final_state["current_node"] == goal["current_node"]

    async def _llm_verification(
        self, system_prompt: str, user_prompt: str, is_fallback: bool = False
    ) -> dict:
        """
        Perform LLM-based verification

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            is_fallback: Using fallback client

        Returns:
            Dict with success and verification data
        """
        client = self.fallback_client if is_fallback else self.llm_client

        if not client:
            return {"success": False, "error": "No LLM client available"}

        try:
            response = await asyncio.to_thread(
                client.generate,
                user_prompt,
                system_prompt=system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse response - extract content from LLMResponse
            parsed = parse_verification_response(response.content)

            if "error" in parsed:
                logger.error(f"Failed to parse verification: {parsed['error']}")
                return {
                    "success": False,
                    "error": parsed["error"],
                    "raw_response": parsed.get("raw_response"),
                }

            return {
                "success": True,
                "verification": parsed,
                "used_fallback": is_fallback,
            }

        except Exception as e:
            logger.error(f"LLM verification error: {str(e)}")
            return {"success": False, "error": str(e)}

    def validate_input(self, input_data: Dict) -> bool:
        """Validate input data"""
        if not isinstance(input_data, dict):
            return False

        required = ["execution_trace", "final_state", "goal"]
        for key in required:
            if key not in input_data:
                logger.error(f"Missing required key: {key}")
                return False

        if not isinstance(input_data["execution_trace"], list):
            logger.error("execution_trace must be a list")
            return False

        return True

    def get_statistics(self) -> Dict:
        """Get verification statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["plans_verified_successful"]
                / self.stats["verifications_performed"]
            )
            if self.stats["verifications_performed"] > 0
            else 0.0,
            "fallback_rate": (
                self.stats["fallback_used"] / self.stats["verifications_performed"]
            )
            if self.stats["verifications_performed"] > 0
            else 0.0,
            "panda_validation_success_rate": (
                (self.stats["panda_validations"] - self.stats["panda_validation_failures"])
                / self.stats["panda_validations"]
            )
            if self.stats["panda_validations"] > 0
            else 0.0,
        }
    
    # ========== PANDA 4-Layer Validation ==========
    
    async def validate_panda_plan(
        self,
        domain_file: str,
        problem_file: str,
        panda_plan_result,
        optimal_plan_length: Optional[int] = None
    ) -> Dict:
        """
        4-Layer PANDA Plan Validation
        
        Layer 1: Syntax Validation (PANDA parser)
        Layer 2: Planning Feasibility (PANDA can generate plan)
        Layer 3: Execution Correctness (Goal achievement)
        Layer 4: Efficiency Metrics (Plan quality)
        
        Args:
            domain_file: Path to HDDL domain
            problem_file: Path to HDDL problem
            panda_plan_result: PANDAPlan from PANDAWrapper.plan()
            optimal_plan_length: Expected optimal length (optional)
        
        Returns:
            {
                "success": bool,
                "validation_layers": {
                    "syntax": {...},
                    "planning": {...},
                    "execution": {...},
                    "efficiency": {...}
                },
                "overall_score": 0-100,
                "issues": [...],
                "suggestions": [...]
            }
        """
        logger.info("[PANDA] Starting 4-layer validation")
        
        validation_result = {
            "success": True,
            "validation_layers": {},
            "overall_score": 0.0,
            "issues": [],
            "suggestions": []
        }
        
        layer_scores = []
        
        # Layer 1: Syntax Validation
        syntax_result = await self._validate_layer1_syntax(domain_file, problem_file)
        validation_result["validation_layers"]["syntax"] = syntax_result
        layer_scores.append(syntax_result["score"])
        
        if not syntax_result["passed"]:
            validation_result["success"] = False
            validation_result["issues"].extend(syntax_result.get("errors", []))
            self.stats["panda_validation_failures"] += 1
            logger.error(f"[PANDA] Layer 1 (Syntax) FAILED: {syntax_result.get('errors')}")
            validation_result["overall_score"] = sum(layer_scores) / 4.0 * 100
            return validation_result
        
        # Layer 2: Planning Feasibility
        planning_result = self._validate_layer2_planning(panda_plan_result)
        validation_result["validation_layers"]["planning"] = planning_result
        layer_scores.append(planning_result["score"])
        
        if not planning_result["passed"]:
            validation_result["success"] = False
            validation_result["issues"].extend(planning_result.get("errors", []))
            self.stats["panda_validation_failures"] += 1
            logger.error(f"[PANDA] Layer 2 (Planning) FAILED")
            validation_result["overall_score"] = sum(layer_scores) / 4.0 * 100
            return validation_result
        
        # Layer 3: Execution Correctness
        execution_result = self._validate_layer3_execution(panda_plan_result)
        validation_result["validation_layers"]["execution"] = execution_result
        layer_scores.append(execution_result["score"])
        
        if not execution_result["passed"]:
            validation_result["issues"].extend(execution_result.get("warnings", []))
            # Not a hard failure, continue to efficiency
        
        # Layer 4: Efficiency Metrics
        efficiency_result = self._validate_layer4_efficiency(
            panda_plan_result,
            optimal_plan_length
        )
        validation_result["validation_layers"]["efficiency"] = efficiency_result
        layer_scores.append(efficiency_result["score"])
        
        validation_result["suggestions"].extend(efficiency_result.get("suggestions", []))
        
        # Calculate overall score
        validation_result["overall_score"] = sum(layer_scores) / len(layer_scores) * 100
        
        self.stats["panda_validations"] += 1
        
        logger.info(
            f"[PANDA] 4-layer validation complete: "
            f"Overall Score = {validation_result['overall_score']:.1f}%, "
            f"Success = {validation_result['success']}"
        )
        
        return validation_result
    
    async def _validate_layer1_syntax(self, domain_file: str, problem_file: str) -> Dict:
        """Layer 1: PANDA Parser Syntax Validation"""
        if not self.panda_wrapper:
            return {
                "passed": False,
                "score": 0.0,
                "errors": ["PANDA wrapper not available"]
            }
        
        try:
            validation_result = self.panda_wrapper.validate_hddl(
                domain_file=domain_file,
                problem_file=problem_file
            )
            
            if validation_result.is_valid:
                return {
                    "passed": True,
                    "score": 1.0,
                    "warnings": validation_result.warnings
                }
            else:
                return {
                    "passed": False,
                    "score": 0.0,
                    "errors": validation_result.syntax_errors + validation_result.semantic_errors
                }
        except Exception as e:
            logger.error(f"Layer 1 validation error: {e}")
            return {
                "passed": False,
                "score": 0.0,
                "errors": [f"Syntax validation failed: {str(e)}"]
            }
    
    def _validate_layer2_planning(self, panda_plan_result) -> Dict:
        """Layer 2: Planning Feasibility Check"""
        if panda_plan_result.success:
            return {
                "passed": True,
                "score": 1.0,
                "plan_length": panda_plan_result.plan_length,
                "search_time_ms": panda_plan_result.search_time_ms,
                "nodes_expanded": panda_plan_result.nodes_expanded
            }
        else:
            return {
                "passed": False,
                "score": 0.0,
                "errors": [f"Planning failed: {panda_plan_result.error}"],
                "result_type": "FAILED"
            }
    
    def _validate_layer3_execution(self, panda_plan_result) -> Dict:
        """Layer 3: Execution Correctness (checks for valid action sequence)"""
        actions = panda_plan_result.actions
        
        if not actions:
            return {
                "passed": False,
                "score": 0.0,
                "errors": ["No actions in plan"]
            }
        
        # Check for duplicate actions (potential inefficiency)
        action_strs = [f"{a['name']}({','.join(a['parameters'])})" for a in actions]
        duplicates = [a for a in action_strs if action_strs.count(a) > 1]
        
        warnings = []
        if duplicates:
            warnings.append(f"Duplicate actions detected: {set(duplicates)}")
        
        # All actions have required fields
        for i, action in enumerate(actions):
            if 'name' not in action or 'parameters' not in action:
                return {
                    "passed": False,
                    "score": 0.5,
                    "errors": [f"Action {i} missing required fields"]
                }
        
        score = 1.0 if not warnings else 0.9
        
        return {
            "passed": True,
            "score": score,
            "action_count": len(actions),
            "warnings": warnings
        }
    
    def _validate_layer4_efficiency(
        self,
        panda_plan_result,
        optimal_plan_length: Optional[int] = None
    ) -> Dict:
        """Layer 4: Efficiency Metrics and Quality Assessment"""
        metrics = {
            "plan_length": panda_plan_result.plan_length,
            "search_time_ms": panda_plan_result.search_time_ms,
            "nodes_expanded": panda_plan_result.nodes_expanded
        }
        
        suggestions = []
        score = 1.0
        
        # Check plan length optimality
        if optimal_plan_length is not None:
            if panda_plan_result.plan_length == optimal_plan_length:
                suggestions.append("Plan is optimal length")
            elif panda_plan_result.plan_length < optimal_plan_length:
                suggestions.append("Plan is shorter than expected optimal length - verify correctness")
                score -= 0.1
            else:
                excess = panda_plan_result.plan_length - optimal_plan_length
                suggestions.append(f"Plan is {excess} steps longer than optimal")
                score -= min(0.3, excess * 0.05)
            
            metrics["optimal_length"] = optimal_plan_length
            metrics["efficiency_ratio"] = optimal_plan_length / panda_plan_result.plan_length if panda_plan_result.plan_length > 0 else 0.0
        
        # Check search efficiency
        if panda_plan_result.search_time_ms > 5000:
            suggestions.append("Search time > 5s - consider domain simplification")
            score -= 0.1
        
        if panda_plan_result.nodes_expanded > 10000:
            suggestions.append("High node expansion - search space may be too large")
            score -= 0.1
        
        # Ensure score is in [0, 1]
        score = max(0.0, min(1.0, score))
        
        return {
            "passed": True,
            "score": score,
            "metrics": metrics,
            "suggestions": suggestions
        }
