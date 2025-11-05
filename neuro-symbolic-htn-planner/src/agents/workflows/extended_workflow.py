"""
Extended Workflow - 5-Agent HTN Planning System

Orchestrates PlanningAgent → DecompositionAgent → ExecutionAgent →
VerificationAgent → ContextAgent with feedback loops
"""

import asyncio
from typing import Dict
from datetime import datetime
from loguru import logger

from ..planning_agent import PlanningAgent
from ..decomposition_agent import DecompositionAgent
from ..execution_agent import ExecutionAgent
from ..verification_agent import VerificationAgent
from ..context_agent import ContextAgent
from ..message_bus import MessageBus
from ..agent_state_manager import AgentStateManager


class ExtendedWorkflow:
    """
    Extended 5-agent HTN planning workflow

    Sequential execution with context tracking:
    1. PlanningAgent: Strategic analysis and strategy selection
    2. DecompositionAgent: Decompose task into HTN plan
    3. ExecutionAgent: Execute plan step-by-step
    4. VerificationAgent: Verify plan correctness and quality
    5. ContextAgent: Track state and provide feedback

    Features:
    - Strategic planning before decomposition
    - Continuous context tracking throughout workflow
    - Feedback loop from context to planning
    - Automatic retry with context-aware strategy adjustment
    - Comprehensive performance metrics
    """

    def __init__(
        self,
        planning_agent: PlanningAgent,
        decomposition_agent: DecompositionAgent,
        execution_agent: ExecutionAgent,
        verification_agent: VerificationAgent,
        context_agent: ContextAgent,
        max_retries: int = 3,
        use_message_bus: bool = False,
        enable_feedback_loop: bool = True,
    ):
        """
        Initialize extended workflow

        Args:
            planning_agent: Agent for strategic planning
            decomposition_agent: Agent for task decomposition
            execution_agent: Agent for plan execution
            verification_agent: Agent for plan verification
            context_agent: Agent for context tracking
            max_retries: Max retries on failure
            use_message_bus: Whether to use MessageBus communication
            enable_feedback_loop: Enable context feedback to planning
        """
        self.planning_agent = planning_agent
        self.decomposition_agent = decomposition_agent
        self.execution_agent = execution_agent
        self.verification_agent = verification_agent
        self.context_agent = context_agent
        self.max_retries = max_retries
        self.use_message_bus = use_message_bus
        self.enable_feedback_loop = enable_feedback_loop

        # Optional message bus for agent communication
        self.message_bus = None
        self.state_manager = None

        if use_message_bus:
            self.message_bus = MessageBus()
            self.state_manager = AgentStateManager()

            # Connect all agents to infrastructure
            for agent in [
                planning_agent,
                decomposition_agent,
                execution_agent,
                verification_agent,
                context_agent,
            ]:
                if hasattr(agent, "set_message_bus"):
                    agent.set_message_bus(self.message_bus)
                if hasattr(agent, "set_state_manager"):
                    agent.set_state_manager(self.state_manager)

        # Workflow statistics
        self.stats = {
            "tasks_processed": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_retries": 0,
            "avg_total_time_ms": 0.0,
            "avg_planning_time_ms": 0.0,
            "avg_decomposition_time_ms": 0.0,
            "avg_execution_time_ms": 0.0,
            "avg_verification_time_ms": 0.0,
            "avg_context_time_ms": 0.0,
            "strategies_evaluated": 0,
            "context_retrievals": 0,
            "feedback_loops_executed": 0,
        }

    async def process_task(self, task_input: Dict) -> Dict:
        """
        Process HTN planning task through full 5-agent workflow

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
                "planning": {...},
                "decomposition": {...},
                "execution": {...},
                "verification": {...},
                "context": {...},
                "final_state": {...},
                "quality_score": float,
                "total_time_ms": float,
                "retry_count": int,
                "workflow_type": "extended_5_agent"
            }
        """
        start_time = datetime.now()
        task = task_input["task"]
        domain = task_input["domain"]

        logger.info(f"🚀 Starting EXTENDED workflow for task: {task}")

        retry_count = 0
        last_error = None
        selected_strategy = None

        for attempt in range(self.max_retries):
            try:
                # Stage 0: Planning (Strategic Analysis)
                logger.info(f"🎯 Stage 0: Strategic Planning (attempt {attempt + 1})")
                planning_start = datetime.now()

                # Get context from previous attempts if available
                context_data = None
                if attempt > 0 and self.enable_feedback_loop:
                    context_data = await self._get_retry_context(attempt)
                    self.stats["feedback_loops_executed"] += 1

                planning_result = await self.planning_agent.process(
                    {
                        "task": task,
                        "domain": domain,
                        "initial_state": task_input["initial_state"],
                        "goal": task_input["goal"],
                        "constraints": task_input.get("constraints", []),
                        "context": {
                            **task_input.get("context", {}),
                            "retry_context": context_data,
                            "attempt": attempt + 1,
                        },
                    }
                )

                planning_time = (datetime.now() - planning_start).total_seconds() * 1000

                if not planning_result["success"]:
                    raise Exception(f"Planning failed: {planning_result.get('error')}")

                selected_strategy = planning_result["recommended_strategy"]
                self.stats["strategies_evaluated"] += len(planning_result["strategies"])

                logger.info(
                    f"✅ Planning complete: "
                    f"{len(planning_result['strategies'])} strategies evaluated, "
                    f"selected '{selected_strategy['name']}' "
                    f"({planning_time:.1f}ms)"
                )

                # Log planning interaction
                await self._log_interaction(
                    agent="PlanningAgent",
                    action="strategic_planning",
                    input_data={"task": task, "domain": domain},
                    output_data=planning_result,
                    success=True,
                )

                # Track planning state
                await self._track_state(
                    phase="planning",
                    state={"selected_strategy": selected_strategy["name"]},
                )

                # Stage 1: Decomposition
                logger.info("📋 Stage 1: Decomposition")
                decomp_start = datetime.now()

                decomposition_result = await self.decomposition_agent.process(
                    {
                        "task": task,
                        "domain": domain,
                        "operators": task_input.get("operators", {}),
                        "constraints": task_input.get("constraints", []),
                        "context": {
                            **task_input.get("context", {}),
                            "strategy": selected_strategy,
                            "planning_insights": planning_result.get(
                                "key_insights", []
                            ),
                        },
                    }
                )

                decomp_time = (datetime.now() - decomp_start).total_seconds() * 1000

                if not decomposition_result["success"]:
                    raise Exception(
                        f"Decomposition failed: " f"{decomposition_result.get('error')}"
                    )

                logger.info(
                    f"✅ Decomposition complete: "
                    f"{len(decomposition_result['methods'])} methods generated "
                    f"({decomp_time:.1f}ms)"
                )

                # Log decomposition interaction
                await self._log_interaction(
                    agent="DecompositionAgent",
                    action="task_decomposition",
                    input_data={"task": task, "strategy": selected_strategy["name"]},
                    output_data=decomposition_result,
                    success=True,
                )

                # Extract plan
                methods = decomposition_result["methods"]
                if not methods:
                    raise Exception("No methods generated")

                plan = methods[0]["subtasks"]

                # Track decomposition state
                await self._track_state(
                    phase="decomposition",
                    state={"methods_count": len(methods), "plan_steps": len(plan)},
                )

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

                # Log execution interaction
                await self._log_interaction(
                    agent="ExecutionAgent",
                    action="plan_execution",
                    input_data={"plan_steps": len(plan)},
                    output_data=execution_result,
                    success=True,
                )

                # Track execution state
                await self._track_state(
                    phase="execution", state=execution_result["final_state"]
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

                # Log verification interaction
                await self._log_interaction(
                    agent="VerificationAgent",
                    action="plan_verification",
                    input_data={"goal": task_input["goal"]},
                    output_data=verification_result,
                    success=verification_result["goal_achieved"],
                )

                # Track verification state
                await self._track_state(
                    phase="verification",
                    state={
                        "goal_achieved": verification_result["goal_achieved"],
                        "quality_score": verification_result["quality_score"],
                    },
                )

                # Stage 4: Context Summary
                logger.info("📊 Stage 4: Context Summary")
                context_start = datetime.now()

                context_summary = await self._get_workflow_summary()

                context_time = (datetime.now() - context_start).total_seconds() * 1000

                logger.info(f"✅ Context summary generated ({context_time:.1f}ms)")

                # Calculate total time
                total_time = (datetime.now() - start_time).total_seconds() * 1000

                # Update statistics
                self._update_stats(
                    success=verification_result["goal_achieved"],
                    total_time=total_time,
                    planning_time=planning_time,
                    decomp_time=decomp_time,
                    exec_time=exec_time,
                    verif_time=verif_time,
                    context_time=context_time,
                    retry_count=retry_count,
                )

                # Build final result
                result = {
                    "success": verification_result["goal_achieved"],
                    "task": task,
                    "domain": domain,
                    "workflow_type": "extended_5_agent",
                    "planning": planning_result,
                    "decomposition": decomposition_result,
                    "execution": execution_result,
                    "verification": verification_result,
                    "context": context_summary,
                    "final_state": execution_result["final_state"],
                    "quality_score": verification_result["quality_score"],
                    "goal_achieved": verification_result["goal_achieved"],
                    "total_time_ms": total_time,
                    "planning_time_ms": planning_time,
                    "decomposition_time_ms": decomp_time,
                    "execution_time_ms": exec_time,
                    "verification_time_ms": verif_time,
                    "context_time_ms": context_time,
                    "retry_count": retry_count,
                    "plan": plan,
                    "selected_strategy": selected_strategy,
                }

                logger.info(
                    f"{'✅' if result['success'] else '❌'} "
                    f"Extended workflow complete: "
                    f"Success={result['success']}, "
                    f"Quality={result['quality_score']:.1f}, "
                    f"Time={total_time:.1f}ms, "
                    f"Strategy={selected_strategy['name']}"
                )

                return result

            except Exception as e:
                retry_count = attempt + 1
                last_error = str(e)
                logger.warning(f"⚠️  Attempt {attempt + 1} failed: {e}")

                # Log failure interaction
                await self._log_interaction(
                    agent="Workflow",
                    action="task_processing",
                    input_data={"task": task, "attempt": attempt + 1},
                    output_data={"error": str(e)},
                    success=False,
                )

                if attempt < self.max_retries - 1:
                    logger.info("🔄 Retrying with context feedback...")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"❌ All {self.max_retries} attempts failed")

        # All retries exhausted
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        self._update_stats(
            success=False,
            total_time=total_time,
            planning_time=0,
            decomp_time=0,
            exec_time=0,
            verif_time=0,
            context_time=0,
            retry_count=retry_count,
        )

        return {
            "success": False,
            "task": task,
            "workflow_type": "extended_5_agent",
            "error": last_error,
            "retry_count": retry_count,
            "total_time_ms": total_time,
        }

    async def _log_interaction(
        self,
        agent: str,
        action: str,
        input_data: Dict,
        output_data: Dict,
        success: bool,
    ):
        """Log interaction to ContextAgent"""
        try:
            await self.context_agent.process(
                {
                    "operation": "log_interaction",
                    "data": {
                        "agent": agent,
                        "action": action,
                        "input": input_data,
                        "output": output_data,
                        "success": success,
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log interaction: {e}")

    async def _track_state(self, phase: str, state: Dict):
        """Track state change to ContextAgent"""
        try:
            await self.context_agent.process(
                {
                    "operation": "track_state",
                    "data": {
                        "phase": phase,
                        "state": state,
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track state: {e}")

    async def _get_retry_context(self, attempt: int) -> Dict:
        """Get context from previous attempts for retry strategy"""
        try:
            result = await self.context_agent.process(
                {
                    "operation": "retrieve_context",
                    "data": {
                        "query": "Previous attempt failures and patterns",
                        "window": 20,
                    },
                }
            )

            if result["success"]:
                self.stats["context_retrievals"] += 1
                return result["result"]

            return {}
        except Exception as e:
            logger.warning(f"Failed to get retry context: {e}")
            return {}

    async def _get_workflow_summary(self) -> Dict:
        """Get summary of workflow execution from ContextAgent"""
        try:
            result = await self.context_agent.process(
                {
                    "operation": "get_history",
                    "data": {"type": "interaction", "limit": 10},
                }
            )

            if result["success"]:
                return {
                    "interaction_count": result["result"]["total_count"],
                    "recent_interactions": len(result["result"]["history"]),
                    "agent_statistics": self.context_agent.get_statistics(),
                }

            return {}
        except Exception as e:
            logger.warning(f"Failed to get workflow summary: {e}")
            return {}

    def _update_stats(
        self,
        success: bool,
        total_time: float,
        planning_time: float,
        decomp_time: float,
        exec_time: float,
        verif_time: float,
        context_time: float,
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

        if planning_time > 0:
            self.stats["avg_planning_time_ms"] = (
                self.stats["avg_planning_time_ms"] * (n - 1) + planning_time
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

        if context_time > 0:
            self.stats["avg_context_time_ms"] = (
                self.stats["avg_context_time_ms"] * (n - 1) + context_time
            ) / n

    def get_statistics(self) -> Dict:
        """Get comprehensive workflow statistics"""
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
            "avg_strategies_per_task": (
                self.stats["strategies_evaluated"] / self.stats["tasks_processed"]
            )
            if self.stats["tasks_processed"] > 0
            else 0.0,
            "planning_agent_stats": self.planning_agent.get_statistics(),
            "decomposition_agent_stats": (self.decomposition_agent.get_statistics()),
            "execution_agent_stats": self.execution_agent.get_statistics(),
            "verification_agent_stats": (self.verification_agent.get_statistics()),
            "context_agent_stats": self.context_agent.get_statistics(),
        }

    def get_full_report(self) -> str:
        """Get comprehensive workflow report"""
        stats = self.get_statistics()

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║       EXTENDED 5-AGENT HTN WORKFLOW REPORT                   ║
╚══════════════════════════════════════════════════════════════╝

📊 Overall Statistics:
   Tasks Processed: {stats['tasks_processed']}
   Successful: {stats['successful_tasks']}
   Failed: {stats['failed_tasks']}
   Success Rate: {stats['success_rate']:.1%}
   Avg Retries: {stats['avg_retries_per_task']:.2f}

⏱️  Performance Metrics:
   Total Time: {stats['avg_total_time_ms']:.1f}ms avg
   Planning: {stats['avg_planning_time_ms']:.1f}ms avg
   Decomposition: {stats['avg_decomposition_time_ms']:.1f}ms avg
   Execution: {stats['avg_execution_time_ms']:.1f}ms avg
   Verification: {stats['avg_verification_time_ms']:.1f}ms avg
   Context: {stats['avg_context_time_ms']:.1f}ms avg

🎯 Advanced Features:
   Strategies Evaluated: {stats['strategies_evaluated']}
   Avg Strategies/Task: {stats['avg_strategies_per_task']:.1f}
   Context Retrievals: {stats['context_retrievals']}
   Feedback Loops: {stats['feedback_loops_executed']}

🤖 Agent Performance:

   PlanningAgent:
      Success Rate: {stats['planning_agent_stats']['success_rate']:.1%}
      Avg Confidence: {stats['planning_agent_stats']['avg_confidence']:.2f}
      Fallback Rate: {stats['planning_agent_stats']['fallback_rate']:.1%}

   DecompositionAgent:
      Success Rate: {stats['decomposition_agent_stats']['success_rate']:.1%}
      Avg Confidence: {stats['decomposition_agent_stats']['avg_confidence']:.2f}
      Fallback Rate: {stats['decomposition_agent_stats']['fallback_rate']:.1%}

   ExecutionAgent:
      Success Rate: {stats['execution_agent_stats']['success_rate']:.1%}
      Total Steps: {stats['execution_agent_stats']['total_steps_executed']}
      LLM Fallback: {stats['execution_agent_stats']['llm_fallback_rate']:.1%}

   VerificationAgent:
      Success Rate: {stats['verification_agent_stats']['success_rate']:.1%}
      Avg Quality: {stats['verification_agent_stats']['avg_quality_score']:.1f}
      Fallback Rate: {stats['verification_agent_stats']['fallback_rate']:.1%}

   ContextAgent:
      Interactions Logged: {stats['context_agent_stats']['interactions_logged']}
      States Tracked: {stats['context_agent_stats']['states_tracked']}
      Contexts Retrieved: {stats['context_agent_stats']['contexts_retrieved']}
      LLM Usage: {stats['context_agent_stats']['llm_usage_rate']:.1%}

╚══════════════════════════════════════════════════════════════╝
"""
        return report
