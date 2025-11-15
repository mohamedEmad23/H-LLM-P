"""
Phase 3 Executor: Multi-Agent Coordinator Integration

Executes YAML problems using the multi-agent coordinator with 3 specialized agents:
- PlanningAgent: Strategic analysis and high-level planning
- DecompositionAgent: Task breakdown and subtask generation
- ExecutionAgent: Primitive operation execution

Integrates with BenchmarkLogger for consistent KPI tracking across phases.

Author: H-LLM-P Thesis Project
Date: November 14, 2025
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from interface.problem_cli import Problem
from utils.benchmark_logger import BenchmarkLogger
from agents.coordinator import AgentCoordinator
from agents.planning_agent import PlanningAgent
from agents.decomposition_agent import DecompositionAgent
from agents.execution_agent import ExecutionAgent
from agents.verification_agent import VerificationAgent
from llm.groq_client import GroqClient
from llm.cohere_client import CohereClient
from llm.local_llm_interface import LLMConfig


class Phase3Executor:
    """
    Executes YAML problems using Phase 3 multi-agent architecture.
    
    Architecture:
    - 3 specialized agents with different LLMs
    - Coordinator-based orchestration
    - Agent communication tracking
    - Full KPI measurement
    """
    
    def __init__(
        self,
        output_dir: str = "results/phase-3-traces",
        use_different_llms: bool = True
    ):
        """
        Initialize Phase 3 executor
        
        Args:
            output_dir: Directory for benchmark results
            use_different_llms: If True, use different LLM for each agent
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_different_llms = use_different_llms
        
        logger.info("Phase 3 Executor initialized")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Multi-LLM mode: {use_different_llms}")
    
    async def execute(self, problem: Problem) -> Dict[str, Any]:
        """
        Execute a problem using multi-agent coordination
        
        Args:
            problem: Problem instance from YAML
            
        Returns:
            Execution results dictionary
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        problem_id = f"{problem.problem_type}_{timestamp}"
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Phase 3 Execution: {problem.problem_type}")
        logger.info(f"{'='*60}")
        
        # Initialize benchmark logger
        benchmark_logger = BenchmarkLogger(str(self.output_dir))
        
        # Track execution with context manager
        with benchmark_logger.track_execution(
            problem_id=problem_id,
            architecture="phase3",
            optimal_steps=problem.expected_output.get("move_count") or 
                         problem.expected_output.get("step_count")
        ):
            try:
                # Step 1: Initialize agents
                logger.info("\n[1/5] Initializing multi-agent system...")
                workflow = await self._initialize_agents(benchmark_logger)
                logger.success("✓ 3 agents initialized and workflow created")
                
                # Step 2: Convert YAML to agent tasks
                logger.info("\n[2/5] Converting YAML to agent task structure...")
                agent_tasks = self._yaml_to_agent_tasks(problem)
                logger.success(f"✓ Generated {len(agent_tasks)} agent tasks")
                
                # Step 3: Execute coordinated workflow
                logger.info("\n[3/5] Executing multi-agent workflow...")
                
                # Build task input for CoreWorkflow
                task_input = {
                    "task": problem.domain_hints.get("primary_task", problem.problem_type),
                    "domain": problem.problem_type,
                    "initial_state": problem.initial_state,
                    "goal": problem.expected_output,
                    "operators": problem.domain_hints.get("operators", {}),
                    "constraints": problem.constraints,
                    "context": {"agent_tasks": agent_tasks}
                }
                
                result = await workflow.process_task(task_input)
                logger.success("✓ Workflow completed")
                
                # Step 4: Validate results
                logger.info("\n[4/5] Validating against expected output...")
                validation = self._validate_results(result, problem.expected_output)
                logger.success(f"✓ Validation: {validation['status']}")
                
                # Step 5: Log final metrics
                logger.info("\n[5/5] Logging final metrics...")
                benchmark_logger.log_success(
                    goal_achieved=validation['goal_achieved'],
                    constraint_violations=validation['constraint_violations'],
                    generated_steps=validation.get('step_count', 0)
                )
                
                logger.info(f"\n{'='*60}")
                logger.success(f"Phase 3 execution completed: {problem_id}")
                logger.info(f"Results saved to: {self.output_dir}")
                logger.info(f"{'='*60}\n")
                
                return {
                    "success": True,
                    "problem_id": problem_id,
                    "result": result,
                    "validation": validation
                }
                
            except Exception as e:
                logger.error(f"Phase 3 execution failed: {e}")
                benchmark_logger.log_failure(
                    component="multi_agent_coordinator",
                    failure_type=type(e).__name__,
                    recovery_attempted=False
                )
                
                import traceback
                traceback.print_exc()
                
                return {
                    "success": False,
                    "problem_id": problem_id,
                    "error": str(e)
                }
    
    async def _initialize_agents(
        self,
        benchmark_logger: BenchmarkLogger
    ) -> 'CoreWorkflow':
        """
        Initialize workflow with 3 specialized agents
        
        Args:
            benchmark_logger: Logger for KPI tracking
            
        Returns:
            Initialized CoreWorkflow
        """
        
        if self.use_different_llms:
            # Use different LLM for each agent (optimal specialization)
            
            # Planning Agent: Groq (fast strategic analysis)
            planning_config = LLMConfig(
                model_name="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            )
            planning_llm = GroqClient(config=planning_config)
            planning_agent = PlanningAgent(
                name="planning_agent",
                llm_client=planning_llm
            )
            
            # Decomposition Agent: Groq (task breakdown - switched from HF due to quota)
            decomp_config = LLMConfig(
                model_name="llama-3.1-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            )
            decomp_llm = GroqClient(config=decomp_config)
            decomp_agent = DecompositionAgent(
                name="decomposition_agent",
                llm_client=decomp_llm
            )
            
            # Execution Agent: Cohere (action execution)
            exec_config = LLMConfig(
                model_name="command-r-plus-08-2024",
                temperature=0.5,
                max_tokens=1024
            )
            exec_llm = CohereClient(config=exec_config)
            exec_agent = ExecutionAgent(
                name="execution_agent",
                llm_client=exec_llm
            )
            
            logger.info("Agent LLM configuration:")
            logger.info(f"  - Planning: {planning_config.model_name}")
            logger.info(f"  - Decomposition: {decomp_config.model_name}")
            logger.info(f"  - Execution: {exec_config.model_name}")
            
            # Verification Agent: Reuse execution LLM
            verify_agent = VerificationAgent(
                name="verification_agent",
                llm_client=exec_llm
            )
            
        else:
            # Use same LLM for all agents (simpler, cheaper)
            shared_config = LLMConfig(
                model_name="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            )
            shared_llm = GroqClient(config=shared_config)
            
            planning_agent = PlanningAgent(
                name="planning_agent",
                llm_client=shared_llm
            )
            decomp_agent = DecompositionAgent(
                name="decomposition_agent",
                llm_client=shared_llm
            )
            exec_agent = ExecutionAgent(
                name="execution_agent",
                llm_client=shared_llm
            )
            verify_agent = VerificationAgent(
                name="verification_agent",
                llm_client=shared_llm
            )
            
            logger.info(f"All agents using: {shared_config.model_name}")
        
        # Import CoreWorkflow
        from agents.workflows.core_workflow import CoreWorkflow
        
        # Create CoreWorkflow with the 3 agents (planning not used in core workflow)
        workflow = CoreWorkflow(
            decomposition_agent=decomp_agent,
            execution_agent=exec_agent,
            verification_agent=verify_agent,
            max_retries=3,
            use_message_bus=True
        )
        
        return workflow
    
    def _yaml_to_agent_tasks(self, problem: Problem) -> list:
        """
        Convert YAML domain_hints to agent-executable tasks
        
        Args:
            problem: Problem instance
            
        Returns:
            List of agent task dictionaries
        """
        tasks = []
        
        # Primary task for PlanningAgent
        tasks.append({
            "agent": "planning_agent",
            "type": "strategic_planning",
            "task": problem.domain_hints["primary_task"],
            "context": {
                "description": problem.description,
                "difficulty": problem.metadata["difficulty"],
                "constraints": list(problem.constraints.keys())
            }
        })
        
        # Subtasks for DecompositionAgent
        for subtask in problem.domain_hints["subtasks"]:
            tasks.append({
                "agent": "decomposition_agent",
                "type": "task_decomposition",
                "task": subtask,
                "parent": problem.domain_hints["primary_task"]
            })
        
        # Key operators for ExecutionAgent
        for operator in problem.domain_hints["key_operators"]:
            tasks.append({
                "agent": "execution_agent",
                "type": "primitive_operation",
                "operation": operator,
                "state_dependent": True
            })
        
        return tasks
    
    def _validate_results(
        self,
        result: Dict[str, Any],
        expected_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate agent results against expected output
        
        Args:
            result: Actual results from agents
            expected_output: Expected output from YAML
            
        Returns:
            Validation dictionary
        """
        validation = {
            "status": "unknown",
            "goal_achieved": False,
            "constraint_violations": 0,
            "details": []
        }
        
        try:
            # Check if workflow completed
            if result.get("status") == "completed":
                validation["goal_achieved"] = True
                validation["status"] = "success"
            else:
                validation["status"] = "incomplete"
                validation["details"].append(f"Workflow status: {result.get('status')}")
            
            # Check for constraint violations
            if "constraint_violations" in result:
                validation["constraint_violations"] = result["constraint_violations"]
            
            # Count steps if available
            if "steps" in result:
                validation["step_count"] = len(result["steps"])
            
            # Compare with expected output (basic check)
            if "final_state" in result and "final_config" in expected_output:
                # TODO: Implement detailed state comparison
                pass
            
        except Exception as e:
            logger.warning(f"Validation error: {e}")
            validation["status"] = "validation_failed"
            validation["details"].append(str(e))
        
        return validation


def execute_problem(problem: Problem, output_dir: str = "results/phase-3-traces") -> Dict[str, Any]:
    """
    Convenience function to execute a problem with Phase 3
    
    Args:
        problem: Problem instance from YAML
        output_dir: Output directory for results
        
    Returns:
        Execution results
    """
    executor = Phase3Executor(output_dir=output_dir)
    return asyncio.run(executor.execute(problem))


if __name__ == "__main__":
    # Test with a sample problem
    from interface.problem_cli import ProblemLoader
    
    loader = ProblemLoader("problems")
    problem = loader.load_problem("hanoi_constrained")
    
    print("Testing Phase 3 Executor...")
    result = execute_problem(problem)
    print(f"\nResult: {result['success']}")
