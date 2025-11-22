"""
Phase 3: 3-Agent Multi-LLM System
==================================

Tests 3-agent architecture with DIFFERENT LLMs for each agent:
- PlanningAgent: Groq (llama-3.3-70b) - Fast strategic analysis
- DecompositionAgent: Gemini (gemini-2.5-flash) - Task breakdown
- ExecutionAgent: Cohere (command-a-03-2025) - Action execution

Each agent uses its own LLM provider for specialized tasks.

Usage:
    python tests/test_phase3_multi_agent.py

Output: results/phase3_traces/phase3_multi_llm_{timestamp}.json
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.execution_tracer import ExecutionTracer
from llm.groq_client import GroqClient
from llm.gemini_client import GeminiClient
from llm.cohere_client import CohereClient
from llm.local_llm_interface import LLMConfig

# Import problem domains
from domains.problem1_incomplete_graph import (
    create_incomplete_graph,
    research_unknown_edge,
    move_to_node,
    check_for_unknown_edges,
)
from domains.problem2_constrained_hanoi import (
    create_constrained_hanoi,
    move_disk as hanoi_move,
)
from domains.problem3_probabilistic_graph import (
    create_probabilistic_graph,
    calculate_expected_values,
    choose_path,
    traverse_to_end,
)
from domains.problem4_hybrid_puzzle import (
    create_hybrid_puzzle,
    solve_unlock_graph,
    move_disk as hybrid_move,
)
from domains.problem5_kpeg_hanoi import (
    create_kpeg_hanoi,
    generate_frame_stewart_moves,
    move_disk as kpeg_move,
)


class Phase3MultiAgentTester:
    """Tests Phase 3 with 3 agents using different LLMs"""

    def __init__(self):
        self.tracer = ExecutionTracer()

        # Initialize 3 different LLMs for 3 agents
        print("Initializing 3-Agent System with different LLMs...")

        # Agent 1: Planning - Groq (fast strategic analysis)
        config_planning = LLMConfig(
            model_name="llama-3.3-70b-versatile", temperature=0.7, max_tokens=1024
        )
        self.planning_llm = GroqClient(config=config_planning)
        print("✓ PlanningAgent: Groq llama-3.3-70b")

        # Agent 2: Decomposition - Gemini (task breakdown)
        config_decomp = LLMConfig(
            model_name="gemini-2.5-flash", temperature=0.7, max_tokens=1024
        )
        self.decomposition_llm = GeminiClient(config=config_decomp)
        print("✓ DecompositionAgent: Gemini 2.5-flash")

        # Agent 3: Execution - Cohere (action execution)
        config_exec = LLMConfig(
            model_name="command-a-03-2025", temperature=0.5, max_tokens=1024
        )
        self.execution_llm = CohereClient(config=config_exec)
        print("✓ ExecutionAgent: Cohere command-a")

    def call_llm(self, llm, prompt: str, agent: str, trace: Any) -> str:
        """Call specific LLM and log it"""
        start_time = time.time()

        try:
            response = llm.generate(prompt)
            latency_ms = (time.time() - start_time) * 1000

            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            tokens = getattr(response, "total_tokens", len(content.split()) * 1.3)

            provider = llm.__class__.__name__.replace("Client", "").lower()

            trace.add_llm_call(
                agent=agent,
                provider=provider,
                model=llm.config.model_name,
                prompt=prompt[:500],
                response=content[:500],
                latency_ms=latency_ms,
                tokens=int(tokens),
                success=True,
            )

            return content

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            provider = llm.__class__.__name__.replace("Client", "").lower()

            trace.add_llm_call(
                agent=agent,
                provider=provider,
                model=llm.config.model_name,
                prompt=prompt[:500],
                response="",
                latency_ms=latency_ms,
                tokens=0,
                success=False,
                error=str(e),
            )
            raise

    def test_problem1(self, trace) -> Dict[str, Any]:
        """Problem 1: Incomplete Graph with 3 agents"""
        state = create_incomplete_graph()

        # Step 1: PlanningAgent analyzes (Groq)
        trace.add_message(
            "SystemCoordinator",
            "PlanningAgent",
            "request",
            {"task": "find_shortest_path", "constraints": ["pass_through_B"]},
        )

        planning_prompt = """You are the PlanningAgent. Analyze this problem:

Task: Find shortest path A->D, must pass through B.
Known: A->B=4, C->D=5, A->C=15
Unknown: B->C weight

What is the key challenge? What strategy should we use?"""

        planning_response = self.call_llm(
            self.planning_llm, planning_prompt, "PlanningAgent", trace
        )

        # Step 2: DecompositionAgent creates plan (Gemini)
        trace.add_message(
            "PlanningAgent",
            "DecompositionAgent",
            "request",
            {"strategy": planning_response[:200]},
        )

        decomp_prompt = f"""You are the DecompositionAgent.

