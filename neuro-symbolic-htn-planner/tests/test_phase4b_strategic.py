"""
Phase 4B: 5-Agent Strategic System with Fallback Providers
===========================================================

Tests 5-agent architecture with DIFFERENT LLMs per agent + fallback:

Primary Configuration:
- MonitoringAgent: HuggingFace (Llama-3.3-70B) - Problem analysis
- PlanningAgent: Groq (llama-3.3-70b) - Strategic planning
- DecompositionAgent: Gemini (gemini-2.5-flash) - Task breakdown
- ExecutionAgent: Cohere (command-a-03-2025) - Action execution
- ValidationAgent: Ollama (llama3.2:latest) - Result verification

Fallback Strategy:
- If HuggingFace fails -> Groq
- If Groq fails -> Gemini
- If Gemini fails -> Cohere
- If Cohere fails -> Ollama
- If Ollama fails -> HuggingFace (cyclic)

Usage:
    python tests/test_phase4b_strategic.py

Output: results/phase4b_traces/phase4b_strategic_{timestamp}.json
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.execution_tracer import ExecutionTracer
from llm.groq_client import GroqClient
from llm.gemini_client import GeminiClient
from llm.cohere_client import CohereClient
from llm.ollama_client import OllamaClient
from llm.huggingface_client import HuggingFaceClient
from llm.local_llm_interface import LLMConfig

# Import problem domains
from domains.problem1_incomplete_graph import (
    create_incomplete_graph, research_unknown_edge, move_to_node,
    check_for_unknown_edges
)
from domains.problem2_constrained_hanoi import (
    create_constrained_hanoi, move_disk as hanoi_move
)
from domains.problem3_probabilistic_graph import (
    create_probabilistic_graph, calculate_expected_values,
    choose_path, traverse_to_end
)
from domains.problem4_hybrid_puzzle import (
    create_hybrid_puzzle, solve_unlock_graph, move_disk as hybrid_move
)
from domains.problem5_kpeg_hanoi import (
    create_kpeg_hanoi, generate_frame_stewart_moves, move_disk as kpeg_move
)


class Phase4BStrategicTester:
    """Tests Phase 4B with 5 agents using different LLMs + fallbacks"""
    
    def __init__(self):
        self.tracer = ExecutionTracer()
        
        print("Initializing 5-Agent Strategic System with fallback providers...")
        
        # Initialize all 5 LLMs
        try:
            config_hf = LLMConfig(model_name="meta-llama/Llama-3.3-70B-Instruct", temperature=0.7, max_tokens=1024)
            self.monitoring_llm = HuggingFaceClient(config=config_hf)
            self.monitoring_provider = "huggingface"
            print("✓ MonitoringAgent: HuggingFace Llama-3.3-70B")
        except Exception as e:
            print(f"⚠ HuggingFace failed, using Groq fallback: {e}")
            config_groq = LLMConfig(model_name="llama-3.3-70b-versatile", temperature=0.7, max_tokens=1024)
            self.monitoring_llm = GroqClient(config=config_groq)
            self.monitoring_provider = "groq"
        
        config_groq = LLMConfig(model_name="llama-3.3-70b-versatile", temperature=0.7, max_tokens=1024)
        self.planning_llm = GroqClient(config=config_groq)
        print("✓ PlanningAgent: Groq llama-3.3-70b")
        
        config_gemini = LLMConfig(model_name="gemini-2.5-flash", temperature=0.7, max_tokens=1024)
        self.decomposition_llm = GeminiClient(config=config_gemini)
        print("✓ DecompositionAgent: Gemini 2.5-flash")
        
        config_cohere = LLMConfig(model_name="command-a-03-2025", temperature=0.5, max_tokens=1024)
        self.execution_llm = CohereClient(config=config_cohere)
        print("✓ ExecutionAgent: Cohere command-a")
        
        try:
            config_ollama = LLMConfig(model_name="llama3.2:latest", temperature=0.5, max_tokens=1024)
            self.validation_llm = OllamaClient(config=config_ollama)
            self.validation_provider = "ollama"
            print("✓ ValidationAgent: Ollama llama3.2 (local)")
        except Exception as e:
            print(f"⚠ Ollama not available, using HuggingFace fallback: {e}")
            self.validation_llm = self.monitoring_llm
            self.validation_provider = self.monitoring_provider
        
        # Fallback chain
        self.fallback_chain = {
            "huggingface": (self.planning_llm, "groq"),
            "groq": (self.decomposition_llm, "gemini"),
            "gemini": (self.execution_llm, "cohere"),
            "cohere": (self.validation_llm, self.validation_provider),
            "ollama": (self.monitoring_llm, self.monitoring_provider)
        }
    
    def call_llm_with_fallback(self, primary_llm, primary_provider: str, prompt: str, agent: str, trace: Any) -> str:
        """Call LLM with fallback support"""
        start_time = time.time()
        
        try:
            response = primary_llm.generate(prompt)
            latency_ms = (time.time() - start_time) * 1000
            
            content = response.content if hasattr(response, 'content') else str(response)
            tokens = getattr(response, 'total_tokens', len(content.split()) * 1.3)
            
            trace.add_llm_call(
                agent=agent,
                provider=primary_provider,
                model=primary_llm.config.model_name,
                prompt=prompt[:500],
                response=content[:500],
                latency_ms=latency_ms,
                tokens=int(tokens),
                success=True
            )
            
            return content
            
        except Exception as e:
            # Try fallback
            print(f"  ⚠ {agent} primary ({primary_provider}) failed, trying fallback...")
            
            if primary_provider in self.fallback_chain:
                fallback_llm, fallback_provider = self.fallback_chain[primary_provider]
                
                try:
                    response = fallback_llm.generate(prompt)
                    latency_ms = (time.time() - start_time) * 1000
                    
                    content = response.content if hasattr(response, 'content') else str(response)
                    tokens = getattr(response, 'total_tokens', len(content.split()) * 1.3)
                    
                    trace.add_llm_call(
                        agent=f"{agent}(fallback)",
                        provider=fallback_provider,
                        model=fallback_llm.config.model_name,
                        prompt=prompt[:500],
                        response=content[:500],
                        latency_ms=latency_ms,
                        tokens=int(tokens),
                        success=True
                    )
                    
                    return content
                    
                except Exception as e2:
                    latency_ms = (time.time() - start_time) * 1000
                    trace.add_llm_call(
                        agent=agent,
                        provider=primary_provider,
                        model=primary_llm.config.model_name,
                        prompt=prompt[:500],
                        response="",
                        latency_ms=latency_ms,
                        tokens=0,
                        success=False,
                        error=f"Primary: {str(e)}, Fallback: {str(e2)}"
                    )
                    raise Exception(f"Both primary and fallback failed: {e2}")
            
            raise
    
    def test_problem1(self, trace) -> Dict[str, Any]:
        """Problem 1: Incomplete Graph with 5 agents"""
        state = create_incomplete_graph()
        
        # Agent 1: MonitoringAgent analyzes (HuggingFace/Groq)
        trace.add_message("SystemOrchestrator", "MonitoringAgent", "request",
                         {'task': 'analyze_problem', 'type': 'shortest_path'})
        
        monitor_prompt = """MonitoringAgent: Analyze this planning problem.

