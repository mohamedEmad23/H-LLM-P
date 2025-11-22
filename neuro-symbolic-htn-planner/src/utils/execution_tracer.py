"""
Comprehensive Execution Tracer for Multi-Agent System

Tracks:
- LLM calls (prompts, responses, latency)
- Agent-to-agent messages
- HTN decompositions
- State transitions
- Failure analysis
- Decision reasoning

Output formats: JSON, Markdown, CSV
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
import csv


@dataclass
class LLMCall:
    """Single LLM API call"""

    timestamp: float
    agent: str  # Which agent made the call
    provider: str  # groq, openai, anthropic
    model: str  # llama3-70b, gpt-4, etc.
    prompt: str
    response: str
    latency_ms: float
    tokens_used: int
    success: bool
    error: Optional[str] = None


@dataclass
class AgentMessage:
    """Message between agents"""

    timestamp: float
    sender: str
    receiver: str
    message_type: str  # request, response, notification
    content: Dict[str, Any]


@dataclass
class HTNDecomposition:
    """HTN method selection and decomposition"""

    timestamp: float
    agent: str
    task: str
    method_chosen: str
    subtasks: List[str]
    reasoning: str


@dataclass
class StateTransition:
    """State change in problem solving"""

    timestamp: float
    agent: str
    action: str
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    success: bool
    message: str


@dataclass
class FailureAnalysis:
    """Analysis of why a phase failed"""

    timestamp: float
    phase: str
    problem: str
    failure_point: str
    root_cause: str
    missing_capability: str
    recovery_attempted: bool


@dataclass
class PhaseExecution:
    """Complete execution trace for one phase on one problem"""

    phase_id: str  # phase1, phase3, phase4b
    phase_name: str
    problem_name: str
    start_time: float
    end_time: Optional[float] = None

    llm_calls: List[LLMCall] = field(default_factory=list)
    agent_messages: List[AgentMessage] = field(default_factory=list)
    htn_decompositions: List[HTNDecomposition] = field(default_factory=list)
    state_transitions: List[StateTransition] = field(default_factory=list)
    failure_analysis: Optional[FailureAnalysis] = None

    success: bool = False
    quality_score: int = 0
    total_cost: float = 0

    def add_llm_call(
        self,
        agent: str,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        latency_ms: float,
        tokens: int,
        success: bool,
        error: Optional[str] = None,
    ):
        """Record LLM call"""
        self.llm_calls.append(
            LLMCall(
                timestamp=time.time(),
                agent=agent,
                provider=provider,
                model=model,
                prompt=prompt,
                response=response,
                latency_ms=latency_ms,
                tokens_used=tokens,
                success=success,
                error=error,
            )
        )

    def add_message(
        self, sender: str, receiver: str, msg_type: str, content: Dict[str, Any]
    ):
        """Record agent message"""
        self.agent_messages.append(
            AgentMessage(
                timestamp=time.time(),
                sender=sender,
                receiver=receiver,
                message_type=msg_type,
                content=content,
            )
        )

    def add_htn_decomposition(
        self, agent: str, task: str, method: str, subtasks: List[str], reasoning: str
    ):
        """Record HTN decomposition"""
        self.htn_decompositions.append(
            HTNDecomposition(
                timestamp=time.time(),
                agent=agent,
                task=task,
                method_chosen=method,
                subtasks=subtasks,
                reasoning=reasoning,
            )
        )

    def add_state_transition(
        self,
        agent: str,
        action: str,
        before: Dict,
        after: Dict,
        success: bool,
        msg: str,
    ):
        """Record state transition"""
        self.state_transitions.append(
            StateTransition(
                timestamp=time.time(),
                agent=agent,
                action=action,
                state_before=before,
                state_after=after,
                success=success,
                message=msg,
            )
        )

    def add_failure_analysis(
        self,
        failure_point: str,
        root_cause: str,
        missing_capability: str,
        recovery: bool,
    ):
        """Record failure analysis"""
        self.failure_analysis = FailureAnalysis(
            timestamp=time.time(),
            phase=self.phase_id,
            problem=self.problem_name,
            failure_point=failure_point,
            root_cause=root_cause,
            missing_capability=missing_capability,
            recovery_attempted=recovery,
        )

    def finalize(self, success: bool, quality_score: int, total_cost: float):
        """Mark execution complete"""
        self.end_time = time.time()
        self.success = success
        self.quality_score = quality_score
        self.total_cost = total_cost


class ExecutionTracer:
    """Manages execution traces for entire benchmark suite"""

    def __init__(self, output_dir: str = "results/execution_traces"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.executions: List[PhaseExecution] = []
        self.current_execution: Optional[PhaseExecution] = None

    def start_phase(self, phase_id: str, phase_name: str, problem_name: str):
        """Start tracing a phase execution"""
        self.current_execution = PhaseExecution(
            phase_id=phase_id,
            phase_name=phase_name,
            problem_name=problem_name,
            start_time=time.time(),
        )
        return self.current_execution

    def end_phase(self, success: bool, quality_score: int, total_cost: float):
        """End tracing and save"""
        if self.current_execution:
            self.current_execution.finalize(success, quality_score, total_cost)
            self.executions.append(self.current_execution)
            self.current_execution = None

    def save_json(self, filename: Optional[str] = None):
        """Save traces to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"execution_trace_{timestamp}.json"

        filepath = self.output_dir / filename

        # Convert to dict
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_executions": len(self.executions),
            },
            "executions": [asdict(e) for e in self.executions],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"✓ JSON trace saved to: {filepath}")
        return filepath

    def save_markdown(self, filename: Optional[str] = None):
        """Save traces to readable Markdown"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"execution_trace_{timestamp}.md"

        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            f.write("# Multi-Agent Execution Trace\n\n")
            f.write(f"**Generated**: {datetime.now().isoformat()}\n\n")
            f.write(f"**Total Executions**: {len(self.executions)}\n\n")
            f.write("---\n\n")

            for exec in self.executions:
                self._write_execution_md(f, exec)

        print(f"✓ Markdown trace saved to: {filepath}")
        return filepath

    def _write_execution_md(self, f, exec: PhaseExecution):
        """Write single execution to markdown"""
        duration = (exec.end_time - exec.start_time) if exec.end_time else 0
        status = "✓ SUCCESS" if exec.success else "✗ FAILED"

        f.write(f"## {exec.problem_name} - {exec.phase_name}\n\n")
        f.write(f"**Status**: {status} | **Score**: {exec.quality_score}/100 | ")
        f.write(f"**Duration**: {duration:.3f}s\n\n")

        # LLM Calls
        if exec.llm_calls:
            f.write("### 🤖 LLM Calls\n\n")
            for i, call in enumerate(exec.llm_calls, 1):
                f.write(
                    f"**Call #{i}** ({call.agent} → {call.provider}/{call.model})\n"
                )
                f.write(f"- **Prompt**: `{call.prompt[:100]}...`\n")
                f.write(f"- **Response**: `{call.response[:100]}...`\n")
                f.write(f"- **Latency**: {call.latency_ms:.2f}ms | ")
                f.write(f"**Tokens**: {call.tokens_used}\n\n")

        # Agent Messages
        if exec.agent_messages:
            f.write("### 💬 Agent Communication\n\n")
            for i, msg in enumerate(exec.agent_messages, 1):
                f.write(f"**Message #{i}**: {msg.sender} → {msg.receiver}\n")
                f.write(f"- **Type**: {msg.message_type}\n")
                f.write(f"- **Content**: {msg.content}\n\n")

        # HTN Decompositions
        if exec.htn_decompositions:
            f.write("### 🔧 HTN Decompositions\n\n")
            for i, htn in enumerate(exec.htn_decompositions, 1):
                f.write(f"**Decomposition #{i}** ({htn.agent})\n")
                f.write(f"- **Task**: {htn.task}\n")
                f.write(f"- **Method**: `{htn.method_chosen}`\n")
                f.write(f"- **Subtasks**: {', '.join(htn.subtasks)}\n")
                f.write(f"- **Reasoning**: {htn.reasoning}\n\n")

        # State Transitions
        if exec.state_transitions:
            f.write("### 📊 State Transitions\n\n")
            for i, trans in enumerate(exec.state_transitions, 1):
                status = "✓" if trans.success else "✗"
                f.write(f"**Transition #{i}** {status} ({trans.agent})\n")
                f.write(f"- **Action**: {trans.action}\n")
                f.write(f"- **Result**: {trans.message}\n\n")

        # Failure Analysis
        if exec.failure_analysis:
            f.write("### ❌ Failure Analysis\n\n")
            fa = exec.failure_analysis
            f.write(f"- **Failure Point**: {fa.failure_point}\n")
            f.write(f"- **Root Cause**: {fa.root_cause}\n")
            f.write(f"- **Missing Capability**: {fa.missing_capability}\n")
            f.write(f"- **Recovery Attempted**: {fa.recovery_attempted}\n\n")

        f.write("---\n\n")

    def save_csv(self, filename: Optional[str] = None):
        """Save summary to CSV"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"execution_summary_{timestamp}.csv"

        filepath = self.output_dir / filename

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Problem",
                    "Phase",
                    "Success",
                    "Quality Score",
                    "LLM Calls",
                    "Messages",
                    "HTN Decomps",
                    "Duration (s)",
                    "Failure Reason",
                ]
            )

            for exec in self.executions:
                duration = (exec.end_time - exec.start_time) if exec.end_time else 0
                failure = (
                    exec.failure_analysis.root_cause if exec.failure_analysis else "N/A"
                )

                writer.writerow(
                    [
                        exec.problem_name,
                        exec.phase_name,
                        exec.success,
                        exec.quality_score,
                        len(exec.llm_calls),
                        len(exec.agent_messages),
                        len(exec.htn_decompositions),
                        f"{duration:.3f}",
                        failure,
                    ]
                )

        print(f"✓ CSV summary saved to: {filepath}")
        return filepath

    def generate_comparison_report(self):
        """Generate cross-phase comparison"""
        from collections import defaultdict

        by_problem = defaultdict(list)
        for exec in self.executions:
            by_problem[exec.problem_name].append(exec)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"comparison_report_{timestamp}.md"

        with open(filepath, "w") as f:
            f.write("# Cross-Phase Comparison Report\n\n")

            for problem, execs in by_problem.items():
                f.write(f"## {problem}\n\n")
                f.write(
                    "| Phase | Success | Score | LLM Calls | Messages | HTN Decomps |\n"
                )
                f.write(
                    "|-------|---------|-------|-----------|----------|-------------|\n"
                )

                for e in sorted(execs, key=lambda x: x.phase_id):
                    status = "✓" if e.success else "✗"
                    f.write(
                        f"| {e.phase_name} | {status} | {e.quality_score}/100 | "
                        f"{len(e.llm_calls)} | {len(e.agent_messages)} | "
                        f"{len(e.htn_decompositions)} |\n"
                    )

                f.write("\n")

        print(f"✓ Comparison report saved to: {filepath}")
        return filepath
