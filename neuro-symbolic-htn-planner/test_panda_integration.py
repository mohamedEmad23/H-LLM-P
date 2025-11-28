"""
PANDA Integration Test - Single Problem
Tests complete neuro-symbolic HTN pipeline with incomplete-graph-p01
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

from src.agents.planning_agent import PlanningAgent
from src.agents.decomposition_agent import DecompositionAgent
from src.agents.execution_agent import ExecutionAgent
from src.agents.verification_agent import VerificationAgent
from src.agents.context_agent import ContextAgent
from src.agents.workflows.panda_workflow import PANDAWorkflow
from src.integrations.panda_wrapper import PANDAWrapper
from src.core.state_manager import State
from src.llm.groq_client import GroqClient
from src.llm.gemini_client import GeminiClient
from src.llm.cohere_client import CohereClient
from src.llm.huggingface_client import HuggingFaceClient
from src.llm.local_llm_interface import LLMConfig

# Load environment variables
load_dotenv()


async def setup_agents():
    """Initialize all agents with real LLM backends"""
    logger.info("[SETUP] Initializing agents with real LLM backends...")
    
    # Initialize LLM clients with proper LLMConfig objects
    groq_client = GroqClient(
        api_key=os.getenv("GROQ_API_KEY"),
        config=LLMConfig(
            model_name="llama-3.3-70b-versatile",  # Updated from deprecated 3.1
            temperature=0.7,
            max_tokens=2048
        )
    )
    
    gemini_client = GeminiClient(
        api_key=os.getenv("GOOGLE_API_KEY"),
        config=LLMConfig(
            model_name="gemini-2.0-flash-exp",
            temperature=0.5,
            max_tokens=2048
        )
    )
    
    cohere_client = CohereClient(
        api_key=os.getenv("COHERE_API_KEY"),
        config=LLMConfig(
            model_name="command-r-plus",
            temperature=0.3,
            max_tokens=2048
        )
    )
    
    hf_client = HuggingFaceClient(
        api_key=os.getenv("HF_TOKEN"),
        config=LLMConfig(
            model_name="meta-llama/Meta-Llama-3-8B-Instruct",
            temperature=0.4,
            max_tokens=1024
        )
    )
    
    # Initialize agents with their respective LLM clients
    planning_agent = PlanningAgent(
        name="PlanningAgent",
        llm_client=groq_client,
        fallback_client=hf_client,
        config={
            "max_strategies": 3,
            "temperature": 0.7,
            "max_tokens": 1500
        }
    )
    
    decomposition_agent = DecompositionAgent(
        name="DecompositionAgent",
        llm_client=gemini_client,
        config={
            "max_retries": 3,
            "temperature": 0.5,
            # Don't initialize PANDA here - workflow will inject it
        }
    )
    
    execution_agent = ExecutionAgent(
        name="ExecutionAgent",
        llm_client=cohere_client,
        config={
            "temperature": 0.3
        }
    )
    
    verification_agent = VerificationAgent(
        name="VerificationAgent",
        llm_client=hf_client,
        fallback_client=gemini_client,
        config={
            "validation_threshold": 0.8,
            "temperature": 0.4
        }
    )
    
    context_agent = ContextAgent(
        name="ContextAgent",
        llm_client=gemini_client,
        config={
            "memory_size": 1000,
            "temperature": 0.5
        }
    )
    
    logger.info("[SETUP] ✓ All agents initialized with real LLM clients")
    return planning_agent, decomposition_agent, execution_agent, verification_agent, context_agent


async def setup_panda_wrapper():
    """Initialize PANDA wrapper with C++ binaries"""
    logger.info("[SETUP] Initializing PANDA wrapper...")
    
    # Path to PANDA-HTN binaries (adjust if needed)
    panda_root = "../PANDA-HTN"
    
    panda_wrapper = PANDAWrapper(
        panda_root=panda_root,
        timeout=120,
        work_dir="./tmp/panda"
    )
    
    logger.info("[SETUP] ✓ PANDA wrapper initialized")
    return panda_wrapper


def create_initial_state():
    """Create initial state for incomplete-graph-p01 problem"""
    # Initial state from problem.hddl:
    # at A, goal-node D, known weights: A-B=4, C-D=5, A-C=15
    # Unknown: B-C weight (requires query-weight action)
    
    state = State()
    
    # Current location
    state.add_predicate("at(A)")
    
    # Goal node
    state.add_predicate("goal-node(D)")
    
    # Known weights (as predicates)
    state.add_predicate("weight(A,B,4)")
    state.add_predicate("weight(C,D,5)")
    state.add_predicate("weight(A,C,15)")
    
    # Edges (bidirectional)
    edges = [("A", "B"), ("B", "C"), ("C", "D"), ("A", "C")]
    for src, dst in edges:
        state.add_predicate(f"edge({src},{dst})")
        state.add_predicate(f"edge({dst},{src})")
    
    # Path tracking (initially zero)
    state.add_predicate("path-length(0)")
    
    # Store metadata for reference
    state.metadata["domain"] = "graph_traversal"
    state.metadata["problem"] = "incomplete-graph-p01"
    state.metadata["goal"] = "Find path from A to D"
    
    return state


async def run_single_test():
    """
    Run single test: incomplete-graph-p01
    
    Tests:
    - Knowledge gap detection (unknown weight B-C)
    - Hierarchical decomposition (find-path → resolve-unknown-weight → traverse)
    - PANDA validation loop
    - 4-layer validation system
    - Method library storage
    """
    
    logger.info("=" * 80)
    logger.info("PANDA INTEGRATION TEST - SINGLE PROBLEM")
    logger.info("Problem: incomplete-graph-p01 (Graph Traversal with Knowledge Gap)")
    logger.info("=" * 80)
    
    # Setup
    planning_agent, decomposition_agent, execution_agent, verification_agent, context_agent = await setup_agents()
    panda_wrapper = await setup_panda_wrapper()
    
    # Create workflow
    workflow = PANDAWorkflow(
        planning_agent=planning_agent,
        decomposition_agent=decomposition_agent,
        execution_agent=execution_agent,
        verification_agent=verification_agent,
        context_agent=context_agent,
        panda_wrapper=panda_wrapper,
        results_dir="./results/panda-results"
    )
    
    # Test configuration
    domain_name = "graph_traversal"
    problem_name = "incomplete-graph-p01"
    domain_file = "./src/domains/graph_traversal/domain.hddl"
    problem_file = "./src/domains/graph_traversal/problem.hddl"
    
    # Verify files exist
    if not Path(domain_file).exists():
        logger.error(f"Domain file not found: {domain_file}")
        return
    if not Path(problem_file).exists():
        logger.error(f"Problem file not found: {problem_file}")
        return
    
    logger.info(f"[TEST] Domain: {domain_file}")
    logger.info(f"[TEST] Problem: {problem_file}")
    
    # Create initial state
    initial_state = create_initial_state()
    
    # Goal description
    goal_description = """
    Find a path from node A to node D in a weighted graph.
    The weight of edge B-C is unknown and must be queried.
    Once the complete path is found, mark it as complete.
    """
    
    # Expected optimal plan length (rough estimate)
    # Decomposition: find-path → resolve-unknown-weight + traverse
    # Actions: query-weight(B,C) + traverse(A,B) + traverse(B,C) + traverse(C,D) + complete-path(D)
    optimal_plan_length = 5
    
    logger.info(f"[TEST] Goal: {goal_description.strip()}")
    logger.info(f"[TEST] Expected optimal plan length: {optimal_plan_length}")
    
    # Execute workflow
    logger.info("[TEST] Starting workflow execution...")
    result = await workflow.execute_workflow(
        domain_name=domain_name,
        problem_name=problem_name,
        domain_file=domain_file,
        problem_file=problem_file,
        initial_state=initial_state,
        goal_description=goal_description,
        optimal_plan_length=optimal_plan_length,
        session_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    # Print results
    logger.info("=" * 80)
    logger.info("TEST RESULTS")
    logger.info("=" * 80)
    
    logger.info(f"Overall Success: {result['success']}")
    logger.info(f"Total Time: {result.get('total_time_ms', 0):.1f}ms")
    
    if result.get('error'):
        logger.error(f"Error: {result['error']}")
    
    # Phase-by-phase results
    phases = result.get('phases', {})
    
    if 'planning' in phases:
        p = phases['planning']
        logger.info(f"\nPhase 1 - Planning: {'✓' if p.get('success') else '✗'}")
        logger.info(f"  LLM: {p.get('llm_used', 'N/A')}")
        logger.info(f"  Time: {p.get('processing_time_ms', 0):.1f}ms")
        logger.info(f"  Strategies: {len(p.get('strategies', []))}")
    
    if 'decomposition' in phases:
        d = phases['decomposition']
        logger.info(f"\nPhase 2 - Decomposition: {'✓' if d.get('success') else '✗'}")
        logger.info(f"  Method: {d.get('method', 'N/A')}")
        logger.info(f"  Used Fallback: {d.get('used_fallback', False)}")
        if d.get('validation_warnings'):
            logger.warning(f"  Warnings: {len(d['validation_warnings'])}")
    
    if 'panda_planning' in phases:
        pp = phases['panda_planning']
        logger.info(f"\nPhase 3 - PANDA Planning: {'✓' if pp.get('success') else '✗'}")
        logger.info(f"  Plan Length: {pp.get('plan_length', 0)}")
        logger.info(f"  Search Time: {pp.get('search_time_ms', 0):.1f}ms")
        logger.info(f"  Nodes Expanded: {pp.get('nodes_expanded', 0)}")
        if pp.get('actions'):
            logger.info(f"  Actions: {pp['actions']}")
    
    if 'execution' in phases:
        ex = phases['execution']
        logger.info(f"\nPhase 4 - Execution: {'✓' if ex.get('success') else '✗'}")
        logger.info(f"  Actions Executed: {len(ex.get('execution_trace', []))}")
    
    if 'validation' in phases:
        v = phases['validation']
        logger.info(f"\nPhase 5 - Validation: {'✓' if v.get('success') else '✗'}")
        if 'overall_score' in v:
            logger.info(f"  Overall Score: {v['overall_score']:.1f}/100")
        if 'layers' in v:
            for layer_name, layer_result in v['layers'].items():
                score = layer_result.get('score', 0.0)
                logger.info(f"  {layer_name}: {score:.2f} {'✓' if layer_result.get('passed') else '✗'}")
    
    if 'storage' in phases:
        s = phases['storage']
        logger.info(f"\nPhase 6 - Storage: {'✓' if s.get('success') else '✗'}")
        logger.info(f"  Trace Stored: {s.get('trace_stored', False)}")
    
    # Workflow statistics
    logger.info("\nWorkflow Statistics:")
    stats = workflow.get_statistics()
    logger.info(f"  Total Workflows: {stats['workflows_executed']}")
    logger.info(f"  Successful: {stats['successful_workflows']}")
    logger.info(f"  Failed: {stats['failed_workflows']}")
    logger.info(f"  Success Rate: {stats['success_rate'] * 100:.1f}%")
    
    logger.info("=" * 80)
    
    # Save detailed report
    report_file = Path("./results/panda-results/test_report.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump({
            "test_name": "incomplete-graph-p01",
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "statistics": stats
        }, f, indent=2, default=str)
    
    logger.info(f"[TEST] Detailed report saved to {report_file}")
    
    return result


if __name__ == "__main__":
    asyncio.run(run_single_test())
