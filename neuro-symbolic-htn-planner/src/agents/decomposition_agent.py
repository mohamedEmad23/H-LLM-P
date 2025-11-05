"""
DecompositionAgent - HTN Task Decomposition
Breaks down high-level tasks into hierarchical subtasks using LLM reasoning
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent
from .prompts.decomposition_prompts import (
    build_decomposition_prompt,
    parse_decomposition_response,
)


class DecompositionAgent(BaseAgent):
    """
    Agent specialized in HTN task decomposition

    Uses LLM (primarily Llama 3.3 70B via HuggingFace) to break down
    complex tasks into hierarchical subtasks following HTN principles.

    Intelligence Type: LLM-Heavy (90% LLM, 10% rules)
    Primary LLM: Llama 3.3 70B (HF) - 1.5s latency
    Fallback LLM: Groq Llama 70B - 2-5s latency
    """

    def __init__(
        self,
        name: str = "DecompositionAgent",
        llm_client=None,
        fallback_client=None,
        config: dict = None,
    ):
        """
        Initialize DecompositionAgent

        Args:
            name: Agent name
            llm_client: Primary LLM client (should be HF Llama 70B)
            fallback_client: Fallback LLM client (should be Groq)
            config: Configuration dict
        """
        super().__init__(name, llm_client, config or {})
        self.fallback_client = fallback_client

        # Agent-specific config
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.temperature = config.get("temperature", 0.7) if config else 0.7
        self.max_tokens = config.get("max_tokens", 2000) if config else 2000

        # Memory integration (will be set later)
        self.memory_system = None

        # Statistics
        self.stats = {
            "decompositions_generated": 0,
            "successful_decompositions": 0,
            "failed_decompositions": 0,
            "fallback_used": 0,
            "avg_confidence": 0.0,
        }

    async def process(self, input_data: Dict) -> Dict:
        """
        Main processing method - decompose task into HTN methods

        Args:
            input_data: {
                "task": "solve_hanoi(3, A, C, B)",
                "domain": "tower_of_hanoi",
                "operators": {...},
                "constraints": [...],
                "context": {...}
            }

        Returns:
            {
                "success": bool,
                "methods": [...],
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
        operators = input_data.get("operators", {})
        constraints = input_data.get("constraints", [])
        context = input_data.get("context", {})

        logger.info(f"Decomposing task: {task} in domain: {domain}")

        # Query memory for hints (if memory system available)
        memory_hints = None
        if self.memory_system:
            memory_hints = await self._get_memory_hints(task, domain)

        # Build prompt
        system_prompt, user_prompt = build_decomposition_prompt(
            task=task,
            domain=domain,
            operators=operators,
            constraints=constraints,
            memory_hints=memory_hints,
            domain_context=context.get("domain_context"),
        )

        # Try primary LLM
        result = await self._generate_decomposition(
            system_prompt, user_prompt, is_fallback=False
        )

        # Try fallback if primary failed
        if not result["success"] and self.fallback_client:
            logger.warning(
                f"Primary LLM failed, trying fallback: {result.get('error')}"
            )
            result = await self._generate_decomposition(
                system_prompt, user_prompt, is_fallback=True
            )
            if result["success"]:
                self.stats["fallback_used"] += 1

        # Update statistics
        self.stats["decompositions_generated"] += 1
        if result["success"]:
            self.stats["successful_decompositions"] += 1
            confidence = result.get("confidence", 0.0)
            # Running average
            n = self.stats["successful_decompositions"]
            self.stats["avg_confidence"] = (
                self.stats["avg_confidence"] * (n - 1) + confidence
            ) / n
        else:
            self.stats["failed_decompositions"] += 1

        # Add metadata
        result["agent"] = self.name
        result["task"] = task
        result["domain"] = domain
        result["processing_time_ms"] = (
            datetime.now() - start_time
        ).total_seconds() * 1000

        # Log interaction
        self.log_interaction(
            {
                "input": input_data,
                "output": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return result

    async def _generate_decomposition(
        self, system_prompt: str, user_prompt: str, is_fallback: bool = False
    ) -> Dict:
        """
        Generate decomposition using LLM

        Args:
            system_prompt: System prompt
            user_prompt: User prompt with task details
            is_fallback: Whether using fallback client

        Returns:
            Dict with success, methods, reasoning, confidence
        """
        client = self.fallback_client if is_fallback else self.llm_client

        if not client:
            return {
                "success": False,
                "error": f"No {'fallback' if is_fallback else 'primary'} LLM client available",
            }

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
            parsed = parse_decomposition_response(response)

            if "error" in parsed:
                logger.error(f"Failed to parse decomposition: {parsed['error']}")
                return {
                    "success": False,
                    "error": parsed["error"],
                    "raw_response": parsed.get("raw_response"),
                }

            # Extract methods and metadata
            methods = parsed.get("methods", [])

            if not methods:
                return {"success": False, "error": "No methods generated"}

            # Calculate average confidence
            confidences = [m.get("confidence", 0.5) for m in methods]
            avg_confidence = sum(confidences) / len(confidences)

            # Collect reasoning
            reasoning_parts = [
                m.get("reasoning", "") for m in methods if m.get("reasoning")
            ]
            combined_reasoning = " | ".join(reasoning_parts)

            return {
                "success": True,
                "methods": methods,
                "reasoning": combined_reasoning,
                "confidence": avg_confidence,
                "alternatives_considered": parsed.get("alternatives_considered", 1),
                "used_fallback": is_fallback,
            }

        except Exception as e:
            logger.error(f"Error generating decomposition: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _get_memory_hints(self, task: str, domain: str) -> Optional[Dict]:
        """
        Query memory system for helpful hints

        Args:
            task: Task being decomposed
            domain: Domain name

        Returns:
            Dict with similar_plans, common_patterns, error_patterns
        """
        if not self.memory_system:
            return None

        try:
            hints = await asyncio.to_thread(
                self.memory_system.get_memory_hints, task, domain
            )
            return hints
        except Exception as e:
            logger.warning(f"Failed to get memory hints: {str(e)}")
            return None

    def validate_input(self, input_data: Dict) -> bool:
        """
        Validate input data structure

        Args:
            input_data: Input dict to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(input_data, dict):
            return False

        required_keys = ["task", "domain"]
        for key in required_keys:
            if key not in input_data:
                logger.error(f"Missing required key: {key}")
                return False

        # Validate task is non-empty string
        if not isinstance(input_data["task"], str) or not input_data["task"]:
            logger.error("Task must be non-empty string")
            return False

        # Validate domain is non-empty string
        if not isinstance(input_data["domain"], str) or not input_data["domain"]:
            logger.error("Domain must be non-empty string")
            return False

        return True

    def set_memory_system(self, memory_system):
        """Set memory system for retrieval augmentation"""
        self.memory_system = memory_system
        logger.info("Memory system connected")

    def get_statistics(self) -> Dict:
        """Get agent performance statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_decompositions"]
                / self.stats["decompositions_generated"]
            )
            if self.stats["decompositions_generated"] > 0
            else 0.0,
            "fallback_rate": (
                self.stats["fallback_used"] / self.stats["decompositions_generated"]
            )
            if self.stats["decompositions_generated"] > 0
            else 0.0,
        }
