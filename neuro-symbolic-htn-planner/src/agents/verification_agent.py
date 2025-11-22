"""
VerificationAgent - HTN Plan Verification and Quality Analysis

Verifies executed plans for correctness, efficiency, and quality.
"""

import asyncio
from typing import Dict
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent
from .prompts.verification_prompts import (
    build_verification_prompt,
    parse_verification_response,
    calculate_quality_metrics,
)


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
        Initialize VerificationAgent

        Args:
            name: Agent name
            llm_client: Primary LLM (Llama 8B HF)
            fallback_client: Fallback LLM (Gemini)
            config: Configuration dict
        """
        super().__init__(name, llm_client, config or {})
        self.fallback_client = fallback_client

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
        }
