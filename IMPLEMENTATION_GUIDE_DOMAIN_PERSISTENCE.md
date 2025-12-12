# IMPLEMENTATION GUIDE: Domain Persistence
**Exact Code to Add for Persistent Domain Learning**

---

## The Problem (in 10 seconds)

```
Generated HDDL → saved to /tmp/ → validated by PANDA → ✓ works!
                                                      ↓
                                                   Deleted on reboot
                                                      ↓
                                              Next problem: regenerate from scratch
```

**Should be**:
```
Generated HDDL → saved to /tmp/ → validated by PANDA → ✓ works!
                                                      ↓
                                           Copy to ./src/domains/{domain}/
                                                      ↓
                                              Persist forever
                                                      ↓
                                    Next problem: Load from disk, skip LLM
```

---

## PART 1: Persist Validated HDDL (2 lines of code)

**File**: `src/agents/decomposition_agent.py`  
**Location**: After line 545 (after PANDA validation succeeds)

### Current Code (lines 540-555)
```python
            if validation_result.is_valid:
                logger.info(f"[PANDA] HDDL validation passed")
                
                return {
                    "success": True,
                    "hddl_domain_file": domain_file,
                    "hddl_problem_file": problem_file,
                    "hddl_domain": hddl_domain,
                    "hddl_problem": hddl_problem,
                    "methods": methods_data.get("methods", []),
                    "validation_warnings": validation_result.warnings
                }
```

### What to Add

```python
            if validation_result.is_valid:
                logger.info(f"[PANDA] HDDL validation passed")
                
                # ========== NEW: PERSIST TO DOMAINS FOLDER ==========
                domain_dir = Path(f"./src/domains/{domain_name}")
                domain_dir.mkdir(parents=True, exist_ok=True)
                
                persistent_domain_file = domain_dir / "domain.hddl"
                persistent_problem_file = domain_dir / "problem.hddl"
                
                # Copy validated HDDL from /tmp to persistent storage
                import shutil
                shutil.copy(domain_file, persistent_domain_file)
                shutil.copy(problem_file, persistent_problem_file)
                
                logger.success(f"[PERSIST] Saved domain to {persistent_domain_file}")
                # ===================================================
                
                return {
                    "success": True,
                    "hddl_domain_file": str(persistent_domain_file),  # ← UPDATE PATH
                    "hddl_problem_file": str(persistent_problem_file),  # ← UPDATE PATH
                    "hddl_domain": hddl_domain,
                    "hddl_problem": hddl_problem,
                    "methods": methods_data.get("methods", []),
                    "validation_warnings": validation_result.warnings,
                    "persisted": True  # ← NEW FLAG
                }
```

### Full Updated Method (After Modification)

