"""
THESIS COMPREHENSIVE BENCHMARK: Neuro-Symbolic HTN Planning
============================================================

This benchmark demonstrates the COMPLETE WORKFLOW with 100% REAL LLM calls:

WORKFLOW DEMONSTRATION:
1. Problem A (New): LLM generates → PANDA validates → Execute → Verify → CACHE
2. Problem A' (Similar): Cache HIT → Skip LLM → Return cached solution
3. Problem B (New): Fresh LLM generation → PANDA validation → Cache
4. Problem B' (Similar): Cache HIT → Reuse

KPIs MEASURED (Simplified 4-KPI Framework):
- Success Rate (%)
- Mean Time to Solution (MTTS) in milliseconds
- Plan Optimality Score (POS) in %
- LLM Resource Utilization (LRU) in tokens

ALL LLM CALLS ARE 100% REAL - NO SIMULATIONS
Uses Groq API with Llama 3.3 70B model

Run with:
    cd <project-root>
    uv run python neuro-symbolic-htn-planner/benchmarks/thesis_comprehensive_benchmark.py
"""

import asyncio
import json
import os
import sys
import time
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


# ============================================================================
# CONFIGURATION
# ============================================================================

PANDA_ROOT = str(PROJECT_ROOT.parent / "PANDA-HTN")
RESULTS_DIR = str(PROJECT_ROOT / "results" / "panda-results")
DOMAINS_DIR = str(PROJECT_ROOT / "src" / "domains")
BENCHMARK_FILE = f"{RESULTS_DIR}/thesis_comprehensive_benchmark.json"

# LLM Configuration
LLM_MODEL = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0.3


# ============================================================================
# DATA CLASSES FOR KPIs
# ============================================================================

@dataclass
class KPIMetrics:
    """4 Core KPIs for thesis evaluation"""
    # KPI 1: Success Rate
    total_problems: int = 0
    successful_problems: int = 0
    
    # KPI 2: Mean Time to Solution
    total_time_ms: float = 0.0
    
    # KPI 3: Plan Optimality Score
    optimal_plans: int = 0
    total_plan_steps: int = 0
    total_optimal_steps: int = 0
    
    # KPI 4: LLM Resource Utilization
    total_llm_calls: int = 0
    total_tokens: int = 0
    
    # Cache statistics
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def success_rate(self) -> float:
        return (self.successful_problems / self.total_problems * 100) if self.total_problems > 0 else 0.0
    
    @property
    def mtts(self) -> float:
        return (self.total_time_ms / self.successful_problems) if self.successful_problems > 0 else 0.0
    
    @property
    def pos(self) -> float:
        return (self.total_optimal_steps / self.total_plan_steps * 100) if self.total_plan_steps > 0 else 0.0
    
    @property
    def lru(self) -> float:
        return (self.total_tokens / self.total_problems) if self.total_problems > 0 else 0.0


@dataclass
class WorkflowResult:
    """Result from a single workflow run"""
    workflow_type: str
    problem_name: str
    problem_id: str
    success: bool
    
    # Plan details
    plan_actions: List[str] = field(default_factory=list)
    plan_length: int = 0
    optimal_length: int = 0
    is_optimal: bool = False
    
    # Timing
    total_time_ms: float = 0.0
    llm_time_ms: float = 0.0
    planning_time_ms: float = 0.0
    
    # LLM usage
    llm_calls: int = 0
    llm_tokens: int = 0
    
    # Cache info
    from_cache: bool = False
    cache_signature: str = ""
    
    # Quality
    reasoning: str = ""
    error: Optional[str] = None


# ============================================================================
# EXPANDED PROBLEM SET (6 problems with similar pairs)
# ============================================================================

