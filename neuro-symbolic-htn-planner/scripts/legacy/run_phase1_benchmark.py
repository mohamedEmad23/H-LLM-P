#!/usr/bin/env python3
"""
Phase 1 Benchmark Runner
========================

Executes all 5 benchmark problems using Phase 1 architecture (Single LLM + HTN).
Supports multiple LLM providers for comparison.

Usage:
    # Run with default provider (Groq)
    python scripts/run_phase1_benchmark.py

    # Run with specific provider
    python scripts/run_phase1_benchmark.py --provider gemini

    # Run specific problem
    python scripts/run_phase1_benchmark.py --problem hanoi_constrained

    # Run with custom output directory
    python scripts/run_phase1_benchmark.py --output results/custom-run

Author: H-LLM-P Thesis Project
Date: November 14, 2025
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from interface.problem_cli import ProblemLoader, ProblemCLI
from utils.benchmark_logger import BenchmarkLogger
from loguru import logger


class Phase1BenchmarkRunner:
    """Orchestrates Phase 1 benchmark execution across all problems"""

    BENCHMARK_PROBLEMS = [
        "hanoi_constrained",
        "sorting",
        "pathfinding",
        "3sum",
        "resource_allocation",
    ]

    SUPPORTED_PROVIDERS = ["groq", "gemini", "cohere", "ollama", "huggingface"]

    def __init__(
        self,
        provider: str = "groq",
        output_dir: str = "results/phase-1-traces",
        problems_dir: str = "problems",
    ):
        """
        Initialize benchmark runner

        Args:
            provider: LLM provider to use
            output_dir: Directory for benchmark results
            problems_dir: Directory containing YAML problems
        """
        self.provider = provider
        self.output_dir = Path(output_dir)

        # Resolve problems_dir relative to project root
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        self.problems_dir = str(project_root / problems_dir)

        # Initialize components
        self.loader = ProblemLoader(self.problems_dir)
        self.cli = ProblemCLI(self.problems_dir)
        self.benchmark_logger = BenchmarkLogger(str(self.output_dir))

        logger.info("Phase 1 Benchmark Runner initialized")
        logger.info(f"Provider: {provider}")
        logger.info(f"Output: {self.output_dir}")

    def run_all_problems(self) -> dict:
        """
        Execute all benchmark problems

        Returns:
            Dictionary with results summary
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "provider": self.provider,
            "problems": {},
            "summary": {
                "total": len(self.BENCHMARK_PROBLEMS),
                "success": 0,
                "failed": 0,
            },
        }

        logger.info(f"\n{'=' * 60}")
        logger.info("Starting Phase 1 Benchmark Suite")
        logger.info(f"Provider: {self.provider}")
        logger.info(f"Problems: {len(self.BENCHMARK_PROBLEMS)}")
        logger.info(f"{'=' * 60}\n")

        for i, problem_name in enumerate(self.BENCHMARK_PROBLEMS, 1):
            logger.info(
                f"\n[{i}/{len(self.BENCHMARK_PROBLEMS)}] Running: {problem_name}"
            )
            logger.info("-" * 60)

            success = self.run_single_problem(problem_name)

            results["problems"][problem_name] = {
                "success": success,
                "timestamp": datetime.now().isoformat(),
            }

            if success:
                results["summary"]["success"] += 1
                logger.success(f"✓ {problem_name} completed successfully")
            else:
                results["summary"]["failed"] += 1
                logger.error(f"✗ {problem_name} failed")

        # Print summary
        logger.info(f"\n{'=' * 60}")
        logger.info("Benchmark Suite Completed")
        logger.info(f"{'=' * 60}")
        logger.info(f"Total: {results['summary']['total']}")
        logger.info(f"Success: {results['summary']['success']}")
        logger.info(f"Failed: {results['summary']['failed']}")
        logger.info(
            f"Success Rate: {results['summary']['success'] / results['summary']['total'] * 100:.1f}%"
        )
        logger.info(f"\nResults saved to: {self.output_dir}")
        logger.info(f"{'=' * 60}\n")

        return results

    def run_single_problem(self, problem_name: str) -> bool:
        """
        Execute single problem

        Args:
            problem_name: Name of problem to run

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load problem
            problem = self.loader.load_problem(problem_name)
            logger.info(f"Loaded: {problem.problem_type}")
            logger.info(f"Difficulty: {problem.metadata['difficulty']}")
            logger.info(f"Primary Task: {problem.domain_hints['primary_task']}")

            # Execute via CLI (which handles benchmark logging)
            self.cli._solve_problem(problem_name)

            return True

        except Exception as e:
            logger.error(f"Error running {problem_name}: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 1 Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_phase1_benchmark.py
  python scripts/run_phase1_benchmark.py --provider gemini
  python scripts/run_phase1_benchmark.py --problem hanoi_constrained
  python scripts/run_phase1_benchmark.py --output results/custom-run
        """,
    )

    parser.add_argument(
        "--provider",
        choices=Phase1BenchmarkRunner.SUPPORTED_PROVIDERS,
        default="groq",
        help="LLM provider to use (default: groq)",
    )

    parser.add_argument("--problem", help="Run specific problem only (default: all)")

    parser.add_argument(
        "--output",
        default="results/phase-1-traces",
        help="Output directory for results (default: results/phase-1-traces)",
    )

    parser.add_argument(
        "--problems-dir",
        default="problems",
        help="Directory containing YAML problems (default: problems)",
    )

    args = parser.parse_args()

    # Initialize runner
    runner = Phase1BenchmarkRunner(
        provider=args.provider, output_dir=args.output, problems_dir=args.problems_dir
    )

    # Run benchmarks
    if args.problem:
        # Single problem
        logger.info(f"Running single problem: {args.problem}")
        success = runner.run_single_problem(args.problem)
        sys.exit(0 if success else 1)
    else:
        # All problems
        results = runner.run_all_problems()
        sys.exit(0 if results["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
