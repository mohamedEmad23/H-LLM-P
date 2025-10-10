"""
Strategic Decomposition Engine (Layer 1) - LLM Ensemble Integration

This module implements the first layer of the Neuro-Symbolic HTN Planner:
the Strategic Decomposition Engine. It uses an ensemble of LLMs with Chain of
Thought (CoT) prompting to break down high-level goals into executable sequences.

Architecture:
- LLM Ensemble: Multiple LLM providers (GPT-5, DeepSeek V3, Llama 4, Groq, etc.)
- CoT Prompting: Chain of Thought reasoning for task decomposition
- HTN Integration: Converts LLM responses to HTN Methods
- Benchmarking: Comprehensive performance metrics per LLM

Primary Metrics:
- Task Success Rate (% of successfully decomposed tasks)
- Total Execution Time (time to generate and validate methods)
- Decomposition Quality (validity, completeness, correctness)
- Token Usage (cost tracking)
- Error Rate (failures per LLM)

Usage:
    engine = StrategicDecompositionEngine()
    engine.add_llm_provider("gpt5", gpt5_client)
    engine.add_llm_provider("deepseek", deepseek_client)
    
    result = engine.decompose_task(
        task_name="make_coffee",
        domain_context=domain,
        benchmark=True
    )
"""

import time
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

# Import core components
import sys
sys.path.insert(0, '../../')
from core.methods import Method
from core.state_manager import StateManager
from llm.local_llm_interface import BaseLLMClient, LLMException
from llm.prompt_builder import PromptBuilder, PromptStrategy, HTNTask, DomainContext
from llm.response_parser import ResponseParser, ParsedMethod


class DecompositionStatus(Enum):
    """Status of a decomposition attempt."""
    SUCCESS = "success"
    FAILED_PARSING = "failed_parsing"
    FAILED_VALIDATION = "failed_validation"
    FAILED_LLM_ERROR = "failed_llm_error"
    FAILED_TIMEOUT = "failed_timeout"


@dataclass
class DecompositionResult:
    """Result of a single decomposition attempt."""
    llm_provider: str
    model_name: str
    status: DecompositionStatus
    method: Optional[ParsedMethod]
    execution_time: float
    tokens_used: Optional[Dict[str, int]]
    confidence_score: float
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "llm_provider": self.llm_provider,
            "model_name": self.model_name,
            "status": self.status.value,
            "success": self.status == DecompositionStatus.SUCCESS,
            "execution_time": round(self.execution_time, 3),
            "tokens_used": self.tokens_used,
            "confidence_score": round(self.confidence_score, 3),
            "errors": self.errors,
            "method_name": self.method.name if self.method else None,
            "num_subtasks": len(self.method.subtasks) if self.method else 0,
            "metadata": self.metadata
        }


