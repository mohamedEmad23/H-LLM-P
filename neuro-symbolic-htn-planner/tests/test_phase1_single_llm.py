"""
Phase 1: Single LLM Benchmark
==============================

Tests basic reasoning capabilities of different LLM providers on all 5 problems.
Each provider is tested independently to compare performance.

Providers tested:
- Groq (llama-3.3-70b-versatile) - Fast inference
- Cohere (command-a-03-2025) - Enterprise API
- Gemini (gemini-2.5-flash) - Google's latest
- Ollama (llama3.2:latest) - Local model
- HuggingFace (meta-llama/Llama-3.3-70B-Instruct) - Open source hub

Usage:
    # Test all providers
    python tests/test_phase1_single_llm.py --provider all
    
    # Test specific provider
    python tests/test_phase1_single_llm.py --provider groq
    python tests/test_phase1_single_llm.py --provider cohere
    python tests/test_phase1_single_llm.py --provider gemini
    python tests/test_phase1_single_llm.py --provider ollama
    python tests/test_phase1_single_llm.py --provider huggingface

Output: results/phase1_traces/phase1_{provider}_{timestamp}.json
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.execution_tracer import ExecutionTracer
from llm.groq_client import GroqClient
from llm.cohere_client import CohereClient
from llm.gemini_client import GeminiClient
from llm.ollama_client import OllamaClient
from llm.huggingface_client import HuggingFaceClient
from llm.local_llm_interface import LLMConfig

# Import problem domains
from domains.problem1_incomplete_graph import create_incomplete_graph
from domains.problem2_constrained_hanoi import create_constrained_hanoi
from domains.problem3_probabilistic_graph import create_probabilistic_graph
from domains.problem4_hybrid_puzzle import create_hybrid_puzzle
from domains.problem5_kpeg_hanoi import create_kpeg_hanoi


class Phase1Tester:
    """Tests Phase 1 (Single LLM) with different providers"""
    
    def __init__(self, provider: str):
        self.provider = provider
        self.tracer = ExecutionTracer()
        self.llm = self._initialize_llm(provider)
        
    def _initialize_llm(self, provider: str):
        """Initialize LLM client based on provider"""
        try:
            if provider == "groq":
                config = LLMConfig(model_name="llama-3.3-70b-versatile", temperature=0.7, max_tokens=2048)
                llm = GroqClient(config=config)
                print(f"✓ Initialized Groq: llama-3.3-70b-versatile")
                
            elif provider == "cohere":
                config = LLMConfig(model_name="command-a-03-2025", temperature=0.7, max_tokens=2048)
                llm = CohereClient(config=config)
                print(f"✓ Initialized Cohere: command-a-03-2025")
                
            elif provider == "gemini":
                config = LLMConfig(model_name="gemini-2.5-flash", temperature=0.7, max_tokens=2048)
                llm = GeminiClient(config=config)
                print(f"✓ Initialized Gemini: gemini-2.5-flash")
                
            elif provider == "ollama":
                config = LLMConfig(model_name="llama3.2:latest", temperature=0.7, max_tokens=2048)
                llm = OllamaClient(config=config)
                print(f"✓ Initialized Ollama: llama3.2:latest (local)")
                
            elif provider == "huggingface":
                config = LLMConfig(model_name="meta-llama/Llama-3.3-70B-Instruct", temperature=0.7, max_tokens=2048)
                llm = HuggingFaceClient(config=config)
                print(f"✓ Initialized HuggingFace: Llama-3.3-70B")
                
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
            return llm
            
        except Exception as e:
            print(f"✗ Failed to initialize {provider}: {e}")
            raise
    
    def call_llm(self, prompt: str, trace: Any) -> str:
        """Make LLM API call and log it"""
        start_time = time.time()
        
        try:
            response = self.llm.generate(prompt)
            latency_ms = (time.time() - start_time) * 1000
            
            content = response.content if hasattr(response, 'content') else str(response)
            tokens = getattr(response, 'total_tokens', len(content.split()) * 1.3)  # Estimate if not available
            
            trace.add_llm_call(
                agent="SingleLLM",
                provider=self.provider,
                model=self.llm.config.model_name,
                prompt=prompt[:500],
                response=content[:500],
                latency_ms=latency_ms,
                tokens=int(tokens),
                success=True
            )
            
            return content
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            trace.add_llm_call(
                agent="SingleLLM",
                provider=self.provider,
                model=self.llm.config.model_name,
                prompt=prompt[:500],
                response="",
                latency_ms=latency_ms,
                tokens=0,
                success=False,
                error=str(e)
            )
            raise
    
    def test_problem1(self, trace) -> Dict[str, Any]:
        """Problem 1: Incomplete Knowledge Graph"""
        _ = create_incomplete_graph()
        
        prompt = """You are solving a shortest path problem.