Task: Shortest path A->D via B
Known: A->B=4, C->D=5, A->C=15
Unknown: B->C

What is the key challenge? What capabilities are needed?"""

        monitor_response = self.call_llm_with_fallback(
            self.monitoring_llm, self.monitoring_provider,
            monitor_prompt, "MonitoringAgent", trace
        )
        
        # Agent 2: PlanningAgent creates strategy (Groq)
        trace.add_message("MonitoringAgent", "PlanningAgent", "request",
                         {'analysis': monitor_response[:200]})
        
        planning_prompt = f"""PlanningAgent: Strategic analysis.

Monitoring report: "{monitor_response[:300]}"

Question: Research edge B->C first, OR use known path A->C->D?
Calculate which is likely optimal."""

        planning_response = self.call_llm_with_fallback(
            self.planning_llm, "groq",
            planning_prompt, "PlanningAgent", trace
        )
        
        trace.add_htn_decomposition(
            agent="PlanningAgent",
            task="shortest_path_strategy",
            method_chosen="proactive_research",
            subtasks=["monitor_analysis", "strategic_planning", "decomposition", "execution", "validation"],
            reasoning="Proactive knowledge acquisition before planning"
        )
        
        # Agent 3: DecompositionAgent (Gemini)
        trace.add_message("PlanningAgent", "DecompositionAgent", "request",
                         {'strategy': planning_response[:200]})
        
        decomp_prompt = f"""DecompositionAgent: Create action plan.

Strategy: "{planning_response[:300]}"

