#!/usr/bin/env python3
"""
Unified Benchmark Harness - Cross-Phase Comparison

Runs all 5 YAML problems across all 3 phases (1, 3, 4) and generates
comprehensive comparison reports.

Usage:
    ./run_full_benchmark.py                           # Run all problems on all phases
    ./run_full_benchmark.py --phases 1 3              # Run specific phases only
    ./run_full_benchmark.py --problems hanoi sorting  # Run specific problems only
    ./run_full_benchmark.py --report-only             # Generate report from existing results

Author: H-LLM-P Thesis Project
Date: November 14, 2025
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
import argparse

# Add parent directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root / "src"))

from interface.problem_cli import ProblemLoader
from interface.phase3_executor import Phase3Executor
from interface.phase4_executor import Phase4Executor


class UnifiedBenchmarkHarness:
    """Orchestrates cross-phase benchmark execution and comparison"""

    def __init__(
        self,
        problems_dir: str = "problems",
        output_dir: str = "results/cross-phase-analysis",
    ):
        """
        Initialize benchmark harness

        Args:
            problems_dir: Directory containing YAML problems
            output_dir: Output directory for analysis results
        """
        self.problems_dir = project_root / problems_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.loader = ProblemLoader(str(self.problems_dir))

        # Phase directories
        self.phase_dirs = {
            "phase1": project_root / "results/phase-1-traces",
            "phase3": project_root / "results/phase-3-traces",
            "phase4": project_root / "results/phase-4-traces",
        }

        logger.info("Unified Benchmark Harness initialized")
        logger.info(f"Problems directory: {self.problems_dir}")
        logger.info(f"Output directory: {self.output_dir}")

    async def run_phase1_problem(self, problem_name: str) -> Dict[str, Any]:
        """Run single problem on Phase 1"""
        from scripts.run_phase1_benchmark import Phase1BenchmarkRunner

        runner = Phase1BenchmarkRunner(
            problems_dir=str(self.problems_dir), provider="groq"
        )
        return await runner.run_single_problem(problem_name)

    async def run_phase3_problem(self, problem_name: str) -> Dict[str, Any]:
        """Run single problem on Phase 3"""
        problem = self.loader.load_problem(problem_name)
        executor = Phase3Executor()
        return await executor.execute(problem)

    async def run_phase4_problem(self, problem_name: str) -> Dict[str, Any]:
        """Run single problem on Phase 4"""
        problem = self.loader.load_problem(problem_name)
        executor = Phase4Executor()
        return await executor.execute(problem)

    async def run_all_phases(
        self, problem_names: List[str], phases: List[int] = [1, 3, 4]
    ) -> Dict[str, Any]:
        """
        Run all problems across specified phases

        Args:
            problem_names: List of problem names to run
            phases: List of phase numbers to test

        Returns:
            Summary of all executions
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"\n{'=' * 80}")
        logger.info("UNIFIED BENCHMARK SUITE")
        logger.info(f"{'=' * 80}")
        logger.info(f"Timestamp: {timestamp}")
        logger.info(f"Problems: {len(problem_names)}")
        logger.info(f"Phases: {phases}")
        logger.info(f"{'=' * 80}\n")

        results = {
            "timestamp": timestamp,
            "problems": problem_names,
            "phases": phases,
            "executions": [],
        }

        total_runs = len(problem_names) * len(phases)
        current_run = 0

        for problem_name in problem_names:
            for phase in phases:
                current_run += 1
                logger.info(
                    f"\n[{current_run}/{total_runs}] Running: {problem_name} on Phase {phase}"
                )

                try:
                    if phase == 1:
                        result = await self.run_phase1_problem(problem_name)
                    elif phase == 3:
                        result = await self.run_phase3_problem(problem_name)
                    elif phase == 4:
                        result = await self.run_phase4_problem(problem_name)
                    else:
                        logger.warning(f"Unknown phase: {phase}")
                        continue

                    results["executions"].append(
                        {
                            "problem": problem_name,
                            "phase": phase,
                            "success": result.get("success", False),
                            "result": result,
                        }
                    )

                    logger.success(f"✓ Completed: {problem_name} - Phase {phase}")

                except Exception as e:
                    logger.error(f"✗ Failed: {problem_name} - Phase {phase}: {e}")
                    results["executions"].append(
                        {
                            "problem": problem_name,
                            "phase": phase,
                            "success": False,
                            "error": str(e),
                        }
                    )

        # Save raw results
        results_file = self.output_dir / f"benchmark_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"\n✓ Results saved to: {results_file}")

        return results

    def generate_comparison_report(self, results: Dict[str, Any]) -> str:
        """Generate cross-phase comparison report"""

        logger.info("\n" + "=" * 80)
        logger.info("GENERATING COMPARISON REPORT")
        logger.info("=" * 80)

        # Summary statistics
        problems = results["problems"]
        phases = results["phases"]
        executions = results["executions"]

        # Calculate success rates per phase
        phase_stats = {}
        for phase in phases:
            phase_execs = [e for e in executions if e["phase"] == phase]
            successful = [e for e in phase_execs if e.get("success", False)]
            phase_stats[phase] = {
                "total": len(phase_execs),
                "successful": len(successful),
                "failed": len(phase_execs) - len(successful),
                "success_rate": len(successful) / len(phase_execs) * 100
                if phase_execs
                else 0,
            }

        # Build report
        report_lines = [
            "\n" + "=" * 80,
            "CROSS-PHASE BENCHMARK COMPARISON REPORT",
            "=" * 80,
            f"\nTimestamp: {results['timestamp']}",
            f"Problems Tested: {len(problems)}",
            f"Phases Tested: {phases}",
            f"Total Executions: {len(executions)}",
            "\n" + "-" * 80,
            "SUCCESS RATES BY PHASE",
            "-" * 80,
        ]

        for phase in sorted(phases):
            stats = phase_stats[phase]
            report_lines.append(
                f"\nPhase {phase}: {stats['successful']}/{stats['total']} "
                f"({stats['success_rate']:.1f}% success rate)"
            )

        report_lines.extend(["\n" + "-" * 80, "PROBLEM-BY-PROBLEM BREAKDOWN", "-" * 80])

        for problem in problems:
            report_lines.append(f"\n{problem}:")
            for phase in sorted(phases):
                phase_exec = next(
                    (
                        e
                        for e in executions
                        if e["problem"] == problem and e["phase"] == phase
                    ),
                    None,
                )
                if phase_exec:
                    status = (
                        "✓ SUCCESS" if phase_exec.get("success", False) else "✗ FAILED"
                    )
                    report_lines.append(f"  Phase {phase}: {status}")

        report_lines.append("\n" + "=" * 80 + "\n")

        report = "\n".join(report_lines)

        # Save report
        report_file = self.output_dir / f"comparison_report_{results['timestamp']}.txt"
        with open(report_file, "w") as f:
            f.write(report)

        logger.info(f"✓ Report saved to: {report_file}")

        # Print to console
        print(report)

        return report


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Unified Benchmark Harness - Cross-Phase Comparison"
    )
    parser.add_argument(
        "--problems", nargs="+", help="Specific problems to run (default: all)"
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        type=int,
        choices=[1, 3, 4],
        default=[1, 3, 4],
        help="Phases to test (default: 1 3 4)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only generate report from existing results",
    )
    parser.add_argument(
        "--results-file", help="Existing results file for report generation"
    )

    args = parser.parse_args()

    # Initialize harness
    harness = UnifiedBenchmarkHarness()

    if args.report_only:
        if not args.results_file:
            logger.error("--results-file required with --report-only")
            sys.exit(1)

        with open(args.results_file, "r") as f:
            results = json.load(f)

        harness.generate_comparison_report(results)
        sys.exit(0)

    # Get problem list
    if args.problems:
        problem_names = args.problems
    else:
        problem_names = harness.loader.list_problems()

    # Run benchmarks
    results = await harness.run_all_phases(problem_names, args.phases)

    # Generate report
    harness.generate_comparison_report(results)

    # Exit code based on success
    successful = sum(1 for e in results["executions"] if e.get("success", False))
    sys.exit(0 if successful > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
