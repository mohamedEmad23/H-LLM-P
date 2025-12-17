"""
DecompositionAgent - HTN Task Decomposition with PANDA Integration
Breaks down high-level tasks into hierarchical subtasks using LLM reasoning,
validates with PANDA HTN planner, and generates valid HDDL domains.

Enhanced with:
- DomainRegistry integration for persistent domain storage
- LLM feedback loop for PANDA validation error correction
- Method library auto-population
"""

import asyncio
import json
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from loguru import logger
from pathlib import Path

from .base_agent import BaseAgent
from .prompts.decomposition_prompts import (
    build_decomposition_prompt,
    parse_decomposition_response,
    build_hddl_correction_prompt,
    build_hddl_generation_prompt,
)
from ..integrations.hddl_domain_generator import HDDLDomainGenerator, HDDLDomain, HDDLProblem
from ..integrations.panda_wrapper import PANDAWrapper
from ..integrations.domain_registry import DomainRegistry
from ..integrations.panda_method_library import PANDAMethodLibrary
import re


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
        
        # Domain template selector configuration
        templates_path = config.get("templates_path", "./config/domain_templates.json") if config else "./config/domain_templates.json"
        self._load_domain_templates(templates_path)
        
        # Validation attempts before fallback
        self.max_validation_attempts = config.get("max_validation_attempts", 3) if config else 3

        # Memory integration (will be set later)
        self.memory_system = None
        
        # ========== DOMAIN REGISTRY INTEGRATION ==========
        # Persistent storage for generated HDDL domains
        # Use consolidated path under results/panda-results/
        registry_path = config.get("registry_path", "./results/panda-results/domain_registry.json") if config else "./results/panda-results/domain_registry.json"
        domains_base_path = config.get("domains_base_path", "./src/domains") if config else "./src/domains"
        
        try:
            self.domain_registry = DomainRegistry(
                registry_path=registry_path,
                domains_base_path=domains_base_path
            )
            # Scan existing domains on initialization
            scanned = self.domain_registry.scan_existing_domains()
            if scanned > 0:
                logger.info(f"[DECOMP] Scanned {scanned} existing domains into registry")
        except Exception as e:
            logger.warning(f"[DECOMP] Failed to initialize DomainRegistry: {e}")
            self.domain_registry = None
        
        # ========== METHOD LIBRARY INTEGRATION ==========
        # Persistent storage for successful HDDL methods
        method_library_path = config.get("method_library_path", "./results/panda-results/method_library.json") if config else "./results/panda-results/method_library.json"
        
        try:
            self.method_library = PANDAMethodLibrary(storage_path=method_library_path)
            logger.info(f"[DECOMP] Method library loaded with {self.method_library.get_statistics()['total_methods']} methods")
        except Exception as e:
            logger.warning(f"[DECOMP] Failed to initialize PANDAMethodLibrary: {e}")
            self.method_library = None
        
        # Enable/disable LLM feedback loop for validation errors
        self.enable_llm_feedback_loop = config.get("enable_llm_feedback_loop", True) if config else True

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
            "domain_registry_hits": 0,
            "domain_registry_misses": 0,
            "llm_feedback_corrections": 0,
            "methods_stored": 0,
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
        stats = {
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
            "domain_registry_hit_rate": (
                self.stats["domain_registry_hits"]
                / (self.stats["domain_registry_hits"] + self.stats["domain_registry_misses"])
            )
            if (self.stats["domain_registry_hits"] + self.stats["domain_registry_misses"]) > 0
            else 0.0,
        }
        
        # Add domain registry statistics if available
        if self.domain_registry:
            stats["domain_registry"] = self.domain_registry.get_statistics()
        
        # Add method library statistics if available
        if self.method_library:
            stats["method_library"] = self.method_library.get_statistics()
        
        return stats
    
    # ========== PANDA Integration Methods ==========
    
    async def process_with_panda_validation(self, input_data: Dict) -> Dict:
        """
        Enhanced process method with PANDA validation loop and domain registry
        
        Workflow:
        1. CHECK DOMAIN REGISTRY FIRST - if domain exists, skip LLM entirely
        2. Generate HDDL methods using LLM
        3. Validate with PANDA parser
        4. If invalid and feedback loop enabled, feed errors back to LLM for correction
        5. If all attempts fail, fallback to hand-coded domain
        6. PERSIST validated domain to registry for future reuse
        7. Store successful methods in method library
        8. Return validated HDDL domain + problem files
        
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
                "from_registry": bool,
                "error": str (if failed)
            }
        """
        start_time = datetime.now()
        
        task = input_data["task"]
        domain_name = input_data["domain"]
        
        logger.info(f"[PANDA] Starting validated decomposition for {task}")
        
        # ========== STEP 1: CHECK DOMAIN REGISTRY FIRST ==========
        # If domain exists in registry, skip LLM generation entirely (25x faster!)
        if self.domain_registry:
            existing_domain = self.domain_registry.lookup_domain(domain_name)
            
            if existing_domain:
                self.stats["domain_registry_hits"] += 1
                
                logger.success(
                    f"[REGISTRY] ★ Domain '{domain_name}' found in registry! "
                    f"Skipping LLM generation (used {existing_domain.usage_count} times, "
                    f"success_rate={existing_domain.success_rate:.2f})"
                )
                
                # Generate problem file for existing domain
                problem_result = await self._generate_problem_for_existing_domain(
                    domain_name=domain_name,
                    existing_domain=existing_domain,
                    task=task,
                    initial_state=input_data.get("initial_state"),
                    goal_tasks=input_data.get("goal_tasks", [(task, [])]),
                    objects=input_data.get("objects", {})
                )
                
                if problem_result["success"]:
                    problem_result["agent"] = self.name
                    problem_result["task"] = task
                    problem_result["domain"] = domain_name
                    problem_result["from_registry"] = True
                    problem_result["used_fallback"] = False
                    problem_result["validation_attempts"] = 0
                    problem_result["processing_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
                    
                    return problem_result
                else:
                    logger.warning(f"[REGISTRY] Problem generation failed for existing domain, proceeding to LLM")
            else:
                self.stats["domain_registry_misses"] += 1
                logger.debug(f"[REGISTRY] Domain '{domain_name}' not in registry, proceeding to LLM generation")
        
        # ========== STEP 2: LLM GENERATION WITH VALIDATION LOOP ==========
        last_validation_errors = []
        last_hddl_text = ""
        
        for attempt in range(1, self.max_validation_attempts + 1):
            logger.info(f"[PANDA] Validation attempt {attempt}/{self.max_validation_attempts}")
            
            # Check if this is a retry with validation errors (LLM feedback loop)
            if attempt > 1 and last_validation_errors and self.enable_llm_feedback_loop:
                logger.info(f"[FEEDBACK] Attempting LLM correction based on {len(last_validation_errors)} validation errors")
                
                # Use LLM feedback loop to correct the HDDL
                correction_result = await self._llm_correct_hddl(
                    domain_name=domain_name,
                    original_hddl=last_hddl_text,
                    validation_errors=last_validation_errors,
                    attempt_number=attempt
                )
                
                if correction_result["success"]:
                    self.stats["llm_feedback_corrections"] += 1
                    
                    # Persist to registry and return
                    await self._persist_and_return(
                        correction_result, domain_name, task, start_time,
                        input_data.get("operators", []), attempt
                    )
                    
                    return correction_result
                else:
                    logger.warning(f"[FEEDBACK] LLM correction failed: {correction_result.get('error')}")
                    last_validation_errors = correction_result.get("validation_errors", [])
                    last_hddl_text = correction_result.get("hddl_text", "")
                    continue
            
            # Generate methods using LLM
            decomposition_result = await self.process(input_data)
            
            if not decomposition_result["success"]:
                logger.warning(f"[PANDA] LLM decomposition failed: {decomposition_result.get('error')}")
                continue
            
            # Convert methods to HDDL and validate
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
                logger.success(f"[PANDA] Validation successful on attempt {attempt}")
                
                # ========== STEP 3: PERSIST TO DOMAIN REGISTRY ==========
                await self._persist_validated_domain(
                    domain_name=domain_name,
                    hddl_result=hddl_result,
                    methods_data=decomposition_result,
                    attempt_number=attempt
                )
                
                # Add metadata
                hddl_result["agent"] = self.name
                hddl_result["task"] = task
                hddl_result["domain"] = domain_name
                hddl_result["used_fallback"] = False
                hddl_result["from_registry"] = False
                hddl_result["validation_attempts"] = attempt
                hddl_result["processing_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
                
                return hddl_result
            else:
                logger.warning(f"[PANDA] Validation failed: {hddl_result.get('error')}")
                
                # Store errors for feedback loop
                last_validation_errors = hddl_result.get("validation_errors", [])
                last_hddl_text = hddl_result.get("hddl_text", "")
                
                # Update input_data with feedback for next attempt
                if "context" not in input_data:
                    input_data["context"] = {}
                input_data["context"]["validation_feedback"] = last_validation_errors
        
        # ========== STEP 4: HAND-CODED FALLBACK ==========
        logger.warning(f"[PANDA] All {self.max_validation_attempts} LLM attempts failed, using hand-coded fallback")
        
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
            fallback_result["from_registry"] = False
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
            "from_registry": False,
            "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
    
    async def _generate_problem_for_existing_domain(
        self,
        domain_name: str,
        existing_domain,
        task: str,
        initial_state,
        goal_tasks: List[Tuple[str, List[str]]],
        objects: Dict[str, str]
    ) -> Dict:
        """
        Generate problem file for a domain already in registry
        
        Args:
            domain_name: Domain name
            existing_domain: RegisteredDomain from registry
            task: Task name
            initial_state: Initial state
            goal_tasks: Goal tasks
            objects: Object declarations
        
        Returns:
            Result dict with domain and problem file paths
        """
        try:
            # Generate HDDL problem
            hddl_problem = self.hddl_generator.generate_problem(
                problem_name=f"{domain_name}_problem",
                domain_name=domain_name,
                init_state=initial_state,
                goal_tasks=goal_tasks,
                objects=objects
            )
            
            # Save to the same domain directory
            domain_dir = Path(existing_domain.domain_file).parent
            problem_file = domain_dir / "problem.hddl"
            
            self.hddl_generator.save_problem(hddl_problem, str(problem_file))
            
            # Validate the combination
            if self.panda_wrapper:
                validation_result = self.panda_wrapper.validate_hddl(
                    domain_file=existing_domain.domain_file,
                    problem_file=str(problem_file)
                )
                
                if not validation_result.is_valid:
                    return {
                        "success": False,
                        "error": f"Problem validation failed with existing domain: {validation_result.syntax_errors}"
                    }
            
            return {
                "success": True,
                "hddl_domain_file": existing_domain.domain_file,
                "hddl_problem_file": str(problem_file),
                "hddl_problem": hddl_problem,
                "validation_warnings": []
            }
            
        except Exception as e:
            logger.error(f"[REGISTRY] Failed to generate problem for existing domain: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _llm_correct_hddl(
        self,
        domain_name: str,
        original_hddl: str,
        validation_errors: List[str],
        attempt_number: int
    ) -> Dict:
        """
        Use LLM to correct HDDL based on validation errors
        
        This implements the LLM feedback loop:
        1. Take the original HDDL that failed validation
        2. Send it to LLM with the specific errors
        3. LLM generates corrected HDDL
        4. Validate the corrected version
        
        Args:
            domain_name: Domain name
            original_hddl: The HDDL text that failed validation
            validation_errors: List of error messages from PANDA
            attempt_number: Current attempt number
        
        Returns:
            Result dict with corrected HDDL or error
        """
        if not self.llm_client and not self.fallback_client:
            return {
                "success": False,
                "error": "No LLM client available for feedback correction"
            }
        
        client = self.llm_client or self.fallback_client
        
        try:
            # Build correction prompt
            system_prompt, user_prompt = build_hddl_correction_prompt(
                original_hddl=original_hddl,
                validation_errors=validation_errors
            )
            
            logger.info(f"[FEEDBACK] Sending {len(validation_errors)} errors to LLM for correction")
            
            # Generate corrected HDDL
            response = await asyncio.to_thread(
                client.generate,
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more deterministic correction
                max_tokens=self.max_tokens
            )
            
            corrected_hddl = response.content.strip()
            
            # Remove any markdown code blocks if present
            if corrected_hddl.startswith("```"):
                lines = corrected_hddl.split("\n")
                corrected_hddl = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
            # Save corrected HDDL to organized temp directory
            temp_dir = Path("./results/panda-results/panda-temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            domain_file = str(temp_dir / f"panda_{domain_name}_corrected_{attempt_number}.hddl")
            with open(domain_file, 'w') as f:
                f.write(corrected_hddl)
            
            # Generate a basic problem file
            problem_file = str(temp_dir / f"panda_{domain_name}_problem_{attempt_number}.hddl")
            
            # Validate with PANDA
            if self.panda_wrapper:
                validation_result = self.panda_wrapper.validate_hddl(
                    domain_file=domain_file,
                    problem_file=problem_file
                )
                
                self.stats["panda_validations"] += 1
                
                if validation_result.is_valid:
                    logger.success(f"[FEEDBACK] LLM correction succeeded!")
                    
                    return {
                        "success": True,
                        "hddl_domain_file": domain_file,
                        "hddl_problem_file": problem_file,
                        "hddl_text": corrected_hddl,
                        "validation_warnings": validation_result.warnings,
                        "corrected_by_feedback": True
                    }
                else:
                    self.stats["panda_validation_failures"] += 1
                    
                    return {
                        "success": False,
                        "error": "Corrected HDDL still failed validation",
                        "validation_errors": validation_result.syntax_errors + validation_result.semantic_errors,
                        "hddl_text": corrected_hddl
                    }
            else:
                # No PANDA wrapper, assume success
                return {
                    "success": True,
                    "hddl_domain_file": domain_file,
                    "hddl_problem_file": problem_file,
                    "hddl_text": corrected_hddl,
                    "validation_warnings": [],
                    "corrected_by_feedback": True
                }
                
        except Exception as e:
            logger.error(f"[FEEDBACK] LLM correction failed: {e}")
            return {
                "success": False,
                "error": f"LLM correction failed: {str(e)}"
            }
    
    async def _persist_validated_domain(
        self,
        domain_name: str,
        hddl_result: Dict,
        methods_data: Dict,
        attempt_number: int
    ) -> None:
        """
        Persist validated domain to registry and store methods in library
        
        Args:
            domain_name: Domain name
            hddl_result: Result dict from validation
            methods_data: Methods data from LLM
            attempt_number: Attempt number (for stats)
        """
        if not self.domain_registry:
            return
        
        try:
            temp_domain_file = hddl_result.get("hddl_domain_file", "")
            temp_problem_file = hddl_result.get("hddl_problem_file", "")
            
            # Persist files from /tmp to ./src/domains/
            persisted_files = self.domain_registry.persist_domain_files(
                domain_name=domain_name,
                temp_domain_file=temp_domain_file,
                temp_problem_file=temp_problem_file
            )
            
            # Update result with persistent paths
            hddl_result["hddl_domain_file"] = persisted_files["domain_file"]
            if persisted_files.get("problem_file"):
                hddl_result["hddl_problem_file"] = persisted_files["problem_file"]
            
            # Count methods and actions
            methods = methods_data.get("methods", [])
            method_count = len(methods)
            
            # Register in registry
            llm_provider = None
            if self.llm_client:
                llm_provider = self.llm_client.__class__.__name__
            
            self.domain_registry.register_domain(
                domain_name=domain_name,
                domain_file=persisted_files["domain_file"],
                problem_file=persisted_files.get("problem_file"),
                method_count=method_count,
                source="llm_generated",
                llm_provider=llm_provider,
                panda_validated=True,
                validation_warnings=hddl_result.get("validation_warnings", [])
            )
            
            logger.success(
                f"[REGISTRY] ★ Persisted domain '{domain_name}' to {persisted_files['domain_file']} "
                f"(methods={method_count})"
            )
            
            # Mark as persisted in the result
            hddl_result["persisted"] = True
            
            # ========== STORE METHODS IN METHOD LIBRARY ==========
            if self.method_library and methods:
                for method in methods:
                    try:
                        # Generate HDDL text for this method
                        hddl_text = self._method_to_hddl(method, domain_name)
                        
                        self.method_library.store_method(
                            domain=domain_name,
                            task_name=method.get("task_name", method.get("task", "unknown")),
                            method_name=method.get("name", "unnamed_method"),
                            hddl_text=hddl_text,
                            parameters=method.get("parameters", {}),
                            preconditions=method.get("preconditions", []),
                            subtasks=method.get("subtasks", []),
                            ordering=method.get("ordering", [])
                        )
                        self.stats["methods_stored"] += 1
                        
                    except Exception as e:
                        logger.warning(f"[METHOD_LIB] Failed to store method: {e}")
                
                logger.info(f"[METHOD_LIB] Stored {len(methods)} methods for domain '{domain_name}'")
            
        except Exception as e:
            logger.error(f"[REGISTRY] Failed to persist domain: {e}")
    
    def _method_to_hddl(self, method: Dict, domain_name: str) -> str:
        """
        Convert a method dict to HDDL text
        
        Args:
            method: Method dictionary
            domain_name: Domain name
        
        Returns:
            HDDL method text
        """
        name = method.get("name", "unnamed_method")
        task_name = method.get("task_name", method.get("task", "unknown_task"))
        params = method.get("parameters", {})
        preconditions = method.get("preconditions", [])
        subtasks = method.get("subtasks", [])
        
        # Format parameters
        params_str = " ".join([f"?{p}" for p in params.keys()]) if isinstance(params, dict) else ""
        
        # Format preconditions
        if preconditions:
            if len(preconditions) == 1:
                precond_str = f"({preconditions[0]})"
            else:
                precond_str = "(and " + " ".join([f"({p})" for p in preconditions]) + ")"
        else:
            precond_str = "()"
        
        # Format subtasks
        if subtasks:
            if len(subtasks) == 1:
                subtask = subtasks[0]
                if isinstance(subtask, dict):
                    subtasks_str = f"({subtask.get('name', subtask.get('task', 'unknown'))})"
                else:
                    subtasks_str = f"({subtask})"
            else:
                subtask_parts = []
                for st in subtasks:
                    if isinstance(st, dict):
                        subtask_parts.append(f"({st.get('name', st.get('task', 'unknown'))})")
                    else:
                        subtask_parts.append(f"({st})")
                subtasks_str = "(and " + " ".join(subtask_parts) + ")"
        else:
            subtasks_str = "()"
        
        return f"""(:method {name}
  :parameters ({params_str})
  :task ({task_name})
  :precondition {precond_str}
  :subtasks {subtasks_str}
)"""
    
    async def _persist_and_return(
        self,
        result: Dict,
        domain_name: str,
        task: str,
        start_time: datetime,
        operators: List,
        attempt: int
    ) -> Dict:
        """Helper to persist domain and format return"""
        await self._persist_validated_domain(
            domain_name=domain_name,
            hddl_result=result,
            methods_data={"methods": []},
            attempt_number=attempt
        )
        
        result["agent"] = self.name
        result["task"] = task
        result["domain"] = domain_name
        result["used_fallback"] = False
        result["from_registry"] = False
        result["validation_attempts"] = attempt
        result["processing_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
        
        return result
    
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
                "hddl_text": str,  # For feedback loop
                "validation_errors": [...],
                "error": str (if failed)
            }
        """
        hddl_text = ""
        
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
            
            # Store HDDL text for feedback loop
            hddl_text = hddl_domain.hddl_text if hasattr(hddl_domain, 'hddl_text') else str(hddl_domain)
            
            # Generate HDDL problem
            hddl_problem = self.hddl_generator.generate_problem(
                problem_name=f"{domain_name}_problem_{attempt_number}",
                domain_name=domain_name,
                init_state=initial_state,
                goal_tasks=goal_tasks,
                objects=objects
            )
            
            # Save to organized temp directory (under results for persistence)
            temp_dir = Path("./results/panda-results/panda-temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            domain_file = str(temp_dir / f"panda_{domain_name}_{attempt_number}.hddl")
            problem_file = str(temp_dir / f"panda_{domain_name}_problem_{attempt_number}.hddl")
            
            self.hddl_generator.save_domain(hddl_domain, domain_file)
            self.hddl_generator.save_problem(hddl_problem, problem_file)
            
            # Read back the HDDL text if not already captured
            if not hddl_text:
                try:
                    with open(domain_file, 'r') as f:
                        hddl_text = f.read()
                except Exception:
                    pass
            
            # Validate with PANDA parser
            if self.panda_wrapper:
                validation_result = self.panda_wrapper.validate_hddl(
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
                        "hddl_text": hddl_text,
                        "methods": methods_data.get("methods", []),
                        "validation_warnings": validation_result.warnings,
                        "persisted": False  # Will be set to True after _persist_validated_domain
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
                        "hddl_text": hddl_text,
                        "error": "PANDA validation failed"
                    }
            else:
                # No PANDA wrapper available, return as success without validation
                logger.warning("[PANDA] No PANDA wrapper available, skipping validation")
                return {
                    "success": True,
                    "hddl_domain_file": domain_file,
                    "hddl_problem_file": problem_file,
                    "hddl_domain": hddl_domain,
                    "hddl_problem": hddl_problem,
                    "hddl_text": hddl_text,
                    "methods": methods_data.get("methods", []),
                    "validation_warnings": ["PANDA validation skipped - no wrapper available"]
                }
        
        except Exception as e:
            logger.error(f"[PANDA] HDDL generation/validation error: {e}")
            return {
                "success": False,
                "hddl_text": hddl_text,
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
            
            temp_dir = Path("./results/panda-results/panda-temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            problem_file = str(temp_dir / f"panda_{domain_name}_fallback_problem.hddl")
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
            return {"success": False, "error": str(e)}

    # ========== DOMAIN TEMPLATE SELECTION ==========
    
    def _load_domain_templates(self, templates_path: str):
        """Load domain templates configuration"""
        try:
            templates_file = Path(templates_path)
            if templates_file.exists():
                with open(templates_file, 'r') as f:
                    self.domain_templates = json.load(f)
                logger.info(f"[TEMPLATE] Loaded {len(self.domain_templates.get('templates', {}))} domain templates")
            else:
                logger.warning(f"[TEMPLATE] Template file not found: {templates_path}, using empty templates")
                self.domain_templates = {"templates": {}, "fallback_template": "graph_traversal"}
        except Exception as e:
            logger.error(f"[TEMPLATE] Failed to load templates: {e}")
            self.domain_templates = {"templates": {}, "fallback_template": "graph_traversal"}
    
    def select_domain_template(self, problem_description: str, domain_hint: str = None) -> Dict:
        """
        Analyze problem and select best matching domain template.
        
        Args:
            problem_description: Natural language problem description
            domain_hint: Optional domain name hint (e.g., "graph_traversal")
            
        Returns:
            {
                "success": bool,
                "template_name": str,
                "domain_path": str,
                "problem_path": str,
                "confidence": float,
                "reasoning": str
            }
        """
        templates = self.domain_templates.get("templates", {})
        
        if not templates:
            return {
                "success": False,
                "error": "No domain templates available"
            }
        
        # If domain hint matches template exactly, use it
        if domain_hint and domain_hint in templates:
            template = templates[domain_hint]
            logger.info(f"[TEMPLATE] Using exact domain match: {domain_hint}")
            return {
                "success": True,
                "template_name": domain_hint,
                "domain_path": template["domain_path"],
                "problem_path": template["problem_path"],
                "confidence": 1.0,
                "reasoning": f"Exact domain match: {domain_hint}"
            }
        
        # Score each template based on keyword matching
        problem_lower = problem_description.lower()
        scores = {}
        
        for template_name, template_data in templates.items():
            score = 0.0
            matched_keywords = []
            
            # Check keywords
            for keyword in template_data.get("keywords", []):
                if keyword.lower() in problem_lower:
                    score += 1.0
                    matched_keywords.append(keyword)
            
            # Check problem patterns
            for pattern in template_data.get("problem_patterns", []):
                if pattern.lower() in problem_lower:
                    score += 2.0  # Patterns weigh more
                    matched_keywords.append(f"pattern:{pattern}")
            
            scores[template_name] = {
                "score": score,
                "matched": matched_keywords
            }
        
        # Select best match
        if not scores or all(s["score"] == 0 for s in scores.values()):
            # No matches, use fallback
            fallback = self.domain_templates.get("fallback_template", "graph_traversal")
            if fallback in templates:
                logger.warning(f"[TEMPLATE] No keyword matches, using fallback: {fallback}")
                template = templates[fallback]
                return {
                    "success": True,
                    "template_name": fallback,
                    "domain_path": template["domain_path"],
                    "problem_path": template["problem_path"],
                    "confidence": 0.3,
                    "reasoning": "No keyword matches, using fallback template"
                }
        
        # Get best match
        best_match = max(scores.items(), key=lambda x: x[1]["score"])
        template_name = best_match[0]
        match_data = best_match[1]
        template = templates[template_name]
        
        confidence = min(match_data["score"] / 3.0, 1.0)  # Normalize to 0-1
        
        logger.success(f"[TEMPLATE] Selected '{template_name}' (score={match_data['score']:.1f}, confidence={confidence:.2f})")
        logger.debug(f"[TEMPLATE] Matched keywords: {match_data['matched']}")
        
        return {
            "success": True,
            "template_name": template_name,
            "domain_path": template["domain_path"],
            "problem_path": template["problem_path"],
            "confidence": confidence,
            "reasoning": f"Matched {len(match_data['matched'])} keywords/patterns: {', '.join(match_data['matched'][:3])}"
        }
        return {
                "success": False,
                "error": f"Fallback failed: {str(e)}"
        }