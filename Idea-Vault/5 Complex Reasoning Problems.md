Here is a finalized suite of 5 complex reasoning problems, designed to be a standardized benchmark. These problems are all *attemptable* by our Phase 1 system but are structured to explicitly test and highlight the performance gains of our more advanced multi-agent architectures (Phase 3 and 4B).

You can use this suite to generate the comparative KPI tables (Success Rate, Plan Quality, Time) that will form the core data-driven argument of your thesis.

---

## 5 Standardized Reasoning Problems for Phased Benchmarking

### 1. Incomplete Knowledge Graph Traversal

This problem tests the system's most basic ability to handle a "knowledge gap." It's a simple test for baseline LLM integration and will later highlight the efficiency of your (future) RAG/Memory agent.

| Category | Specialization/Decomposition | Core Problem |
| :--- | :--- | :--- |
| **Graph Traversal** | Knowledge Gap Resolution | Find the shortest path in a graph where a critical edge weight is unknown. |

**The Problem:**
Given a directed, weighted graph $G$. The goal is to find the shortest path from node **A** to node **D**. The path must pass through node **B**.

* `Edge(A, B)` weight = 4
* `Edge(B, C)` weight = **`UNKNOWN`**
* `Edge(C, D)` weight = 5
* `Edge(A, C)` weight = 15

The system is given a rule: "To find an `UNKNOWN` weight, you must call a research tool (LLM prompt) to query the knowledge base for `weight(B, C)`." The correct, hidden value is 8.

**Benchmark Purpose (How it Tests Each Phase):**
* **Phase 1 (CoT + HTN):** Will it identify the `UNKNOWN` gap? Will its single CoT call correctly *both* identify the gap *and* find the value `8`? It's likely to fail or hallucinate a value.
* **Phase 3 (3-Agent):** The `DecompositionAgent` must create a plan that explicitly includes a step to "find_unknown_weight(B, C)" *before* the `ExecutionAgent` (symbolic $A^*$ algorithm) can run. This tests modularity.
* **Phase 4B (5-Agent):** The `PlanningAgent` should identify this as a "knowledge gap" problem *before* decomposition. The plan will be more robust, and the `ContextAgent` will track the state ("weight_known = false").

---

### 2. Constrained Tower of Hanoi

This problem tests the system's ability to modify a known, complex algorithm based on a new, hard constraint. It is designed to fail in simple phases and be solved by your advanced strategic planner.

| Category | Recursive Planning/Constraint | Core Problem |
| :--- | :--- | :--- |
| **Tower of Hanoi** | Constraint Adherence | Solve the 3-peg, $N$-disk Tower of Hanoi, but with one peg marked as "fragile." |

**The Problem:**
Solve the standard 3-peg, 3-disk Tower of Hanoi (move 3 disks from **Peg A** to **Peg C**). However, there is one critical constraint:
* **The Fragile Peg:** The largest disk (disk 3) can **never** be placed on **Peg B**. All other disks (1 and 2) can use Peg B normally.

**Benchmark Purpose (How it Tests Each Phase):**
* **Phase 1 (CoT + HTN):** **Will almost certainly fail.** The LLM will generate the standard, optimal Hanoi algorithm, which involves moving disk 3 from A to C, but *only after* moving the (1,2) sub-tower from A to **B**. This violates the "fragile peg" constraint. **KPI: 0% Success.**
* **Phase 3 (3-Agent):** The `DecompositionAgent` *might* solve this if prompted perfectly, but it's trying to solve two problems at once: "solve hanoi" and "obey constraint." It will likely fail.
* **Phase 4B (5-Agent):** This is the key test for your `PlanningAgent`. Its job is to analyze constraints *before* decomposition. It should create a new meta-strategy:
    1.  The standard Hanoi plan is invalid.
    2.  A new plan must be formed: Move 2-disk sub-tower from A $\rightarrow$ B. Move disk 3 from A $\rightarrow$ C. Move 2-disk sub-tower from B $\rightarrow$ C.
    3.  This strategy is then passed to the `DecompositionAgent`. This cleanly separates strategic planning from task decomposition. **KPI: High Success.**

---

### 3. Probabilistic Graph Traversal

This problem tests the system's ability to handle uncertainty and make an optimal **trade-off decision**, moving beyond finding a "correct" plan to finding the *best* plan.

| Category | Graph Traversal/Observability | Core Problem |
| :--- | :--- | :--- |
| **Dynamic Graph** | Time/Risk Trade-off | Find the "best" path in a graph where edges have a probabilistic (risky) cost. |

**The Problem:**
Find the path from **Start** to **End** with the lowest *expected* total time.

* **Path 1 (Safe Route):** `Start` $\rightarrow$ `A` $\rightarrow$ `End`.
    * `Edge(A, End)` has a *guaranteed* time of **30 minutes**.
* **Path 2 (Risky Route):** `Start` $\rightarrow$ `B` $\rightarrow$ `End`.
    * `Edge(B, End)` has a **10-minute** base time, but a **50% probability** ($P_{risk}$) of a **+30 minute** penalty ($T_{pen}$).

The system *must* choose one path and cannot turn back.