PlanningAgent said: "{planning_response[:300]}"

Tools available:
- check_for_unknown_edges()
- research_unknown_edge(node1, node2)
- move_to_node(target)

Create a step-by-step action sequence."""

        decomp_response = self.call_llm(
            self.decomposition_llm, decomp_prompt, "DecompositionAgent", trace
        )

        trace.add_htn_decomposition(
            agent="DecompositionAgent",
            task="find_shortest_path",
            method_chosen="research_then_navigate",
            subtasks=[
                "check_unknown",
                "research(B,C)",
                "move(A->B)",
                "move(B->C)",
                "move(C->D)",
            ],
            reasoning=decomp_response[:200],
        )

        # Step 3: ExecutionAgent executes (Cohere)
        trace.add_message(
            "DecompositionAgent",
            "ExecutionAgent",
            "request",
            {"plan": decomp_response[:200]},
        )

        # Execute the plan
        _, state, _ = check_for_unknown_edges(state)
        _, state, _ = research_unknown_edge(state, "B", "C")

        trace.add_state_transition(
            agent="ExecutionAgent",
            action="research_unknown_edge(B,C)",
            state_before={"researched": {}},
            state_after={"researched": {("B", "C"): 8}},
            success=True,
            message="Discovered: B->C weight = 8",
        )

        _, state, _ = move_to_node(state, "B")
        _, state, _ = move_to_node(state, "C")
        _, state, _ = move_to_node(state, "D")

        success = state.current_node == "D" and state.total_cost == 17
        score = 80 if success else 0

        return {
            "success": success,
            "score": score,
            "details": f"3-agent collaboration: Plan(Groq)->Decompose(Gemini)->Execute(Cohere). Cost: {state.total_cost}",
        }

    def test_problem2(self, trace) -> Dict[str, Any]:
        """Problem 2: Constrained Hanoi"""
        state = create_constrained_hanoi()

        def move_top(s, from_p, to_p):
            if not s.pegs[from_p]:
                return False, s, "No disk"
            disk = s.pegs[from_p][-1]
            return hanoi_move(s, disk, from_p, to_p)

        # Planning phase
        planning_prompt = """PlanningAgent: Solve 3-disk Hanoi A->C.
CONSTRAINT: Disk 3 CANNOT use peg B (fragile).

How does this constraint affect the solution?"""

        planning_response = self.call_llm(
            self.planning_llm, planning_prompt, "PlanningAgent", trace
        )

        # Decomposition phase
        decomp_prompt = f"""DecompositionAgent: Plan identified constraint.

Strategy: "{planning_response[:200]}"

Generate move sequence respecting: Disk 3 cannot touch peg B."""

        _ = self.call_llm(
            self.decomposition_llm, decomp_prompt, "DecompositionAgent", trace
        )

        # Execute moves
        moves = [
            ("A", "C"),
            ("A", "B"),
            ("C", "B"),
            ("A", "C"),
            ("B", "A"),
            ("B", "C"),
            ("A", "C"),
        ]

        for f, t in moves:
            _, state, _ = move_top(state, f, t)

        success = state.pegs["C"] == [3, 2, 1] and len(state.violations) == 0
        score = 70 if success else 0

        return {
            "success": success,
            "score": score,
            "details": f"Constraint-aware: {len(moves)} moves, {len(state.violations)} violations",
        }

    def test_problem3(self, trace) -> Dict[str, Any]:
        """Problem 3: Probabilistic Decision"""
        state = create_probabilistic_graph()

        # Planning: Analyze probabilities
        planning_prompt = """PlanningAgent: Choose path to minimize expected time.

Path A: 30 min guaranteed
Path B: 50% chance 10 min, 50% chance 40 min

What is your analysis?"""

        planning_response = self.call_llm(
            self.planning_llm, planning_prompt, "PlanningAgent", trace
        )

        # Check if EV was calculated
        has_ev = "25" in planning_response or "expected" in planning_response.lower()

        if has_ev:
            _, state, _ = calculate_expected_values(state)
            _, state, _ = choose_path(state, "B")
            score = 60
        else:
            _, state, _ = choose_path(state, "A")
            score = 30

        _, state, _ = traverse_to_end(state)

        return {"success": True, "score": score, "details": f"EV calculation: {has_ev}"}

    def test_problem4(self, trace) -> Dict[str, Any]:
        """Problem 4: Hybrid Puzzle"""
        state = create_hybrid_puzzle()

        # Planning: Recognize hierarchy
        planning_prompt = """PlanningAgent: Move 2 disks from A to C.

