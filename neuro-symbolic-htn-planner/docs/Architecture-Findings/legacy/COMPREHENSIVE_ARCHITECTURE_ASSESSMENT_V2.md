# BRUTAL HONEST ASSESSMENT: Current Architecture vs True HTN

**Date**: November 25, 2025  
**Assessment Type**: Comprehensive Architectural Analysis  
**Purpose**: Determine system's alignment with HTN principles for thesis methodology section

---

## EXECUTIVE SUMMARY: THE UNVARNISHED TRUTH

You have built a **sophisticated multi-agent LLM orchestration system with CoT reasoning**. You have NOT built an **HTN planner**. These are fundamentally different things.

**What you claim to have:**
- Neuro-Symbolic HTN Planner with Multi-Agent System
- Hierarchical Task Network decomposition
- Tree-of-Thoughts reasoning for method selection

**What you actually have:**
- Flat LLM planner with sequential task generation
- Chain-of-Thought (CoT) reasoning (NOT Tree-of-Thoughts)
- Multi-agent workflow for task execution
- No decomposition stack, no recursion engine, no method library lookup

**The Gap**: Your system generates a flat list of tasks from an LLM prompt. A true HTN planner recursively decomposes compound tasks using method libraries, maintains a task stack, and tracks state changes through primitive operator application. You do neither.

---

## PART 1: WHAT IS A TRUE HTN PLANNER?

Based on my analysis of the SHOP2 source code (`shop2.lisp`, `search.lisp`, `task-reductions.lisp`) and the academic papers, here are the **non-negotiable components** of an HTN planner:

### 1.1 The SHOP2 Core Algorithm (from `search.lisp`)

```lisp
;; The actual SHOP2 seek-plans function (simplified):
(defmethod seek-plans (domain state tasks top-tasks partial-plan ...)
  (cond
    ;; BASE CASE: No more tasks - we have a plan!
    ((null top-tasks)
     (seek-plans-null ...))
    
    ;; RECURSIVE CASE: Process next task
    (t
     (let ((task1 (choose-task top-tasks)))
       (seek-plans-task domain task1 state tasks ...)))))

(defmethod seek-plans-task (domain task1 state ...)
  ;; THIS IS THE KEY DISTINCTION
  (if (primitivep (get-task-name task1))
      ;; PRIMITIVE: Apply operator, update state
      (seek-plans-primitive domain task1 state ...)
      ;; COMPOUND: Find method, decompose, recurse
      (seek-plans-nonprimitive domain task1 state ...)))

(defmethod seek-plans-nonprimitive (domain task1 state ...)
  ;; Find applicable methods for this task
  (let ((methods (methods domain task-name)))
    (dolist (m methods)
      ;; Try each method
      (multiple-value-bind (result1 unifier1)
          (apply-method domain state task-body m ...)
        (when result1
          ;; RECURSIVELY decompose subtasks
          (seek-plans domain state tasks1 top-tasks1 ...))))))
```

### 1.2 The Five Pillars of True HTN Planning

| Pillar | Description | SHOP2 Implementation | Your System |
|--------|-------------|---------------------|-------------|
| **1. Task Stack** | LIFO structure holding tasks to decompose | `top-tasks`, `tasks` lists with recursive calls | ❌ None - flat task list |
| **2. Primitive/Compound Distinction** | Explicit type system for tasks | `primitivep` predicate, separate handlers | ❌ All tasks treated equally |
| **3. Method Library** | Pre-defined decomposition rules | `(methods domain task-name)` lookup | ❌ LLM generates on-the-fly |
| **4. Recursive Decomposition** | Methods produce subtasks that are recursively planned | `seek-plans` calls itself after `apply-method` | ❌ Single-shot LLM generation |
| **5. State Tracking** | Forward-chaining state updates | `apply-operator` modifies state, `tag-state` for backtracking | ⚠️ Partial - ExecutionAgent tracks but doesn't drive planning |

### 1.3 Critical SHOP2 Code You Must Understand

From `task-reductions.lisp` - **Method Application**:

```lisp
(defmethod apply-method ((domain domain) state task-body method ...)
  ;; 1. Unify method head with task
  (setq task-unifier (unify (second method) task-body))
  
  ;; 2. Check preconditions against current state
  (setq state-unifiers (find-satisfiers pre state ...))
  
  ;; 3. Return reduction (subtasks) with unifier
  (return-from apply-method 
    (values answers unifiers)))
```

From `task-reductions.lisp` - **Operator Application**:

