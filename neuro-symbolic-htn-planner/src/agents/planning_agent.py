"""
PlanningAgent - Strategic Long-Term Planning

Evaluates multiple decomposition alternatives and selects optimal strategies.
Performs high-level strategic analysis before detailed decomposition.
"""

import asyncio
from typing import Dict, List
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent


class PlanningAgent(BaseAgent):
    """
    Agent specialized in strategic planning

    Analyzes problems from multiple perspectives, generates alternative
    strategies, and selects optimal approaches before detailed decomposition.

    Intelligence Type: LLM-Heavy (85% LLM, 15% rules)
    Primary LLM: Groq Llama 70B - Ultra-fast strategic analysis (2-5s)
    Fallback LLM: Llama 3.3 70B (HF) - High-quality reasoning (1.5s)
    """

    def __init__(
        self,
        name: str = "PlanningAgent",
        llm_client=None,
        fallback_client=None,
        config: dict = None,
    ):
        """
        Initialize PlanningAgent

        Args:
            name: Agent name
            llm_client: Primary LLM client (should be Groq Llama 70B)
            fallback_client: Fallback LLM client (should be HF Llama 70B)
            config: Configuration dict
        """
        super().__init__(name, llm_client, config or {})
        self.fallback_client = fallback_client

        # Agent-specific config
        self.max_strategies = config.get("max_strategies", 3) if config else 3
        self.temperature = config.get("temperature", 0.8) if config else 0.8
        self.max_tokens = config.get("max_tokens", 1500) if config else 1500

        # Statistics
        self.stats = {
            "plans_generated": 0,
            "successful_plans": 0,
            "failed_plans": 0,
            "fallback_used": 0,
            "avg_strategies_per_plan": 0.0,
            "avg_confidence": 0.0,
        }

    async def process(self, input_data: Dict) -> Dict:
        """
        Main processing method - generate strategic plan

        Args:
            input_data: {
                "task": "solve_hanoi(3, A, C, B)",
                "domain": "tower_of_hanoi",
                "initial_state": {...},
                "goal": {...},
                "constraints": [...],
                "context": {...}
            }

        Returns:
            {
                "success": bool,
                "strategies": [...],  # Multiple strategic approaches
                "recommended_strategy": {...},  # Best strategy
                "reasoning": str,
                "confidence": float,
                "error": str (if failed)
            }
        """
        start_time = datetime.now()

        # Validate input
        if not self.validate_input(input_data):
            return {"success": False, "error": "Invalid input data", "agent": self.name}

        task = input_data["task"]
        domain = input_data["domain"]
        initial_state = input_data.get("initial_state", {})
        goal = input_data.get("goal", {})

        logger.info(f"Planning strategies for task: {task} in domain: {domain}")

        # Build strategic planning prompt
        system_prompt, user_prompt = self._build_planning_prompt(
            task=task,
            domain=domain,
            initial_state=initial_state,
            goal=goal,
            constraints=input_data.get("constraints", []),
            context=input_data.get("context", {}),
        )

        # Generate strategies
        result = await self._generate_strategies(system_prompt, user_prompt)

        if result["success"]:
            self.stats["plans_generated"] += 1
            self.stats["successful_plans"] += 1
            self.stats["avg_strategies_per_plan"] = (
                self.stats["avg_strategies_per_plan"]
                * (self.stats["plans_generated"] - 1)
                + len(result["strategies"])
            ) / self.stats["plans_generated"]
            self.stats["avg_confidence"] = (
                self.stats["avg_confidence"] * (self.stats["plans_generated"] - 1)
                + result["confidence"]
            ) / self.stats["plans_generated"]
        else:
            self.stats["plans_generated"] += 1
            self.stats["failed_plans"] += 1

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        result["processing_time_ms"] = processing_time
        result["agent"] = self.name

        logger.info(
            f"Planning complete: {len(result.get('strategies', []))} strategies, "
            f"confidence: {result.get('confidence', 0):.2f}, "
            f"time: {processing_time:.1f}ms"
        )

        return result

    def _build_planning_prompt(
        self,
        task: str,
        domain: str,
        initial_state: Dict,
        goal: Dict,
        constraints: List,
        context: Dict,
    ) -> tuple:
        """Build strategic planning prompt"""

        system_prompt = """You are a strategic planning expert for HTN (Hierarchical Task Network) planning.

Your role is to analyze a planning problem from multiple perspectives and propose different strategic approaches before detailed decomposition.

For each problem:
1. Analyze the problem structure (initial state, goal, domain characteristics)
2. Identify key challenges and opportunities
3. Generate 2-3 alternative strategic approaches
4. Evaluate trade-offs (optimality vs speed, resource usage, etc.)
5. Recommend the best strategy with clear reasoning

Respond in JSON format:
{
  "strategies": [
    {
      "name": "strategy_name",
      "approach": "description",
      "advantages": ["list", "of", "advantages"],
      "disadvantages": ["list", "of", "disadvantages"],
      "estimated_complexity": "low|medium|high",
      "estimated_optimality": "suboptimal|near_optimal|optimal"
    }
  ],
  "recommended_strategy": "strategy_name",
  "reasoning": "why this strategy is best for this problem",
  "confidence": 0.95,
  "key_insights": ["insight1", "insight2"]
}"""

        # Format initial state and goal
        state_str = self._format_state(initial_state)
        goal_str = self._format_state(goal)

        user_prompt = f"""Analyze this planning problem and propose strategic approaches:

**Task**: {task}
**Domain**: {domain}

**Initial State**:
{state_str}

**Goal State**:
{goal_str}

**Constraints**: {", ".join(constraints) if constraints else "None"}

**Domain Context**: {context.get("domain_description", "Standard HTN planning domain")}

Generate {self.max_strategies} alternative strategies, evaluate them, and recommend the best approach."""

        return system_prompt, user_prompt

    def _format_state(self, state: Dict) -> str:
        """Format state dict for prompt"""
        if not state:
            return "Not specified"

        lines = []
        for key, value in state.items():
            lines.append(f"  {key}: {value}")

        return "\n".join(lines) if lines else "Empty state"

    async def _generate_strategies(
        self, system_prompt: str, user_prompt: str, is_fallback: bool = False
    ) -> Dict:
        """Generate strategic plans using LLM"""

        client = self.fallback_client if is_fallback else self.llm_client

        if not client:
            logger.warning(
                f"{'Fallback' if is_fallback else 'Primary'} LLM not available"
            )
            if not is_fallback and self.fallback_client:
                logger.info("Trying fallback LLM...")
                self.stats["fallback_used"] += 1
                return await self._generate_strategies(
                    system_prompt, user_prompt, is_fallback=True
                )

            # Return rule-based fallback
            return self._rule_based_planning()

        try:
            # Generate response
            response = await asyncio.to_thread(
                client.generate,
                user_prompt,
                system_prompt=system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse response
            parsed = self._parse_planning_response(response)

            if parsed["success"]:
                return parsed

            # If parsing failed, try fallback
            if not is_fallback and self.fallback_client:
                logger.warning("Primary LLM response parsing failed, trying fallback")
                self.stats["fallback_used"] += 1
                return await self._generate_strategies(
                    system_prompt, user_prompt, is_fallback=True
                )

            return parsed

        except Exception as e:
            logger.error(f"LLM generation error: {e}")

            if not is_fallback and self.fallback_client:
                logger.info("Trying fallback due to error")
                self.stats["fallback_used"] += 1
                return await self._generate_strategies(
                    system_prompt, user_prompt, is_fallback=True
                )

            return {
                "success": False,
                "error": f"LLM generation failed: {str(e)}",
                "strategies": [],
            }

    def _parse_planning_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
        import json
        import re

        try:
            # Extract JSON from markdown code blocks if present
            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL
            )
            if json_match:
                response = json_match.group(1)

            # Parse JSON
            data = json.loads(response)

            # Validate required fields
            if "strategies" not in data or not data["strategies"]:
                return {
                    "success": False,
                    "error": "No strategies generated",
                    "strategies": [],
                }

            if "recommended_strategy" not in data:
                # Auto-select first strategy
                data["recommended_strategy"] = data["strategies"][0]["name"]

            # Find recommended strategy object
            recommended = next(
                (
                    s
                    for s in data["strategies"]
                    if s["name"] == data["recommended_strategy"]
                ),
                data["strategies"][0],
            )

            return {
                "success": True,
                "strategies": data["strategies"],
                "recommended_strategy": recommended,
                "reasoning": data.get("reasoning", "No reasoning provided"),
                "confidence": data.get("confidence", 0.5),
                "key_insights": data.get("key_insights", []),
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {
                "success": False,
                "error": f"Failed to parse JSON: {str(e)}",
                "strategies": [],
            }

        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return {
                "success": False,
                "error": f"Failed to parse response: {str(e)}",
                "strategies": [],
            }

    def _rule_based_planning(self) -> Dict:
        """Fallback rule-based planning when no LLM available"""
        logger.info("Using rule-based planning fallback")

        return {
            "success": True,
            "strategies": [
                {
                    "name": "greedy_forward",
                    "approach": "Greedy forward search from initial to goal",
                    "advantages": ["Simple", "Fast"],
                    "disadvantages": ["May not be optimal"],
                    "estimated_complexity": "low",
                    "estimated_optimality": "suboptimal",
                },
                {
                    "name": "backward_chaining",
                    "approach": "Work backward from goal to initial state",
                    "advantages": ["Goal-directed", "Efficient"],
                    "disadvantages": ["May miss alternatives"],
                    "estimated_complexity": "medium",
                    "estimated_optimality": "near_optimal",
                },
            ],
            "recommended_strategy": {
                "name": "greedy_forward",
                "approach": "Greedy forward search from initial to goal",
                "advantages": ["Simple", "Fast"],
                "disadvantages": ["May not be optimal"],
                "estimated_complexity": "low",
                "estimated_optimality": "suboptimal",
            },
            "reasoning": "Default strategy selected (no LLM available)",
            "confidence": 0.5,
            "key_insights": ["Using rule-based fallback"],
        }

    def validate_input(self, input_data: Dict) -> bool:
        """Validate input data"""
        required_fields = ["task", "domain"]
        return all(field in input_data for field in required_fields)

    def get_statistics(self) -> Dict:
        """Get agent statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_plans"] / self.stats["plans_generated"]
                if self.stats["plans_generated"] > 0
                else 0.0
            ),
            "fallback_rate": (
                self.stats["fallback_used"] / self.stats["plans_generated"]
                if self.stats["plans_generated"] > 0
                else 0.0
            ),
        }
