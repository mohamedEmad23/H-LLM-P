"""
Core Workflow - 3-Agent HTN Planning System

Orchestrates DecompositionAgent → ExecutionAgent → VerificationAgent
"""

import asyncio
from typing import Dict
from datetime import datetime
from loguru import logger

from ..decomposition_agent import DecompositionAgent
from ..execution_agent import ExecutionAgent
from ..verification_agent import VerificationAgent
from ..message_bus import MessageBus
from ..agent_state_manager import AgentStateManager


class CoreWorkflow:
    """
    Core 3-agent HTN planning workflow

    Sequential execution:
    1. DecompositionAgent: Decompose task into HTN plan
    2. ExecutionAgent: Execute plan step-by-step
    3. VerificationAgent: Verify plan correctness and quality

    Features:
    - Automatic retry on failure (configurable)
    - Detailed logging at each stage
    - Performance metrics collection
    - Optional memory integration
    """

    def __init__(
        self,
        decomposition_agent: DecompositionAgent,
        execution_agent: ExecutionAgent,
        verification_agent: VerificationAgent,
        max_retries: int = 3,
        use_message_bus: bool = False,
    ):
        """
        Initialize workflow

        Args:
            decomposition_agent: Agent for task decomposition
            execution_agent: Agent for plan execution
            verification_agent: Agent for plan verification
            max_retries: Max retries on failure
            use_message_bus: Whether to use MessageBus communication
        """
        self.decomposition_agent = decomposition_agent
        self.execution_agent = execution_agent
        self.verification_agent = verification_agent
        self.max_retries = max_retries
        self.use_message_bus = use_message_bus

        # Optional message bus for agent communication
        self.message_bus = None
        self.state_manager = None

        if use_message_bus:
            self.message_bus = MessageBus()
            self.state_manager = AgentStateManager()

            # Connect agents to infrastructure
            decomposition_agent.set_message_bus(self.message_bus)
            decomposition_agent.set_state_manager(self.state_manager)

            execution_agent.set_message_bus(self.message_bus)
            execution_agent.set_state_manager(self.state_manager)

            verification_agent.set_message_bus(self.message_bus)
            verification_agent.set_state_manager(self.state_manager)

        # Workflow statistics
        self.stats = {
            "tasks_processed": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_retries": 0,
            "avg_total_time_ms": 0.0,
            "avg_decomposition_time_ms": 0.0,
            "avg_execution_time_ms": 0.0,
            "avg_verification_time_ms": 0.0,
        }

    async def process_task(self, task_input: Dict) -> Dict:
        """
        Process HTN planning task through full workflow

        Args:
            task_input: {
                "task": "solve_hanoi(3, A, C, B)",
                "domain": "tower_of_hanoi",
                "initial_state": {...},
                "goal": {...},
                "operators": {...},
                "constraints": [...],
                "optimal_steps": 7 (optional)
            }

        Returns:
            {
                "success": bool,
                "task": str,
                "decomposition": {...},
                "execution": {...},
                "verification": {...},
                "final_state": {...},
                "quality_score": float,
                "total_time_ms": float,
                "retry_count": int
            }
        """
        start_time = datetime.now()
        task = task_input["task"]
        domain = task_input["domain"]

        logger.info(f"🚀 Starting workflow for task: {task}")

        retry_count = 0
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Stage 1: Decomposition
                logger.info(f"📋 Stage 1: Decomposition (attempt {attempt + 1})")
                decomp_start = datetime.now()

                decomposition_result = await self.decomposition_agent.process(
                    {
                        "task": task,
                        "domain": domain,
                        "operators": task_input.get("operators", {}),
                        "constraints": task_input.get("constraints", []),
                        "context": task_input.get("context", {}),
                    }
                )

                decomp_time = (datetime.now() - decomp_start).total_seconds() * 1000

                if not decomposition_result["success"]:
                    raise Exception(
                        f"Decomposition failed: {decomposition_result.get('error')}"
                    )

                logger.info(
                    f"✅ Decomposition complete: "
                    f"{len(decomposition_result['methods'])} methods generated "
                    f"({decomp_time:.1f}ms)"
                )

                # Extract plan from first method (or combine methods)
                methods = decomposition_result["methods"]
                if not methods:
                    raise Exception("No methods generated")

                # Use first method's subtasks as the plan
                plan = methods[0]["subtasks"]

                # Stage 2: Execution
                logger.info(f"⚙️  Stage 2: Execution ({len(plan)} steps)")
                exec_start = datetime.now()

                execution_result = await self.execution_agent.process(
                    {
                        "plan": plan,
                        "initial_state": task_input["initial_state"],
                        "domain": domain,
                        "operators": task_input.get("operators", {}),
                    }
                )

                exec_time = (datetime.now() - exec_start).total_seconds() * 1000

                if not execution_result["success"]:
                    raise Exception(
                        f"Execution failed: {execution_result.get('errors')}"
                    )

                logger.info(
                    f"✅ Execution complete: "
                    f"{execution_result['steps_completed']}/"
                    f"{execution_result['steps_total']} steps "
                    f"({exec_time:.1f}ms)"
                )

                # Stage 3: Verification
                logger.info("🔍 Stage 3: Verification")
                verif_start = datetime.now()

                verification_result = await self.verification_agent.process(
                    {
                        "execution_trace": execution_result["execution_trace"],
                        "final_state": execution_result["final_state"],
                        "initial_state": task_input["initial_state"],
                        "goal": task_input["goal"],
                        "domain": domain,
                        "optimal_steps": task_input.get("optimal_steps"),
                    }
                )

                verif_time = (datetime.now() - verif_start).total_seconds() * 1000

                logger.info(
                    f"✅ Verification complete: "
                    f"Goal={'achieved' if verification_result['goal_achieved'] else 'NOT achieved'}, "
                    f"Quality={verification_result['quality_score']:.1f} "
                    f"({verif_time:.1f}ms)"
                )

                # Calculate total time
                total_time = (datetime.now() - start_time).total_seconds() * 1000

                # Update statistics
                self._update_stats(
                    success=verification_result["goal_achieved"],
                    total_time=total_time,
                    decomp_time=decomp_time,
                    exec_time=exec_time,
                    verif_time=verif_time,
                    retry_count=retry_count,
                )

                # Build final result
                result = {
                    "success": verification_result["goal_achieved"],
                    "task": task,
                    "domain": domain,
                    "decomposition": decomposition_result,
                    "execution": execution_result,
                    "verification": verification_result,
                    "final_state": execution_result["final_state"],
                    "quality_score": verification_result["quality_score"],
                    "goal_achieved": verification_result["goal_achieved"],
                    "total_time_ms": total_time,
                    "decomposition_time_ms": decomp_time,
                    "execution_time_ms": exec_time,
                    "verification_time_ms": verif_time,
                    "retry_count": retry_count,
                    "plan": plan,
                }

                logger.info(
                    f"{'✅' if result['success'] else '❌'} "
                    f"Workflow complete: "
                    f"Success={result['success']}, "
                    f"Quality={result['quality_score']:.1f}, "
                    f"Time={total_time:.1f}ms"
                )

                return result

            except Exception as e:
                retry_count = attempt + 1
                last_error = str(e)
                logger.warning(f"⚠️  Attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    logger.info("🔄 Retrying...")
                    await asyncio.sleep(1)  # Brief delay before retry
                else:
                    logger.error(f"❌ All {self.max_retries} attempts failed")

        # All retries exhausted
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        self._update_stats(
            success=False,
            total_time=total_time,
            decomp_time=0,
            exec_time=0,
            verif_time=0,
            retry_count=retry_count,
        )

        return {
            "success": False,
            "task": task,
            "error": last_error,
            "retry_count": retry_count,
            "total_time_ms": total_time,
        }

    def _update_stats(
        self,
        success: bool,
        total_time: float,
        decomp_time: float,
        exec_time: float,
        verif_time: float,
        retry_count: int,
    ):
        """Update workflow statistics"""
        self.stats["tasks_processed"] += 1

        if success:
            self.stats["successful_tasks"] += 1
        else:
            self.stats["failed_tasks"] += 1

        self.stats["total_retries"] += retry_count

        # Update running averages
        n = self.stats["tasks_processed"]

        self.stats["avg_total_time_ms"] = (
            self.stats["avg_total_time_ms"] * (n - 1) + total_time
        ) / n

        if decomp_time > 0:
            self.stats["avg_decomposition_time_ms"] = (
                self.stats["avg_decomposition_time_ms"] * (n - 1) + decomp_time
            ) / n

        if exec_time > 0:
            self.stats["avg_execution_time_ms"] = (
                self.stats["avg_execution_time_ms"] * (n - 1) + exec_time
            ) / n

        if verif_time > 0:
            self.stats["avg_verification_time_ms"] = (
                self.stats["avg_verification_time_ms"] * (n - 1) + verif_time
            ) / n

    def get_statistics(self) -> Dict:
        """Get workflow statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_tasks"] / self.stats["tasks_processed"]
            )
            if self.stats["tasks_processed"] > 0
            else 0.0,
            "avg_retries_per_task": (
                self.stats["total_retries"] / self.stats["tasks_processed"]
            )
            if self.stats["tasks_processed"] > 0
            else 0.0,
            "decomposition_agent_stats": (self.decomposition_agent.get_statistics()),
            "execution_agent_stats": (self.execution_agent.get_statistics()),
            "verification_agent_stats": (self.verification_agent.get_statistics()),
        }

    def get_full_report(self) -> str:
        """Get comprehensive workflow report"""
        stats = self.get_statistics()

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║          MULTI-AGENT HTN WORKFLOW REPORT                     ║
╚══════════════════════════════════════════════════════════════╝

📊 Overall Statistics:
   Tasks Processed: {stats["tasks_processed"]}
   Successful: {stats["successful_tasks"]}
   Failed: {stats["failed_tasks"]}
   Success Rate: {stats["success_rate"]:.1%}
   Avg Retries: {stats["avg_retries_per_task"]:.2f}

⏱️  Performance Metrics:
   Total Time: {stats["avg_total_time_ms"]:.1f}ms avg
   Decomposition: {stats["avg_decomposition_time_ms"]:.1f}ms avg
   Execution: {stats["avg_execution_time_ms"]:.1f}ms avg
   Verification: {stats["avg_verification_time_ms"]:.1f}ms avg

🤖 Agent Performance:

   DecompositionAgent:
      Success Rate: {stats["decomposition_agent_stats"]["success_rate"]:.1%}
      Avg Confidence: {stats["decomposition_agent_stats"]["avg_confidence"]:.2f}
      Fallback Rate: {stats["decomposition_agent_stats"]["fallback_rate"]:.1%}

   ExecutionAgent:
      Success Rate: {stats["execution_agent_stats"]["success_rate"]:.1%}
      Total Steps: {stats["execution_agent_stats"]["total_steps_executed"]}
      Validation Failures: {stats["execution_agent_stats"]["validation_failure_rate"]:.1%}
      LLM Fallback: {stats["execution_agent_stats"]["llm_fallback_rate"]:.1%}

   VerificationAgent:
      Success Rate: {stats["verification_agent_stats"]["success_rate"]:.1%}
      Avg Quality: {stats["verification_agent_stats"]["avg_quality_score"]:.1f}
      Fallback Rate: {stats["verification_agent_stats"]["fallback_rate"]:.1%}

╚══════════════════════════════════════════════════════════════╝
"""
        return report