```lisp
(defmethod apply-operator ((domain domain) state task-body operator ...)
  ;; 1. Check preconditions
  (setq pu (find-satisfiers pre state ...))
  
  ;; 2. Apply delete list
  (dolist (d dels-subbed)
    (delete-atom-from-state d state ...))
  
  ;; 3. Apply add list  
  (dolist (a adds-subbed)
    (add-atom-to-state a state ...))
  
  ;; Return applied operator with state tag for backtracking
  (values head-subbed statetag protections cost unifier))
```

---

## PART 2: YOUR CURRENT ARCHITECTURE DISSECTED

### 2.1 What DecompositionAgent Actually Does

From your `decomposition_agent.py`:

```python
async def process(self, input_data: Dict) -> Dict:
    # Build prompt (system + user)
    system_prompt, user_prompt = build_decomposition_prompt(
        task=task,
        domain=domain,
        operators=operators,
        constraints=constraints,
        memory_hints=memory_hints,
        domain_context=context.get("domain_context"),
    )
    
    # Single LLM call
    result = await self._generate_decomposition(system_prompt, user_prompt)
    
    # Parse response into methods
    parsed = parse_decomposition_response(response.content)
    methods = parsed.get("methods", [])
    
    return {"success": True, "methods": methods, ...}
```

**Critical Problems:**

1. **Single-shot generation**: One LLM call produces the entire "decomposition"
2. **No recursion**: Methods are not recursively processed
3. **No method library**: LLM invents decompositions from scratch each time
4. **No precondition checking**: Methods selected without state validation
5. **No unification**: No variable binding between task parameters and method heads

### 2.2 What Your Core Workflow Actually Does

From your `core_workflow.py`:

```python
async def process_task(self, task_input: Dict) -> Dict:
    # Stage 1: Decomposition (ONE LLM call)
    decomposition_result = await self.decomposition_agent.process({...})
    methods = decomposition_result["methods"]
    plan = methods[0]["subtasks"]  # Just take first method's subtasks
    
    # Stage 2: Execution (sequential, no recursive decomposition)
    execution_result = await self.execution_agent.process({
        "plan": plan,
        "initial_state": task_input["initial_state"],
        ...
    })
    
    # Stage 3: Verification
    verification_result = await self.verification_agent.process({...})
```

**Critical Problems:**

1. **Flat plan structure**: `plan` is a flat list of steps, not a hierarchical task network
2. **No compound task handling in execution**: Steps executed sequentially, not decomposed
3. **Single method selection**: Takes `methods[0]` without search or backtracking
4. **No state-driven method selection**: Decomposition doesn't check current state

### 2.3 What Your Core HTN Planner Actually Does

From your `src/core/htn_planner.py`:

```python
def _handle_compound_task(self, task, state, depth, max_depth):
    # Find applicable methods (this is correct!)
    applicable_methods = self.methods.get_applicable_methods(task.name, state)
    
    if not applicable_methods:
        # KNOWLEDGE GAP - but LLM integration is placeholder
        if self.use_llm:
            logger.info(f"🤖 Would query LLM here (Phase 2)")
            self.stats["llm_queries"] += 1
            return None  # ← DOES NOTHING!
        else:
            return None
    
    # Try each applicable method
    for method in applicable_methods:
        subtasks = method.get_subtasks()
        plan = self._plan_tasks(subtasks, state, depth + 1, max_depth)  # Recursive!
        if plan is not None:
            return plan
```

**The Irony**: Your `src/core/htn_planner.py` IS a true HTN planner structure! But:

1. It's **never used by your multi-agent system**
2. The LLM integration is a placeholder (`return None`)
3. Your agents bypass this entirely with their own flat LLM-based planning

---

## PART 3: THE THEORETICAL GAP

### 3.1 Computational Complexity Mismatch

From Erol et al. "Complexity Results for HTN Planning":

| Planning Type | Complexity | What It Can Express |
|---------------|------------|---------------------|
| Propositional STRIPS | PSPACE-complete | Regular languages (finite state machines) |
| Regular HTN | EXPSPACE-complete | Regular languages (more compact) |
| General HTN | **Undecidable** | Context-free languages, Turing-complete |
| Your System | PSPACE-complete (at best) | Regular languages only |

**The Problem**: Your LLM generates a flat sequence of actions. This is mathematically equivalent to STRIPS planning. You cannot represent:

- Recursive problems (Towers of Hanoi with arbitrary n)
- Context-sensitive decompositions
- Procedural constraints ("always do X before Y in method Z")

### 3.2 The Task vs Goal Distinction

From the SHOP2 paper:

> "The objective of an HTN planner is to produce a sequence of actions that perform some activity or task. The description of a planning domain includes a set of operators similar to those of classical planning, and also a set of methods, each of which is a prescription for how to decompose a task into subtasks."