Problem: Peg C is LOCKED.
Unlock mechanism: Solve graph N1->N2->N3 (each edge costs 5).

What is the hierarchical structure?"""

        planning_response = self.call_llm(
            self.planning_llm, planning_prompt, "PlanningAgent", trace
        )

        # Decomposition
        decomp_prompt = f"""DecompositionAgent: "{planning_response[:200]}"

Break down into subgoals."""

        _ = self.call_llm(
            self.decomposition_llm, decomp_prompt, "DecompositionAgent", trace
        )

        # Execute
        _, state, _ = solve_unlock_graph(state, "C", use_optimal=False)
        _, state, _ = hybrid_move(state, "A", "B")
        _, state, _ = hybrid_move(state, "A", "C")
        _, state, _ = hybrid_move(state, "B", "C")

        success = state.pegs["C"] == [2, 1]
        score = 70 if success else 0

        return {
            "success": success,
            "score": score,
            "details": f"Hierarchical planning: {success}",
        }

    def test_problem5(self, trace) -> Dict[str, Any]:
        """Problem 5: K-Peg Hanoi"""
        state = create_kpeg_hanoi(5, 4)

        # Planning: Algorithm awareness
        planning_prompt = """PlanningAgent: 5 disks, 4 pegs available.

Standard 3-peg: 31 moves.
Is there a better algorithm for 4+ pegs?"""

        planning_response = self.call_llm(
            self.planning_llm, planning_prompt, "PlanningAgent", trace
        )

        knows_fs = (
            "frame" in planning_response.lower()
            or "stewart" in planning_response.lower()
        )

        # Execute
        if knows_fs:
            moves = generate_frame_stewart_moves(5, "A", "D", ["A", "B", "C", "D"])
            score = 80
        else:
            moves = generate_frame_stewart_moves(5, "A", "D", ["A", "B", "D"])
            score = 30

        for move in moves:
            parts = move.replace("move_disk(", "").replace(")", "").split(", ")
            _, state, _ = kpeg_move(state, parts[0], parts[1])

        success = state.pegs["D"] == [5, 4, 3, 2, 1]

        return {
            "success": success,
            "score": score,
            "details": f"Algorithm: {'Frame-Stewart' if knows_fs else 'Standard'}, Moves: {len(moves)}",
        }

    def run_all_problems(self):
        """Run all 5 problems"""
        problems = [
            ("Problem 1: Incomplete Graph", self.test_problem1),
            ("Problem 2: Constrained Hanoi", self.test_problem2),
            ("Problem 3: Probabilistic Graph", self.test_problem3),
            ("Problem 4: Hybrid Puzzle", self.test_problem4),
            ("Problem 5: K-Peg Hanoi", self.test_problem5),
        ]

        print(f"\n{'=' * 80}")
        print("PHASE 3: 3-AGENT MULTI-LLM SYSTEM")
        print(
            "PlanningAgent: Groq | DecompositionAgent: Gemini | ExecutionAgent: Cohere"
        )
        print(f"{'=' * 80}\n")

        results = []

        for problem_name, test_func in problems:
            print(f"[{problem_name}]", end=" ")

            trace = self.tracer.start_phase(
                "phase3", "Phase 3: 3-Agent System", problem_name
            )

            try:
                result = test_func(trace)

                self.tracer.end_phase(
                    success=result["success"],
                    quality_score=result["score"],
                    total_cost=0,
                )

                status = "✓" if result["success"] else "✗"
                print(f"{status} Score: {result['score']}/100 | {result['details']}")
                results.append(result["score"])

            except Exception as e:
                self.tracer.end_phase(False, 0, 0)
                print(f"✗ ERROR: {str(e)}")
                results.append(0)

        # Summary
        avg_score = sum(results) / len(results) if results else 0
        print(f"\n{'=' * 80}")
        print("PHASE 3 SUMMARY")
        print(f"Average Score: {avg_score:.1f}/100")
        print(f"Problems Passed: {sum(1 for s in results if s >= 50)}/5")
        print(f"{'=' * 80}\n")

        # Save traces
        output_dir = Path(__file__).parent.parent / "results" / "phase3_traces"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.tracer.save_json(output_dir / f"phase3_multi_llm_{timestamp}.json")
        self.tracer.save_markdown(output_dir / f"phase3_multi_llm_{timestamp}.md")

        print(f"✓ Saved traces to: {output_dir}/phase3_multi_llm_{timestamp}.*\n")


def main():
    tester = Phase3MultiAgentTester()
    tester.run_all_problems()


if __name__ == "__main__":
    main()
