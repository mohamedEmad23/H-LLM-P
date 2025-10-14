"""
Household Tasks Testing Framework

Tests the Strategic Decomposition Engine on simple, linear household tasks.

Test Cases:
1. Make a cup of coffee
2. Clean a room
3. Prepare breakfast
4. Set the table

Metrics:
- Task success rate (% of successfully decomposed tasks)
- Total execution time per task
- Quality score (correctness of subtask ordering)
- LLM comparison (which models perform best)
"""

import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger
from algorithms.strategic_decomposition_engine import (
    StrategicDecompositionEngine,
    BenchmarkReport
)
from llm.prompt_builder import DomainContext
from llm.local_llm_interface import LLMConfig


class HouseholdTaskTests:
    """Test suite for household tasks."""
    
    def __init__(self):
        """Initialize test suite."""
        self.engine = StrategicDecompositionEngine()
        self.results = []
        
    def setup_llm_providers(self):
        """Setup LLM providers for testing."""
        logger.info("Setting up LLM providers...")
        
        # Setup instructions
        providers_setup = []
        
        # Try GitHub Models - DeepSeek V3 (if token available)
        if os.getenv("GITHUB_TOKEN"):
            try:
                from llm.github_models_client import GitHubModelsClient
                
                deepseek_client = GitHubModelsClient(
                    config=LLMConfig(
                        model_name="deepseek/DeepSeek-V3-0324",
                        temperature=0.7,
                        max_tokens=1000
                    )
                )
                # Skip availability check - add directly (we know it works from testing)
                self.engine.add_llm_provider("deepseek_v3", deepseek_client)
                providers_setup.append("✅ DeepSeek V3 (671B MoE, GitHub Models)")
                logger.info("DeepSeek V3 added successfully")
            except Exception as e:
                logger.warning(f"GitHub Models (DeepSeek V3) setup failed: {e}")
        
        # Try Ollama (if running locally)
        try:
            from llm.ollama_client import OllamaClient
            
            ollama_client = OllamaClient(
                config=LLMConfig(
                    model_name="llama3.1:8b",
                    temperature=0.7,
                    max_tokens=1000
                )
            )
            if ollama_client.is_available():
                self.engine.add_llm_provider("llama_local", ollama_client)
                providers_setup.append("✅ Llama 3.1 8B (Ollama local)")
        except Exception as e:
            logger.warning(f"Ollama setup failed: {e}")
        
        # Try Groq (if API key available)
        if os.getenv("GROQ_API_KEY"):
            try:
                from llm.groq_client import GroqClient
                
                groq_client = GroqClient(
                    config=LLMConfig(
                        model_name="llama-3.3-70b-versatile",
                        temperature=0.7,
                        max_tokens=1000
                    )
                )
                if groq_client.is_available():
                    self.engine.add_llm_provider("groq_llama70b", groq_client)
                    providers_setup.append("✅ Groq Llama 3.3 70B (ultra-fast)")
            except Exception as e:
                logger.warning(f"Groq setup failed: {e}")
        
        # Try Gemini (if API key available)
        if os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY"):
            try:
                from llm.gemini_client import GeminiClient
                
                gemini_client = GeminiClient(
                    config=LLMConfig(
                        model_name="gemini-2.0-flash-exp",
                        temperature=0.7,
                        max_tokens=1000
                    )
                )
                if gemini_client.is_available():
                    self.engine.add_llm_provider("gemini_flash", gemini_client)
                    providers_setup.append("✅ Gemini 2.0 Flash")
            except Exception as e:
                logger.warning(f"Gemini setup failed: {e}")
        
        # Try Cohere (if API key available)
        if os.getenv("COHERE_API_KEY"):
            try:
                from llm.cohere_client import CohereClient
                
                cohere_client = CohereClient(
                    config=LLMConfig(
                        model_name="command-r-plus-08-2024",
                        temperature=0.7,
                        max_tokens=1000
                    )
                )
                if cohere_client.is_available():
                    self.engine.add_llm_provider("cohere_command", cohere_client)
                    providers_setup.append("✅ Cohere Command R+ (Aug 2024)")
            except Exception as e:
                logger.warning(f"Cohere setup failed: {e}")
        
        # Mistral skipped (401 unauthorized)
        
        if not self.engine.llm_providers:
            raise RuntimeError(
                "No LLM providers available. Please start Ollama or configure API keys: "
                "GROQ_API_KEY, GOOGLE_GEMINI_API_KEY, COHERE_API_KEY"
            )
        
        logger.success(f"LLM providers ready: {len(self.engine.llm_providers)}")
        for provider in providers_setup:
            print(f"  {provider}")
        
        return providers_setup
    
    def test_make_coffee(self) -> BenchmarkReport:
        """Test: Make a cup of coffee."""
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Make a Cup of Coffee")
        logger.info("="*80)
        
        domain = DomainContext(
            domain_name="coffee_making",
            available_operators=[
                "grind_beans(beans, ground_coffee)",
                "fill_water(machine, water)",
                "brew_coffee(machine, ground_coffee, brewed_coffee)",
                "pour_coffee(brewed_coffee, cup)"
            ],
            available_methods=[],
            state_variables=[
                "has_ingredient(X)",
                "ground(X)",
                "filled(X)",
                "brewed(X)",
                "poured(X)"
            ]
        )
        
        result = self.engine.decompose_task(
            task_name="make_coffee",
            task_description="Make a cup of coffee from beans",
            parameters=["beans", "machine", "cup"],
            domain_context=domain,
            preconditions=[
                "has_ingredient(beans)",
                "has_ingredient(water)",
                "clean(machine)",
                "clean(cup)"
            ],
            effects=["poured(coffee, cup)", "coffee_ready(cup)"],
            benchmark=True,
            timeout=30.0
        )
        
        report = result["benchmark_report"]
        self.results.append(("make_coffee", report))
        
        logger.success(f"✅ Test complete: {report.success_rate:.1%} success rate")
        return report
    
    def test_clean_room(self) -> BenchmarkReport:
        """Test: Clean a room."""
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Clean a Room")
        logger.info("="*80)
        
        domain = DomainContext(
            domain_name="room_cleaning",
            available_operators=[
                "pick_up_items(room, items)",
                "vacuum_floor(room)",
                "dust_surfaces(room)",
                "take_out_trash(room, trash)"
            ],
            available_methods=[],
            state_variables=[
                "clean(X)",
                "organized(X)",
                "vacuumed(X)",
                "dusted(X)"
            ]
        )
        
        result = self.engine.decompose_task(
            task_name="clean_room",
            task_description="Clean a room thoroughly",
            parameters=["room"],
            domain_context=domain,
            preconditions=["messy(room)"],
            effects=["clean(room)", "organized(room)"],
            benchmark=True,
            timeout=30.0
        )
        
        report = result["benchmark_report"]
        self.results.append(("clean_room", report))
        
        logger.success(f"✅ Test complete: {report.success_rate:.1%} success rate")
        return report
    
    def test_prepare_breakfast(self) -> BenchmarkReport:
        """Test: Prepare breakfast."""
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Prepare Breakfast")
        logger.info("="*80)
        
        domain = DomainContext(
            domain_name="breakfast_preparation",
            available_operators=[
                "crack_eggs(eggs, bowl)",
                "heat_pan(pan)",
                "scramble_eggs(bowl, pan, scrambled_eggs)",
                "toast_bread(bread, toaster, toast)",
                "pour_juice(juice, glass)"
            ],
            available_methods=[],
            state_variables=[
                "cooked(X)",
                "toasted(X)",
                "poured(X)",
                "ready(X)"
            ]
        )
        
        result = self.engine.decompose_task(
            task_name="prepare_breakfast",
            task_description="Prepare scrambled eggs, toast, and juice",
            parameters=["eggs", "bread", "juice"],
            domain_context=domain,
            preconditions=[
                "has_ingredient(eggs)",
                "has_ingredient(bread)",
                "has_ingredient(juice)"
            ],
            effects=["ready(breakfast)", "cooked(eggs)", "toasted(bread)"],
            benchmark=True,
            timeout=30.0
        )
        
        report = result["benchmark_report"]
        self.results.append(("prepare_breakfast", report))
        
        logger.success(f"✅ Test complete: {report.success_rate:.1%} success rate")
        return report
    
    def test_set_table(self) -> BenchmarkReport:
        """Test: Set the table."""
        logger.info("\n" + "="*80)
        logger.info("TEST 4: Set the Table")
        logger.info("="*80)
        
        domain = DomainContext(
            domain_name="table_setting",
            available_operators=[
                "place_plates(table, plates)",
                "place_utensils(table, utensils)",
                "place_glasses(table, glasses)",
                "place_napkins(table, napkins)"
            ],
            available_methods=[],
            state_variables=[
                "on_table(X)",
                "set(table)",
                "ready_for_meal(table)"
            ]
        )
        
        result = self.engine.decompose_task(
            task_name="set_table",
            task_description="Set the table for dinner",
            parameters=["table", "num_people"],
            domain_context=domain,
            preconditions=["clean(table)"],
            effects=["set(table)", "ready_for_meal(table)"],
            benchmark=True,
            timeout=30.0
        )
        
        report = result["benchmark_report"]
        self.results.append(("set_table", report))
        
        logger.success(f"✅ Test complete: {report.success_rate:.1%} success rate")
        return report
    
    def generate_summary_report(self, output_dir: str = "results"):
        """Generate comprehensive summary report."""
        logger.info("\n" + "="*80)
        logger.info("Generating Summary Report")
        logger.info("="*80)
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Calculate aggregate metrics
        total_tasks = len(self.results)
        aggregate_success_rate = sum(r.success_rate for _, r in self.results) / total_tasks if total_tasks > 0 else 0
        aggregate_time = sum(r.average_execution_time for _, r in self.results) / total_tasks if total_tasks > 0 else 0
        total_tokens = sum(r.total_tokens_used for _, r in self.results)
        
        # Per-LLM aggregate performance
        llm_stats = {}
        for task_name, report in self.results:
            for llm_name, result in report.results_per_llm.items():
                if llm_name not in llm_stats:
                    llm_stats[llm_name] = {
                        "successes": 0,
                        "total": 0,
                        "total_time": 0,
                        "total_tokens": 0
                    }
                
                llm_stats[llm_name]["total"] += 1
                if result.status.value == "success":
                    llm_stats[llm_name]["successes"] += 1
                llm_stats[llm_name]["total_time"] += result.execution_time
                if result.tokens_used:
                    llm_stats[llm_name]["total_tokens"] += result.tokens_used.get('total_tokens', 0)
        
        # Generate markdown summary
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        md = f"# Household Tasks Benchmark Summary\n\n"
        md += f"**Generated**: {timestamp}\n\n"
        md += f"**Strategic Decomposition Engine (Layer 1) - LLM Ensemble Performance**\n\n"
        
        md += "## Aggregate Metrics\n\n"
        md += f"- **Total Tasks**: {total_tasks}\n"
        md += f"- **Overall Success Rate**: {aggregate_success_rate:.1%}\n"
        md += f"- **Average Execution Time**: {aggregate_time:.3f}s\n"
        md += f"- **Total Tokens Used**: {total_tokens:,}\n"
        md += f"- **LLMs Tested**: {len(llm_stats)}\n\n"
        
        md += "## Tasks Tested\n\n"
        for i, (task_name, report) in enumerate(self.results, 1):
            md += f"{i}. **{task_name}**: {report.success_rate:.1%} success ({report.successful_attempts}/{report.total_attempts})\n"
        
        md += "\n## LLM Performance Comparison\n\n"
        md += "| LLM | Success Rate | Avg Time (s) | Total Tokens | Tasks Passed |\n"
        md += "|-----|--------------|--------------|--------------|---------------|\n"
        
        for llm_name, stats in sorted(
            llm_stats.items(),
            key=lambda x: (x[1]["successes"] / x[1]["total"], -x[1]["total_time"] / x[1]["total"])
        ):
            success_rate = stats["successes"] / stats["total"] if stats["total"] > 0 else 0
            avg_time = stats["total_time"] / stats["total"] if stats["total"] > 0 else 0
            
            md += f"| {llm_name} | {success_rate:.1%} | {avg_time:.3f} | "
            md += f"{stats['total_tokens']:,} | {stats['successes']}/{stats['total']} |\n"
        
        md += "\n## Best LLM per Task\n\n"
        for task_name, report in self.results:
            md += f"- **{task_name}**: {report.best_llm or 'None'}\n"
        
        md += "\n## Detailed Results\n\n"
        for task_name, report in self.results:
            md += f"### {task_name}\n\n"
            md += report.to_markdown()
            md += "\n---\n\n"
        
        # Save summary
        summary_path = os.path.join(output_dir, "household_tasks_summary.md")
        with open(summary_path, 'w') as f:
            f.write(md)
        
        logger.success(f"Summary report saved: {summary_path}")
        
        # Save JSON
        json_path = os.path.join(output_dir, "household_tasks_results.json")
        with open(json_path, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "aggregate_metrics": {
                    "total_tasks": total_tasks,
                    "success_rate": aggregate_success_rate,
                    "average_time": aggregate_time,
                    "total_tokens": total_tokens,
                    "llms_tested": len(llm_stats)
                },
                "llm_performance": llm_stats,
                "task_results": [
                    {"task": name, "report": report.to_dict()}
                    for name, report in self.results
                ]
            }, f, indent=2)
        
        logger.success(f"JSON results saved: {json_path}")
        
        # Print summary to console
        print("\n" + "="*80)
        print("SUMMARY RESULTS")
        print("="*80)
        print(f"\nOverall Success Rate: {aggregate_success_rate:.1%}")
        print(f"Average Execution Time: {aggregate_time:.3f}s")
        print(f"Total Tokens Used: {total_tokens:,}")
        print(f"\nLLM Rankings:")
        for i, (llm_name, stats) in enumerate(sorted(
            llm_stats.items(),
            key=lambda x: (x[1]["successes"] / x[1]["total"], -x[1]["total_time"] / x[1]["total"])
        ), 1):
            success_rate = stats["successes"] / stats["total"]
            avg_time = stats["total_time"] / stats["total"]
            print(f"{i}. {llm_name}: {success_rate:.1%} success, {avg_time:.3f}s avg")
        print("\n" + "="*80)


