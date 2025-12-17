# Agent Interaction Map & Data Flow
**Visual Guide to How Your 5 Agents Actually Work Together**

---

## COMPLETE DATA FLOW THROUGH SYSTEM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        USER INITIATES WORKFLOW                              │
│  problem_name="incomplete-graph-p01", domain_name="graph_traversal"        │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PANDAWorkflow.execute_workflow()                                           │
│  Location: src/agents/workflows/panda_workflow.py:99                       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
        ┌────────────┐  ┌──────────────┐  ┌───────────────┐
        │CACHE CHECK │  │SIMILARITY    │  │SETUP WORKFLOW │
        │problem_    │  │SEARCH        │  │RESULT DICT    │
        │cache.json  │  │find_similar()│  │               │
        └───┬────────┘  └──────┬───────┘  └───────────────┘
            │                   │
            │ Cache HIT?        │ Similar problems?
            │ YES ──────────────┼──→ Return cached    ✓ Exit early!
            │                   │    solution
            │ NO                │
            │                   ▼ YES (pass hints)
            │           Extract strategies
            │           Pass to planning agent
            │
            ▼ NO (continue)
            
┌──────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: STRATEGIC PLANNING                           │
│                                                                          │
│  INPUT: {                                                               │
│    "domain_name": "graph_traversal",                                   │
│    "goal_description": "Find path from A to D",                        │
│    "initial_state": State(...),                                        │
│    "strategy_hints": [...]  # ← from similarity search                │
│  }                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  PlanningAgent          │
                    │  (Groq Llama 70B)       │
                    │                         │
                    │  Generates strategies   │
                    │  for decomposition      │
                    └───────────┬─────────────┘
                                │
                OUTPUT: {       │
                  "success": true,
                  "strategies": [
                    {
                      "name": "Dijkstra's Strategy",
                      "approach": "Find shortest path...",
                      "advantages": [...],
                      "estimated_complexity": "medium"
                    },
                    ...
                  ],
                  "reasoning": "...",
                  "processing_time_ms": 1570.7,
                  "llm_used": "Groq Llama 70B"
                }

┌──────────────────────────────────────────────────────────────────────────┐
│                   PHASE 2: HDDL GENERATION & VALIDATION                 │
│                                                                          │
│  INPUT: {                                                               │
│    "domain_name": "graph_traversal",                                   │
│    "initial_state": State(...),                                        │
│    "goal_tasks": [("find-path", ["A", "D"])],                         │
│    "planning_strategies": [...] # ← from Phase 1                       │
│  }                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │DecompositionAgent    │
                    │ (HF Llama 70B)       │
                    │                      │
                    │ Step A:              │
                    │ Generate Methods     │
                    │ from strategy hints  │
                    └───────────┬──────────┘
                                │
                          METHOD LIBRARY
                                │
                    ┌───────────▼──────────┐
                    │ HDDLDomainGenerator  │
                    │                      │
                    │ Step B:              │
                    │ Convert Method →     │
                    │ HDDL syntax          │
                    └───────────┬──────────┘
                                │
                       HDDL FILES (temporary)
                                │
                    ┌───────────▼──────────┐
                    │  PANDAWrapper        │
                    │  .validate_hddl()    │
                    │                      │
                    │ Step C:              │
                    │ Check PANDA parser   │
                    │ (max 3 attempts)     │
                    └───────────┬──────────┘
                                │
                    If validation fails:
                    │   └─→ Try fallback hand-coded domain
                    │
                    If validation succeeds:
                    │   └─→ Continue to Phase 3
                    │
                OUTPUT: {
                  "success": true,
                  "hddl_domain_file": "./src/domains/graph_traversal/domain.hddl",
                  "hddl_problem_file": "./src/domains/graph_traversal/problem.hddl",
                  "used_fallback": true,  ← ⚠️ Using hand-coded, not LLM-gen
                  "validation_warnings": []
                }

┌──────────────────────────────────────────────────────────────────────────┐
│              PHASE 3: PANDA HTN PLANNING (External Symbolic)             │
│                                                                          │
│  INPUT: {                                                               │
│    "domain_file": "./src/domains/graph_traversal/domain.hddl",         │
│    "problem_file": "./src/domains/graph_traversal/problem.hddl"        │
│  }                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │  PANDAWrapper        │
                    │  .solve()            │
                    │                      │
                    │ Invokes PANDA        │
                    │ C++ binary:          │
                    │ - Parsing            │
                    │ - Grounding          │
                    │ - Planning (HTN)     │
                    │ - Plan conversion    │
                    └───────────┬──────────┘
                                │
                                ▼
                    Files generated:
                    - .parsed
                    - .sas
                    - .solution
                    
                OUTPUT: {
                  "success": true,
                  "plan_file": "tmp/panda/test_20251129_195643.solution",
                  "plan_length": 4,
                  "search_time_ms": 0.0,
                  "nodes_expanded": 5,
                  "actions": [
                    {"name": "traverse", "parameters": ["A", "C"]},
                    {"name": "traverse", "parameters": ["C", "D"]},
                    {"name": "complete-path", "parameters": ["D"]}
                  ]
                }

