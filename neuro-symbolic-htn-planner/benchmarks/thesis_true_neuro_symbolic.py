"""
TRUE NEURO-SYMBOLIC BENCHMARK: LLM Generates HDDL from Scratch
===============================================================

This benchmark demonstrates the ACTUAL neuro-symbolic workflow:

1. User provides a natural language problem description
2. LLM GENERATES HDDL domain and problem files from scratch
3. PANDA VALIDATES the LLM-generated HDDL
4. If invalid → FEEDBACK LOOP → LLM corrects based on PANDA errors
5. If valid → EXECUTE plan with PANDA
6. STORE generated domain for future reuse

NO HAND-CODED DOMAINS - LLM generates everything from scratch!

Run with:
    cd <project-root>
    uv run python neuro-symbolic-htn-planner/benchmarks/thesis_true_neuro_symbolic.py
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
LLM_GENERATED_DIR = str(PROJECT_ROOT / "results" / "llm-generated-hddl")
BENCHMARK_FILE = f"{RESULTS_DIR}/thesis_true_neuro_symbolic.json"

# LLM Configuration
LLM_MODEL = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0.2  # Lower for more consistent HDDL generation

# Maximum validation attempts before giving up
MAX_VALIDATION_ATTEMPTS = 3


# ============================================================================
# PROBLEM DEFINITIONS (Natural Language Only - NO HDDL)
# ============================================================================

PROBLEMS = [
    {
        "id": "simple_delivery",
        "name": "Simple Package Delivery",
        "description": """
        A robot needs to deliver a package from location A to location B.
        
        The robot can:
        - Move between connected locations
        - Pick up a package (if at same location)
        - Put down a package (if holding it)
        
        Initial state:
        - Robot is at location A
        - Package is at location A
        - Locations A and B are connected
        
        Goal: Package should be at location B
        """,
        "domain_name": "simple_delivery",
        "expected_actions": ["move", "pick-up", "put-down"],
        "optimal_plan_length": 3  # pick-up, move, put-down
    },
    {
        "id": "light_switch",
        "name": "Light Switch Control",
        "description": """
        Control a light switch system.
        
        Actions available:
        - Turn on a light (if it's off)
        - Turn off a light (if it's on)
        
        Initial state:
        - Light1 is off
        - Light2 is off
        
        Goal: Light1 should be on, Light2 should be on
        """,
        "domain_name": "light_switch",
        "expected_actions": ["turn-on", "turn-off"],
        "optimal_plan_length": 2  # turn-on light1, turn-on light2
    },
    {
        "id": "block_stacking",
        "name": "Simple Block Stacking",
        "description": """
        Stack blocks on a table.
        
        Actions available:
        - Pick up a block (if hand is empty and block is clear)
        - Put down a block on table (if holding a block)
        - Stack a block on another block (if holding a block and target is clear)
        - Unstack a block from another block (if hand is empty and block is clear)
        
        Initial state:
        - Block A is on table
        - Block B is on table
        - Hand is empty
        - Both blocks are clear
        
        Goal: Block A should be on Block B
        """,
        "domain_name": "block_stacking",
        "expected_actions": ["pick-up", "put-down", "stack", "unstack"],
        "optimal_plan_length": 2  # pick-up A, stack A on B
    }
]


# ============================================================================
# HDDL GENERATION PROMPTS
# ============================================================================

DOMAIN_GENERATION_PROMPT = """You are an expert HDDL (Hierarchical Domain Definition Language) generator for the PANDA HTN planner.

Generate a COMPLETE and VALID HDDL domain file for the following problem:

{problem_description}

CRITICAL REQUIREMENTS:
1. Use ONLY these HDDL constructs that PANDA supports:
   - (:requirements :typing :hierarchy)
   - (:types ...) 
   - (:predicates ...)
   - (:task ...) for abstract tasks
   - (:method ...) with :parameters, :task, :precondition, :subtasks, :ordering
   - (:action ...) with :parameters, :precondition, :effect

2. EVERY abstract task MUST have at least one method
3. Methods MUST reference the task they decompose with (:task ...)
4. Use simple predicate names (no special characters)
5. Include a top-level task that can be decomposed

EXAMPLE STRUCTURE:
```
(define (domain example-domain)
  (:requirements :typing :hierarchy)
  
  (:types
    location object - object
  )
  
  (:predicates
    (at ?obj - object ?loc - location)
    (holding ?obj - object)
  )
  
  (:task achieve-goal
    :parameters ())
  
  (:method method-achieve-goal
    :parameters ()
    :task (achieve-goal)
    :precondition ()
    :subtasks (and
      (task1 (primitive-action))
    )
  )
  
  (:action primitive-action
    :parameters ()
    :precondition ()
    :effect ()
  )
)
```

Generate ONLY the HDDL domain code. No explanations, no markdown, just valid HDDL.
Domain name should be: {domain_name}
"""

PROBLEM_GENERATION_PROMPT = """You are an expert HDDL problem generator for the PANDA HTN planner.

Generate a COMPLETE and VALID HDDL problem file for:

{problem_description}

The domain file is:
{domain_content}

CRITICAL REQUIREMENTS:
1. Problem name: {problem_name}
2. Domain reference must match: {domain_name}
3. Objects must match types defined in domain
4. Init predicates must use predicates from domain
5. Use (:htn :ordered-tasks ...) to specify the goal task

EXAMPLE STRUCTURE:
```
(define (problem example-problem)
  (:domain example-domain)
  
  (:objects
    obj1 obj2 - object
    loc1 loc2 - location
  )
  
  (:init
    (at obj1 loc1)
    (clear obj1)
  )
  
  (:htn
    :ordered-tasks (and
      (task1 (achieve-goal))
    )
  )
)
```

Generate ONLY the HDDL problem code. No explanations, no markdown, just valid HDDL.
"""

CORRECTION_PROMPT = """The HDDL you generated has validation errors from PANDA parser:

ERRORS:
{errors}

ORIGINAL HDDL:
{original_hddl}

Please fix the errors and regenerate the HDDL. Common issues:
- Missing method for a task
- Type mismatches in predicates
- Invalid syntax in :subtasks or :ordering
- Missing :task reference in method

Generate ONLY the corrected HDDL code. No explanations.
"""


# ============================================================================
# HDDL GENERATION AND VALIDATION
# ============================================================================

@dataclass
class HDDLGenerationResult:
    """Result of HDDL generation attempt"""
    success: bool
    domain_content: str = ""
    problem_content: str = ""
    domain_file: str = ""
    problem_file: str = ""
    validation_attempts: int = 0
    validation_errors: List[str] = field(default_factory=list)
    llm_calls: int = 0
    llm_tokens: int = 0
    generation_time_ms: float = 0.0
    error: Optional[str] = None


async def generate_hddl_with_validation(
    problem: dict,
    output_dir: Path
) -> HDDLGenerationResult:
    """
    Generate HDDL domain and problem files using LLM with PANDA validation loop.
    
    This is the CORE of the neuro-symbolic approach:
    1. LLM generates HDDL
    2. PANDA validates
    3. If invalid → LLM corrects based on errors
    4. Repeat until valid or max attempts reached
    """
    from src.llm.groq_client import GroqClient
    from src.llm.local_llm_interface import LLMConfig
    from src.integrations.panda_wrapper import PANDAWrapper
    
    start_time = time.perf_counter()
    result = HDDLGenerationResult(success=False)
    
    # Initialize LLM
    config = LLMConfig(
        model_name=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=4000
    )
    llm = GroqClient(config=config)
    
    # Initialize PANDA
    panda = PANDAWrapper(panda_root=PANDA_ROOT, results_dir=RESULTS_DIR)
    
    # Create output directory
    problem_dir = output_dir / problem["domain_name"]
    problem_dir.mkdir(parents=True, exist_ok=True)
    
    domain_file = str(problem_dir / "domain.hddl")
    problem_file = str(problem_dir / "problem.hddl")
    
    print(f"\n{'='*60}")
    print(f"  GENERATING HDDL FOR: {problem['name']}")
    print(f"{'='*60}")
    print(f"  Output: {problem_dir}")
    print(f"  Max validation attempts: {MAX_VALIDATION_ATTEMPTS}")
    print(f"{'='*60}\n")
    
    # ========== STEP 1: Generate Domain ==========
    print("  [Step 1] Generating HDDL domain with LLM...")
    
    domain_prompt = DOMAIN_GENERATION_PROMPT.format(
        problem_description=problem["description"],
        domain_name=problem["domain_name"]
    )
    
    logger.info(f"[HDDL-GEN] Generating domain for {problem['id']}")
    
    try:
        domain_response = llm.generate(
            prompt=domain_prompt,
            system_prompt="You are an expert HDDL generator. Output ONLY valid HDDL code."
        )
        result.llm_calls += 1
        result.llm_tokens += domain_response.tokens_used.get("total_tokens", 0) if domain_response.tokens_used else 0
        
        domain_content = _clean_hddl_response(domain_response.content)
        
        print(f"    ✓ Domain generated: {len(domain_content)} chars, {result.llm_tokens} tokens")
        print(f"    Preview: {domain_content[:100]}...")
        
    except Exception as e:
        result.error = f"Domain generation failed: {e}"
        result.generation_time_ms = (time.perf_counter() - start_time) * 1000
        return result
    
    # ========== STEP 2: Generate Problem ==========
    print("\n  [Step 2] Generating HDDL problem with LLM...")
    
    problem_prompt = PROBLEM_GENERATION_PROMPT.format(
        problem_description=problem["description"],
        domain_content=domain_content,
        problem_name=f"{problem['domain_name']}-p01",
        domain_name=problem["domain_name"]
    )
    
    try:
        problem_response = llm.generate(
            prompt=problem_prompt,
            system_prompt="You are an expert HDDL generator. Output ONLY valid HDDL code."
        )
        result.llm_calls += 1
        result.llm_tokens += problem_response.tokens_used.get("total_tokens", 0) if problem_response.tokens_used else 0
        
        problem_content = _clean_hddl_response(problem_response.content)
        
        print(f"    ✓ Problem generated: {len(problem_content)} chars")
        print(f"    Preview: {problem_content[:100]}...")
        
    except Exception as e:
        result.error = f"Problem generation failed: {e}"
        result.generation_time_ms = (time.perf_counter() - start_time) * 1000
        return result
    
    # ========== STEP 3: Validation Loop ==========
    print(f"\n  [Step 3] PANDA Validation Loop (max {MAX_VALIDATION_ATTEMPTS} attempts)...")
    
    for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
        result.validation_attempts = attempt
        print(f"\n    Attempt {attempt}/{MAX_VALIDATION_ATTEMPTS}:")
        
        # Save current versions
        with open(domain_file, 'w') as f:
            f.write(domain_content)
        with open(problem_file, 'w') as f:
            f.write(problem_content)
        
        print(f"      → Saved domain to: {domain_file}")
        print(f"      → Saved problem to: {problem_file}")
        
        # Validate with PANDA
        print(f"      → Running PANDA validation...")
        validation = panda.validate_hddl(domain_file, problem_file)
        
        if validation.is_valid:
            print(f"      ✓ VALIDATION PASSED!")
            result.success = True
            result.domain_content = domain_content
            result.problem_content = problem_content
            result.domain_file = domain_file
            result.problem_file = problem_file
            break
        else:
            # Collect errors
            errors = validation.syntax_errors + validation.semantic_errors
            result.validation_errors.extend(errors)
            
            print(f"      ✗ VALIDATION FAILED:")
            for err in errors[:3]:  # Show first 3 errors
                print(f"        - {err[:80]}...")
            
            if attempt < MAX_VALIDATION_ATTEMPTS:
                # ========== FEEDBACK LOOP: LLM Corrects ==========
                print(f"\n      → Sending errors to LLM for correction...")
                
                # Try to correct domain first
                correction_prompt = CORRECTION_PROMPT.format(
                    errors="\n".join(errors[:5]),
                    original_hddl=domain_content
                )
                
                try:
                    correction_response = llm.generate(
                        prompt=correction_prompt,
                        system_prompt="Fix the HDDL errors. Output ONLY corrected HDDL code."
                    )
                    result.llm_calls += 1
                    result.llm_tokens += correction_response.tokens_used.get("total_tokens", 0) if correction_response.tokens_used else 0
                    
                    domain_content = _clean_hddl_response(correction_response.content)
                    print(f"      ✓ Domain corrected by LLM")
                    
                    # Regenerate problem for corrected domain
                    problem_prompt = PROBLEM_GENERATION_PROMPT.format(
                        problem_description=problem["description"],
                        domain_content=domain_content,
                        problem_name=f"{problem['domain_name']}-p01",
                        domain_name=problem["domain_name"]
                    )
                    
                    problem_response = llm.generate(
                        prompt=problem_prompt,
                        system_prompt="You are an expert HDDL generator. Output ONLY valid HDDL code."
                    )
                    result.llm_calls += 1
                    result.llm_tokens += problem_response.tokens_used.get("total_tokens", 0) if problem_response.tokens_used else 0
                    
                    problem_content = _clean_hddl_response(problem_response.content)
                    print(f"      ✓ Problem regenerated for corrected domain")
                    
                except Exception as e:
                    print(f"      ✗ Correction failed: {e}")
    
    if not result.success:
        result.error = f"Validation failed after {MAX_VALIDATION_ATTEMPTS} attempts"
    
    result.generation_time_ms = (time.perf_counter() - start_time) * 1000
    return result


def _clean_hddl_response(content: str) -> str:
    """Clean LLM response to extract pure HDDL code"""
    content = content.strip()
    
    # Remove markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```hddl or ```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    
    return content.strip()


# ============================================================================
# PLANNING WITH LLM-GENERATED HDDL
# ============================================================================

@dataclass
class PlanningResult:
    """Result of planning with LLM-generated HDDL"""
    success: bool
    plan_actions: List[str] = field(default_factory=list)
    plan_length: int = 0
    planning_time_ms: float = 0.0
    nodes_expanded: int = 0
    error: Optional[str] = None


async def plan_with_generated_hddl(
    domain_file: str,
    problem_file: str,
    problem_id: str
) -> PlanningResult:
    """Run PANDA planning on LLM-generated HDDL"""
    from src.integrations.panda_wrapper import PANDAWrapper
    
    start_time = time.perf_counter()
    result = PlanningResult(success=False)
    
    print(f"\n  [Step 4] Running PANDA Planning on LLM-generated HDDL...")
    
    try:
        panda = PANDAWrapper(panda_root=PANDA_ROOT, results_dir=RESULTS_DIR)
        
        plan_result = panda.plan(
            domain_file=domain_file,
            problem_file=problem_file,
            output_name=f"llm_gen_{problem_id}"
        )
        
        result.planning_time_ms = (time.perf_counter() - start_time) * 1000
        
        if plan_result.success:
            result.success = True
            result.plan_actions = [
                f"{a['name']}({','.join(a['parameters'])})"
                for a in plan_result.actions
            ]
            result.plan_length = len(result.plan_actions)
            result.nodes_expanded = plan_result.nodes_expanded
            
            print(f"    ✓ Planning SUCCESS!")
            print(f"    Plan length: {result.plan_length}")
            print(f"    Nodes expanded: {result.nodes_expanded}")
            print(f"    Actions:")
            for i, action in enumerate(result.plan_actions, 1):
                print(f"      {i}. {action}")
        else:
            result.error = plan_result.error
            print(f"    ✗ Planning FAILED: {plan_result.error}")
            
    except Exception as e:
        result.error = str(e)
        result.planning_time_ms = (time.perf_counter() - start_time) * 1000
        print(f"    ✗ Planning ERROR: {e}")
    
    return result


# ============================================================================
# MAIN BENCHMARK
# ============================================================================

async def run_true_neuro_symbolic_benchmark():
    """
    Run the TRUE neuro-symbolic benchmark:
    LLM generates HDDL → PANDA validates → Feedback loop → Execute → Store
    """
    
    print("\n" + "=" * 80)
    print("  TRUE NEURO-SYMBOLIC BENCHMARK")
    print("  LLM Generates HDDL from Scratch - NO Hand-Coded Domains!")
    print("=" * 80)
    print(f"  LLM Provider: Groq")
    print(f"  Model: {LLM_MODEL}")
    print(f"  Problems: {len(PROBLEMS)}")
    print(f"  Max validation attempts: {MAX_VALIDATION_ATTEMPTS}")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    print("\n  100% REAL LLM CALLS - LLM GENERATES ALL HDDL FILES")
    print("=" * 80)
    
    # Create output directory for LLM-generated HDDL
    output_dir = Path(LLM_GENERATED_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  LLM-generated HDDL will be saved to: {output_dir}")
    
    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "llm_provider": "groq",
            "llm_model": LLM_MODEL,
            "total_problems": len(PROBLEMS),
            "max_validation_attempts": MAX_VALIDATION_ATTEMPTS,
            "output_directory": str(output_dir),
            "real_llm_calls": True,
            "hand_coded_domains": False  # KEY DIFFERENCE
        },
        "problem_results": [],
        "summary": {
            "total_problems": len(PROBLEMS),
            "hddl_generation_success": 0,
            "planning_success": 0,
            "total_llm_calls": 0,
            "total_tokens": 0,
            "total_validation_attempts": 0
        }
    }
    
    for i, problem in enumerate(PROBLEMS):
        print(f"\n\n{'#' * 80}")
        print(f"  PROBLEM {i+1}/{len(PROBLEMS)}: {problem['name']}")
        print(f"  ID: {problem['id']}")
        print(f"{'#' * 80}")
        print(f"\n  Description:\n{problem['description'][:200]}...")
        
        problem_result = {
            "problem_id": problem["id"],
            "problem_name": problem["name"],
            "hddl_generation": None,
            "planning": None,
            "overall_success": False
        }
        
        # ========== HDDL Generation with Validation Loop ==========
        gen_result = await generate_hddl_with_validation(problem, output_dir)
        
        problem_result["hddl_generation"] = {
            "success": gen_result.success,
            "domain_file": gen_result.domain_file,
            "problem_file": gen_result.problem_file,
            "validation_attempts": gen_result.validation_attempts,
            "validation_errors": gen_result.validation_errors[:5],  # First 5 errors
            "llm_calls": gen_result.llm_calls,
            "llm_tokens": gen_result.llm_tokens,
            "generation_time_ms": gen_result.generation_time_ms,
            "error": gen_result.error
        }
        
        results["summary"]["total_llm_calls"] += gen_result.llm_calls
        results["summary"]["total_tokens"] += gen_result.llm_tokens
        results["summary"]["total_validation_attempts"] += gen_result.validation_attempts
        
        if gen_result.success:
            results["summary"]["hddl_generation_success"] += 1
            
            # ========== Planning with LLM-Generated HDDL ==========
            plan_result = await plan_with_generated_hddl(
                gen_result.domain_file,
                gen_result.problem_file,
                problem["id"]
            )
            
            problem_result["planning"] = {
                "success": plan_result.success,
                "plan_actions": plan_result.plan_actions,
                "plan_length": plan_result.plan_length,
                "expected_length": problem.get("optimal_plan_length"),
                "is_optimal": plan_result.plan_length == problem.get("optimal_plan_length", 0),
                "planning_time_ms": plan_result.planning_time_ms,
                "nodes_expanded": plan_result.nodes_expanded,
                "error": plan_result.error
            }
            
            if plan_result.success:
                results["summary"]["planning_success"] += 1
                problem_result["overall_success"] = True
                
                # ========== Store Generated Domain ==========
                print(f"\n  [Step 5] Storing LLM-generated domain for future reuse...")
                print(f"    → Domain saved: {gen_result.domain_file}")
                print(f"    → Problem saved: {gen_result.problem_file}")
        else:
            problem_result["planning"] = {"success": False, "error": "HDDL generation failed"}
        
        results["problem_results"].append(problem_result)
        
        # Summary for this problem
        print(f"\n  {'─' * 60}")
        print(f"  PROBLEM SUMMARY: {problem['name']}")
        print(f"  {'─' * 60}")
        print(f"  HDDL Generation: {'✓ SUCCESS' if gen_result.success else '✗ FAILED'}")
        print(f"  Validation Attempts: {gen_result.validation_attempts}")
        print(f"  LLM Calls: {gen_result.llm_calls}")
        print(f"  Tokens Used: {gen_result.llm_tokens}")
        if gen_result.success and problem_result.get("planning", {}).get("success"):
            print(f"  Planning: ✓ SUCCESS")
            print(f"  Plan Length: {problem_result['planning']['plan_length']}")
        elif gen_result.success:
            print(f"  Planning: ✗ FAILED")
        print(f"  Overall: {'✓ SUCCESS' if problem_result['overall_success'] else '✗ FAILED'}")
    
    # ========== FINAL SUMMARY ==========
    print("\n\n" + "=" * 80)
    print("  TRUE NEURO-SYMBOLIC BENCHMARK - FINAL RESULTS")
    print("=" * 80)
    
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'HDDL GENERATION (LLM → PANDA Validation)':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Problems Attempted':<35} {len(PROBLEMS):>21} │")
    print(f"  │ {'HDDL Generation Success':<35} {results['summary']['hddl_generation_success']:>21} │")
    success_rate = results['summary']['hddl_generation_success'] / len(PROBLEMS) * 100
    print(f"  │ {'Success Rate':<35} {success_rate:>20.1f}% │")
    print(f"  │ {'Total Validation Attempts':<35} {results['summary']['total_validation_attempts']:>21} │")
    print(f"  └{'─' * 60}┘")
    
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'PLANNING (Using LLM-Generated HDDL)':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Problems with Valid HDDL':<35} {results['summary']['hddl_generation_success']:>21} │")
    print(f"  │ {'Planning Success':<35} {results['summary']['planning_success']:>21} │")
    if results['summary']['hddl_generation_success'] > 0:
        plan_rate = results['summary']['planning_success'] / results['summary']['hddl_generation_success'] * 100
        print(f"  │ {'Planning Success Rate':<35} {plan_rate:>20.1f}% │")
    print(f"  └{'─' * 60}┘")
    
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'LLM RESOURCE USAGE':^58} │")
    print(f"  ├{'─' * 60}┤")
    print(f"  │ {'Total LLM Calls':<35} {results['summary']['total_llm_calls']:>21} │")
    print(f"  │ {'Total Tokens Used':<35} {results['summary']['total_tokens']:>21} │")
    avg_tokens = results['summary']['total_tokens'] / results['summary']['total_llm_calls'] if results['summary']['total_llm_calls'] > 0 else 0
    print(f"  │ {'Avg Tokens per Call':<35} {avg_tokens:>20.1f} │")
    print(f"  └{'─' * 60}┘")
    
    print(f"\n  ┌{'─' * 60}┐")
    print(f"  │ {'LLM-GENERATED HDDL FILES':^58} │")
    print(f"  ├{'─' * 60}┤")
    for pr in results["problem_results"]:
        if pr["hddl_generation"]["success"]:
            print(f"  │ {pr['problem_id']:<20} ✓ Saved to llm-generated-hddl/ │")
        else:
            print(f"  │ {pr['problem_id']:<20} ✗ Generation failed{' '*14} │")
    print(f"  └{'─' * 60}┘")
    
    # Save results
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    with open(BENCHMARK_FILE, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n  Results saved to: {BENCHMARK_FILE}")
    print(f"  LLM-generated HDDL saved to: {output_dir}")
    print("=" * 80)
    print("\n  BENCHMARK COMPLETE - 100% REAL LLM CALLS, NO HAND-CODED DOMAINS")
    print("=" * 80)
    
    return results


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    asyncio.run(run_true_neuro_symbolic_benchmark())