@dataclass
class BenchmarkReport:
    """Comprehensive benchmark report for LLM ensemble."""
    task_name: str
    total_attempts: int
    successful_attempts: int
    success_rate: float
    average_execution_time: float
    total_tokens_used: int
    results_per_llm: Dict[str, DecompositionResult]
    best_llm: Optional[str]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "task_name": self.task_name,
            "summary": {
                "total_attempts": self.total_attempts,
                "successful_attempts": self.successful_attempts,
                "success_rate": f"{self.success_rate:.1%}",
                "average_execution_time": f"{self.average_execution_time:.3f}s",
                "total_tokens": self.total_tokens_used,
                "best_llm": self.best_llm
            },
            "results_per_llm": {
                name: result.to_dict() 
                for name, result in self.results_per_llm.items()
            },
            "timestamp": self.timestamp
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        md = f"# Benchmark Report: {self.task_name}\n\n"
        md += f"**Generated**: {self.timestamp}\n\n"
        md += "## Summary\n\n"
        md += f"- **Total Attempts**: {self.total_attempts}\n"
        md += f"- **Successful**: {self.successful_attempts}\n"
        md += f"- **Success Rate**: {self.success_rate:.1%}\n"
        md += f"- **Avg Execution Time**: {self.average_execution_time:.3f}s\n"
        md += f"- **Total Tokens**: {self.total_tokens_used:,}\n"
        md += f"- **Best LLM**: {self.best_llm or 'None'}\n\n"
        
        md += "## Results by LLM\n\n"
        md += "| LLM | Model | Status | Time (s) | Tokens | Confidence | Subtasks |\n"
        md += "|-----|-------|--------|----------|--------|------------|----------|\n"
        
        for name, result in sorted(
            self.results_per_llm.items(),
            key=lambda x: (x[1].status == DecompositionStatus.SUCCESS, -x[1].execution_time)
        ):
            status_emoji = "✅" if result.status == DecompositionStatus.SUCCESS else "❌"
            tokens = result.tokens_used.get('total_tokens', 0) if result.tokens_used else 0
            subtasks = len(result.method.subtasks) if result.method else 0
            
            md += f"| {name} | {result.model_name} | {status_emoji} {result.status.value} | "
            md += f"{result.execution_time:.3f} | {tokens} | {result.confidence_score:.0%} | {subtasks} |\n"
        
        md += "\n## Detailed Results\n\n"
        for name, result in self.results_per_llm.items():
            md += f"### {name}\n\n"
            md += f"- **Model**: {result.model_name}\n"
            md += f"- **Status**: {result.status.value}\n"
            md += f"- **Execution Time**: {result.execution_time:.3f}s\n"
            md += f"- **Confidence**: {result.confidence_score:.1%}\n"
            
            if result.tokens_used:
                md += f"- **Tokens**: {result.tokens_used.get('total_tokens', 0)} "
                md += f"({result.tokens_used.get('prompt_tokens', 0)} prompt + "
                md += f"{result.tokens_used.get('completion_tokens', 0)} completion)\n"
            
            if result.method:
                md += f"- **Method**: {result.method.name}\n"
                md += f"- **Subtasks**: {len(result.method.subtasks)}\n"
                md += f"  - {', '.join(st[0] for st in result.method.subtasks)}\n"
            
            if result.errors:
                md += f"- **Errors**:\n"
                for error in result.errors:
                    md += f"  - {error}\n"
            
            md += "\n"
        
        return md