┌──────────────────────────────────────────────────────────────────────────┐
│              PHASE 4: PLAN EXECUTION (Simulated in Python)              │
│                                                                          │
│  INPUT: {                                                               │
│    "panda_plan": [PlannerResult(...)]                                   │
│    "initial_state": State(...),                                         │
│    "domain_name": "graph_traversal"                                     │
│  }                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │ ExecutionAgent       │
                    │ (70% Symbolic)       │
                    │                      │
                    │ For each action:     │
                    │ 1. Check precond.    │
                    │ 2. Apply effects     │
                    │ 3. Log transition    │
                    │ 4. Track trace       │
                    └───────────┬──────────┘
                                │
                OUTPUT: {
                  "success": true,
                  "execution_trace": [
                    {
                      "step": 1,
                      "action": "traverse",
                      "state_before": {...},
                      "state_after": {...}
                    },
                    ...
                  ],
                  "final_state": {...},
                  "execution_time_ms": 45.2
                }

┌──────────────────────────────────────────────────────────────────────────┐
│        PHASE 5: 4-LAYER VALIDATION (Symbolic + LLM Assessment)          │
│                                                                          │
│  INPUT: {                                                               │
│    "hddl_domain_file": "./src/domains/graph_traversal/domain.hddl",     │
│    "panda_plan": [...]                                                  │
│    "execution_trace": [...]                                             │
│    "final_state": {...}                                                 │
│    "goal_description": "Find path from A to D"                          │
│  }                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │VerificationAgent     │
                    │ (Gemini 2.0)         │
                    │                      │
                    │ Layer 1: Syntax      │
                    │ - Parentheses        │
                    │ - Structure          │
                    │                      │
                    │ Layer 2: Semantics   │
                    │ - PANDA parser       │
                    │ - Domain validity    │
                    │                      │
                    │ Layer 3: Correctness │
                    │ - Precond. checking  │
                    │ - Effects applied    │
                    │                      │
                    │ Layer 4: Goal Achiev.│
                    │ - Final state ⊨ goal│
                    │ - Plan optimality    │
                    └───────────┬──────────┘
                                │
                OUTPUT: {
                  "success": true,
                  "layer_1_syntax": {"valid": true},
                  "layer_2_semantic": {"valid": true},
                  "layer_3_correctness": {"valid": true},
                  "layer_4_goal": {"achieved": true},
                  "overall_valid": true
                }

