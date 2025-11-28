"""
DecompositionAgent - HTN Task Decomposition with PANDA Integration
Breaks down high-level tasks into hierarchical subtasks using LLM reasoning,
validates with PANDA HTN planner, and generates valid HDDL domains.
"""

import asyncio
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from loguru import logger
from pathlib import Path

from .base_agent import BaseAgent
from .prompts.decomposition_prompts import (
    build_decomposition_prompt,
    parse_decomposition_response,
)
from ..integrations.hddl_domain_generator import HDDLDomainGenerator, HDDLDomain, HDDLProblem
from ..integrations.panda_wrapper import PANDAWrapper


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
        Initialize DecompositionAgent with PANDA integration

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

        # PANDA integration (lazy initialization or passed via config)
        self.panda_wrapper = config.get("panda_wrapper") if config else None
        if self.panda_wrapper is None:
            # Try to initialize if PANDA path is provided
            panda_root = config.get("panda_root") if config else None
            if panda_root:
                try:
                    self.panda_wrapper = PANDAWrapper(panda_root=panda_root)
                except FileNotFoundError:
                    logger.warning(f"PANDA binaries not found at {panda_root}, will require external wrapper")
                    
        self.hddl_generator = HDDLDomainGenerator()
        
        # Hand-coded fallback domains
        self.fallback_domains_path = Path(config.get("fallback_domains_path", "./src/domains") if config else "./src/domains")
        
        # Validation attempts before fallback
        self.max_validation_attempts = config.get("max_validation_attempts", 3) if config else 3

        # Memory integration (will be set later)
        self.memory_system = None

        # Statistics
        self.stats = {
            "decompositions_generated": 0,
            "successful_decompositions": 0,
            "failed_decompositions": 0,
            "fallback_used": 0,
            "avg_confidence": 0.0,
            "panda_validations": 0,
            "panda_validation_failures": 0,
            "hand_coded_fallbacks": 0,
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

            # Parse response - extract content from LLMResponse
            parsed = parse_decomposition_response(response.content)

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
            "panda_validation_success_rate": (
                (self.stats["panda_validations"] - self.stats["panda_validation_failures"])
                / self.stats["panda_validations"]
            )
            if self.stats["panda_validations"] > 0
            else 0.0,
        }
    
    # ========== PANDA Integration Methods ==========
    
    async def process_with_panda_validation(self, input_data: Dict) -> Dict:
        """
        Enhanced process method with PANDA validation loop
        
        Workflow:
        1. Generate HDDL methods using LLM
        2. Validate with PANDA parser
        3. If invalid, get feedback and retry (up to max_validation_attempts)
        4. If all attempts fail, fallback to hand-coded domain
        5. Return validated HDDL domain + problem files
        
        Args:
            input_data: {
                "task": "find_path(A, C)",
                "domain": "graph_traversal",
                "operators": [...],
                "initial_state": State object,
                "goal_state": State object,
                "constraints": [...],
                "context": {...}
            }
        
        Returns:
            {
                "success": bool,
                "hddl_domain_file": str,
                "hddl_problem_file": str,
                "methods": [...],
                "validation_result": {...},
                "used_fallback": bool,
                "error": str (if failed)
            }
        """
        start_time = datetime.now()
        
        task = input_data["task"]
        domain_name = input_data["domain"]
        
        logger.info(f"[PANDA] Starting validated decomposition for {task}")
        
        # Attempt 1: Try LLM-generated methods with validation loop
        for attempt in range(1, self.max_validation_attempts + 1):
            logger.info(f"[PANDA] Validation attempt {attempt}/{self.max_validation_attempts}")
            
            # Generate methods using LLM
            decomposition_result = await self.process(input_data)
            
            if not decomposition_result["success"]:
                logger.warning(f"[PANDA] LLM decomposition failed: {decomposition_result.get('error')}")
                continue
            
            # Convert methods to HDDL
            hddl_result = await self._generate_and_validate_hddl(
                domain_name=domain_name,
                methods_data=decomposition_result,
                operators=input_data.get("operators", []),
                initial_state=input_data.get("initial_state"),
                goal_tasks=input_data.get("goal_tasks", [(task, [])]),
                objects=input_data.get("objects", {}),
                attempt_number=attempt
            )
            
            if hddl_result["success"]:
                logger.info(f"[PANDA] Validation successful on attempt {attempt}")
                
                # Add metadata
                hddl_result["agent"] = self.name
                hddl_result["task"] = task
                hddl_result["domain"] = domain_name
                hddl_result["used_fallback"] = False
                hddl_result["validation_attempts"] = attempt
                hddl_result["processing_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
                
                return hddl_result
            else:
                logger.warning(f"[PANDA] Validation failed: {hddl_result.get('error')}")
                
                # Update input_data with feedback for next attempt
                input_data["context"]["validation_feedback"] = hddl_result.get("validation_errors", [])
        
        # Attempt 2: All LLM attempts failed, try hand-coded fallback
        logger.warning(f"[PANDA] All {self.max_validation_attempts} attempts failed, using hand-coded fallback")
        
        fallback_result = await self._use_hand_coded_fallback(
            domain_name=domain_name,
            task=task,
            initial_state=input_data.get("initial_state"),
            goal_tasks=input_data.get("goal_tasks", [(task, [])]),
            objects=input_data.get("objects", {})
        )
        
        if fallback_result["success"]:
            self.stats["hand_coded_fallbacks"] += 1
            fallback_result["used_fallback"] = True
            fallback_result["agent"] = self.name
            fallback_result["processing_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
            return fallback_result
        
        # Complete failure
        return {
            "success": False,
            "error": "LLM decomposition and hand-coded fallback both failed",
            "agent": self.name,
            "task": task,
            "domain": domain_name,
            "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
    
    async def _generate_and_validate_hddl(
        self,
        domain_name: str,
        methods_data: Dict,
        operators: List,
        initial_state,
        goal_tasks: List[Tuple[str, List[str]]],
        objects: Dict[str, str],
        attempt_number: int
    ) -> Dict:
        """
        Generate HDDL domain/problem files and validate with PANDA
        
        Args:
            domain_name: Domain name
            methods_data: Dict with "methods" from LLM
            operators: List of Operator objects
            initial_state: State object
            goal_tasks: List of (task_name, parameters)
            objects: Object declarations
            attempt_number: Current validation attempt
        
        Returns:
            {
                "success": bool,
                "hddl_domain_file": str,
                "hddl_problem_file": str,
                "validation_errors": [...],
                "error": str (if failed)
            }
        """
        try:
            # Convert LLM methods to MethodLibrary format
            from ..core.methods import MethodLibrary, Method
            
            method_library = MethodLibrary()
            
            for method_data in methods_data.get("methods", []):
                method = Method(
                    name=method_data.get("name", "unknown_method"),
                    task_name=method_data.get("task_name", "unknown_task"),
                    parameters=method_data.get("parameters", {}),
                    preconditions=method_data.get("preconditions", []),
                    subtasks=method_data.get("subtasks", []),
                    ordering=method_data.get("ordering", []),
                    priority=method_data.get("priority", 1.0)
                )
                method_library.register(method)
            
            # Generate HDDL domain
            hddl_domain = self.hddl_generator.generate_domain(
                domain_name=domain_name,
                methods=method_library,
                operators=operators
            )
            
            # Generate HDDL problem
            hddl_problem = self.hddl_generator.generate_problem(
                problem_name=f"{domain_name}_problem_{attempt_number}",
                domain_name=domain_name,
                init_state=initial_state,
                goal_tasks=goal_tasks,
                objects=objects
            )
            
            # Save to temporary files
            domain_file = f"/tmp/panda_{domain_name}_{attempt_number}.hddl"
            problem_file = f"/tmp/panda_{domain_name}_problem_{attempt_number}.hddl"
            
            self.hddl_generator.save_domain(hddl_domain, domain_file)
            self.hddl_generator.save_problem(hddl_problem, problem_file)
            
            # Validate with PANDA parser
            validation_result = await self.panda_wrapper.validate_hddl(
                domain_file=domain_file,
                problem_file=problem_file
            )
            
            self.stats["panda_validations"] += 1
            
            if validation_result.is_valid:
                logger.info(f"[PANDA] HDDL validation passed")
                
                return {
                    "success": True,
                    "hddl_domain_file": domain_file,
                    "hddl_problem_file": problem_file,
                    "hddl_domain": hddl_domain,
                    "hddl_problem": hddl_problem,
                    "methods": methods_data.get("methods", []),
                    "validation_warnings": validation_result.warnings
                }
            else:
                self.stats["panda_validation_failures"] += 1
                
                logger.warning(
                    f"[PANDA] Validation failed: "
                    f"{len(validation_result.syntax_errors)} syntax errors, "
                    f"{len(validation_result.semantic_errors)} semantic errors"
                )
                
                return {
                    "success": False,
                    "validation_errors": validation_result.syntax_errors + validation_result.semantic_errors,
                    "error": "PANDA validation failed"
                }
        
        except Exception as e:
            logger.error(f"[PANDA] HDDL generation/validation error: {e}")
            return {
                "success": False,
                "error": f"HDDL generation failed: {str(e)}"
            }
    
    async def _use_hand_coded_fallback(
        self,
        domain_name: str,
        task: str,
        initial_state,
        goal_tasks: List[Tuple[str, List[str]]],
        objects: Dict[str, str]
    ) -> Dict:
        """
        Use pre-written hand-coded HDDL domain as fallback
        
        Args:
            domain_name: Domain name (e.g., "graph_traversal", "tower_of_hanoi")
            task: Task name
            initial_state: Initial state
            goal_tasks: Goal tasks
            objects: Object declarations
        
        Returns:
            {
                "success": bool,
                "hddl_domain_file": str,
                "hddl_problem_file": str,
                "error": str (if failed)
            }
        """
        try:
            # Look for hand-coded domain file
            domain_dir = self.fallback_domains_path / domain_name
            domain_file = domain_dir / "domain.hddl"
            
            if not domain_file.exists():
                return {
                    "success": False,
                    "error": f"No hand-coded fallback domain found at {domain_file}"
                }
            
            logger.info(f"[PANDA] Using hand-coded fallback: {domain_file}")
            
            # Generate problem file for hand-coded domain
            hddl_problem = self.hddl_generator.generate_problem(
                problem_name=f"{domain_name}_fallback_problem",
                domain_name=domain_name,
                init_state=initial_state,
                goal_tasks=goal_tasks,
                objects=objects
            )
            
            problem_file = f"/tmp/panda_{domain_name}_fallback_problem.hddl"
            self.hddl_generator.save_problem(hddl_problem, problem_file)
            
            # Validate the combination
            validation_result = await self.panda_wrapper.validate_hddl(
                domain_file=str(domain_file),
                problem_file=problem_file
            )
            
            if validation_result.is_valid:
                return {
                    "success": True,
                    "hddl_domain_file": str(domain_file),
                    "hddl_problem_file": problem_file,
                    "is_hand_coded": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Hand-coded domain validation failed: {validation_result.syntax_errors}"
                }
        
        except Exception as e:
            logger.error(f"[PANDA] Hand-coded fallback failed: {e}")
            return {
                "success": False,
                "error": f"Fallback failed: {str(e)}"
            }