**SHOP2**: Plans for **tasks** (activities to perform)
**Your System**: Plans for **goals** (states to achieve)

This is the fundamental conceptual error. When your LLM generates:
```
["partition_array", "sort_left", "sort_right"]
```

It's generating a sequence of goals/steps, NOT a hierarchical task decomposition. A true decomposition would be:

```
Task: sort_array(arr, 0, n)
  → Method: quicksort_decomposition
    → Subtask: partition(arr, 0, n) [COMPOUND]
      → Method: hoare_partition
        → Subtask: select_pivot(arr, 0, n) [PRIMITIVE]
        → Subtask: swap_loop(arr, 0, n) [COMPOUND]
          → Method: partition_sweep
            → Subtask: compare(arr[i], pivot) [PRIMITIVE]
            → Subtask: swap(arr, i, j) [PRIMITIVE]
            → Subtask: swap_loop(arr, i+1, n) [RECURSIVE]
    → Subtask: sort_array(arr, 0, p-1) [RECURSIVE COMPOUND]
    → Subtask: sort_array(arr, p+1, n) [RECURSIVE COMPOUND]
```

### 3.3 Tree-of-Thoughts vs Chain-of-Thought

From your Architecture-Reformation.md:

> "LLMs function... leveraging the Tree-of-Thoughts (ToT) methodology to explore the search space of task decompositions."

**What ToT requires:**
1. Generate multiple candidate decompositions (branches)
2. Evaluate each branch against heuristic/state
3. Expand best branches recursively
4. Backtrack when branches fail

**What you have (CoT):**
1. Generate one decomposition
2. Execute it
3. Check if it worked
4. Done

Your system has **no branching**, **no parallel exploration**, **no backtracking mechanism** in the decomposition phase.

---

## PART 4: COMPARISON WITH STATE-OF-THE-ART

### 4.1 HIPLAN (Recent Paper - Aug 2025)

HIPLAN is a hierarchical planning framework, but it's **also not true HTN**. However, it's more honest about what it is:

**HIPLAN's approach:**
- Uses "milestones" as high-level subgoals (similar to HTN methods)
- Generates step-wise hints for local adaptation
- Retrieves from a milestone library (similar to method library)
- Has explicit global/local distinction

**Key difference from your system:**
- HIPLAN acknowledges it's a **planning framework with LLM**, not an HTN planner
- Has structured retrieval from a pre-built library
- Maintains clear milestone transitions with state tracking

### 4.2 Fast and Accurate Task Planning (Neuro-Symbolic)

This paper provides a better model for what you should build:

```
Pipeline:
1. Planning formulation (PDDL encoding)
2. Subgoal generation (L-Model - LLM as world model)
3. Task planning per subgoal:
   - If MDL moderate: Use symbolic planner
   - If MDL large: Use MCTS + LLM as rollout policy
```

**Key insight**: They use LLM for **subgoal generation** (high-level) and **symbolic/MCTS planners** for actual planning. The LLM doesn't replace the planner; it augments it.

### 4.3 A Roadmap to Guide the Integration of LLMs in HP

This paper provides the taxonomy you need:

| LLM Role | Description | Your System |
|----------|-------------|-------------|
| **Problem Definition** | Generate/translate planning elements | ✓ Context Agent |
| **Plan Elaboration - LLM Planner** | LLM functions as the planner | ❌ This is what you have (anti-pattern) |
| **Plan Elaboration - Graph Search** | LLM embedded in search algorithm | ❌ Not implemented |
| **Plan Elaboration - Planning Guidance** | LLM provides heuristics/preferences | ❌ Planning Agent exists but doesn't guide search |
| **Post-Processing** | Translate/explain plan | ⚠️ Partial |

**Their verdict on LLM Planner approach:**
> "3% correct plans, and none with a correct hierarchical decomposition"

This is the approach you've implemented. It doesn't work for true hierarchical planning.

---

## PART 5: YOUR OPTIONS

### Option A: Full HTN Implementation (3-4 weeks)

**What you would build:**