**Benchmark Purpose (How it Tests Each Phase):**
* **Phase 1 (CoT + HTN):** Will fail to be optimal. It will see `10 minutes` and `30 minutes` and choose Path 2, ignoring the probability. It cannot perform the "expected value" calculation. **KPI: Low Plan Quality.**
* **Phase 3 (3-Agent):** Will also fail. The `DecompositionAgent` is not an analyst; it will just try to find *a* path.
* **Phase 4B (5-Agent):** The `PlanningAgent` can be prompted to perform a strategic analysis. It should calculate:
    1.  **Expected Time (Path 1):** 30 minutes.
    2.  **Expected Time (Path 2):** ($0.50 \times 10 \text{ min}$) + ($0.50 \times (10 + 30) \text{ min}$) = 5 + 20 = **25 minutes**.
    3.  The agent should conclude that Path 2 is strategically superior. This proves the value of an analytical planning-specific agent. **KPI: High Plan Quality.**

---

### 4. Hybrid Hanoi-Graph Puzzle

This problem tests **task specialization** and **hierarchical decomposition**. It forces the system to solve a problem composed of two completely different, interleaved task types.

| Category | Recursive Planning + Graph Traversal | Core Problem |
| :--- | :--- | :--- |
| **Hybrid Problem** | Task Decomposition & Specialization | A recursive problem (Hanoi) where each move is "gated" by a graph-search sub-problem. |

**The Problem:**
Solve the **2-disk**, 3-peg Tower of Hanoi (A to C). However, the rules are modified:
* **Peg Locking:** To move a disk *onto* a peg (A, B, or C), that peg must be "unlocked."
* **Unlocking Mechanism:** To unlock a peg, the system must solve a unique shortest-path problem on an "unlocking graph" associated with that peg (e.g., "To unlock Peg B, find path X $\rightarrow$ Y in graph `G_B`").
* A peg automatically re-locks after the move is complete.

**Benchmark Purpose (How it Tests Each Phase):**
* **Phase 1 (CoT + HTN):** **Total Failure.** The single LLM will be asked to generate one giant plan that interleaves recursion and $A^*$ pathfinding. It will get confused, lose context, and produce an invalid, non-working plan. **KPI: 0% Success.**
* **Phase 3 (3-Agent):** **Potential Success.** The `DecompositionAgent` can create a long, *linear* plan:
    1.  `unlock_peg_B` (solve graph `G_B`)
    2.  `move_disk_1_A_to_B`
    3.  `unlock_peg_C` (solve graph `G_C`)
    4.  `move_disk_2_A_to_C`
    5.  ...and so on.
    The `ExecutionAgent` (symbolic) can then execute this step-by-step. It works, but it's inefficiently planned. **KPI: Medium Success, High Time.**
* **Phase 4B (5-Agent):** **High Success.** The `PlanningAgent` identifies the two task domains. The `DecompositionAgent` (specialized in recursion) *only* solves the Hanoi part, producing a 3-step plan: `(1, A, B)`, `(2, A, C)`, `(1, B, C)`. The **Orchestrator** (the workflow logic) then iterates through this plan. For *each step*, it *first* calls the `ExecutionAgent` (specialized in graphs) to solve the "unlock" sub-problem, and *then* calls it again to perform the "move" action. This demonstrates true specialization and hierarchical control.

---

### 5. Generalized K-Peg Hanoi

This "final boss" problem tests **strategic synthesis** and **in-context learning**. It requires the system to *research and discover* a complex, non-trivial algorithm from scratch using only its LLM reasoning.

| Category | Generalization/Strategic Planning | Core Problem |
| :--- | :--- | :--- |
| **Generalized Hanoi** | Strategic Synthesis & Discovery | Solve the $N$-disk, $K$-peg problem (e.g., 5 disks, 4 pegs). |

**The Problem:**
Solve the generalized Tower of Hanoi with **5 disks** and **4 pegs** (A, B, C, D), moving the stack from A to D. The system is not told how.

(This requires the Frame-Stewart algorithm, which is a complex, optimized recursive solution. The formula is $M(N, K) = \min_{1 \le k \le N} \{ 2 \cdot M(N-k, K) + M(k, K-1) \}$).

**Benchmark Purpose (How it Tests Each Phase):**
* **Phase 1 & 3:** **Total Failure.** Neither the single LLM nor the `DecompositionAgent` can independently invent or correctly apply the Frame-Stewart algorithm. They will fail or produce a hideously sub-optimal plan. **KPI: 0% Success.**
* **Phase 4B (5-Agent):** **This is the only phase that has a chance.**
    1.  The `PlanningAgent` is tasked to "find the optimal algorithm for K-peg Hanoi."
    2.  It uses its LLM to "research" and *finds* the Frame-Stewart algorithm and its recursive formula.
    3.  It then tasks the `DecompositionAgent` to "apply the Frame-Stewart algorithm to solve for N=5, K=4."
    4.  The `DecompositionAgent` (now *given* the strategy) can successfully generate the complex, optimal recursive plan.
    This demonstrates the pinnacle of your architecture: **using one agent (`Planning`) for meta-strategic reasoning and discovery to *inform* another agent (`Decomposition`) on how to perform its specialized task.**