Current State:
- You are at node A
- Goal: Reach node D, passing through node B
- Known edges: A->B (cost 4), C->D (cost 5), A->C (cost 15)
- Unknown edge: B->C (weight unknown)

Task: Find the shortest path from A to D passing through B.

Think step by step. What actions do you take? What is the challenge?"""

        response = self.call_llm(prompt, trace)
        
        # Evaluate: Does LLM recognize the knowledge gap?
        recognizes_gap = any(word in response.lower() for word in ['unknown', 'don\'t know', 'missing', 'research', 'discover'])
        
        if recognizes_gap:
            score = 20  # Recognizes problem but can't solve
            trace.add_failure_analysis(
                failure_point="knowledge_gap",
                root_cause="Identified unknown edge but no tool to research it",
                missing_capability="Modular tool-calling architecture",
                recovery=False
            )
        else:
            score = 0  # Hallucinates or ignores
            trace.add_failure_analysis(
                failure_point="hallucination",
                root_cause="LLM hallucinated edge weight or ignored unknown",
                missing_capability="Tool integration",
                recovery=False
            )
        
        return {'success': False, 'score': score, 'details': f"Gap recognition: {recognizes_gap}"}
    
    def test_problem2(self, trace) -> Dict[str, Any]:
        """Problem 2: Constrained Hanoi"""
        _ = create_constrained_hanoi()
        
        prompt = """Solve Tower of Hanoi: Move 3 disks from peg A to peg C.