┌──────────────────────────────────────────────────────────────────────────┐
│           PHASE 6: STORE RESULTS (Persistence & Learning)               │
│                                                                          │
│  INPUT: {                                                               │
│    "session_id": "test_20251129_195643",                               │
│    "domain_name": "graph_traversal",                                   │
│    "problem_name": "incomplete-graph-p01",                             │
│    "hddl_domain": HDDLDomain(...),                                     │
│    "panda_plan": [...],                                                │
│    "validation_result": {...}                                          │
│  }                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │ ContextAgent         │
                    │ (Gemini 2.0)         │
                    │                      │
                    │ Stores:              │
                    │ - Execution trace    │
                    │ - Session data       │
                    │ - Statistics         │
                    └───────────┬──────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
  ┌──────────────┐    ┌────────────────┐    ┌──────────────────┐
  │problem_cache │    │similarity_     │    │agent_interactions│
  │.json         │    │index/          │    │/*.json           │
  │              │    │                │    │                  │
  │Stores:       │    │Stores:         │    │Stores:           │
  │- Problem sig.│    │- Problem ID    │    │- All 6 phases    │
  │- Solution    │    │- Similar probs │    │- Full workflow   │
  │- Actions     │    │- Strategies    │    │- Statistics      │
  │- Time        │    │- Plan length   │    │- Timings         │
  └──────────────┘    └────────────────┘    └──────────────────┘

                                │
                        ┌───────▴────────┐
                        │                 │
                        ▼                 ▼
                    Result JSON    Return to Caller
                    (saved to disk)
```

---

## AGENT INTERACTION MATRIX

| Interaction | From | To | Mechanism | Data Passed | Used For |
|---|---|---|---|---|---|
| **1** | User | PANDAWorkflow | Function call | domain, problem, state | Entry point |
| **2** | PANDAWorkflow | ProblemCache | Direct call | domain, state, goal | Cache lookup |
| **3** | PANDAWorkflow | SimilaritySearch | Direct call | domain, goal, state | Strategy hints |
| **4** | PANDAWorkflow | PlanningAgent | Async call | goal, hints | Generate strategies |
| **5** | PlanningAgent | PANDAWorkflow | Return value | strategies list | Next phase input |
| **6** | PANDAWorkflow | DecompositionAgent | Async call | domain, goal, operators | Generate HDDL |
| **7** | DecompositionAgent | HDDLDomainGenerator | Direct call | Methods, Operators | HDDL syntax |
| **8** | HDDLDomainGenerator | PANDAWrapper | File write | HDDL text | PANDA validation |
| **9** | PANDAWrapper | DecompositionAgent | Return value | validation result | Success/fail |
| **10** | DecompositionAgent | PANDAWorkflow | Return value | HDDL file paths | Next phase input |
| **11** | PANDAWorkflow | PANDAWrapper | Direct call | domain_file, problem_file | HTN planning |
| **12** | PANDAWrapper | PANDA binary | Subprocess | Files via CLI | External planning |
| **13** | PANDA binary | PANDAWrapper | File output | .solution file | Plan extraction |
| **14** | PANDAWorkflow | ExecutionAgent | Async call | PANDA plan, initial state | Plan execution |
| **15** | ExecutionAgent | PANDAWorkflow | Return value | execution trace, final state | Validation input |
| **16** | PANDAWorkflow | VerificationAgent | Async call | plan, trace, goal | Validation |
| **17** | VerificationAgent | PANDAWorkflow | Return value | validation results | Storage input |
| **18** | PANDAWorkflow | ContextAgent | Async call | trace, domain, problem | Store results |
| **19** | ContextAgent | ProblemCache | Direct write | solution, timestamp | Store for reuse |
| **20** | ContextAgent | SimilaritySearch | Direct write | problem metadata | Update index |

---

## ACTUAL CODE FLOW (From panda_workflow.py)

```python
async def execute_workflow(self, ...):
    # CACHE CHECK
    if self.enable_cache:                          # Line ~160
        cached = self.problem_cache.check_cache(...)
        if cached:
            return cached_result  # ← EARLY EXIT!
    
    # SIMILARITY SEARCH
    if self.enable_similarity:                     # Line ~180
        similar_problems = self.similarity_search.find_similar(...)
        if similar_problems:
            strategy_hints = extract_strategies(...)
    
    # PHASE 1: PLANNING
    planning_result = await self._phase1_planning( # Line ~250
        ..., strategy_hints=strategy_hints
    )
    
    # PHASE 2: DECOMPOSITION
    decomposition_result = await self._phase2_decomposition_validation(
        ..., planning_strategies=planning_result.get("strategies", [])
    )
    
    # PHASE 3: PANDA
    panda_result = await self._phase3_panda_planning(
        domain_file=decomposition_result["hddl_domain_file"],
        problem_file=decomposition_result["hddl_problem_file"],
        ...
    )
    
    # PHASE 4: EXECUTION
    execution_result = await self._phase4_execution(
        panda_plan=panda_result["panda_plan"],
        initial_state=initial_state,
        ...
    )
    
    # PHASE 5: VERIFICATION
    validation_result = await self._phase5_validation(
        panda_plan=panda_result["panda_plan"],
        execution_trace=execution_result.get("execution_trace", []),
        ...
    )
    
    # PHASE 6: STORAGE
    storage_result = await self._phase6_store_results(
        decomposition_result=decomposition_result,
        panda_result=panda_result,
        validation_result=validation_result
    )
    
    # CACHE STORE (if successful)
    if workflow_result["success"] and self.enable_cache:  # Line ~360
        self.problem_cache.store_solution(...)
    
    # SIMILARITY INDEX UPDATE (if successful)
    if workflow_result["success"] and self.enable_similarity:  # Line ~380
        self.similarity_search.add_solved_problem(...)
    
    return workflow_result
```

---

## KEY INSIGHTS

### ✅ What Works Well

1. **Linear pipeline** is effective for this domain
2. **Memory systems are integrated** (cache + similarity)
3. **Data flows cleanly** between phases
4. **Fallback mechanisms** handle failures
5. **Results are fully logged** for analysis

### ❌ What's Missing

1. **Feedback loops**: No agent can influence earlier agents mid-workflow
2. **Conditional branching**: Always follows same sequence
3. **Parallel execution**: All agents are sequential
4. **Inter-agent negotiation**: No agent debates with another

### 🎯 When to Use Message Bus

You'd want message bus if:
- Agents need to **negotiate** (DecompositionAgent rejects PANDA plan)
- Agents need **bidirectional feedback** (Verification tells Planning it failed)
- Agents work in **parallel** (multiple strategies explored simultaneously)
- Agents need **async broadcasting** (context updates affect all agents)

Currently: **Not needed** - linear pipeline is simpler and works well.