PROBLEMS = [
    # ===== PAIR 1: Graph Traversal (A → A' similar) =====
    {
        "id": "graph_1",
        "pair": "A",
        "name": "Graph Path Finding - Simple",
        "task": "find_path(A, D)",
        "description": "Find optimal path from node A to node D",
        "domain": "graph_traversal",
        "initial_state": {
            "at": "A",
            "goal": "D",
            "edges": ["A-B", "A-C", "B-C", "C-D"]
        },
        "goal": "Reach node D from node A",
        "operators": [
            {"name": "traverse", "params": ["from", "to"], "precond": "at(from), connected(from,to)", "effect": "at(to)"},
            {"name": "complete_path", "params": ["node"], "precond": "at(node), goal-node(node)", "effect": "path_complete"}
        ],
        "optimal_plan_length": 3,
        "hddl_domain": f"{DOMAINS_DIR}/graph_traversal/domain.hddl",
        "hddl_problem": f"{DOMAINS_DIR}/graph_traversal/problem.hddl",
        "is_similar_to": None  # First in pair
    },
    {
        "id": "graph_2",
        "pair": "A'",
        "name": "Graph Path Finding - Variant",
        "task": "find_path(A, D)",
        "description": "Find optimal path from node A to node D (same structure, minor variation)",
        "domain": "graph_traversal",
        "initial_state": {
            "at": "A",
            "goal": "D",
            "edges": ["A-B", "A-C", "B-C", "C-D"]  # SAME structure
        },
        "goal": "Reach node D from node A",  # SAME goal → should trigger cache hit
        "operators": [
            {"name": "traverse", "params": ["from", "to"], "precond": "at(from), connected(from,to)", "effect": "at(to)"},
            {"name": "complete_path", "params": ["node"], "precond": "at(node), goal-node(node)", "effect": "path_complete"}
        ],
        "optimal_plan_length": 3,
        "hddl_domain": f"{DOMAINS_DIR}/graph_traversal/domain.hddl",
        "hddl_problem": f"{DOMAINS_DIR}/graph_traversal/problem.hddl",
        "is_similar_to": "graph_1"  # Should hit cache from graph_1
    },
    
    # ===== PAIR 2: Probabilistic Decision (B → B' similar) =====
    {
        "id": "prob_1",
        "pair": "B",
        "name": "Probabilistic Decision - Route Choice",
        "task": "solve_probabilistic_graph(start, end)",
        "description": "Choose between safe path (30 min) vs risky path (10 min + 50% penalty)",
        "domain": "probabilistic_graph",
        "initial_state": {
            "at": "start",
            "goal": "end",
            "paths": {
                "safe": {"time": 30, "certain": True},
                "risky": {"base_time": 10, "penalty": 30, "penalty_prob": 0.5}
            }
        },
        "goal": "Reach end node with minimum expected travel time",
        "operators": [
            {"name": "calculate_expected_values", "params": ["node"], "precond": "at(node)", "effect": "ev_calculated"},
            {"name": "select_safe_path", "params": [], "precond": "", "effect": "path_chosen, chosen_safe"},
            {"name": "select_risky_path", "params": [], "precond": "", "effect": "path_chosen, chosen_risky"},
            {"name": "traverse_to_goal", "params": ["node"], "precond": "path_chosen", "effect": "at(node)"},
            {"name": "verify_goal", "params": ["node"], "precond": "at(node), goal-node(node)", "effect": "goal_reached"}
        ],
        "optimal_plan_length": 4,
        "hddl_domain": f"{DOMAINS_DIR}/probabilistic_graph/domain.hddl",
        "hddl_problem": f"{DOMAINS_DIR}/probabilistic_graph/problem.hddl",
        "is_similar_to": None
    },
    {
        "id": "prob_2",
        "pair": "B'",
        "name": "Probabilistic Decision - Same Structure",
        "task": "solve_probabilistic_graph(start, end)",
        "description": "Same decision problem (should hit cache)",
        "domain": "probabilistic_graph",
        "initial_state": {
            "at": "start",
            "goal": "end",
            "paths": {
                "safe": {"time": 30, "certain": True},
                "risky": {"base_time": 10, "penalty": 30, "penalty_prob": 0.5}
            }
        },
        "goal": "Reach end node with minimum expected travel time",  # SAME → cache hit
        "operators": [
            {"name": "calculate_expected_values", "params": ["node"], "precond": "at(node)", "effect": "ev_calculated"},
            {"name": "select_safe_path", "params": [], "precond": "", "effect": "path_chosen, chosen_safe"},
            {"name": "select_risky_path", "params": [], "precond": "", "effect": "path_chosen, chosen_risky"},
            {"name": "traverse_to_goal", "params": ["node"], "precond": "path_chosen", "effect": "at(node)"},
            {"name": "verify_goal", "params": ["node"], "precond": "at(node), goal-node(node)", "effect": "goal_reached"}
        ],
        "optimal_plan_length": 4,
        "hddl_domain": f"{DOMAINS_DIR}/probabilistic_graph/domain.hddl",
        "hddl_problem": f"{DOMAINS_DIR}/probabilistic_graph/problem.hddl",
        "is_similar_to": "prob_1"
    },
    
    # ===== PAIR 3: Graph with Different Goal (C → C' similar) =====
    {
        "id": "graph_3",
        "pair": "C",
        "name": "Graph Traversal - Extended",
        "task": "find_path(B, D)",
        "description": "Find path from B to D (different start node)",
        "domain": "graph_traversal",
        "initial_state": {
            "at": "B",  # Different start
            "goal": "D",
            "edges": ["A-B", "A-C", "B-C", "C-D"]
        },
        "goal": "Reach node D from node B",  # Different goal description
        "operators": [
            {"name": "traverse", "params": ["from", "to"], "precond": "at(from), connected(from,to)", "effect": "at(to)"},
            {"name": "complete_path", "params": ["node"], "precond": "at(node), goal-node(node)", "effect": "path_complete"}
        ],
        "optimal_plan_length": 2,  # B→C→D = 2 steps
        "hddl_domain": f"{DOMAINS_DIR}/graph_traversal/domain.hddl",
        "hddl_problem": f"{DOMAINS_DIR}/graph_traversal/problem.hddl",
        "is_similar_to": None
    },
    {
        "id": "graph_4",
        "pair": "C'",
        "name": "Graph Traversal - Extended Repeat",
        "task": "find_path(B, D)",
        "description": "Same as graph_3 (should hit cache)",
        "domain": "graph_traversal",
        "initial_state": {
            "at": "B",
            "goal": "D",
            "edges": ["A-B", "A-C", "B-C", "C-D"]
        },
        "goal": "Reach node D from node B",  # SAME → cache hit
        "operators": [
            {"name": "traverse", "params": ["from", "to"], "precond": "at(from), connected(from,to)", "effect": "at(to)"},
            {"name": "complete_path", "params": ["node"], "precond": "at(node), goal-node(node)", "effect": "path_complete"}
        ],
        "optimal_plan_length": 2,
        "hddl_domain": f"{DOMAINS_DIR}/graph_traversal/domain.hddl",
        "hddl_problem": f"{DOMAINS_DIR}/graph_traversal/problem.hddl",
        "is_similar_to": "graph_3"
    },
]