```python
class TrueHTNPlanner:
    def __init__(self):
        self.method_library: Dict[str, List[HTNMethod]] = {}
        self.operator_library: Dict[str, Operator] = {}
        self.state: State = State()
        self.task_stack: List[Task] = []
    
    def plan(self, initial_task: Task, initial_state: State) -> Plan:
        self.state = initial_state.copy()
        self.task_stack = [initial_task]
        plan = []
        
        while self.task_stack:
            task = self.task_stack.pop(0)  # FIFO for ordered task decomposition
            
            if task.is_primitive():
                # Apply operator
                operator = self.operator_library[task.name]
                if operator.preconditions_met(self.state):
                    self.state = operator.apply(self.state, task.parameters)
                    plan.append(task)
                else:
                    return self.backtrack()  # Backtracking on failure
            else:
                # Compound task - find applicable method
                methods = self.get_applicable_methods(task)
                
                if not methods:
                    # LLM INTEGRATION POINT: Generate method
                    method = self.llm_generate_method(task, self.state)
                    if method:
                        methods = [method]
                    else:
                        return self.backtrack()
                
                # Push subtasks to front of stack (SHOP2 style)
                chosen_method = self.select_method(methods)  # Can use LLM for ranking
                subtasks = chosen_method.instantiate(task.parameters, self.state)
                self.task_stack = subtasks + self.task_stack  # Prepend!
        
        return Plan(actions=plan, final_state=self.state)
```

**Required components:**
1. Task class with `is_primitive()` method
2. Operator class with `preconditions_met()` and `apply()`
3. Method class with `preconditions`, `subtasks`, `instantiate()`
4. State class with add/delete operations
5. Backtracking mechanism (state snapshots)
6. LLM integration for:
   - Method generation when library is empty
   - Method ranking when multiple apply
   - Heuristic evaluation

**Effort**: 3-4 weeks of focused work

### Option B: Honest Reframing (1 week)

Keep your current system but be honest about what it is:

**New framing:**
- "LLM-Based Task Planning with Multi-Agent Orchestration"
- "Neuro-Symbolic Planning Architecture with Hierarchical Decomposition Capabilities"
- NOT "HTN Planner"

**Thesis narrative:**
> "We explore the integration of LLMs into planning systems, comparing purely symbolic HTN approaches (Phase 1 baseline) with LLM-augmented multi-agent systems (Phases 3-4). While our multi-agent system does not implement full HTN decomposition, it demonstrates practical approaches to task planning that leverage LLM capabilities for flexible problem-solving."

**Deliverables:**
1. Rename components honestly
2. Document the architectural differences
3. Position as comparative study, not HTN implementation
4. Emphasize the multi-agent orchestration contribution

### Option C: Hybrid Minimal HTN (2 weeks)

Implement the **minimum viable HTN** to make the claim technically valid:

**What you need:**
1. Add `CompoundTask` and `PrimitiveTask` types to your task schema
2. Modify DecompositionAgent to return **hierarchical** structures
3. Add recursive processing in the workflow
4. Implement state tracking during decomposition
5. Show at least one problem (Hanoi, sorting) with true recursive decomposition

**Implementation:**

```python
# In decomposition_agent.py
async def process(self, input_data: Dict) -> Dict:
    task = input_data["task"]
    state = input_data.get("state", {})
    
    # Check if primitive
    if self.is_primitive_task(task):
        return {"type": "primitive", "task": task, "success": True}
    
    # Compound task - decompose
    decomposition = await self._decompose_task(task, state)
    
    # RECURSIVELY process subtasks
    processed_subtasks = []
    for subtask in decomposition["subtasks"]:
        result = await self.process({
            "task": subtask,
            "domain": input_data["domain"],
            "state": state,  # Would need state updates here
            "operators": input_data.get("operators", {})
        })
        processed_subtasks.append(result)
    
    return {
        "type": "compound",
        "task": task,
        "method": decomposition["method"],
        "subtasks": processed_subtasks,
        "success": all(s["success"] for s in processed_subtasks)
    }
```

---

## PART 6: RECOMMENDATIONS FOR THESIS

### 6.1 Immediate Actions

1. **Stop calling it an HTN planner** in documentation until it actually is one
2. **Read the SHOP2 source code** thoroughly - it's well-commented Lisp
3. **Decide between Options A, B, or C** based on your timeline

### 6.2 For Methodology Section

**If you go with Option B (Honest Reframing):**

Write your methodology as:

> **Section 4: System Architecture**
> 
> Our system implements a multi-agent planning architecture inspired by HTN principles but adapted for LLM integration. Unlike classical HTN planners (SHOP2, UMCP) which perform recursive task decomposition through method libraries, our approach leverages LLMs for flexible task breakdown.
> 
> **4.1 Distinction from Classical HTN**
> 
> Classical HTN planners operate through:
> 1. Explicit task stack with LIFO processing
> 2. Pre-defined method libraries with preconditions
> 3. Forward-chaining state updates
> 4. Backtracking on method failure
> 
> Our system differs by:
> 1. Using LLM-generated decompositions (on-the-fly method generation)
> 2. Single-level decomposition with execution validation
> 3. Multi-agent collaboration for planning validation
> 
> **4.2 Rationale for Design Choices**
> 
> We chose this architecture because:
> 1. LLMs can handle novel domains without pre-defined method libraries
> 2. Multi-agent validation provides robustness without full backtracking
> 3. Real-world problems often don't have perfect HTN domain models