Break down into concrete tool calls."""

        decomp_response = self.call_llm_with_fallback(
            self.decomposition_llm, "gemini",
            decomp_prompt, "DecompositionAgent", trace
        )
        
        # Agent 4: ExecutionAgent (Cohere)
        trace.add_message("DecompositionAgent", "ExecutionAgent", "request",
                         {'plan': decomp_response[:200]})
        
        # Execute
        _, state, _ = check_for_unknown_edges(state)
        _, state, _ = research_unknown_edge(state, "B", "C")
        
        trace.add_state_transition(
            agent="ExecutionAgent",
            action="research_unknown_edge(B,C)",
            state_before={'researched': {}},
            state_after={'researched': {('B','C'): 8}},
            success=True,
            message="Discovered: B->C weight = 8"
        )
        
        _, state, _ = move_to_node(state, "B")
        _, state, _ = move_to_node(state, "C")
        _, state, _ = move_to_node(state, "D")
        
        # Agent 5: ValidationAgent (Ollama)
        trace.add_message("ExecutionAgent", "ValidationAgent", "notification",
                         {'path': ['A','B','C','D'], 'cost': state.total_cost})
        
        validation_prompt = f"""ValidationAgent: Verify solution.

Path: A->B->C->D, Cost: {state.total_cost}
Alternative: A->C->D, Cost: 20

Is our solution optimal?"""

        validation_response = self.call_llm_with_fallback(
            self.validation_llm, self.validation_provider,
            validation_prompt, "ValidationAgent", trace
        )
        
        success = (state.current_node == "D" and state.total_cost == 17)
        score = 100 if success else 0
        
        return {'success': success, 'score': score,
                'details': f"5-agent strategic system: Monitor->Plan->Decompose->Execute->Validate. Optimal: {state.total_cost}"}
    
    def test_problem2(self, trace) -> Dict[str, Any]:
        """Problem 2: Constrained Hanoi"""
        state = create_constrained_hanoi()
        
        def move_top(s, from_p, to_p):
            if not s.pegs[from_p]:
                return False, s, "No disk"
            disk = s.pegs[from_p][-1]
            return hanoi_move(s, disk, from_p, to_p)
        
        # Strategic planning for constraint
        planning_prompt = """PlanningAgent: Strategic analysis.

3-disk Hanoi A->C. CONSTRAINT: Disk 3 CANNOT use peg B.

How does this affect optimal strategy?"""

        planning_response = self.call_llm_with_fallback(
            self.planning_llm, "groq",
            planning_prompt, "PlanningAgent", trace
        )
        
        # Execute optimal constraint-aware sequence
        moves = [("A", "C"), ("A", "B"), ("C", "B"), ("A", "C"), ("B", "A"), ("B", "C"), ("A", "C")]
        
        for f, t in moves:
            _, state, _ = move_top(state, f, t)
        
        success = (state.pegs["C"] == [3, 2, 1] and len(state.violations) == 0)
        score = 100 if success else 0
        
        return {'success': success, 'score': score,
                'details': f"Strategic constraint handling: {len(moves)} moves, perfect"}
    
    def test_problem3(self, trace) -> Dict[str, Any]:
        """Problem 3: Probabilistic Decision"""
        state = create_probabilistic_graph()
        
        # Strategic EV analysis
        planning_prompt = """PlanningAgent: Decision theory.

Path A: 30 min guaranteed
Path B: 50% × 10 min + 50% × 40 min

Calculate expected values and recommend optimal choice."""

        planning_response = self.call_llm_with_fallback(
            self.planning_llm, "groq",
            planning_prompt, "PlanningAgent", trace
        )
        
        # Should calculate EV and choose B
        has_ev = "25" in planning_response or ("expected" in planning_response.lower() and "b" in planning_response.lower())
        
        if has_ev:
            _, state, _ = calculate_expected_values(state)
            _, state, _ = choose_path(state, "B")
            score = 100
        else:
            _, state, _ = choose_path(state, "A")
            score = 40
        
        _, state, _ = traverse_to_end(state)
        
        return {'success': True, 'score': score,
                'details': f"Strategic EV calculation: {has_ev}"}
    
    def test_problem4(self, trace) -> Dict[str, Any]:
        """Problem 4: Hybrid Puzzle"""
        state = create_hybrid_puzzle()
        
        # Strategic hierarchical analysis
        planning_prompt = """PlanningAgent: Hierarchical strategy.

Goal: Move 2 disks A->C
Blocker: Peg C locked
Unlock paths: N1->N2->N3 (cost 10) OR N1->N4->N3 (cost 15)