def main():
    """Run household tasks test suite."""
    print("="*80)
    print("Strategic Decomposition Engine - Household Tasks Testing")
    print("="*80)
    print("\nPhase 3: Strategic Decomposition Engine (Layer 1)")
    print("Testing LLM ensemble on simple, linear household tasks\n")
    
    # Initialize
    test_suite = HouseholdTaskTests()
    
    # Setup LLM providers
    try:
        providers = test_suite.setup_llm_providers()
        print(f"\n✅ {len(providers)} LLM provider(s) configured\n")
    except Exception as e:
        logger.error(f"Failed to setup LLM providers: {e}")
        print("\n❌ No LLM providers available")
        print("\nTo run this test, you need at least one of:")
        print("  1. GITHUB_TOKEN in .env (for GPT-5, DeepSeek V3, Llama 4)")
        print("  2. Ollama running locally (ollama serve)")
        print("  3. GROQ_API_KEY in .env")
        print("  4. GOOGLE_API_KEY in .env")
        return
    
    # Run tests
    start_time = time.time()
    
    try:
        test_suite.test_make_coffee()
        test_suite.test_clean_room()
        test_suite.test_prepare_breakfast()
        test_suite.test_set_table()
    except KeyboardInterrupt:
        logger.warning("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Test suite error: {e}")
    
    total_time = time.time() - start_time
    
    # Generate summary
    if test_suite.results:
        test_suite.generate_summary_report("results")
        print(f"\n✅ All tests completed in {total_time:.2f}s")
        print("\nResults saved to:")
        print("  - results/household_tasks_summary.md")
        print("  - results/household_tasks_results.json")
    else:
        print("\n❌ No test results to report")


if __name__ == "__main__":
    main()
