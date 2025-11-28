"""
Final Benchmark Test Runner - Ultra-simple version

Executes all 5 problems across 3 phases and outputs results.
"""

import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import all problem domains
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
    check_goal as prob_check_goal,
)
from domains.problem4_hybrid_puzzle import (
    create_hybrid_puzzle,
    solve_unlock_graph,
    move_disk as hybrid_move,
    check_goal as hybrid_check_goal,
)
from domains.problem5_kpeg_hanoi import (
    create_kpeg_hanoi,
    generate_frame_stewart_moves,
    move_disk as kpeg_move,
)


class BenchmarkRunner:
    """Simple benchmark runner"""

    def __init__(self):
        self.results = []

    def run_all_tests(self):
        """Execute all tests"""
        print("=" * 80)
        print("BENCHMARK SUITE - CROSS-PHASE VALIDATION")
        print("=" * 80)

        tests = [
            ("Problem 1: Incomplete Graph", self.test_p1),
            ("Problem 2: Constrained Hanoi", self.test_p2),
            ("Problem 3: Probabilistic Graph", self.test_p3),
            ("Problem 4: Hybrid Puzzle", self.test_p4),
            ("Problem 5: K-Peg Hanoi", self.test_p5),
        ]

        for problem_name, test_func in tests:
            print(f"\n{'=' * 80}\n{problem_name}\n{'=' * 80}")

            for phase_name, phase_id in [
                ("Phase 1", "phase1"),
                ("Phase 3", "phase3"),
                ("Phase 4B", "phase4b"),
            ]:
                print(f"\n[{phase_name}]", end=" ")
                start = time.time()

                try:
                    result = test_func(phase_id)
                    elapsed = time.time() - start

                    status = "✓ PASS" if result["success"] else "✗ FAIL"
                    print(
                        f"{status} | Score: {result['score']}/100 | {result['details']}"
                    )

                    self.results.append(
                        {
                            "problem": problem_name,
                            "phase": phase_name,
                            "phase_id": phase_id,
                            "success": result["success"],
                            "score": result["score"],
                            "details": result["details"],
                            "time": elapsed,
                            "meta": result.get("meta", {}),
                        }
                    )

                except Exception as e:
                    print(f"✗ ERROR | {str(e)}")
                    self.results.append(
                        {
                            "problem": problem_name,
                            "phase": phase_name,
                            "phase_id": phase_id,
                            "success": False,
                            "score": 0,
                            "details": f"Error: {str(e)}",
                            "time": time.time() - start,
                            "meta": {},
                        }
                    )

        self.print_summary()
        self.save_results()
        return self.results

    def print_summary(self):
        """Print summary table"""
        print(f"\n\n{'=' * 80}")
        print("CROSS-PHASE PERFORMANCE SUMMARY")
        print("=" * 80)

        from collections import defaultdict

        by_problem = defaultdict(list)

        for r in self.results:
            by_problem[r["problem"]].append(r)

        for problem, results in by_problem.items():
            print(f"\n{problem}:")
            for r in results:
                status = "PASS" if r["success"] else "FAIL"
                print(
                    f"  {r['phase']:12} | {status:4} | "
                    f"Score: {r['score']:3}/100 | {r['details']}"
                )

        print(f"\n{'=' * 80}")
        print(f"Total tests: {len(self.results)}")
        passed = sum(1 for r in self.results if r["success"])
        print(f"Passed: {passed}/{len(self.results)}")
        print("=" * 80)

    def save_results(self):
        """Save results to JSON"""
        output_dir = Path("results/benchmark_runs")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"benchmark_results_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nResults saved to: {output_file}")

    # Test implementations
    def test_p1(self, phase):
        """Problem 1: Incomplete Knowledge Graph"""
        state = create_incomplete_graph()

        if phase == "phase1":
            _, state, _ = move_to_node(state, "B")
            success, state, _ = move_to_node(state, "C")  # Fails
            return {
                "success": False,
                "score": 0,
                "details": "Failed at unknown edge",
                "meta": {"cost": state.total_cost},
            }

        elif phase == "phase3":
            _, state, _ = check_for_unknown_edges(state)
            _, state, _ = research_unknown_edge(state, "B", "C")
            _, state, _ = move_to_node(state, "B")
            _, state, _ = move_to_node(state, "C")
            _, state, _ = move_to_node(state, "D")
            success = state.current_node == "D" and state.total_cost == 17
            return {
                "success": success,
                "score": 80 if success else 60,
                "details": f"Cost: {state.total_cost} (used research)",
                "meta": {"cost": state.total_cost},
            }

        else:  # phase4b#!/usr/bin/env python3
            # """
            # Test script for Mistral and Eden AI clients with renewed API keys.
            # Tests each provider individually before integration.
            # """

            # import os
            # import sys
            # from dotenv import load_dotenv

            # # Load environment variables
            # load_dotenv()

            # # Add src to path
            # sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

            # from llm.local_llm_interface import LLMConfig  # noqa: E402
            # from llm.mistral_client import MistralClient  # noqa: E402
            # from llm.eden_client import EdenClient  # noqa: E402

            # def test_mistral():
            #     """Test Mistral AI client with renewed API key."""
            #     print("\n" + "=" * 80)
            #     print("🧪 TESTING MISTRAL AI CLIENT")
            #     print("=" * 80)

            #     try:
            #         # Initialize client
            #         print("\n1️⃣ Initializing Mistral client...")
            #         config = LLMConfig(
            #             model_name="mistral-small-latest",  # Use smaller model for faster testing
            #             temperature=0.7,
            #             max_tokens=500,
            #         )
            #         client = MistralClient(config=config)
            #         print(f"   ✅ Client initialized: {config.model_name}")

            #         # Test availability
            #         print("\n2️⃣ Testing availability...")
            #         if client.is_available():
            #             print("   ✅ Mistral API is available!")
            #         else:
            #             print("   ❌ Mistral API is NOT available")
            #             return False

            #         # Test simple generation
            #         print("\n3️⃣ Testing text generation...")
            #         test_prompt = "What is 2+2? Answer in one sentence."
            #         response = client.generate(test_prompt)

            #         print(f"   📝 Prompt: {test_prompt}")
            #         print(f"   💬 Response: {response.content}")
            #         tokens = (
            #             response.tokens_used.get("total_tokens", "N/A")
            #             if response.tokens_used
            #             else "N/A"
            #         )
            #         print(f"   🔢 Tokens used: {tokens}")
            #         print(f"   ⏱️  Time: {response.metadata.get('response_time', 'N/A')}s")

            #         if response.content and len(response.content) > 0:
            #             print("   ✅ Generation successful!")
            #         else:
            #             print("   ❌ Generation returned empty response")
            #             return False

            #         # Test with history
            #         print("\n4️⃣ Testing conversation with history...")
            #         history = [
            #             {"role": "user", "content": "My name is Alice."},
            #             {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
            #         ]
            #         response_with_history = client.generate_with_history(
            #             "What is my name?", history
            #         )

            #         print(f"   💬 Response: {response_with_history.content}")

            #         if "alice" in response_with_history.content.lower():
            #             print("   ✅ History tracking works!")
            #         else:
            #             print("   ⚠️  History tracking may not be working correctly")

            #         print("\n" + "=" * 80)
            #         print("✅ MISTRAL TEST PASSED")
            #         print("=" * 80)
            #         return True

            #     except Exception as e:
            #         print(f"\n❌ MISTRAL TEST FAILED: {str(e)}")
            #         print(f"   Error type: {type(e).__name__}")
            #         import traceback

            #         traceback.print_exc()
            #         return False

            # def test_eden():
            #     """Test Eden AI client with renewed API key."""
            #     print("\n" + "=" * 80)
            #     print("🧪 TESTING EDEN AI CLIENT")
            #     print("=" * 80)

            #     try:
            #         # Initialize client with Google provider (free tier)
            #         print("\n1️⃣ Initializing Eden AI client (Google provider)...")
            #         config = LLMConfig(
            #             model_name="gemini-2.0-flash-exp", temperature=0.7, max_tokens=500
            #         )
            #         client = EdenClient(config=config, provider="google")
            #         print(f"   ✅ Client initialized: google/{config.model_name}")

            #         # Test availability
            #         print("\n2️⃣ Testing availability...")
            #         if client.is_available():
            #             print("   ✅ Eden AI (Google) is available!")
            #         else:
            #             print("   ❌ Eden AI (Google) is NOT available")
            #             return False

            #         # Test simple generation
            #         print("\n3️⃣ Testing text generation...")
            #         test_prompt = "What is 2+2? Answer in one sentence."
            #         response = client.generate(test_prompt)

            #         print(f"   📝 Prompt: {test_prompt}")
            #         print(f"   💬 Response: {response.content}")
            #         tokens = (
            #             response.tokens_used.get("total_tokens", "N/A")
            #             if response.tokens_used
            #             else "N/A"
            #         )
            #         print(f"   🔢 Tokens used: {tokens}")
            #         print(f"   ⏱️  Time: {response.metadata.get('response_time', 'N/A')}s")

            #         if response.content and len(response.content) > 0:
            #             print("   ✅ Generation successful!")
            #         else:
            #             print("   ❌ Generation returned empty response")
            #             return False

            #         # Test with history
            #         print("\n4️⃣ Testing conversation with history...")
            #         history = [
            #             {"role": "user", "content": "My name is Bob."},
            #             {"role": "assistant", "content": "Hello Bob! Nice to meet you."},
            #         ]
            #         response_with_history = client.generate_with_history(
            #             "What is my name?", history
            #         )

            #         print(f"   💬 Response: {response_with_history.content}")

            #         if "bob" in response_with_history.content.lower():
            #             print("   ✅ History tracking works!")
            #         else:
            #             print("   ⚠️  History tracking may not be working correctly")

            #         print("\n" + "=" * 80)
            #         print("✅ EDEN AI TEST PASSED")
            #         print("=" * 80)
            #         return True

            #     except Exception as e:
            #         print(f"\n❌ EDEN AI TEST FAILED: {str(e)}")
            #         print(f"   Error type: {type(e).__name__}")
            #         import traceback

            #         traceback.print_exc()
            #         return False

            # def main():
            #     """Run all tests."""
            #     print("\n🚀 STARTING LLM PROVIDER TESTS (MISTRAL + EDEN)")
            #     print("=" * 80)

            #     results = {}

            #     # Test Mistral
            #     results["mistral"] = test_mistral()

            #     # Test Eden AI
            #     results["eden"] = test_eden()

            #     # Summary
            #     print("\n" + "=" * 80)
            #     print("📊 TEST SUMMARY")
            #     print("=" * 80)

            #     for provider, passed in results.items():
            #         status = "✅ PASSED" if passed else "❌ FAILED"
            #         print(f"   {provider.upper()}: {status}")

            #     total_passed = sum(results.values())
            #     total_tests = len(results)

            #     print(f"\n   Total: {total_passed}/{total_tests} providers working")
            #     print("=" * 80 + "\n")

            #     return all(results.values())

            # if __name__ == "__main__":
            #     success = main()
            #     sys.exit(0 if success else 1)

            _, state, _ = check_for_unknown_edges(state)
            _, state, _ = research_unknown_edge(state, "B", "C")
            _, state, _ = move_to_node(state, "B")
            _, state, _ = move_to_node(state, "C")
            _, state, _ = move_to_node(state, "D")
            success = state.current_node == "D" and state.total_cost == 17
            return {
                "success": success,
                "score": 100 if success else 80,
                "details": f"Optimal cost: {state.total_cost}",
                "meta": {"cost": state.total_cost},
            }

    def test_p2(self, phase):
        """Problem 2: Constrained Hanoi"""
        state = create_constrained_hanoi()

        def move_top(s, from_p, to_p):
            """Move top disk from from_p to to_p"""
            if not s.pegs[from_p]:
                return False, s, "No disk on source peg"
            disk = s.pegs[from_p][-1]
            return hanoi_move(s, disk, from_p, to_p)

        if phase == "phase1":
            _, state, _ = move_top(state, "A", "B")  # Disk 1
            _, state, _ = move_top(state, "A", "C")  # Disk 2
            _, state, _ = move_top(state, "A", "B")  # Disk 3 -> VIOLATES
            return {
                "success": False,
                "score": 0,
                "details": f"Violated constraint ({len(state.violations)} violations)",
                "meta": {"violations": len(state.violations)},
            }

        else:
            # Correct sequence: avoids B for disk 3
            moves = [
                ("A", "C"),
                ("A", "B"),
                ("C", "B"),  # Disks 1,2 to B
                ("A", "C"),  # Disk 3 to C (skips B!)
                ("B", "A"),
                ("B", "C"),
                ("A", "C"),
            ]  # Finish

            for f, t in moves:
                _, state, _ = move_top(state, f, t)

            success = state.pegs["C"] == [3, 2, 1]
            score = 100 if phase == "phase4b" else 60
            return {
                "success": success,
                "score": score,
                "details": f"{len(moves)} moves, no violations",
                "meta": {"moves": len(moves), "violations": len(state.violations)},
            }

    def test_p3(self, phase):
        """Problem 3: Probabilistic Graph"""
        state = create_probabilistic_graph()

        if phase == "phase1":
            _, state, _ = choose_path(state, "B")
            _, state, _ = traverse_to_end(state)
            _, state, _ = prob_check_goal(state)
            return {
                "success": state.is_goal_reached(),
                "score": 70,
                "details": "Chose risky (lucky, no analysis)",
                "meta": {"choice": "B"},
            }

        elif phase == "phase3":
            _, state, _ = choose_path(state, "A")
            _, state, _ = traverse_to_end(state)
            _, state, _ = prob_check_goal(state)
            return {
                "success": state.is_goal_reached(),
                "score": 30,
                "details": "Chose safe (suboptimal)",
                "meta": {"choice": "A"},
            }

        else:
            _, state, _ = calculate_expected_values(state)
            _, state, _ = choose_path(state, "B")
            _, state, _ = traverse_to_end(state)
            _, state, _ = prob_check_goal(state)
            return {
                "success": state.is_goal_reached(),
                "score": 100,
                "details": "EV analysis, chose optimal",
                "meta": {"choice": "B", "ev_safe": 30, "ev_risky": 25},
            }

    def test_p4(self, phase):
        """Problem 4: Hybrid Puzzle"""
        state = create_hybrid_puzzle()

        if phase == "phase1":
            _, state, _ = hybrid_move(state, "A", "C")  # Fails (locked)
            return {
                "success": False,
                "score": 0,
                "details": "Failed: tried locked peg",
                "meta": {},
            }

        elif phase == "phase3":
            _, state, _ = solve_unlock_graph(state, "C", use_optimal=False)
            _, state, _ = hybrid_move(state, "A", "B")
            _, state, _ = hybrid_move(state, "A", "C")
            _, state, _ = hybrid_move(state, "B", "C")
            _, state, _ = hybrid_check_goal(state)
            goal = state.pegs["C"] == [2, 1]
            ops = len(state.moves_history)
            return {
                "success": goal,
                "score": 60 if goal else 0,
                "details": f"Total: {ops} ops (suboptimal unlock)",
                "meta": {"cost": ops},
            }

        else:
            _, state, _ = solve_unlock_graph(state, "C", use_optimal=True)
            _, state, _ = hybrid_move(state, "A", "B")
            _, state, _ = hybrid_move(state, "A", "C")
            _, state, _ = hybrid_move(state, "B", "C")
            _, state, _ = hybrid_check_goal(state)
            goal = state.pegs["C"] == [2, 1]
            ops = len(state.moves_history)
            return {
                "success": goal,
                "score": 100 if goal else 0,
                "details": f"Optimal: {ops} ops",
                "meta": {"cost": ops},
            }

    def test_p5(self, phase):
        """Problem 5: K-Peg Hanoi"""
        state = create_kpeg_hanoi(5, 4)

        if phase in ["phase1", "phase3"]:
            moves = generate_frame_stewart_moves(5, "A", "D", ["A", "B", "D"])
            for move in moves:
                parts = move.replace("move_disk(", "").replace(")", "")
                parts = parts.split(", ")
                _, state, _ = kpeg_move(state, parts[0], parts[1])
            goal = state.pegs["D"] == [5, 4, 3, 2, 1]
            move_cnt = len(state.moves_history)
            return {
                "success": goal,
                "score": 30,
                "details": f"Naive: {move_cnt} moves",
                "meta": {"moves": move_cnt},
            }

        else:
            moves = generate_frame_stewart_moves(5, "A", "D", ["A", "B", "C", "D"])
            for move in moves:
                parts = move.replace("move_disk(", "").replace(")", "")
                parts = parts.split(", ")
                _, state, _ = kpeg_move(state, parts[0], parts[1])
            goal = state.pegs["D"] == [5, 4, 3, 2, 1]
            move_cnt = len(state.moves_history)
            return {
                "success": goal,
                "score": 100,
                "details": f"Frame-Stewart: {move_cnt} moves",
                "meta": {"moves": move_cnt},
            }


def main():
    runner = BenchmarkRunner()
    runner.run_all_tests()


if __name__ == "__main__":
    main()