CONSTRAINT: Disk 3 (largest) CANNOT use peg B (it's fragile and will break).

What sequence of moves do you make? Explain your strategy."""

        response = self.call_llm(prompt, trace)
        
        # Evaluate: Does LLM respect the constraint?
        respects_constraint = ('fragile' in response.lower() or 'constraint' in response.lower()) and not ('disk 3' in response.lower() and 'to b' in response.lower())
        
        if respects_constraint:
            score = 40  # Understands but may not execute perfectly
        else:
            score = 0
            trace.add_failure_analysis(
                failure_point="constraint_violation",
                root_cause="Violated constraint: disk 3 on fragile peg B",
                missing_capability="Constraint-aware planning",
                recovery=False
            )
        
        return {'success': respects_constraint, 'score': score, 'details': f"Constraint aware: {respects_constraint}"}
    
    def test_problem3(self, trace) -> Dict[str, Any]:
        """Problem 3: Probabilistic Decision"""
        _ = create_probabilistic_graph()
        
        prompt = """Choose the best path to minimize expected travel time:

Path A (Safe): 30 minutes guaranteed
Path B (Risky): 50% chance of 10 minutes, 50% chance of 40 minutes

Which path should you choose? Show your calculation."""

        response = self.call_llm(prompt, trace)
        
        # Evaluate: Does LLM calculate expected value?
        calculates_ev = any(word in response.lower() for word in ['expected', '25', '0.5', 'probability'])
        chooses_optimal = 'b' in response.lower() or 'risky' in response.lower()
        
        if calculates_ev and chooses_optimal:
            score = 80
        elif calculates_ev:
            score = 60
        else:
            score = 40  # Lucky guess
            trace.add_failure_analysis(
                failure_point="no_ev_calculation",
                root_cause="Did not calculate expected value",
                missing_capability="Probabilistic reasoning",
                recovery=False
            )
        
        return {'success': chooses_optimal, 'score': score, 'details': f"EV calc: {calculates_ev}, Optimal: {chooses_optimal}"}
    
    def test_problem4(self, trace) -> Dict[str, Any]:
        """Problem 4: Hybrid Puzzle"""
        _ = create_hybrid_puzzle()
        
        prompt = """Hybrid planning problem:

Setup:
- 2 disks on peg A, goal is to move them to peg C
- BUT peg C is LOCKED
- To unlock C, you must solve: Navigate graph N1->N2->N3 (each step costs 5)

What is your strategy? What do you do first?"""

        response = self.call_llm(prompt, trace)
        
        # Evaluate: Does LLM recognize hierarchical decomposition?
        recognizes_hierarchy = any(word in response.lower() for word in ['unlock', 'first', 'before', 'graph', 'n1', 'n2', 'n3'])
        
        if recognizes_hierarchy:
            score = 30  # Understands structure
        else:
            score = 0
            trace.add_failure_analysis(
                failure_point="no_hierarchy",
                root_cause="Tried to move disks without unlocking peg",
                missing_capability="Hierarchical decomposition",
                recovery=False
            )
        
        return {'success': recognizes_hierarchy, 'score': score, 'details': f"Hierarchical: {recognizes_hierarchy}"}
    
    def test_problem5(self, trace) -> Dict[str, Any]:
        """Problem 5: K-Peg Hanoi"""
        _ = create_kpeg_hanoi(5, 4)
        
        prompt = """Tower of Hanoi variant:

- 5 disks to move from peg A to peg D
- You have 4 pegs available (not just 3!)
- Standard 3-peg algorithm requires 31 moves
- There exists a more efficient algorithm for 4+ pegs

Question: Do you know of a better algorithm for this case? If so, what is it?"""

        response = self.call_llm(prompt, trace)
        
        # Evaluate: Does LLM know Frame-Stewart algorithm?
        knows_fs = any(word in response.lower() for word in ['frame', 'stewart', '13 moves', 'recursive split'])
        suggests_research = any(word in response.lower() for word in ['research', 'look up', 'optimal', 'better'])
        
        if knows_fs:
            score = 100  # Unlikely but possible
        elif suggests_research:
            score = 50  # Knows there's something better
        else:
            score = 20  # Uses standard algorithm
            trace.add_failure_analysis(
                failure_point="no_algorithm_discovery",
                root_cause="Unaware of Frame-Stewart algorithm for 4+ pegs",
                missing_capability="Strategic synthesis & research",
                recovery=False
            )
        
        return {'success': knows_fs, 'score': score, 'details': f"Knows FS: {knows_fs}, Suggests research: {suggests_research}"}
    
    def run_all_problems(self):
        """Run all 5 problems with this provider"""
        problems = [
            ("Problem 1: Incomplete Graph", self.test_problem1),
            ("Problem 2: Constrained Hanoi", self.test_problem2),
            ("Problem 3: Probabilistic Graph", self.test_problem3),
            ("Problem 4: Hybrid Puzzle", self.test_problem4),
            ("Problem 5: K-Peg Hanoi", self.test_problem5),
        ]
        
        print(f"\n{'='*80}")
        print(f"PHASE 1 TEST: {self.provider.upper()}")
        print(f"Model: {self.llm.config.model_name}")
        print(f"{'='*80}\n")
        
        results = []
        
        for problem_name, test_func in problems:
            print(f"[{problem_name}]", end=" ")
            
            trace = self.tracer.start_phase("phase1", "Phase 1: Single LLM", problem_name)
            
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
        print(f"SUMMARY: {self.provider.upper()}")
        print(f"Average Score: {avg_score:.1f}/100")
        print(f"Problems Passed: {sum(1 for s in results if s >= 50)}/5")
        print(f"{'='*80}\n")
        
        # Save traces
        # Create results directory
        output_dir = Path(__file__).parent.parent / "results" / "phase1_traces"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.tracer.save_json(output_dir / f"phase1_{self.provider}_{timestamp}.json")
        self.tracer.save_markdown(output_dir / f"phase1_{self.provider}_{timestamp}.md")
        
        print(f"✓ Saved traces to: {output_dir}/phase1_{self.provider}_{timestamp}.*\n")


def main():
    parser = argparse.ArgumentParser(description="Phase 1: Single LLM Benchmark")
    parser.add_argument(
        "--provider",
        choices=["all", "groq", "cohere", "gemini", "ollama", "huggingface"],
        default="groq",
        help="LLM provider to test"
    )
    
    args = parser.parse_args()
    
    if args.provider == "all":
        providers = ["groq", "cohere", "gemini", "ollama", "huggingface"]
    else:
        providers = [args.provider]
    
    for provider in providers:
        try:
            tester = Phase1Tester(provider)
            tester.run_all_problems()
        except Exception as e:
            print(f"✗ Failed to test {provider}: {e}\n")
            continue


if __name__ == "__main__":
    main()
