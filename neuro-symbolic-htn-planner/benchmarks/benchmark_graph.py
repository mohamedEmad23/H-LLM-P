"""
Graph Traversal Benchmarking Script

Tests shortest path finding on various graph sizes.
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
from src.domains.graph_traversal.domain import GraphTraversalDomain


async def run_graph_benchmark(graph_type: str, iterations: int = 10):
    """Run benchmark for graph problems"""

    print(f"\n{'=' * 70}")
    print(f"  BENCHMARKING {graph_type.upper()} ({iterations} iterations)")
    print(f"{'=' * 70}\n")

    # Create agents
    print("Initializing agents...")
    llm_decomp = HuggingFaceClient(model_name="meta-llama/Llama-3.3-70B-Instruct")
    llm_verif = HuggingFaceClient(model_name="meta-llama/Llama-3.1-8B-Instruct")

    decomp_agent = DecompositionAgent(llm_client=llm_decomp)
    exec_agent = ExecutionAgent(llm_client=None)
    verif_agent = VerificationAgent(llm_client=llm_verif)

    workflow = CoreWorkflow(
        decomposition_agent=decomp_agent,
        execution_agent=exec_agent,
        verification_agent=verif_agent,
        max_retries=2,
    )

    domain = GraphTraversalDomain()

    # Create test graph based on type
    if graph_type == "simple_3node":
        graph = domain.create_simple_graph([("A", "B"), ("B", "C")])
        start, goal = "A", "C"
        expected_path = ["A", "B", "C"]

    elif graph_type == "diamond_4node":
        graph = domain.create_simple_graph(
            [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
        )
        start, goal = "A", "D"
        expected_path = 3  # Length 3 (A -> B/C -> D)

    elif graph_type == "complex_6node":
        graph = domain.create_simple_graph(
            [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E"), ("E", "F")]
        )
        start, goal = "A", "F"
        expected_path = 5  # Length 5

    else:
        raise ValueError(f"Unknown graph type: {graph_type}")

    initial_state = domain.get_initial_state(graph, start)
    goal_state = {"current_node": goal}

    results = []
    successes = 0
    optimal_paths = 0
    total_time = 0
    total_quality = 0

    for i in range(iterations):
        print(f"\nIteration {i + 1}/{iterations}...")
        start_time = time.time()

        try:
            result = await workflow.process_task(
                {
                    "task": f"find_shortest_path({start}, {goal})",
                    "domain": "graph_traversal",
                    "initial_state": initial_state,
                    "goal": goal_state,
                    "operators": domain.operators,
                    "methods": domain.methods,
                }
            )

            elapsed = time.time() - start_time
            total_time += elapsed

            success = result["success"] and result["goal_achieved"]
            if success:
                successes += 1
                total_quality += result["quality_score"]

                # Check path optimality
                final_state = result.get("final_state", {})
                path_length = len(final_state.get("path", []))

                if isinstance(expected_path, list):
                    is_optimal = path_length == len(expected_path)
                else:
                    is_optimal = path_length == expected_path

                if is_optimal:
                    optimal_paths += 1
                    status = "✅ SUCCESS (OPTIMAL)"
                else:
                    status = (
                        f"✅ SUCCESS (suboptimal: {path_length} vs {expected_path})"
                    )
            else:
                status = "❌ FAILED"

            print(
                f"  {status} - Quality: {result['quality_score']:.1f}, Time: {elapsed:.2f}s"
            )

            results.append(
                {
                    "iteration": i + 1,
                    "success": success,
                    "quality_score": result["quality_score"],
                    "time_seconds": elapsed,
                    "path_length": len(result.get("final_state", {}).get("path", [])),
                    "retry_count": result.get("retry_count", 0),
                }
            )

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append({"iteration": i + 1, "success": False, "error": str(e)})

    # Statistics
    success_rate = (successes / iterations) * 100
    optimal_rate = (optimal_paths / successes * 100) if successes > 0 else 0
    avg_time = total_time / iterations
    avg_quality = total_quality / successes if successes > 0 else 0

    print(f"\n{'=' * 70}")
    print(f"  {graph_type.upper()} SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total Iterations: {iterations}")
    print(f"Successes: {successes}/{iterations} ({success_rate:.1f}%)")
    print(f"Optimal Paths: {optimal_paths}/{successes} ({optimal_rate:.1f}%)")
    print(f"Average Quality: {avg_quality:.1f}/100")
    print(f"Average Time: {avg_time:.2f}s")
    print(f"{'=' * 70}\n")

    return {
        "graph_type": graph_type,
        "iterations": iterations,
        "successes": successes,
        "success_rate": success_rate,
        "optimal_paths": optimal_paths,
        "optimal_rate": optimal_rate,
        "avg_quality": avg_quality,
        "avg_time": avg_time,
        "results": results,
    }


async def main():
    """Run all graph benchmarks"""

    print("\n" + "=" * 70)
    print("  PHASE 4A.7.2: GRAPH TRAVERSAL BENCHMARKING")
    print("=" * 70)

    all_results = {}

    # Simple 3-node graph
    all_results["simple_3node"] = await run_graph_benchmark(
        "simple_3node", iterations=10
    )

    # Diamond 4-node graph
    all_results["diamond_4node"] = await run_graph_benchmark(
        "diamond_4node", iterations=10
    )

    # Complex 6-node graph
    all_results["complex_6node"] = await run_graph_benchmark(
        "complex_6node", iterations=10
    )

    # Save results
    output_file = "results/graph_benchmark_results.json"
    Path("results").mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✅ Benchmark complete! Results saved to {output_file}")

    # Overall summary
    print("\n" + "=" * 70)
    print("  OVERALL SUMMARY")
    print("=" * 70)
    for key, data in all_results.items():
        print(
            f"{data['graph_type']}: {data['success_rate']:.1f}% success, "
            f"{data['optimal_rate']:.1f}% optimal, {data['avg_quality']:.1f} quality, "
            f"{data['avg_time']:.2f}s avg time"
        )
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
