"""
PANDA Workflow Orchestrator
Complete neuro-symbolic HTN planning pipeline integrating all 5 agents with PANDA framework

Enhanced with:
- DomainRegistry integration for persistent domain learning
- Automatic domain reuse across workflow executions
- Statistics tracking for domain usage
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from ..planning_agent import PlanningAgent
from ..decomposition_agent import DecompositionAgent
from ..execution_agent import ExecutionAgent
from ..verification_agent import VerificationAgent
from ..context_agent import ContextAgent
from ...integrations.panda_wrapper import PANDAWrapper, PlannerResult
from ...integrations.problem_cache import ProblemCache
from ...integrations.domain_registry import DomainRegistry
from ...integrations.panda_method_library import PANDAMethodLibrary
from ...memory.similarity_search import SimilaritySearch, SimilarProblem
from ...core.state_manager import State


class PANDAWorkflow:
    """
    Complete Neuro-Symbolic HTN Planning Workflow
    
    Pipeline:
    1. PlanningAgent → Strategic analysis and approach selection
    2. DecompositionAgent → LLM-generated HDDL + PANDA validation
    3. PANDAWrapper → Symbolic HTN planning
    4. ExecutionAgent → Hierarchical plan execution
    5. VerificationAgent → 4-layer validation
    6. ContextAgent → Method library storage + trace logging
    
    All LLM calls are REAL (Groq, Gemini, HuggingFace, Cohere, Ollama)
    """
    
    def __init__(
        self,
        planning_agent: PlanningAgent,
        decomposition_agent: DecompositionAgent,
        execution_agent: ExecutionAgent,
        verification_agent: VerificationAgent,
        context_agent: ContextAgent,
        panda_wrapper: PANDAWrapper,
        results_dir: str = "./results/panda-results",
        enable_cache: bool = True,
        enable_similarity: bool = True,
        similarity_threshold: float = 0.75
    ):
        """
        Initialize PANDA Workflow
        
        Args:
            planning_agent: Strategic planning agent (Groq Llama 70B)
            decomposition_agent: HDDL generation agent (Gemini/HF Llama 70B)
            execution_agent: Plan execution agent (Cohere + rules)
            verification_agent: Validation agent (HF Llama 8B + Gemini)
            context_agent: Memory and context tracking (Gemini 2.0)
            panda_wrapper: PANDA-HTN framework interface
            results_dir: Directory for saving results
            enable_cache: Enable problem caching for repeated queries
            enable_similarity: Enable similarity-based strategy hints
            similarity_threshold: Minimum similarity score for hints (0.0-1.0)
        """
        self.planning_agent = planning_agent
        self.decomposition_agent = decomposition_agent
        self.execution_agent = execution_agent
        self.verification_agent = verification_agent
        self.context_agent = context_agent
        self.panda_wrapper = panda_wrapper
        
        # Inject PANDA wrapper into agents that need it
        if not hasattr(decomposition_agent, 'panda_wrapper') or decomposition_agent.panda_wrapper is None:
            decomposition_agent.panda_wrapper = panda_wrapper
        if not hasattr(verification_agent, 'panda_wrapper') or verification_agent.panda_wrapper is None:
            verification_agent.panda_wrapper = panda_wrapper
        
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Problem Cache for recognizing repeated problems
        self.enable_cache = enable_cache
        if enable_cache:
            cache_path = str(self.results_dir / "problem_cache.json")
            self.problem_cache = ProblemCache(cache_path=cache_path)
        else:
            self.problem_cache = None
        
        # Similarity Search for strategy hints on cache miss
        self.enable_similarity = enable_similarity
        if enable_similarity:
            similarity_path = str(self.results_dir / "similarity_index")
            try:
                self.similarity_search = SimilaritySearch(
                    index_path=similarity_path,
                    similarity_threshold=similarity_threshold
                )
            except Exception as e:
                logger.warning(f"Failed to initialize SimilaritySearch: {e}")
                self.similarity_search = None
                self.enable_similarity = False
        else:
            self.similarity_search = None
        
        # ========== DOMAIN REGISTRY INTEGRATION ==========
        # Persistent storage for generated HDDL domains - enables domain reuse
        registry_path = str(self.results_dir / "domain_registry.json")
        domains_base_path = "./src/domains"
        
        try:
            self.domain_registry = DomainRegistry(
                registry_path=registry_path,
                domains_base_path=domains_base_path
            )
            # Scan existing domains on initialization
            scanned = self.domain_registry.scan_existing_domains()
            if scanned > 0:
                logger.info(f"[WORKFLOW] Scanned {scanned} existing domains into registry")
            
            logger.info(
                f"[WORKFLOW] DomainRegistry initialized with "
                f"{len(self.domain_registry.registry)} domains"
            )
        except Exception as e:
            logger.warning(f"[WORKFLOW] Failed to initialize DomainRegistry: {e}")
            self.domain_registry = None
        
        # ========== METHOD LIBRARY INTEGRATION ==========
        # Persistent storage for successful HDDL methods
        method_library_path = str(self.results_dir / "method_library.json")
        
        try:
            self.method_library = PANDAMethodLibrary(storage_path=method_library_path)
            logger.info(
                f"[WORKFLOW] PANDAMethodLibrary initialized with "
                f"{self.method_library.get_statistics()['total_methods']} methods"
            )
        except Exception as e:
            logger.warning(f"[WORKFLOW] Failed to initialize PANDAMethodLibrary: {e}")
            self.method_library = None
        
        # Workflow statistics
        self.stats = {
            "workflows_executed": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "similarity_hits": 0,
            "similarity_misses": 0,
            "domain_registry_hits": 0,
            "domain_registry_misses": 0,
            "avg_total_time_ms": 0.0,
            "avg_planning_time_ms": 0.0,
            "avg_panda_time_ms": 0.0,
            "avg_execution_time_ms": 0.0
        }
    
    async def execute_workflow(
        self,
        domain_name: str,
        problem_name: str,
        domain_file: str,
        problem_file: str,
        initial_state: State,
        goal_description: str,
        optimal_plan_length: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Execute complete neuro-symbolic HTN planning workflow
        
        Args:
            domain_name: Domain name (e.g., "graph_traversal")
            problem_name: Problem name (e.g., "incomplete-graph-p01")
            domain_file: Path to HDDL domain file
            problem_file: Path to HDDL problem file
            initial_state: Initial world state
            goal_description: Natural language goal description
            optimal_plan_length: Expected optimal plan length (for validation)
            session_id: Session identifier (generated if not provided)
        
        Returns:
            Complete workflow result with all agent outputs
        """
        workflow_start = datetime.now()
        session_id = session_id or f"session_{workflow_start.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info("=" * 80)
        logger.info(f"[WORKFLOW] Starting PANDA workflow for {domain_name}/{problem_name}")
        logger.info(f"[WORKFLOW] Session ID: {session_id}")
        logger.info("=" * 80)
        
        # =========== CACHE CHECK ===========
        # Check if we've solved this exact problem before
        if self.enable_cache and self.problem_cache:
            initial_state_dict = initial_state.to_dict() if hasattr(initial_state, 'to_dict') else {}
            cached = self.problem_cache.check_cache(
                domain=domain_name,
                initial_state=initial_state_dict,
                goal_description=goal_description
            )
            
            if cached:
                self.stats["cache_hits"] += 1
                
                # EXPLICIT CACHE HIT NOTIFICATION
                print("\n" + "=" * 80)
                print("★ ★ ★  CACHE HIT: PLAN ALREADY EXISTS FOR THIS PROBLEM  ★ ★ ★")
                print("=" * 80)
                print(f"  Problem: {problem_name}")
                print(f"  Domain:  {domain_name}")
                print(f"  Cached Signature: {cached.signature}")
                print(f"  Original Solution Time: {cached.total_time_ms:.1f}ms")
                print(f"  Cache Hit Count: {cached.hit_count}")
                print(f"  Cached Actions: {len(cached.plan_actions)}")
                for i, action in enumerate(cached.plan_actions, 1):
                    print(f"    {i}. {action.get('name', '?')}({', '.join(action.get('parameters', []))})")
                print("=" * 80)
                print("  → Skipping LLM calls and PANDA planning (reusing cached solution)")
                print("=" * 80 + "\n")
                
                logger.success(
                    f"[WORKFLOW] ★ CACHE HIT - Reusing solution for '{problem_name}' "
                    f"(saved ~{cached.total_time_ms:.0f}ms)"
                )
                
                # Return cached result with updated session_id
                cached_result = cached.solution.copy()
                cached_result["session_id"] = session_id
                cached_result["timestamp"] = workflow_start.isoformat()
                cached_result["from_cache"] = True
                cached_result["cache_signature"] = cached.signature
                cached_result["original_time_ms"] = cached.total_time_ms
                cached_result["total_time_ms"] = (datetime.now() - workflow_start).total_seconds() * 1000
                
                return cached_result
            else:
                self.stats["cache_misses"] += 1
        # ===================================
        
        # =========== SIMILARITY SEARCH ===========
        # Check for similar problems to get strategy hints
        similar_problems: List[SimilarProblem] = []
        strategy_hints: List[Dict] = []
        
        if self.enable_similarity and self.similarity_search:
            try:
                initial_state_dict = initial_state.to_dict() if hasattr(initial_state, 'to_dict') else {}
                similar_problems = self.similarity_search.find_similar(
                    domain=domain_name,
                    goal=goal_description,
                    init_state=initial_state_dict,
                    top_k=3
                )
                
                if similar_problems:
                    self.stats["similarity_hits"] += 1
                    # Extract strategies from top 2 similar problems
                    for sp in similar_problems[:2]:
                        strategy_hints.extend(sp.strategies)
                    
                    print("\n" + "-" * 60)
                    print("◆ SIMILARITY MATCH: Found similar solved problems")
                    print("-" * 60)
                    for i, sp in enumerate(similar_problems, 1):
                        print(f"  {i}. {sp.problem_id} (similarity: {sp.similarity_score:.3f})")
                        print(f"     Domain: {sp.domain}, Plan length: {sp.plan_length}")
                    print("-" * 60)
                    print(f"  → Using {len(strategy_hints)} strategy hints for planning")
                    print("-" * 60 + "\n")
                    
                    logger.info(
                        f"[SIMILARITY] Found {len(similar_problems)} similar problems, "
                        f"using {len(strategy_hints)} strategy hints"
                    )
                else:
                    self.stats["similarity_misses"] += 1
                    logger.debug("[SIMILARITY] No similar problems found above threshold")
            except Exception as e:
                logger.warning(f"[SIMILARITY] Error during similarity search: {e}")
                self.stats["similarity_misses"] += 1
        # =========================================
        
        workflow_result = {
            "session_id": session_id,
            "domain": domain_name,
            "problem": problem_name,
            "timestamp": workflow_start.isoformat(),
            "phases": {},
            "success": False,
            "error": None,
            "from_cache": False,
            "similarity_hints_used": len(strategy_hints) > 0,
            "similar_problems_found": len(similar_problems)
        }
        
        try:
            # Phase 1: Strategic Planning
            logger.info("[WORKFLOW] Phase 1: Strategic Analysis")
            planning_result = await self._phase1_planning(
                domain_name=domain_name,
                goal_description=goal_description,
                initial_state=initial_state,
                strategy_hints=strategy_hints
            )
            workflow_result["phases"]["planning"] = planning_result
            
            if not planning_result["success"]:
                workflow_result["error"] = "Planning phase failed"
                return await self._finalize_workflow(workflow_result, workflow_start)
            
            # Phase 2: HDDL Generation + PANDA Validation
            logger.info("[WORKFLOW] Phase 2: HDDL Generation & Validation")
            decomposition_result = await self._phase2_decomposition_validation(
                domain_name=domain_name,
                domain_file=domain_file,
                problem_file=problem_file,
                planning_strategies=planning_result.get("strategies", [])
            )
            workflow_result["phases"]["decomposition"] = decomposition_result
            
            if not decomposition_result["success"]:
                workflow_result["error"] = "HDDL generation/validation failed"
                return await self._finalize_workflow(workflow_result, workflow_start)
            
            # Phase 3: PANDA HTN Planning
            logger.info("[WORKFLOW] Phase 3: PANDA HTN Planning")
            panda_result = await self._phase3_panda_planning(
                domain_file=decomposition_result["hddl_domain_file"],
                problem_file=decomposition_result["hddl_problem_file"],
                session_id=session_id,
                task_name=problem_name
            )
            workflow_result["phases"]["panda_planning"] = panda_result
            
            if not panda_result["success"]:
                workflow_result["error"] = "PANDA planning failed"
                return await self._finalize_workflow(workflow_result, workflow_start)
            
            # Phase 4: Plan Execution
            logger.info("[WORKFLOW] Phase 4: Plan Execution")
            execution_result = await self._phase4_execution(
                panda_plan=panda_result["panda_plan"],
                initial_state=initial_state,
                domain_name=domain_name
            )
            workflow_result["phases"]["execution"] = execution_result
            
            if not execution_result["success"]:
                workflow_result["error"] = "Execution failed"
                # Continue to validation even if execution failed (for debugging)
            
            # Phase 5: 4-Layer Validation
            logger.info("[WORKFLOW] Phase 5: 4-Layer Validation")
            validation_result = await self._phase5_validation(
                domain_file=decomposition_result["hddl_domain_file"],
                problem_file=decomposition_result["hddl_problem_file"],
                panda_plan=panda_result["panda_plan"],
                execution_trace=execution_result.get("execution_trace", []),
                final_state=execution_result.get("final_state", {}),
                goal_description=goal_description,
                optimal_plan_length=optimal_plan_length
            )
            workflow_result["phases"]["validation"] = validation_result
            
            # Phase 6: Store Results in Context/Memory
            logger.info("[WORKFLOW] Phase 6: Store in Memory")
            storage_result = await self._phase6_store_results(
                session_id=session_id,
                domain_name=domain_name,
                problem_name=problem_name,
                decomposition_result=decomposition_result,
                panda_result=panda_result,
                validation_result=validation_result
            )
            workflow_result["phases"]["storage"] = storage_result
            
            # Determine overall success
            workflow_result["success"] = (
                planning_result["success"] and
                decomposition_result["success"] and
                panda_result["success"] and
                validation_result["success"]
            )
            
            if workflow_result["success"]:
                self.stats["successful_workflows"] += 1
                logger.success("[WORKFLOW] ✓ Workflow completed successfully")
                
                # =========== CACHE STORE ===========
                # Store successful solution for future reuse
                if self.enable_cache and self.problem_cache:
                    initial_state_dict = initial_state.to_dict() if hasattr(initial_state, 'to_dict') else {}
                    total_time_ms = (datetime.now() - workflow_start).total_seconds() * 1000
                    
                    self.problem_cache.store_solution(
                        domain=domain_name,
                        problem_name=problem_name,
                        initial_state=initial_state_dict,
                        goal_description=goal_description,
                        solution=workflow_result,
                        plan_actions=panda_result.get("actions", []),
                        strategies=planning_result.get("strategies", []),
                        total_time_ms=total_time_ms,
                        panda_search_time_ms=panda_result.get("search_time_ms", 0.0)
                    )
                # ===================================
                
                # =========== SIMILARITY INDEX STORE ===========
                # Store in similarity index for future strategy hints
                if self.enable_similarity and self.similarity_search:
                    try:
                        initial_state_dict = initial_state.to_dict() if hasattr(initial_state, 'to_dict') else {}
                        self.similarity_search.add_solved_problem(
                            problem_id=f"{domain_name}_{problem_name}",
                            domain=domain_name,
                            goal=goal_description,
                            init_state=initial_state_dict,
                            strategies=planning_result.get("strategies", []),
                            plan_actions=panda_result.get("actions", [])
                        )
                        
                        # Record success for any similar problems that provided hints
                        if similar_problems:
                            for sp in similar_problems[:2]:
                                self.similarity_search.record_success(sp.problem_id)
                    except Exception as e:
                        logger.warning(f"[SIMILARITY] Failed to store in index: {e}")
                # ==============================================
                
                # =========== DOMAIN REGISTRY UPDATE ===========
                # Update success statistics for the domain
                if self.domain_registry:
                    try:
                        self.domain_registry.update_success(domain_name, success=True)
                        
                        # Track if this was from registry
                        if decomposition_result.get("from_registry"):
                            self.stats["domain_registry_hits"] += 1
                            workflow_result["domain_from_registry"] = True
                        else:
                            self.stats["domain_registry_misses"] += 1
                            workflow_result["domain_from_registry"] = False
                            
                    except Exception as e:
                        logger.warning(f"[REGISTRY] Failed to update success: {e}")
                # =============================================
                
                # =========== METHOD LIBRARY AUTO-POPULATE ===========
                # Store successful methods for future reuse
                if self.method_library and decomposition_result.get("methods"):
                    try:
                        methods = decomposition_result.get("methods", [])
                        for method in methods:
                            # Generate HDDL text for this method
                            hddl_text = self._method_to_hddl_text(method, domain_name)
                            
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
                        
                        if methods:
                            logger.info(f"[METHOD_LIB] Stored {len(methods)} methods for domain '{domain_name}'")
                            
                    except Exception as e:
                        logger.warning(f"[METHOD_LIB] Failed to store methods: {e}")
                # ====================================================
            else:
                self.stats["failed_workflows"] += 1
                logger.warning(f"[WORKFLOW] ✗ Workflow completed with errors: {workflow_result['error']}")
                
                # Update domain registry with failure
                if self.domain_registry:
                    try:
                        self.domain_registry.update_success(domain_name, success=False)
                    except Exception as e:
                        logger.debug(f"[REGISTRY] Failed to update failure: {e}")
            
        except Exception as e:
            logger.error(f"[WORKFLOW] Fatal error: {e}", exc_info=True)
            workflow_result["error"] = f"Fatal error: {str(e)}"
            workflow_result["success"] = False
            self.stats["failed_workflows"] += 1
        
        return await self._finalize_workflow(workflow_result, workflow_start)
    
    async def _phase1_planning(
        self,
        domain_name: str,
        goal_description: str,
        initial_state: State,
        strategy_hints: Optional[List[Dict]] = None
    ) -> Dict:
        """Phase 1: Strategic Planning with PlanningAgent
        
        Args:
            domain_name: Domain name
            goal_description: Goal description
            initial_state: Initial world state
            strategy_hints: Optional strategy hints from similar problems
        """
        try:
            planning_input = {
                "task": goal_description,  # PlanningAgent expects "task" not "goal"
                "domain": domain_name,
                "goal": goal_description,
                "initial_state": initial_state.to_dict() if hasattr(initial_state, 'to_dict') else {},
                "context": {"workflow": "panda_integration"}
            }
            
            # Add strategy hints from similar problems if available
            if strategy_hints:
                planning_input["strategy_hints"] = strategy_hints
                planning_input["context"]["has_similarity_hints"] = True
                logger.info(f"[PHASE1] Using {len(strategy_hints)} strategy hints from similar problems")
            
            result = await self.planning_agent.process(planning_input)
            
            return {
                "success": result.get("success", False),
                "strategies": result.get("strategies", []),
                "reasoning": result.get("reasoning", ""),
                "processing_time_ms": result.get("processing_time_ms", 0.0),
                "llm_used": result.get("primary_llm", "Groq Llama 70B"),
                "used_similarity_hints": bool(strategy_hints)
            }
        except Exception as e:
            logger.error(f"Phase 1 error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _phase2_decomposition_validation(
        self,
        domain_name: str,
        domain_file: str,
        problem_file: str,
        planning_strategies: list
    ) -> Dict:
        """Phase 2: HDDL Generation with PANDA Validation Loop"""
        try:
            # Note: For hand-coded domains, we skip LLM generation
            # and use the existing HDDL files directly
            logger.info(f"Using existing HDDL files: {domain_file}, {problem_file}")
            
            # Validate existing HDDL files with PANDA
            validation_result = self.panda_wrapper.validate_hddl(
                domain_file=domain_file,
                problem_file=problem_file
            )
            
            if validation_result.is_valid:
                return {
                    "success": True,
                    "hddl_domain_file": domain_file,
                    "hddl_problem_file": problem_file,
                    "used_fallback": True,  # Using hand-coded domain
                    "validation_warnings": validation_result.warnings,
                    "method": "hand_coded_domain"
                }
            else:
                return {
                    "success": False,
                    "error": "HDDL validation failed",
                    "validation_errors": validation_result.syntax_errors + validation_result.semantic_errors
                }
        except Exception as e:
            logger.error(f"Phase 2 error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _phase3_panda_planning(
        self,
        domain_file: str,
        problem_file: str,
        session_id: str,
        task_name: str
    ) -> Dict:
        """Phase 3: PANDA HTN Planning"""
        try:
            # Use task_name or session_id for output file naming
            output_name = f"{session_id}_{task_name}"
            
            panda_plan = self.panda_wrapper.plan(
                domain_file=domain_file,
                problem_file=problem_file,
                output_name=output_name
            )
            
            return {
                "success": panda_plan.success,
                "panda_plan": panda_plan,
                "plan_length": panda_plan.plan_length if hasattr(panda_plan, 'plan_length') else 0,
                "search_time_ms": panda_plan.search_time_ms if hasattr(panda_plan, 'search_time_ms') else 0.0,
                "nodes_expanded": panda_plan.nodes_expanded if hasattr(panda_plan, 'nodes_expanded') else 0,
                "actions": panda_plan.actions if hasattr(panda_plan, 'actions') else [],
                "error": panda_plan.error
            }
        except Exception as e:
            logger.error(f"Phase 3 error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _phase4_execution(
        self,
        panda_plan,
        initial_state: State,
        domain_name: str
    ) -> Dict:
        """Phase 4: Execute PANDA Plan"""
        try:
            execution_result = await self.execution_agent.execute_panda_plan_from_wrapper(
                panda_plan_result=panda_plan,
                initial_state=initial_state.to_dict() if hasattr(initial_state, 'to_dict') else {},
                domain=domain_name
            )
            
            return execution_result
        except Exception as e:
            logger.error(f"Phase 4 error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _phase5_validation(
        self,
        domain_file: str,
        problem_file: str,
        panda_plan,
        execution_trace: list,
        final_state: dict,
        goal_description: str,
        optimal_plan_length: Optional[int]
    ) -> Dict:
        """Phase 5: 4-Layer Validation"""
        try:
            validation_result = await self.verification_agent.validate_panda_plan(
                domain_file=domain_file,
                problem_file=problem_file,
                panda_plan_result=panda_plan,
                optimal_plan_length=optimal_plan_length
            )
            
            return validation_result
        except Exception as e:
            logger.error(f"Phase 5 error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _phase6_store_results(
        self,
        session_id: str,
        domain_name: str,
        problem_name: str,
        decomposition_result: dict,
        panda_result: dict,
        validation_result: dict
    ) -> Dict:
        """Phase 6: Store in ContextAgent Memory"""
        try:
            # Store PANDA execution trace
            trace_result = await self.context_agent.process({
                "operation": "store_panda_trace",
                "data": {
                    "session_id": session_id,
                    "task_name": problem_name,
                    "domain": domain_name,
                    "plan": {
                        "plan_length": panda_result.get("plan_length", 0),
                        "search_time_ms": panda_result.get("search_time_ms", 0.0),
                        "nodes_expanded": panda_result.get("nodes_expanded", 0)
                    },
                    "result": "success" if validation_result.get("success") else "failure",
                    "execution_time_ms": panda_result.get("search_time_ms", 0.0)
                }
            })
            
            return {
                "success": trace_result.get("success", False),
                "trace_stored": trace_result.get("success", False)
            }
        except Exception as e:
            logger.error(f"Phase 6 error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _finalize_workflow(self, workflow_result: Dict, start_time: datetime) -> Dict:
        """Finalize workflow and save results"""
        total_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        workflow_result["total_time_ms"] = total_time_ms
        
        # Update statistics
        self.stats["workflows_executed"] += 1
        n = self.stats["workflows_executed"]
        self.stats["avg_total_time_ms"] = (
            self.stats["avg_total_time_ms"] * (n - 1) + total_time_ms
        ) / n
        
        # Save results to file
        result_file = self.results_dir / "agent_interactions" / f"{workflow_result['session_id']}_workflow.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(result_file, 'w') as f:
                json.dump(workflow_result, f, indent=2, default=str)
            logger.info(f"[WORKFLOW] Results saved to {result_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
        
        logger.info(f"[WORKFLOW] Total time: {total_time_ms:.1f}ms")
        logger.info("=" * 80)
        
        return workflow_result
    
    def _method_to_hddl_text(self, method: Dict, domain_name: str) -> str:
        """
        Convert a method dict to HDDL text format
        
        Args:
            method: Method dictionary with name, parameters, preconditions, subtasks
            domain_name: Domain name for context
        
        Returns:
            HDDL method text string
        """
        name = method.get("name", "unnamed_method")
        task_name = method.get("task_name", method.get("task", "unknown_task"))
        params = method.get("parameters", {})
        preconditions = method.get("preconditions", [])
        subtasks = method.get("subtasks", [])
        
        # Format parameters
        if isinstance(params, dict):
            params_str = " ".join([f"?{p}" for p in params.keys()])
        elif isinstance(params, list):
            params_str = " ".join([f"?{p}" for p in params])
        else:
            params_str = ""
        
        # Format preconditions
        if preconditions:
            if len(preconditions) == 1:
                precond_str = f"({preconditions[0]})"
            else:
                precond_str = "(and " + " ".join([f"({p})" if not p.startswith("(") else p for p in preconditions]) + ")"
        else:
            precond_str = "()"
        
        # Format subtasks
        if subtasks:
            subtask_parts = []
            for st in subtasks:
                if isinstance(st, dict):
                    st_name = st.get('name', st.get('task', 'unknown'))
                    st_params = st.get('parameters', [])
                    if st_params:
                        subtask_parts.append(f"({st_name} {' '.join(st_params)})")
                    else:
                        subtask_parts.append(f"({st_name})")
                elif isinstance(st, str):
                    if not st.startswith("("):
                        subtask_parts.append(f"({st})")
                    else:
                        subtask_parts.append(st)
            
            if len(subtask_parts) == 1:
                subtasks_str = subtask_parts[0]
            else:
                subtasks_str = "(and " + " ".join(subtask_parts) + ")"
        else:
            subtasks_str = "()"
        
        return f"""(:method {name}
  :parameters ({params_str})
  :task ({task_name})
  :precondition {precond_str}
  :subtasks {subtasks_str}
)"""
    
    def get_statistics(self) -> Dict:
        """Get workflow statistics including all memory systems"""
        stats = {
            **self.stats,
            "success_rate": (
                self.stats["successful_workflows"] / self.stats["workflows_executed"]
            ) if self.stats["workflows_executed"] > 0 else 0.0
        }
        
        # Add cache statistics if enabled
        if self.enable_cache and self.problem_cache:
            cache_stats = self.problem_cache.get_statistics()
            stats["cache"] = cache_stats
            stats["cache_hit_rate"] = (
                self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
            ) if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0.0
        
        # Add domain registry statistics
        if self.domain_registry:
            stats["domain_registry"] = self.domain_registry.get_statistics()
            stats["domain_registry_hit_rate"] = (
                self.stats["domain_registry_hits"] / 
                (self.stats["domain_registry_hits"] + self.stats["domain_registry_misses"])
            ) if (self.stats["domain_registry_hits"] + self.stats["domain_registry_misses"]) > 0 else 0.0
        
        # Add method library statistics
        if self.method_library:
            stats["method_library"] = self.method_library.get_statistics()
        
        # Add similarity search statistics
        if self.enable_similarity and self.similarity_search:
            try:
                stats["similarity_hit_rate"] = (
                    self.stats["similarity_hits"] /
                    (self.stats["similarity_hits"] + self.stats["similarity_misses"])
                ) if (self.stats["similarity_hits"] + self.stats["similarity_misses"]) > 0 else 0.0
            except Exception:
                pass
        
        return stats