class StrategicDecompositionEngine:
    """
    Strategic Decomposition Engine (Layer 1)
    
    Uses an ensemble of LLMs with Chain of Thought prompting to decompose
    high-level goals into HTN methods.
    """
    
    def __init__(self):
        """Initialize the Strategic Decomposition Engine."""
        self.llm_providers: Dict[str, BaseLLMClient] = {}
        self.prompt_builder = PromptBuilder(PromptStrategy.REASONING)
        self.parser = ResponseParser()
        self.benchmarks: List[BenchmarkReport] = []
        
        logger.info("Strategic Decomposition Engine initialized")
    
    def add_llm_provider(self, name: str, client: BaseLLMClient) -> None:
        """
        Add an LLM provider to the ensemble.
        
        Args:
            name: Name/identifier for this provider (e.g., "gpt5", "deepseek_v3")
            client: LLM client instance
        """
        self.llm_providers[name] = client
        logger.info(f"Added LLM provider: {name} ({client.provider_name})")
    
    def decompose_task(
        self,
        task_name: str,
        task_description: str,
        parameters: List[str],
        domain_context: DomainContext,
        preconditions: Optional[List[str]] = None,
        effects: Optional[List[str]] = None,
        benchmark: bool = True,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Decompose a task using the LLM ensemble.
        
        Args:
            task_name: Name of the task to decompose
            task_description: Description of what the task does
            parameters: Task parameters
            domain_context: HTN domain context
            preconditions: Expected preconditions
            effects: Expected effects
            benchmark: If True, benchmark all LLMs; else use first available
            timeout: Timeout per LLM in seconds
            
        Returns:
            Dictionary with:
                - best_method: The best ParsedMethod found
                - benchmark_report: BenchmarkReport (if benchmark=True)
                - provider_used: Name of LLM that generated best method
        """
        if not self.llm_providers:
            raise ValueError("No LLM providers configured. Add providers first.")
        
        # Create HTN task
        task = HTNTask(
            name=task_name,
            parameters=parameters,
            preconditions=preconditions or [],
            effects=effects or [],
            description=task_description
        )
        
        # Build prompts
        system_prompt = self.prompt_builder.get_system_prompt()
        user_prompt = self.prompt_builder.build_task_decomposition_prompt(
            task, domain_context, include_examples=True
        )
        
        if benchmark:
            return self._benchmark_all_llms(
                task, system_prompt, user_prompt, timeout
            )
        else:
            return self._decompose_with_first_available(
                task, system_prompt, user_prompt, timeout
            )
    
    def _benchmark_all_llms(
        self,
        task: HTNTask,
        system_prompt: str,
        user_prompt: str,
        timeout: float
    ) -> Dict[str, Any]:
        """Benchmark all LLM providers."""
        results: Dict[str, DecompositionResult] = {}
        
        logger.info(f"Benchmarking {len(self.llm_providers)} LLM providers for task: {task.name}")
        
        for provider_name, client in self.llm_providers.items():
            logger.info(f"Testing provider: {provider_name}")
            
            result = self._decompose_with_llm(
                provider_name,
                client,
                system_prompt,
                user_prompt,
                timeout
            )
            results[provider_name] = result
            
            status_emoji = "✅" if result.status == DecompositionStatus.SUCCESS else "❌"
            logger.info(
                f"  {status_emoji} {provider_name}: {result.status.value} "
                f"({result.execution_time:.3f}s, confidence: {result.confidence_score:.1%})"
            )
        
        # Generate benchmark report
        successful = [r for r in results.values() if r.status == DecompositionStatus.SUCCESS]
        total_tokens = sum(
            r.tokens_used.get('total_tokens', 0) 
            for r in results.values() 
            if r.tokens_used
        )
        
        # Find best LLM (highest confidence among successful, fastest as tiebreaker)
        best_llm = None
        best_method = None
        if successful:
            best_result = max(
                successful,
                key=lambda r: (r.confidence_score, -r.execution_time)
            )
            best_llm = best_result.llm_provider
            best_method = best_result.method
        
        report = BenchmarkReport(
            task_name=task.name,
            total_attempts=len(results),
            successful_attempts=len(successful),
            success_rate=len(successful) / len(results) if results else 0.0,
            average_execution_time=sum(r.execution_time for r in results.values()) / len(results),
            total_tokens_used=total_tokens,
            results_per_llm=results,
            best_llm=best_llm,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        self.benchmarks.append(report)
        
        return {
            "best_method": best_method,
            "benchmark_report": report,
            "provider_used": best_llm
        }
    
    def _decompose_with_first_available(
        self,
        task: HTNTask,
        system_prompt: str,
        user_prompt: str,
        timeout: float
    ) -> Dict[str, Any]:
        """Decompose using first available LLM (faster, no benchmarking)."""
        for provider_name, client in self.llm_providers.items():
            try:
                result = self._decompose_with_llm(
                    provider_name,
                    client,
                    system_prompt,
                    user_prompt,
                    timeout
                )
                
                if result.status == DecompositionStatus.SUCCESS:
                    return {
                        "best_method": result.method,
                        "benchmark_report": None,
                        "provider_used": provider_name
                    }
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        raise LLMException(
            f"All LLM providers failed to decompose task: {task.name}",
            provider="ensemble"
        )
    
    def _decompose_with_llm(
        self,
        provider_name: str,
        client: BaseLLMClient,
        system_prompt: str,
        user_prompt: str,
        timeout: float
    ) -> DecompositionResult:
        """Decompose using a single LLM."""
        start_time = time.time()
        errors = []
        method = None
        status = DecompositionStatus.FAILED_LLM_ERROR
        tokens_used = None
        confidence = 0.0
        
        try:
            # Generate with LLM
            response = client.generate(
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=client.config.max_tokens,
                temperature=client.config.temperature
            )
            
            tokens_used = response.tokens_used
            
            # Parse response
            try:
                method = self.parser.parse(response.content)
                confidence = method.confidence
                
                # Validate parsed method
                is_valid, issues = self.parser.validate_method(method)
                
                if is_valid:
                    status = DecompositionStatus.SUCCESS
                else:
                    status = DecompositionStatus.FAILED_VALIDATION
                    errors.extend(issues)
            
            except Exception as e:
                status = DecompositionStatus.FAILED_PARSING
                errors.append(f"Parsing error: {str(e)}")
        
        except LLMException as e:
            status = DecompositionStatus.FAILED_LLM_ERROR
            errors.append(f"LLM error: {str(e)}")
        
        except Exception as e:
            status = DecompositionStatus.FAILED_LLM_ERROR
            errors.append(f"Unexpected error: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return DecompositionResult(
            llm_provider=provider_name,
            model_name=client.config.model_name,
            status=status,
            method=method,
            execution_time=execution_time,
            tokens_used=tokens_used,
            confidence_score=confidence,
            errors=errors,
            metadata={
                "provider": client.provider_name,
                "timeout": timeout
            }
        )
    
    def get_latest_benchmark(self) -> Optional[BenchmarkReport]:
        """Get the most recent benchmark report."""
        return self.benchmarks[-1] if self.benchmarks else None
    
    def export_benchmarks(self, filepath: str, format: str = "json") -> None:
        """
        Export all benchmark reports to file.
        
        Args:
            filepath: Output file path
            format: "json" or "markdown"
        """
        if format == "json":
            with open(filepath, 'w') as f:
                json.dump(
                    [b.to_dict() for b in self.benchmarks],
                    f,
                    indent=2
                )
        elif format == "markdown":
            with open(filepath, 'w') as f:
                for i, benchmark in enumerate(self.benchmarks):
                    if i > 0:
                        f.write("\n---\n\n")
                    f.write(benchmark.to_markdown())
        
        logger.success(f"Exported {len(self.benchmarks)} benchmarks to {filepath}")


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("Strategic Decomposition Engine - Example")
    print("="*80)
    print("\nThis example demonstrates the Strategic Decomposition Engine (Layer 1)")
    print("which uses an LLM ensemble with Chain of Thought prompting.")
    print("\nTo run a real test, you need to:")
    print("1. Configure LLM clients (see github_models_client.py, ollama_client.py)")
    print("2. Define a domain context")
    print("3. Call engine.decompose_task() with benchmarking enabled")
    print("\nExample code:")
    print("""
    # Initialize engine
    engine = StrategicDecompositionEngine()
    
    # Add LLM providers
    from llm.github_models_client import GitHubModelsClient
    from llm.ollama_client import OllamaClient
    
    gpt5_client = GitHubModelsClient(config=LLMConfig(model_name="openai/gpt-5"))
    engine.add_llm_provider("gpt5", gpt5_client)
    
    deepseek_client = GitHubModelsClient(config=LLMConfig(model_name="deepseek-ai/DeepSeek-V3"))
    engine.add_llm_provider("deepseek_v3", deepseek_client)
    
    ollama_client = OllamaClient(config=LLMConfig(model_name="llama3.1:8b"))
    engine.add_llm_provider("llama_local", ollama_client)
    
    # Define domain
    domain = DomainContext(
        domain_name="cooking",
        available_operators=["grind_beans", "fill_water", "brew", "pour"],
        available_methods=[],
        state_variables=["has_ingredient", "clean", "coffee_ready"]
    )
    
    # Decompose task with benchmarking
    result = engine.decompose_task(
        task_name="make_coffee",
        task_description="Make a cup of coffee",
        parameters=[],
        domain_context=domain,
        preconditions=["has_ingredient(coffee_beans)", "has_ingredient(water)"],
        effects=["coffee_ready(cup)"],
        benchmark=True
    )
    
    # Get results
    best_method = result["best_method"]
    report = result["benchmark_report"]
    
    # Print report
    print(report.to_markdown())
    
    # Export benchmarks
    engine.export_benchmarks("benchmarks.json", format="json")
    engine.export_benchmarks("benchmarks.md", format="markdown")
    """)
    print("\n" + "="*80)
    print("✅ Strategic Decomposition Engine module ready")
    print("="*80)