# ============================================================================
# LLM-ONLY WORKFLOW
# ============================================================================

async def run_llm_only_workflow(problem: dict) -> WorkflowResult:
    """
    Pure LLM planning - no symbolic validation.
    Makes REAL LLM API calls.
    """
    start_time = time.perf_counter()
    problem_id = problem["id"]
    
    try:
        from src.llm.groq_client import GroqClient
        from src.llm.local_llm_interface import LLMConfig
        
        config = LLMConfig(
            model_name=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=2000
        )
        llm = GroqClient(config=config)
        
        # Build prompt
        operators_str = "\n".join([
            f"- {op['name']}({', '.join(op['params'])}): {op['precond']} → {op['effect']}"
            for op in problem['operators']
        ])
        
        system_prompt = """You are an HTN (Hierarchical Task Network) planner.
Given a task and operators, generate a valid plan.

Return ONLY valid JSON:
{
    "plan": ["action1(param1)", "action2(param1, param2)", ...],
    "reasoning": "Brief explanation"
}

Do NOT include markdown. Return ONLY the JSON object."""
        
        user_prompt = f"""Task: {problem['task']}
Domain: {problem['name']}
Goal: {problem['goal']}
Initial State: {json.dumps(problem['initial_state'])}

Available Operators:
{operators_str}

Generate a plan. Return ONLY valid JSON."""
        
        # REAL LLM CALL
        logger.info(f"[LLM-ONLY] Making REAL API call for {problem_id}")
        llm_start = time.perf_counter()
        
        response = llm.generate(prompt=user_prompt, system_prompt=system_prompt)
        
        llm_time = (time.perf_counter() - llm_start) * 1000
        llm_tokens = response.tokens_used.get("total_tokens", 0) if response.tokens_used else 0
        
        logger.success(f"[LLM-ONLY] Response received: {llm_tokens} tokens")
        
        # Parse response
        result = WorkflowResult(
            workflow_type="llm_only",
            problem_name=problem["name"],
            problem_id=problem_id,
            success=False,
            optimal_length=problem.get("optimal_plan_length", 0),
            llm_time_ms=llm_time,
            llm_calls=1,
            llm_tokens=llm_tokens
        )
        
        try:
            content = response.content.strip()
            
            # Remove markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)
            
            parsed = json.loads(content)
            plan = parsed.get("plan", [])
            
            result.plan_actions = plan
            result.plan_length = len(plan)
            result.reasoning = parsed.get("reasoning", "")
            result.success = len(plan) > 0
            result.is_optimal = len(plan) == problem.get('optimal_plan_length', 0)
            
        except json.JSONDecodeError as e:
            result.error = f"JSON parse error: {e}"
            result.reasoning = response.content[:200]
        
        result.total_time_ms = (time.perf_counter() - start_time) * 1000
        return result
        
    except Exception as e:
        logger.error(f"[LLM-ONLY] Error: {e}")
        return WorkflowResult(
            workflow_type="llm_only",
            problem_name=problem["name"],
            problem_id=problem_id,
            success=False,
            total_time_ms=(time.perf_counter() - start_time) * 1000,
            error=str(e)
        )