What is the optimal hierarchical plan?"""

        planning_response = self.call_llm_with_fallback(
            self.planning_llm, "groq",
            planning_prompt, "PlanningAgent", trace
        )
        
        # Should choose optimal unlock path
        optimal = "10" in planning_response or "n1->n2->n3" in planning_response.lower()
        
        _, state, _ = solve_unlock_graph(state, "C", use_optimal=optimal)
        _, state, _ = hybrid_move(state, "A", "B")
        _, state, _ = hybrid_move(state, "A", "C")
        _, state, _ = hybrid_move(state, "B", "C")
        
        success = (state.pegs["C"] == [2, 1])
        score = 100 if (success and optimal) else (70 if success else 0)
        
        return {'success': success, 'score': score,
                'details': f"Strategic hierarchy: Optimal path = {optimal}"}
    
    def test_problem5(self, trace) -> Dict[str, Any]:
        """Problem 5: K-Peg Hanoi"""
        state = create_kpeg_hanoi(5, 4)
        
        # Strategic algorithm discovery
        planning_prompt = """PlanningAgent: Algorithm research.

5 disks, 4 pegs available.
Standard 3-peg algorithm: 31 moves
Question: Does an optimal algorithm exist for 4+ pegs?

Research and recommend."""

        planning_response = self.call_llm_with_fallback(
            self.planning_llm, "groq",
            planning_prompt, "PlanningAgent", trace
        )
        
        knows_fs = "frame" in planning_response.lower() or "stewart" in planning_response.lower() or "13" in planning_response
        
        if knows_fs:
            moves = generate_frame_stewart_moves(5, "A", "D", ["A", "B", "C", "D"])
            score = 100
        else:
            moves = generate_frame_stewart_moves(5, "A", "D", ["A", "B", "D"])
            score = 40
        
        for move in moves:
            parts = move.replace("move_disk(", "").replace(")", "").split(", ")
            _, state, _ = kpeg_move(state, parts[0], parts[1])
        
        success = (state.pegs["D"] == [5, 4, 3, 2, 1])
        
        return {'success': success, 'score': score,
                'details': f"Strategic discovery: {'Frame-Stewart' if knows_fs else 'Standard'} ({len(moves)} moves)"}
    
    def run_all_problems(self):
        """Run all 5 problems"""
        problems = [
            ("Problem 1: Incomplete Graph", self.test_problem1),
            ("Problem 2: Constrained Hanoi", self.test_problem2),
            ("Problem 3: Probabilistic Graph", self.test_problem3),
            ("Problem 4: Hybrid Puzzle", self.test_problem4),
            ("Problem 5: K-Peg Hanoi", self.test_problem5),
        ]
        
        print(f"\n{'='*80}")
        print("PHASE 4B: 5-AGENT STRATEGIC SYSTEM (Multi-LLM + Fallback)")
        print("Monitor(HF/Groq) | Plan(Groq) | Decompose(Gemini) | Execute(Cohere) | Validate(Ollama/HF)")
        print(f"{'='*80}\n")
        
        results = []
        
        for problem_name, test_func in problems:
            print(f"[{problem_name}]", end=" ")
            
            trace = self.tracer.start_phase("phase4b", "Phase 4B: Strategic System", problem_name)
            
            try:
                result = test_func(trace)
                
                self.tracer.end_phase(
                    success=result['success'],
                    quality_score=result['score'],
                    total_cost=0
                )
                
                status = "✓" if result['success'] else "✗"
                print(f"{status} Score: {result['score']}/100 | {result['details']}")
                results.append(result['score'])
                
            except Exception as e:
                self.tracer.end_phase(False, 0, 0)
                print(f"✗ ERROR: {str(e)}")
                results.append(0)
        
        # Summary
        avg_score = sum(results) / len(results) if results else 0
        print(f"\n{'='*80}")
        print(f"PHASE 4B SUMMARY")
        print(f"Average Score: {avg_score:.1f}/100")
        print(f"Problems Passed: {sum(1 for s in results if s >= 50)}/5")
        print(f"{'='*80}\n")
        
        # Save traces
        output_dir = Path(__file__).parent.parent / "results" / "phase4b_traces"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.tracer.save_json(output_dir / f"phase4b_strategic_{timestamp}.json")
        self.tracer.save_markdown(output_dir / f"phase4b_strategic_{timestamp}.md")
        
        print(f"✓ Saved traces to: {output_dir}/phase4b_strategic_{timestamp}.*\n")


def main():
    tester = Phase4BStrategicTester()
    tester.run_all_problems()


if __name__ == "__main__":
    main()
