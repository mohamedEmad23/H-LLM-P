#!/usr/bin/env python3
"""
Phase 4 Benchmark Runner

Executes all YAML problems using Phase 4 strategic multi-agent architecture.
Tests 5+ agent coordination with verification loops and context coherence tracking.

Usage:
    ./run_phase4_benchmark.py                      # Run all problems, multi-LLM mode
    ./run_phase4_benchmark.py --single-llm         # Use same LLM for all agents
    ./run_phase4_benchmark.py --problem hanoi      # Run specific problem

Author: H-LLM-P Thesis Project
Date: November 14, 2025
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from loguru import logger
import argparse

# Add parent directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root / "src"))

from interface.problem_cli import ProblemLoader, Problem
from interface.phase4_executor import Phase4Executor
from utils.benchmark_logger import BenchmarkLogger


class Phase4BenchmarkRunner:
    """Orchestrates Phase 4 strategic benchmark execution across multiple problems."""
    
    def __init__(
        self,
        problems_dir: str = "problems",
        output_dir: str = "results/phase-4-traces",
        use_different_llms: bool = True
    ):
        """
        Initialize benchmark runner
        
        Args:
            problems_dir: Directory containing YAML problems
            output_dir: Output directory for results
            use_different_llms: Use different LLM for each agent
        """
        # Resolve paths relative to project root
        self.problems_dir = project_root / problems_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.problems_dir.exists():
            raise FileNotFoundError(f"Problems directory not found: {self.problems_dir}")
        
        self.loader = ProblemLoader(str(self.problems_dir))
        self.use_different_llms = use_different_llms
        
        logger.info("Phase 4 Benchmark Runner initialized")
        logger.info(f"Problems directory: {self.problems_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Multi-LLM mode: {use_different_llms}")
    
    async def run_single_problem(
        self,
        problem_name: str
    ) -> dict:
        """
        Run benchmark on a single problem
        
        Args:
            problem_name: Problem name (without .yaml extension)
            
        Returns:
            Execution result
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Phase 4 Benchmark: {problem_name}")
        logger.info(f"{'='*80}")
        
        try:
            # Load problem
            problem = self.loader.load_problem(problem_name)
            
            if problem is None:
                logger.error(f"Failed to load problem: {problem_name}")
                return {
                    "success": False,
                    "problem": problem_name,
                    "error": "Failed to load problem"
                }
            
            # Execute with Phase 4
            executor = Phase4Executor(
                output_dir=str(self.output_dir),
                use_different_llms=self.use_different_llms
            )
            result = await executor.execute(problem)
            
            logger.success(f"✓ Completed: {problem_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed: {problem_name} - {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "problem": problem_name,
                "error": str(e)
            }
    
    async def run_all_problems(self) -> dict:
        """
        Run benchmark on all available problems
        
        Returns:
            Summary of all executions
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"\n{'='*80}")
        logger.info("Phase 4 Strategic Benchmark Suite")
        logger.info(f"Timestamp: {timestamp}")
        logger.info(f"Multi-LLM mode: {self.use_different_llms}")
        logger.info(f"{'='*80}\n")
        
        # Get all problems
        problem_names = self.loader.list_problems()
        
        if not problem_names:
            logger.warning("No problems found in directory")
            return {"success": False, "error": "No problems found"}
        
        logger.info(f"Found {len(problem_names)} problems to benchmark:")
        for name in problem_names:
            logger.info(f"  - {name}")
        
        # Run all problems
        results = []
        successful = 0
        failed = 0
        
        for i, problem_name in enumerate(problem_names, 1):
            logger.info(f"\n[{i}/{len(problem_names)}] Processing: {problem_name}")
            
            result = await self.run_single_problem(problem_name)
            results.append(result)
            
            if result["success"]:
                successful += 1
            else:
                failed += 1
        
        # Summary
        logger.info(f"\n{'='*80}")
        logger.info("Phase 4 Benchmark Complete")
        logger.info(f"{'='*80}")
        logger.info(f"Total problems: {len(problem_names)}")
        logger.success(f"Successful: {successful}")
        if failed > 0:
            logger.error(f"Failed: {failed}")
        logger.info(f"Results saved to: {self.output_dir}")
        logger.info(f"{'='*80}\n")
        
        return {
            "success": True,
            "timestamp": timestamp,
            "total": len(problem_names),
            "successful": successful,
            "failed": failed,
            "results": results
        }


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 4 Strategic Multi-Agent Benchmark Runner"
    )
    parser.add_argument(
        "--problem",
        type=str,
        help="Run specific problem (without .yaml extension)"
    )
    parser.add_argument(
        "--single-llm",
        action="store_true",
        help="Use same LLM for all agents (default: different LLMs)"
    )
    parser.add_argument(
        "--problems-dir",
        default="problems",
        help="Problems directory (default: problems)"
    )
    parser.add_argument(
        "--output-dir",
        default="results/phase-4-traces",
        help="Output directory (default: results/phase-4-traces)"
    )
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = Phase4BenchmarkRunner(
        problems_dir=args.problems_dir,
        output_dir=args.output_dir,
        use_different_llms=not args.single_llm
    )
    
    # Run benchmark
    if args.problem:
        result = await runner.run_single_problem(args.problem)
        sys.exit(0 if result["success"] else 1)
    else:
        summary = await runner.run_all_problems()
        sys.exit(0 if summary["successful"] > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