```python
async def _generate_and_validate_hddl(
    self,
    domain_name: str,
    methods_data: Dict,
    operators: List,
    initial_state,
    goal_tasks: List[Tuple[str, List[str]]],
    objects: Dict[str, str],
    attempt_number: int
) -> Dict:
    """
    Generate HDDL domain/problem files and validate with PANDA
    
    Args:
        domain_name: Domain name
        methods_data: Dict with "methods" from LLM
        operators: List of Operator objects
        initial_state: State object
        goal_tasks: List of (task_name, parameters)
        objects: Object declarations
        attempt_number: Current validation attempt
    
    Returns:
        {
            "success": bool,
            "hddl_domain_file": str,
            "hddl_problem_file": str,
            "validation_errors": [...],
            "persisted": bool,  ← NEW
            "error": str (if failed)
        }
    """
    try:
        # Convert LLM methods to MethodLibrary format
        from ..core.methods import MethodLibrary, Method
        
        method_library = MethodLibrary()
        
        for method_data in methods_data.get("methods", []):
            method = Method(
                name=method_data.get("name", "unknown_method"),
                task_name=method_data.get("task_name", "unknown_task"),
                parameters=method_data.get("parameters", {}),
                preconditions=method_data.get("preconditions", []),
                subtasks=method_data.get("subtasks", []),
                ordering=method_data.get("ordering", []),
                priority=method_data.get("priority", 1.0)
            )
            method_library.register(method)
        
        # Generate HDDL domain
        hddl_domain = self.hddl_generator.generate_domain(
            domain_name=domain_name,
            methods=method_library,
            operators=operators
        )
        
        # Generate HDDL problem
        hddl_problem = self.hddl_generator.generate_problem(
            problem_name=f"{domain_name}_problem_{attempt_number}",
            domain_name=domain_name,
            init_state=initial_state,
            goal_tasks=goal_tasks,
            objects=objects
        )
        
        # Save to temporary files for validation
        domain_file = f"/tmp/panda_{domain_name}_{attempt_number}.hddl"
        problem_file = f"/tmp/panda_{domain_name}_problem_{attempt_number}.hddl"
        
        self.hddl_generator.save_domain(hddl_domain, domain_file)
        self.hddl_generator.save_problem(hddl_problem, problem_file)
        
        # Validate with PANDA parser
        validation_result = await self.panda_wrapper.validate_hddl(
            domain_file=domain_file,
            problem_file=problem_file
        )
        
        self.stats["panda_validations"] += 1
        
        if validation_result.is_valid:
            logger.info(f"[PANDA] HDDL validation passed")
            
            # ========== NEW: PERSIST TO DOMAINS FOLDER ==========
            domain_dir = Path(f"./src/domains/{domain_name}")
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            persistent_domain_file = domain_dir / "domain.hddl"
            persistent_problem_file = domain_dir / "problem.hddl"
            
            # Copy validated HDDL from /tmp to persistent storage
            import shutil
            shutil.copy(domain_file, persistent_domain_file)
            shutil.copy(problem_file, persistent_problem_file)
            
            logger.success(f"[PERSIST] Saved domain to {persistent_domain_file}")
            # ===================================================
            
            return {
                "success": True,
                "hddl_domain_file": str(persistent_domain_file),
                "hddl_problem_file": str(persistent_problem_file),
                "hddl_domain": hddl_domain,
                "hddl_problem": hddl_problem,
                "methods": methods_data.get("methods", []),
                "validation_warnings": validation_result.warnings,
                "persisted": True
            }
        else:
            self.stats["panda_validation_failures"] += 1
            
            logger.warning(
                f"[PANDA] Validation failed: "
                f"{len(validation_result.syntax_errors)} syntax errors, "
                f"{len(validation_result.semantic_errors)} semantic errors"
            )
            
            return {
                "success": False,
                "validation_errors": validation_result.syntax_errors + validation_result.semantic_errors,
                "error": "PANDA validation failed",
                "persisted": False
            }
    
    except Exception as e:
        logger.error(f"[PANDA] HDDL generation/validation error: {e}")
        return {
            "success": False,
            "error": f"HDDL generation failed: {str(e)}",
            "persisted": False
        }
```

**Required imports at top of file**:
```python
from pathlib import Path
import shutil
```

---

## PART 2: Domain Lookup Before LLM (Optional but Recommended)

**File**: `src/agents/decomposition_agent.py`  
**Location**: At start of `_generate_and_validate_hddl()` method (before LLM call)

### Add This Check

```python
async def _generate_and_validate_hddl(...):
    """Generate HDDL domain/problem files and validate with PANDA"""
    
    # ========== NEW: CHECK IF DOMAIN ALREADY EXISTS ==========
    existing_domain_path = Path(f"./src/domains/{domain_name}/domain.hddl")
    existing_problem_path = Path(f"./src/domains/{domain_name}/problem.hddl")
    
    if existing_domain_path.exists() and existing_problem_path.exists():
        logger.success(f"[LOOKUP] Found existing domain at {existing_domain_path}")
        
        # Return existing domain without LLM call
        return {
            "success": True,
            "hddl_domain_file": str(existing_domain_path),
            "hddl_problem_file": str(existing_problem_path),
            "validation_warnings": [],
            "persisted": True,
            "from_cache": True  ← NEW FLAG
        }
    # ========================================================
    
    try:
        # ... rest of method (LLM generation, etc.)
```

**Impact**: Skips expensive LLM call if domain exists, saves 2-5 seconds per problem

---

## PART 3: Track Persistence in Workflow

**File**: `src/agents/workflows/panda_workflow.py`  
**Location**: Around line 260 (after decomposition phase)

### Current Code
```python
            decomposition_result = await self._phase2_decomposition_validation(
                domain_name=domain_name,
                domain_file=domain_file,
                problem_file=problem_file,
                planning_strategies=planning_result.get("strategies", [])
            )
            workflow_result["phases"]["decomposition"] = decomposition_result
```

### Add Logging (optional but useful)

```python
            decomposition_result = await self._phase2_decomposition_validation(
                domain_name=domain_name,
                domain_file=domain_file,
                problem_file=problem_file,
                planning_strategies=planning_result.get("strategies", [])
            )
            workflow_result["phases"]["decomposition"] = decomposition_result
            
            # ========== NEW: LOG PERSISTENCE ==========
            if decomposition_result.get("persisted"):
                logger.success(
                    f"[WORKFLOW] Domain persisted to "
                    f"{decomposition_result.get('hddl_domain_file')}"
                )
            if decomposition_result.get("from_cache"):
                logger.success(
                    f"[WORKFLOW] Domain loaded from cache "
                    f"(skipped LLM generation)"
                )
            # ========================================
```

---

## PART 4: Test It Works

Create test file: `test_domain_persistence.py`