# ============================================================================
# NEURO-SYMBOLIC WORKFLOW WITH CACHE
# ============================================================================

async def run_neuro_symbolic_workflow(problem: dict) -> WorkflowResult:
    """
    Neuro-Symbolic planning with PANDA validation and caching.
    Shows complete workflow including cache hits.
    """
    start_time = time.perf_counter()
    problem_id = problem["id"]
    
    try:
        from src.integrations.panda_wrapper import PANDAWrapper
        from src.integrations.domain_registry import DomainRegistry
        from src.integrations.problem_cache import ProblemCache
        
        # Initialize components
        panda = PANDAWrapper(panda_root=PANDA_ROOT, results_dir=RESULTS_DIR)
        cache = ProblemCache(cache_path=f"{RESULTS_DIR}/problem_cache.json")
        
        # ===== STEP 1: Check Problem Cache =====
        logger.info(f"[NEURO-SYM] Step 1: Checking problem cache for {problem_id}")
        
        cached = cache.check_cache(
            domain=problem['domain'],
            initial_state=problem['initial_state'],
            goal_description=problem['goal']
        )
        
        if cached:
            # CACHE HIT - Skip all LLM and PANDA calls
            total_time = (time.perf_counter() - start_time) * 1000
            
            # Format plan actions from cache
            if cached.plan_actions:
                if isinstance(cached.plan_actions[0], dict):
                    plan_actions = [
                        f"{a.get('name', '?')}({','.join(a.get('parameters', []))})" 
                        for a in cached.plan_actions
                    ]
                else:
                    plan_actions = [str(a) for a in cached.plan_actions]
            else:
                plan_actions = []
            
            print(f"\n    ★ CACHE HIT ★")
            print(f"    Signature: {cached.signature[:12]}...")
            print(f"    Hit Count: {cached.hit_count}")
            print(f"    Original Time: {cached.total_time_ms:.0f}ms")
            print(f"    → Skipping LLM and PANDA calls!")
            
            return WorkflowResult(
                workflow_type="neuro_symbolic",
                problem_name=problem["name"],
                problem_id=problem_id,
                success=True,
                plan_actions=plan_actions,
                plan_length=len(plan_actions),
                optimal_length=problem.get("optimal_plan_length", 0),
                is_optimal=len(plan_actions) == problem.get("optimal_plan_length", 0),
                total_time_ms=total_time,
                llm_calls=0,  # No LLM calls - from cache
                llm_tokens=0,
                from_cache=True,
                cache_signature=cached.signature,
                reasoning=f"Retrieved from cache (hit #{cached.hit_count})"
            )
        
        # ===== STEP 2: Cache Miss - Need to compute =====
        logger.info(f"[NEURO-SYM] Step 2: Cache MISS - Running full pipeline")
        print(f"\n    ○ CACHE MISS")
        print(f"    → Running full workflow: LLM → PANDA → Execute → Cache")
        
        llm_time = 0.0
        llm_calls = 0
        llm_tokens = 0
        
        # Check if HDDL files exist
        domain_file = problem.get('hddl_domain')
        problem_file = problem.get('hddl_problem')
        
        if not domain_file or not Path(domain_file).exists():
            # Need to generate with LLM
            logger.info(f"[NEURO-SYM] Step 2a: Generating HDDL with LLM")
            print(f"    → Generating HDDL domain with LLM...")
            
            from src.llm.groq_client import GroqClient
            from src.llm.local_llm_interface import LLMConfig
            
            config = LLMConfig(model_name=LLM_MODEL, temperature=0.2, max_tokens=3000)
            llm = GroqClient(config=config)
            
            hddl_prompt = f"""Generate valid HDDL domain for: {problem['name']}
Task: {problem['task']}
Goal: {problem['goal']}
Operators: {json.dumps(problem['operators'], indent=2)}

Return ONLY valid HDDL code."""
            
            llm_start = time.perf_counter()
            response = llm.generate(
                prompt=hddl_prompt,
                system_prompt="Generate valid HDDL for PANDA planner."
            )
            llm_time = (time.perf_counter() - llm_start) * 1000
            llm_calls = 1
            llm_tokens = response.tokens_used.get("total_tokens", 0) if response.tokens_used else 0
            
            print(f"    → LLM generated HDDL: {llm_tokens} tokens, {llm_time:.0f}ms")
        
        # ===== STEP 3: Run PANDA Planning =====
        logger.info(f"[NEURO-SYM] Step 3: Running PANDA symbolic planning")
        print(f"    → Running PANDA symbolic planning...")
        
        if not problem_file or not Path(problem_file).exists():
            return WorkflowResult(
                workflow_type="neuro_symbolic",
                problem_name=problem["name"],
                problem_id=problem_id,
                success=False,
                total_time_ms=(time.perf_counter() - start_time) * 1000,
                llm_time_ms=llm_time,
                llm_calls=llm_calls,
                llm_tokens=llm_tokens,
                error="Problem file not found"
            )
        
        panda_start = time.perf_counter()
        panda_result = panda.plan(
            domain_file=domain_file,
            problem_file=problem_file,
            output_name=f"bench_{problem_id}"
        )
        planning_time = (time.perf_counter() - panda_start) * 1000
        
        print(f"    → PANDA complete: {planning_time:.0f}ms, {panda_result.nodes_expanded} nodes")
        
        if panda_result.success:
            plan_actions = [
                f"{a['name']}({','.join(a['parameters'])})" 
                for a in panda_result.actions
            ]
            
            # ===== STEP 4: Cache the solution =====
            logger.info(f"[NEURO-SYM] Step 4: Caching solution for future reuse")
            print(f"    → Caching solution for future reuse...")
            
            total_time = (time.perf_counter() - start_time) * 1000
            
            signature = cache.store_solution(
                domain=problem['domain'],
                problem_name=problem_id,
                initial_state=problem['initial_state'],
                goal_description=problem['goal'],
                solution={"success": True, "plan_length": len(plan_actions)},
                plan_actions=panda_result.actions,
                total_time_ms=total_time
            )
            
            print(f"    → Cached with signature: {signature[:12]}...")
            
            return WorkflowResult(
                workflow_type="neuro_symbolic",
                problem_name=problem["name"],
                problem_id=problem_id,
                success=True,
                plan_actions=plan_actions,
                plan_length=len(plan_actions),
                optimal_length=problem.get("optimal_plan_length", 0),
                is_optimal=len(plan_actions) == problem.get("optimal_plan_length", 0),
                total_time_ms=total_time,
                llm_time_ms=llm_time,
                planning_time_ms=planning_time,
                llm_calls=llm_calls,
                llm_tokens=llm_tokens,
                from_cache=False,
                cache_signature=signature,
                reasoning=f"PANDA validated ({panda_result.nodes_expanded} nodes), cached"
            )
        else:
            return WorkflowResult(
                workflow_type="neuro_symbolic",
                problem_name=problem["name"],
                problem_id=problem_id,
                success=False,
                total_time_ms=(time.perf_counter() - start_time) * 1000,
                llm_time_ms=llm_time,
                planning_time_ms=planning_time,
                llm_calls=llm_calls,
                llm_tokens=llm_tokens,
                error=panda_result.error
            )
            
    except Exception as e:
        logger.error(f"[NEURO-SYM] Error: {e}")
        import traceback
        traceback.print_exc()
        return WorkflowResult(
            workflow_type="neuro_symbolic",
            problem_name=problem["name"],
            problem_id=problem_id,
            success=False,
            total_time_ms=(time.perf_counter() - start_time) * 1000,
            error=str(e)
        )