### 6.3 Questions to Ask Your Professor

Before proceeding, clarify:

1. "Is recursive HTN decomposition (as in SHOP2) a hard requirement, or is a hierarchical multi-agent planning approach acceptable?"

2. "Do you expect a method library with explicit preconditions, or is LLM-based method generation acceptable?"

3. "Should I compare against a true HTN planner (SHOP2, Panda), or is comparison against LLM baselines (ReAct, Reflexion) sufficient?"

---

## PART 7: THE BOTTOM LINE

### What You Have

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR CURRENT SYSTEM                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   User Task ──► Decomposition Agent ──► Flat Task List  │
│                     (LLM Call)                          │
│                         │                               │
│                         ▼                               │
│   Flat Task List ──► Execution Agent ──► Results        │
│                     (Sequential)                        │
│                         │                               │
│                         ▼                               │
│   Results ──► Verification Agent ──► Final Output       │
│                                                         │
│   No recursion. No stack. No method library.            │
│   No state-driven decomposition.                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### What You Claimed

```
┌─────────────────────────────────────────────────────────┐
│                    HTN PLANNER (SHOP2 STYLE)            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Task Stack: [T1(compound)]                            │
│        │                                                │
│        ▼                                                │
│   Pop T1 ──► Find Methods ──► Select M1                 │
│                                   │                     │
│                                   ▼                     │
│   Push Subtasks: [T1.1, T1.2, T1.3]                     │
│        │                                                │
│        ▼                                                │
│   Pop T1.1 (primitive) ──► Apply Operator ──► State'    │
│        │                                                │
│        ▼                                                │
│   Pop T1.2 (compound) ──► Find Methods ──► Recurse...   │
│        │                                                │
│        ▼                                                │
│   [Continue until stack empty]                          │
│                                                         │
│   Recursion. Stack. Method library.                     │
│   State-driven decomposition with backtracking.         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### The Gap

| Feature | Required for HTN | Your System |
|---------|------------------|-------------|
| Task Stack (LIFO) | ✓ Required | ❌ Missing |
| Recursive Decomposition | ✓ Required | ❌ Missing |
| Method Library | ✓ Required | ❌ LLM generates on-the-fly |
| Precondition Checking | ✓ Required | ⚠️ Partial (in execution only) |
| State Updates in Planning | ✓ Required | ❌ Missing |
| Backtracking | ✓ Required | ❌ Missing |
| Primitive/Compound Types | ✓ Required | ❌ All tasks equal |
| Unification/Variable Binding | ✓ Required | ❌ Missing |

**Your system is 2/8 on HTN requirements, with partial credit.**

---

## APPENDIX: SHOP2 Code Analysis Summary

### Key Files and Their Functions

| File | Purpose | Critical Functions |
|------|---------|-------------------|
| `shop2.lisp` | Entry point, find-plans | `find-plans`, `find-plans-1` |
| `search.lisp` | Core planning loop | `seek-plans`, `seek-plans-task`, `seek-plans-primitive`, `seek-plans-nonprimitive` |
| `task-reductions.lisp` | Method/operator application | `apply-method`, `apply-operator`, `get-top-tasks`, `replace-task-main-list` |
| `protections.lisp` | State protection handling | `add-protection`, `delete-protection` |

### The Core Loop (Pseudocode)

```
FUNCTION seek-plans(state, tasks, partial-plan):
    IF no tasks remaining:
        RETURN partial-plan as solution
    
    task = first task from tasks
    
    IF task is primitive:
        operator = lookup operator for task
        IF operator preconditions satisfied in state:
            new_state = apply operator effects
            new_plan = partial-plan + operator
            RETURN seek-plans(new_state, remaining tasks, new_plan)
        ELSE:
            RETURN FAILURE (trigger backtracking)
    
    ELSE (task is compound):
        methods = lookup methods for task
        FOR each method in methods:
            IF method preconditions satisfied in state:
                subtasks = instantiate method with task parameters
                new_tasks = subtasks + remaining tasks
                result = seek-plans(state, new_tasks, partial-plan)
                IF result is not FAILURE:
                    RETURN result
        RETURN FAILURE (all methods failed)
```

This is what you need to implement. Your current system does not do this.

---

**END OF ASSESSMENT**

*This document should inform your thesis methodology and clarify the path forward.*