```python
import asyncio
import sys
from pathlib import Path

sys.path.append(".")

from src.agents.decomposition_agent import DecompositionAgent
from src.core.state_manager import State

async def test_persistence():
    """Test that generated domains are persisted"""
    
    # Create agent
    decomp_agent = DecompositionAgent(
        name="test_decomposition",
        config={
            "max_retries": 2,
            "fallback_domains_path": "./src/domains"
        }
    )
    
    # Test data
    test_input = {
        "task": "find_path(A, D)",
        "domain": "test_graph_domain_v2",  # ← Use unique name
        "operators": [],
        "initial_state": State(),
        "goal_tasks": [("find_path", ["A", "D"])],
        "context": {}
    }
    
    print("\n" + "="*80)
    print("TEST 1: Generate and Persist Domain")
    print("="*80)
    
    result = await decomp_agent.process(test_input)
    
    if result["success"]:
        print(f"✓ Domain generation successful")
        
        # Check if file was persisted
        domain_path = Path(f"./src/domains/test_graph_domain_v2/domain.hddl")
        if domain_path.exists():
            print(f"✓ Domain persisted to {domain_path}")
            print(f"  File size: {domain_path.stat().st_size} bytes")
        else:
            print(f"✗ Domain NOT persisted to {domain_path}")
    else:
        print(f"✗ Domain generation failed: {result.get('error')}")
    
    print("\n" + "="*80)
    print("TEST 2: Load from Cache (No LLM Call)")
    print("="*80)
    
    # This should load from disk without calling LLM
    result2 = await decomp_agent.process(test_input)
    
    if result2.get("from_cache"):
        print(f"✓ Domain loaded from cache (skipped LLM!)")
    elif result2["success"]:
        print(f"? Domain processed (check logs for persistence)")
    else:
        print(f"✗ Failed: {result2.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_persistence())
```

**Run it**:
```bash
cd /path/to/neuro-symbolic-htn-planner
python test_domain_persistence.py
```

**Expected output**:
```
================================================================================
TEST 1: Generate and Persist Domain
================================================================================
✓ Domain generation successful
✓ Domain persisted to ./src/domains/test_graph_domain_v2/domain.hddl
  File size: 1247 bytes

================================================================================
TEST 2: Load from Cache (No LLM Call)
================================================================================
✓ Domain loaded from cache (skipped LLM!)
```

---

## Summary of Changes

| File | Lines | Change | Effort |
|------|-------|--------|--------|
| decomposition_agent.py | +15 | Persist after validation | 5 min |
| decomposition_agent.py | +10 | Lookup before LLM | 5 min |
| panda_workflow.py | +8 | Log persistence status | 3 min |
| test_domain_persistence.py | +50 | Test script | 10 min |
| **Total** | **~83** | **Domain learning** | **~25 min** |

---

## What This Achieves

### Before
```
Problem 1: graph_traversal/problem_01
├─ LLM: 3 seconds (generate methods)
├─ HDDL: 0.5 seconds (convert to HDDL)
├─ PANDA: 0.3 seconds (validate)
└─ Total: 3.8 seconds

Problem 2: graph_traversal/problem_02 (same domain!)
├─ LLM: 3 seconds (REGENERATE - wasted!)
├─ HDDL: 0.5 seconds (regenerate)
├─ PANDA: 0.3 seconds (revalidate)
└─ Total: 3.8 seconds (could be 0.1s!)
```

### After
```
Problem 1: graph_traversal/problem_01
├─ LLM: 3 seconds (generate methods)
├─ HDDL: 0.5 seconds (convert to HDDL)
├─ PANDA: 0.3 seconds (validate)
├─ Persist: 0.1 seconds (save to disk)
└─ Total: 3.9 seconds

Problem 2: graph_traversal/problem_02 (same domain!)
├─ Lookup: 0.01 seconds (check if exists)
├─ Load: 0.05 seconds (read from disk)
├─ Use: 0.1 seconds (PANDA uses existing domain)
└─ Total: 0.16 seconds (25x FASTER!)
```

---

## Verification Checklist

After implementation:

- [ ] Code compiles without errors
- [ ] Test script runs successfully
- [ ] Domain files appear in `./src/domains/{domain_name}/`
- [ ] Second run on same domain is faster
- [ ] Fallback to hand-coded still works
- [ ] Workflow results include "persisted" flag
- [ ] No data loss on reboot (files are permanent)
- [ ] PANDA still validates correctly

---

## Questions?

If implementation doesn't work:

1. Check imports: `from pathlib import Path`, `import shutil`
2. Ensure `./src/domains/` directory exists
3. Check file permissions (writable)
4. Look for errors in logs with `[PERSIST]` prefix
5. Verify `domain_name` parameter is valid filename

Good luck! 🎉

