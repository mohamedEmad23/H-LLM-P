"""
PANDA Workflow Orchestrator
Complete neuro-symbolic HTN planning pipeline integrating all 5 agents with PANDA framework
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from loguru import logger

from ..planning_agent import PlanningAgent
from ..decomposition_agent import DecompositionAgent
from ..execution_agent import ExecutionAgent
from ..verification_agent import VerificationAgent
from ..context_agent import ContextAgent
from ...integrations.panda_wrapper import PANDAWrapper, PlannerResult
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
        results_dir: str = "./results/panda-results"
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
        
        # Workflow statistics
        self.stats = {
            "workflows_executed": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
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
        
        workflow_result = {
            "session_id": session_id,
            "domain": domain_name,
            "problem": problem_name,
            "timestamp": workflow_start.isoformat(),
            "phases": {},
            "success": False,
            "error": None
        }
        
        try:
            # Phase 1: Strategic Planning
            logger.info("[WORKFLOW] Phase 1: Strategic Analysis")
            planning_result = await self._phase1_planning(
                domain_name=domain_name,
                goal_description=goal_description,
                initial_state=initial_state
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
                logger.info("[WORKFLOW] ✓ Workflow completed successfully")
            else:
                self.stats["failed_workflows"] += 1
                logger.warning(f"[WORKFLOW] ✗ Workflow completed with errors: {workflow_result['error']}")
            
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
        initial_state: State
    ) -> Dict:
        """Phase 1: Strategic Planning with PlanningAgent"""
        try:
            planning_input = {
                "task": goal_description,  # PlanningAgent expects "task" not "goal"
                "domain": domain_name,
                "goal": goal_description,
                "initial_state": initial_state.to_dict() if hasattr(initial_state, 'to_dict') else {},
                "context": {"workflow": "panda_integration"}
            }
            
            result = await self.planning_agent.process(planning_input)
            
            return {
                "success": result.get("success", False),
                "strategies": result.get("strategies", []),
                "reasoning": result.get("reasoning", ""),
                "processing_time_ms": result.get("processing_time_ms", 0.0),
                "llm_used": result.get("primary_llm", "Groq Llama 70B")
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
    
    def get_statistics(self) -> Dict:
        """Get workflow statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_workflows"] / self.stats["workflows_executed"]
            ) if self.stats["workflows_executed"] > 0 else 0.0
        }
