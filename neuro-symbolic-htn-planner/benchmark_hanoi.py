"""
Tower of Hanoi Benchmarking Script

Runs comprehensive benchmarks for 3-disk, 4-disk, 5-disk problems.
Tests the full 3-agent pipeline with real LLMs (no mocks).

NO DOCUMENTATION - Just runs and prints results.
"""

import asyncio
import time
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agents.decomposition_agent import DecompositionAgent
from src.agents.execution_agent import ExecutionAgent
from src.agents.verification_agent import VerificationAgent
from src.agents.workflows.core_workflow import CoreWorkflow
from src.llm.huggingface_client import HuggingFaceClient


async def run_hanoi_benchmark(num_disks: int, iterations: int = 10):
    """Run benchmark for N-disk Tower of Hanoi"""

    print(f"\n{'='*70}")
    print(f"  BENCHMARKING {num_disks}-DISK TOWER OF HANOI ({iterations} iterations)")
    print(f"{'='*70}\n")

    # Create agents with real LLMs
    print("Initializing agents...")
    llm_decomp = HuggingFaceClient(model_name="meta-llama/Llama-3.3-70B-Instruct")
    llm_verif = HuggingFaceClient(model_name="meta-llama/Llama-3.1-8B-Instruct")

    decomp_agent = DecompositionAgent(llm_client=llm_decomp)
    exec_agent = ExecutionAgent(llm_client=None)  # Symbolic only
    verif_agent = VerificationAgent(llm_client=llm_verif)

    workflow = CoreWorkflow(
        decomposition_agent=decomp_agent,
        execution_agent=exec_agent,
        verification_agent=verif_agent,
        max_retries=2,
    )

    # Build initial state and goal
    initial_pegs = {"A": list(range(num_disks, 0, -1)), "B": [], "C": []}
    goal_pegs = {"A": [], "B": [], "C": list(range(num_disks, 0, -1))}
    optimal_steps = 2**num_disks - 1

    results = []
    successes = 0
    total_time = 0
    total_quality = 0

    for i in range(iterations):
        print(f"\nIteration {i+1}/{iterations}...")
        start = time.time()

        try:
            result = await workflow.process_task(
                {
                    "task": f"solve_hanoi({num_disks}, A, C, B)",
                    "domain": "tower_of_hanoi",
                    "initial_state": {"pegs": initial_pegs.copy()},
                    "goal": {"pegs": goal_pegs.copy()},
                    "operators": {
                        "move_disk": {
                            "parameters": ["disk", "from", "to"],
                            "preconditions": ["disk_on_top"],
                            "effects": ["disk_moved"],
                        }
                    },
                    "optimal_steps": optimal_steps,
                }
            )

            elapsed = time.time() - start
            total_time += elapsed

            if result["success"] and result["goal_achieved"]:
                successes += 1
                total_quality += result["quality_score"]
                status = "✅ SUCCESS"
            else:
                status = "❌ FAILED"

            print(
                f"  {status} - Quality: {result['quality_score']:.1f}, Time: {elapsed:.2f}s"
            )

            results.append(
                {
                    "iteration": i + 1,
                    "success": result["success"],
                    "goal_achieved": result["goal_achieved"],
                    "quality_score": result["quality_score"],
                    "time_seconds": elapsed,
                    "plan_length": len(result.get("plan", [])),
                    "optimal_steps": optimal_steps,
                    "retry_count": result.get("retry_count", 0),
                }
            )

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append({"iteration": i + 1, "success": False, "error": str(e)})

    # Calculate statistics
    success_rate = (successes / iterations) * 100
    avg_time = total_time / iterations
    avg_quality = total_quality / successes if successes > 0 else 0

    # Print summary
    print(f"\n{'='*70}")
    print(f"  {num_disks}-DISK HANOI SUMMARY")
    print(f"{'='*70}")
    print(f"Total Iterations: {iterations}")
    print(f"Successes: {successes}/{iterations} ({success_rate:.1f}%)")
    print(f"Average Quality: {avg_quality:.1f}/100")
    print(f"Average Time: {avg_time:.2f}s")
    print(f"Optimal Steps: {optimal_steps}")
    print(f"{'='*70}\n")

    return {
        "num_disks": num_disks,
        "iterations": iterations,
        "successes": successes,
        "success_rate": success_rate,
        "avg_quality": avg_quality,
        "avg_time": avg_time,
        "optimal_steps": optimal_steps,
        "results": results,
    }


async def main():
    """Run all benchmarks"""

    print("\n" + "=" * 70)
    print("  PHASE 4A.7.1: TOWER OF HANOI COMPREHENSIVE BENCHMARKING")
    print("=" * 70)

    all_results = {}

    # 3-disk (target: 90%+)
    all_results["3_disk"] = await run_hanoi_benchmark(3, iterations=10)

    # 4-disk (target: 75%+)
    all_results["4_disk"] = await run_hanoi_benchmark(4, iterations=10)

    # 5-disk (target: 60%+)
    all_results["5_disk"] = await run_hanoi_benchmark(5, iterations=10)

    # Save raw results
    output_file = "results/hanoi_benchmark_results.json"
    Path("results").mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✅ Benchmark complete! Results saved to {output_file}")

    # Print overall summary
    print("\n" + "=" * 70)
    print("  OVERALL SUMMARY")
    print("=" * 70)
    for key, data in all_results.items():
        print(
            f"{data['num_disks']}-disk: {data['success_rate']:.1f}% success, "
            f"{data['avg_quality']:.1f} avg quality, {data['avg_time']:.2f}s avg time"
        )
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