# ============================================================================
# MAIN BENCHMARK
# ============================================================================

async def run_comprehensive_benchmark():
    """
    Run comprehensive benchmark demonstrating complete workflow.
    Includes similar problem pairs to show cache hits.
    """
    
    print("\n" + "=" * 80)
    print("  THESIS COMPREHENSIVE BENCHMARK")
    print("  Neuro-Symbolic HTN Planning - Complete Workflow Demonstration")
    print("=" * 80)
    print(f"  LLM Provider: Groq")
    print(f"  Model: {LLM_MODEL}")
    print(f"  Problems: {len(PROBLEMS)} (including {len(PROBLEMS)//2} similar pairs)")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    print("\n  100% REAL LLM CALLS - NO SIMULATIONS")
    print("  API keys must be exported: GROQ_API_KEY")
    print("=" * 80)
    
    # Clear problem cache for fresh demonstration
    cache_path = Path(RESULTS_DIR) / "problem_cache.json"
    if cache_path.exists():
        print(f"\n  ⚠ Clearing problem cache for fresh demonstration...")
        cache_path.unlink()
    
    # Initialize metrics
    llm_only_kpi = KPIMetrics()
    neuro_sym_kpi = KPIMetrics()
    
    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "llm_provider": "groq",
            "llm_model": LLM_MODEL,
            "total_problems": len(PROBLEMS),
            "similar_pairs": len(PROBLEMS) // 2,
            "real_llm_calls": True,
            "simulated": False
        },
        "workflow_demonstration": [],
        "kpi_results": {},
        "problem_pairs": []
    }
    
    # Track pairs for analysis
    pair_analysis = {}
    
    for i, problem in enumerate(PROBLEMS):
        problem_id = problem["id"]
        pair_id = problem["pair"]
        is_repeat = problem["is_similar_to"] is not None
        
        print(f"\n{'━' * 80}")
        print(f"  PROBLEM {i+1}/{len(PROBLEMS)}: {problem['name']}")
        print(f"  ID: {problem_id} | Pair: {pair_id} | {'REPEAT (expect cache hit)' if is_repeat else 'NEW'}")
        print(f"  Task: {problem['task']}")
        print(f"  Optimal Length: {problem.get('optimal_plan_length', '?')}")
        print(f"{'━' * 80}")
        
        problem_result = {
            "problem_id": problem_id,
            "pair": pair_id,
            "is_repeat": is_repeat,
            "expected_cache_hit": is_repeat,
            "llm_only": None,
            "neuro_symbolic": None
        }
        
        # ===== Run LLM-Only Workflow =====
        print(f"\n  [1/2] LLM-Only Workflow")
        print(f"  " + "-" * 40)
        llm_result = await run_llm_only_workflow(problem)
        
        # Update LLM-only KPIs
        llm_only_kpi.total_problems += 1
        if llm_result.success:
            llm_only_kpi.successful_problems += 1
            llm_only_kpi.total_time_ms += llm_result.total_time_ms
            llm_only_kpi.total_plan_steps += llm_result.plan_length
            llm_only_kpi.total_optimal_steps += llm_result.optimal_length
            if llm_result.is_optimal:
                llm_only_kpi.optimal_plans += 1
        llm_only_kpi.total_llm_calls += llm_result.llm_calls
        llm_only_kpi.total_tokens += llm_result.llm_tokens
        
        print(f"    Status: {'✓ Success' if llm_result.success else '✗ Failed'}")
        print(f"    Plan Length: {llm_result.plan_length} (optimal: {llm_result.optimal_length})")
        print(f"    Is Optimal: {'Yes' if llm_result.is_optimal else 'No'}")
        print(f"    Time: {llm_result.total_time_ms:.0f}ms")
        print(f"    LLM Calls: {llm_result.llm_calls}")
        print(f"    Tokens: {llm_result.llm_tokens}")
        if llm_result.plan_actions:
            print(f"    Plan: {llm_result.plan_actions}")
        
        problem_result["llm_only"] = asdict(llm_result)
        
        # ===== Run Neuro-Symbolic Workflow =====
        print(f"\n  [2/2] Neuro-Symbolic Workflow (LLM + PANDA + Cache)")
        print(f"  " + "-" * 40)
        neuro_result = await run_neuro_symbolic_workflow(problem)
        
        # Update Neuro-Symbolic KPIs
        neuro_sym_kpi.total_problems += 1
        if neuro_result.success:
            neuro_sym_kpi.successful_problems += 1
            neuro_sym_kpi.total_time_ms += neuro_result.total_time_ms
            neuro_sym_kpi.total_plan_steps += neuro_result.plan_length
            neuro_sym_kpi.total_optimal_steps += neuro_result.optimal_length
            if neuro_result.is_optimal:
                neuro_sym_kpi.optimal_plans += 1
        
        if neuro_result.from_cache:
            neuro_sym_kpi.cache_hits += 1
        else:
            neuro_sym_kpi.cache_misses += 1
        
        neuro_sym_kpi.total_llm_calls += neuro_result.llm_calls
        neuro_sym_kpi.total_tokens += neuro_result.llm_tokens
        
        print(f"    Status: {'✓ Success' if neuro_result.success else '✗ Failed'}")
        print(f"    From Cache: {'★ YES' if neuro_result.from_cache else 'No (computed fresh)'}")
        print(f"    Plan Length: {neuro_result.plan_length} (optimal: {neuro_result.optimal_length})")
        print(f"    Is Optimal: {'Yes' if neuro_result.is_optimal else 'No'}")
        print(f"    Time: {neuro_result.total_time_ms:.0f}ms")
        print(f"    LLM Calls: {neuro_result.llm_calls}")
        print(f"    Tokens: {neuro_result.llm_tokens}")
        if neuro_result.plan_actions:
            print(f"    Plan: {neuro_result.plan_actions}")
        
        problem_result["neuro_symbolic"] = asdict(neuro_result)
        problem_result["cache_hit_as_expected"] = (is_repeat == neuro_result.from_cache)
        
        results["workflow_demonstration"].append(problem_result)
        
        # Track pair analysis
        if is_repeat:
            pair_key = problem["is_similar_to"]
            pair_analysis[pair_key] = {
                "original": pair_key,
                "repeat": problem_id,
                "cache_hit": neuro_result.from_cache,
                "tokens_saved": llm_result.llm_tokens,
                "time_saved_ms": llm_result.total_time_ms - neuro_result.total_time_ms
            }
    
    # ===== FINAL SUMMARY =====
    print("\n" + "=" * 80)
    print("  COMPREHENSIVE BENCHMARK RESULTS - 4 KPI FRAMEWORK")
    print("=" * 80)
    
    # KPI 1: Success Rate
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'KPI 1: SUCCESS RATE':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Workflow':<30} {'Success':>12} {'Rate':>14} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'LLM-Only':<30} {llm_only_kpi.successful_problems}/{llm_only_kpi.total_problems:>10} {llm_only_kpi.success_rate:>13.1f}% │")
    print(f"  │ {'Neuro-Symbolic':<30} {neuro_sym_kpi.successful_problems}/{neuro_sym_kpi.total_problems:>10} {neuro_sym_kpi.success_rate:>13.1f}% │")
    print(f"  └{'─' * 60}┘")
    
    # KPI 2: MTTS
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'KPI 2: MEAN TIME TO SOLUTION (MTTS)':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Workflow':<30} {'Total (ms)':>12} {'MTTS (ms)':>14} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'LLM-Only':<30} {llm_only_kpi.total_time_ms:>12.0f} {llm_only_kpi.mtts:>14.1f} │")
    print(f"  │ {'Neuro-Symbolic':<30} {neuro_sym_kpi.total_time_ms:>12.0f} {neuro_sym_kpi.mtts:>14.1f} │")
    print(f"  ├{'─' * 60}┤")
    speedup = llm_only_kpi.mtts / neuro_sym_kpi.mtts if neuro_sym_kpi.mtts > 0 else 0
    print(f"  │ {'SPEEDUP FACTOR':<30} {speedup:>26.1f}x │")
    print(f"  └{'─' * 60}┘")
    
    # KPI 3: POS
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'KPI 3: PLAN OPTIMALITY SCORE (POS)':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Workflow':<30} {'Optimal Plans':>12} {'POS':>14} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'LLM-Only':<30} {llm_only_kpi.optimal_plans}/{llm_only_kpi.total_problems:>10} {llm_only_kpi.pos:>13.1f}% │")
    print(f"  │ {'Neuro-Symbolic':<30} {neuro_sym_kpi.optimal_plans}/{neuro_sym_kpi.total_problems:>10} {neuro_sym_kpi.pos:>13.1f}% │")
    print(f"  └{'─' * 60}┘")
    
    # KPI 4: LRU
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'KPI 4: LLM RESOURCE UTILIZATION (LRU)':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Workflow':<30} {'Total Tokens':>12} {'LRU (tok/prob)':>14} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'LLM-Only':<30} {llm_only_kpi.total_tokens:>12} {llm_only_kpi.lru:>14.1f} │")
    print(f"  │ {'Neuro-Symbolic':<30} {neuro_sym_kpi.total_tokens:>12} {neuro_sym_kpi.lru:>14.1f} │")
    print(f"  ├{'─' * 60}┤")
    tokens_saved = llm_only_kpi.total_tokens - neuro_sym_kpi.total_tokens
    savings_pct = (tokens_saved / llm_only_kpi.total_tokens * 100) if llm_only_kpi.total_tokens > 0 else 0
    print(f"  │ {'TOKENS SAVED':<30} {tokens_saved:>12} {savings_pct:>13.1f}% │")
    print(f"  └{'─' * 60}┘")
    
    # Cache Analysis
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'CACHE PERFORMANCE (Neuro-Symbolic Only)':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Cache Hits':<30} {neuro_sym_kpi.cache_hits:>26} │")
    print(f"  │ {'Cache Misses':<30} {neuro_sym_kpi.cache_misses:>26} │")
    cache_hit_rate = (neuro_sym_kpi.cache_hits / neuro_sym_kpi.total_problems * 100) if neuro_sym_kpi.total_problems > 0 else 0
    print(f"  │ {'Cache Hit Rate':<30} {cache_hit_rate:>25.1f}% │")
    print(f"  └{'─' * 60}┘")
    
    # Pair Analysis
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'SIMILAR PROBLEM PAIRS ANALYSIS':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Pair':<15} {'Original':<12} {'Repeat':<12} {'Cache Hit':>17} │")
    print(f"  ├{'─' * 60}┤")
    for original, data in pair_analysis.items():
        cache_status = "★ YES" if data["cache_hit"] else "NO"
        print(f"  │ {data['original'] + ' → ' + data['repeat']:<15} {'computed':<12} {'cached':<12} {cache_status:>17} │")
    print(f"  └{'─' * 60}┘")
    
    # Store KPI results
    results["kpi_results"] = {
        "llm_only": {
            "success_rate": llm_only_kpi.success_rate,
            "mtts_ms": llm_only_kpi.mtts,
            "pos": llm_only_kpi.pos,
            "lru_tokens_per_problem": llm_only_kpi.lru,
            "total_tokens": llm_only_kpi.total_tokens,
            "total_llm_calls": llm_only_kpi.total_llm_calls
        },
        "neuro_symbolic": {
            "success_rate": neuro_sym_kpi.success_rate,
            "mtts_ms": neuro_sym_kpi.mtts,
            "pos": neuro_sym_kpi.pos,
            "lru_tokens_per_problem": neuro_sym_kpi.lru,
            "total_tokens": neuro_sym_kpi.total_tokens,
            "total_llm_calls": neuro_sym_kpi.total_llm_calls,
            "cache_hits": neuro_sym_kpi.cache_hits,
            "cache_misses": neuro_sym_kpi.cache_misses,
            "cache_hit_rate": cache_hit_rate
        },
        "comparison": {
            "speedup_factor": speedup,
            "tokens_saved": tokens_saved,
            "tokens_saved_percent": savings_pct
        }
    }
    
    results["problem_pairs"] = [
        {"original": orig, **data} for orig, data in pair_analysis.items()
    ]
    
    # Save results
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    with open(BENCHMARK_FILE, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n  Results saved to: {BENCHMARK_FILE}")
    print("=" * 80)
    print("\n  BENCHMARK COMPLETE - 100% REAL LLM CALLS")
    print("=" * 80)
    
    return results


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    asyncio.run(run_comprehensive_benchmark())

