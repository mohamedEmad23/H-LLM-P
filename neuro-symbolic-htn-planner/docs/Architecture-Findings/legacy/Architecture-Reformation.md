# Architectural Reformation: A Roadmap for Transitioning from Flat Planning to Neuro-Symbolic Hierarchical Task Networks

## 1. Executive Summary and Architectural Imperative

The transition from a non-hierarchical, "flat" planning architecture to a Neuro-Symbolic Hierarchical Task Network (HTN) represents a paradigm shift in automated reasoning that moves beyond simple state-space search into the realm of semantic task decomposition. The current system, characterized by the user as lacking a stack, recursion, and memory, suffers from inherent limitations associated with classical STRIPS-style planning. These flat planners operate by searching a state space for a sequence of atomic actions that transition an initial state to a goal state. While this approach is valid for simple logistics or puzzles like the Blocks World, theoretical analysis confirms that it fails to capture the _semantic structure_ and procedural complexities of real-world domains. It treats all actions as atomic peers, ignoring the procedural knowledge—the "standard operating procedures"—that human experts utilize to solve complex problems.

The proposed architectural reformation requires a rigorous integration of three advanced paradigms:

1. **Symbolic Core (SHOP2/TLPLAN Hybrid):** A forward-chaining HTN engine that maintains explicit world state history, enabling the use of temporal logic for search control.1
2. **Neural Cognition (LLM Integration):** Large Language Models (LLMs) function not as the planner itself, but as heuristic generators and decomposition engines, leveraging the Tree-of-Thoughts (ToT) methodology to explore the search space of task decompositions.
3. **Multi-Agent Orchestration:** A distributed system where specialized agents (Decomposers, Critics, Executors) collaborate to manage the interactions between symbolic rigor and neural creativity.

This report provides an exhaustive roadmap for architecting this system. It focuses on remediating the specific defects of the current flat system—specifically the implementation of the decomposition stack, the recursion engine, and state memory—while layering advanced neuro-symbolic capabilities on top. The analysis draws heavily upon the theoretical foundations of HTN complexity, the operational semantics of Ordered Task Decomposition (SHOP2), and the logic-based search control mechanisms of TLPLAN.

---

## 2. The Pathology of Flat Planning: Theoretical Constraints

To successfully architect the new system, it is imperative to understand the theoretical ceiling of the current "flat" implementation. The user's current system relies on finding a path through a state graph. However, complex problem solving is rarely about finding a path; it is about decomposing a high-level intent into executable steps.

### 2.1 The Expressivity Gap: Regularity vs. Context-Free Languages

Research into the complexity of planning algorithms demonstrates that HTN planning is strictly more expressive than operator-based (STRIPS) planning. A flat planner searches for a path in a graph of states, a process that is computationally equivalent to finding a string in a Regular Language. An HTN planner, conversely, performs a grammar parsing operation. It starts with a high-level task and recursively rewrites it into subtasks until primitive actions remain.

The theoretical literature confirms that mapping HTN problems to STRIPS problems is often impossible without an exponential explosion in the size of the domain description, or impossible altogether if the domain requires context-free constructs.1 The user's current inability to handle recursion is not merely a feature gap; it is a theoretical deficiency. Without recursion, the planner cannot represent domains where the depth of the solution depends on the input size in a non-linear way (e.g., the Towers of Hanoi or recursive assembly tasks).

Table 1 illustrates the complexity classes associated with different planning paradigms, highlighting why the move to HTN is mathematically necessary for complex problem solving.

|**Planning Paradigm**|**Structure**|**Complexity Class**|**Decidability**|**Key Limitation**|
|---|---|---|---|---|
|**Propositional STRIPS**|Flat State Space|PSPACE-complete|Decidable|Cannot represent recursive structures; limited to regular languages. 1|
|**Regular HTN**|Hierarchical (No recursion)|EXPSPACE-complete|Decidable|Equivalent to STRIPS but more compact; still lacks full expressive power. 1|
|**Total-Order HTN**|Ordered Decomposition|EXPSPACE-hard|Decidable (with restrictions)|Requires strict ordering constraints; powerful but computationally expensive. 1|
|**General HTN**|Recursive & Partial Order|Semi-Decidable|**Undecidable**|Can represent any computable function (Turing Complete); requires bounding to solve. 1|

The "Regularity" property mentioned in the research is crucial. A "Regular" HTN problem is one where each decomposition produces at most one compound subtask, allowing the hierarchy to be flattened into a linear sequence.1 The user's goal of a "Neuro-Symbolic HTN" implies a desire to move beyond Regularity into General HTN planning, which supports multiple compound subtasks and recursion. This shift renders the current "flat" architecture obsolete, as flat planners cannot natively process the Context-Free Grammars required to represent general HTN domains.

### 2.2 The Semantics of Task Decomposition

The fundamental flaw in the current system—described as a "flat planner" lacking a stack—is that it attempts to treat compound tasks as simple goals. In formal HTN semantics, a task is not a state to be achieved ($S_{goal}$), but an activity to be performed ($T_{activity}$). This distinction is subtle but profound.

In STRIPS planning, the objective is to reach a state where `On(A, B)` is true. Any sequence of actions that achieves this is valid. In HTN planning, the objective might be `BuildTower(A, B)`. If the user simply places A on B, the STRIPS goal is met. However, if the `BuildTower` method requires `Inspect(A)` and `Clean(B)` before stacking, the STRIPS plan is invalid because it failed to follow the standard operating procedure.1 The user's current system fails because it lacks the mechanism—specifically the **Decomposition Stack**—to enforce these procedural constraints.

### 2.3 The Necessity of Ordered Task Decomposition

The architectural model recommended for this restart is **Ordered Task Decomposition**, exemplified by the SHOP2 system.1 This choice is strategic for a Neuro-Symbolic system. In many HTN planners (partial-order HTN), tasks are unordered, and the "state" of the world is not fully known at intermediate steps of the planning process. The planner must reason about sets of possible worlds.

SHOP2, however, plans in the same order that tasks are executed (forward-chaining). This means that at every step of the decomposition process, the planner knows the **exact current state** of the world.1 This addresses the "missing memory" defect. By forcing the planner to commit to an execution order during planning, the system maintains a complete snapshot of the virtual world (the current state), which can then be fed to the LLM to ground its reasoning.

---

## 3. Architecting the Symbolic Core: Remediation of Defects

The foundation of the new system must be a robust symbolic HTN engine. This engine provides the "scaffolding" for the AI agents. This section details the data structures and algorithmic flow required to fix the "No Stack," "No Recursion," and "Missing Memory" defects.

### 3.1 Implementing the Decomposition Stack (The Recursion Engine)

The user's lack of a stack is the primary barrier to HTN functionality. In an HTN, the "Goal" is a **Task Network**—a list of tasks to be performed. The planner processes this network not as a queue of states, but as a stack of activities.

The Stack Architecture:

The planner must maintain a TaskStack. This is not merely a storage structure but the driver of the planning loop.

1. **Initialization:** The stack is populated with the initial high-level tasks from the problem description.

2. **The Planning Loop (SHOP2 Algorithm):**

    - Pop the first task $t$ from the `TaskStack`.   
    - **Case A (Primitive Task):** If $t$ is an operator (primitive action), the planner checks its preconditions against the current state memory. If valid, the effects are applied to the state, the action is recorded in the plan, and the loop continues.1
    - **Case B (Compound Task):** If $t$ is a compound task, the system must find a **Method** to decompose it. A Method maps the compound task $t$ to a sequence of subtasks $t_1, t_2,..., t_n$.
    - **Push Operations:** The subtasks $t_1...t_n$ are pushed onto the `TaskStack` at the _front_, preserving the execution order. This Last-In, First-Out (LIFO) mechanism for decomposition ensures that subtasks are processed before their siblings, enabling recursion.

Recursion Implementation:

Recursion occurs when a Method for Task $A$ includes Task $A$ (or a variation of it) in its subtask list. For example, a method for transport_all(packages) might decompose into [transport(p1), transport_all(rest_packages)]. Without a stack to hold these expanding nested references, the system cannot process this logic. The stack depth grows linearly with the number of recursive calls, allowing the system to handle problems of arbitrary size, constrained only by memory.

### 3.2 Implementing Memory: The Forward-Chaining State Database

The "missing memory" defect implies the current planner does not track how the world changes during the search. A Neuro-Symbolic planner requires a rigorous state management system, similar to the "Current State" maintained by SHOP2 and TLPLAN.1

World State Memory:

Following the SHOP2 model, the system must maintain a mutable state object. When a primitive operator is applied, the system must apply its Add and Delete lists to this state.

- **Architecture:** Use a structured database (similar to a STRIPS database or a relational DB) to hold literals (e.g., `on(A, B)`, `clear(C)`).

- **Function Values:** The state must support more than boolean predicates; it must track function values (e.g., `fuel(truck) = 45`, `distance(A, B) = 100`). This allows for metric planning, a capability highlighted in the SHOP2 analysis.1

- **Versioning:** To support backtracking (Tree-of-Thoughts), the memory must support _snapshots_ or _deltas_. When the planner explores a branch that fails, it must revert the memory to the state before that branch was taken.

Search History Memory (The Path):

To support the Multi-Agent critics and the LLM, the system must track not just the current state, but the sequence of states and tasks that led there. This enables the use of Temporal Logic for search control. As defined in the TLPLAN research, control formulas often depend on the history (e.g., "Never pick up a block if we just put it down").1 The memory module must store the trajectory $\langle w_0, w_1,... w_i \rangle$ where $w$ represents world states.

### 3.3 The Domain Description Language (DDL)

The architecture must standardize on a formal language for defining domain knowledge. Standard PDDL is insufficient for HTN. The system should adopt a structure compatible with **HDDL (Hierarchical Domain Definition Language)** or SHOP2's input format.

**Key Structures:**

- **Tasks:** Signatures of activities (e.g., `transport(package, destination)`).
    
- **Operators:** Primitive actions with Preconditions/Effects (e.g., `drive_truck`).
    
- **Methods:** The core of the HTN. A method consists of:
    - _Head:_ The task it decomposes.

    - _Preconditions:_ Logic to check if this method is applicable in the current state.

    - _Subtasks:_ The resulting list of lower-level tasks.

    - _Ordering Constraints:_ SHOP2 allows defining partial orders within a method, though it linearizes them for execution.1

---

## 4. Neuro-Symbolic Integration: The LLM and Tree-of-Thoughts

Once the symbolic core (Stack + Memory) is functional, the neural components are integrated to drive the decision-making process. Pure symbolic HTN planners rely on hand-coded heuristics to choose which method to apply when multiple are applicable. In this architecture, the LLM replaces these hand-coded heuristics, acting as a dynamic, learned heuristic function.

### 4.1 The LLM as the Heuristic Engine

In complex domains, a high-level task might have dozens of applicable methods. SHOP2 allows sorting these methods using programmed heuristics, such as `sort-by` clauses that order variable bindings by cost.1 We replace or augment this static sorting with dynamic LLM reasoning.

**Mechanism:**

1. The Symbolic Core identifies all valid methods for the current task $t$ based on precondition satisfaction.
    
2. The system prompts the LLM: "Given the current state and the task, which of these valid methods [List of Methods] is most likely to lead to an optimal solution?"
    
3. The LLM ranks the methods. The Symbolic Core pushes the subtasks of the highest-ranked method onto the stack.
    

Lifting and Variable Binding:

Standard HTN planners use unification to bind variables (e.g., matching ?truck to Truck1). LLMs are notoriously bad at strict logical unification. The architecture should employ a "Lifted" strategy:

1. **Symbolic Binding:** The Symbolic Core identifies all _possible_ variable bindings for a method based on the state database (e.g., find all trucks at location X).
    
2. **Neural Selection:** The list of valid bindings is passed to the LLM. The LLM selects the best binding based on semantic context (e.g., "Pick the truck that is refrigerated because the cargo is milk"). This prevents the LLM from hallucinating objects that don't exist while allowing it to use "common sense" optimization.
    

### 4.2 Tree-of-Thoughts (ToT) Decomposition

The Tree-of-Thoughts prompting strategy is isomorphic to HTN search. A "Thought" in ToT corresponds to a "Task Decomposition" in HTN.

**Architecture of the ToT Module:**

- **Node:** Represents a specific tuple of `(CurrentState, TaskStack)`.
    
- **Edge:** Represents the application of a specific Method or Operator.
    
- **Generator:** The LLM acts as the node generator. When faced with a compound task, the LLM generates $k$ potential decompositions (thoughts).
    
- **Evaluator:** Instead of just the LLM evaluating the thoughts, the architecture uses a **Hybrid Evaluator**:
    
    - _Symbolic Check:_ Is the decomposition valid according to the domain definition? (Prunes hallucinations).
        
    - _Neural Check:_ Does this decomposition semantically move towards the goal? (Heuristic evaluation).
        

Solving the Recursion Limit via ToT:

LLMs struggle with infinite recursion. The symbolic core must enforce a depth_limit in the ToT search. If a branch exceeds depth $N$ without reaching primitive actions, the ToT manager prunes that branch, forcing the LLM to explore alternative, shallower decompositions.

### 4.3 Context Relevance Filtering

To enable the LLM to function effectively, the "State Memory" must be serialized into a prompt. However, dumping a raw database of 5,000 literals (common in logistics problems) will overflow context windows or confuse the model.

Mechanism:

The architecture requires a filtering layer. Before prompting the LLM, the system identifies the objects referenced in the current task's arguments. It then queries the State Memory for literals strictly relevant to those objects (and their immediate neighbors/containers). This filtered state is passed to the LLM, ensuring focus and reducing hallucination.

---

## 5. Search Control and Pruning: The TLPLAN Logic Layer

A critical insight from the analysis of high-performance planners is that domain physics (operators) are insufficient; efficient planning requires **Search Control Knowledge**. The user's flat planner likely failed due to combinatorial explosion. To prevent this, we integrate the logic-based search control mechanisms found in TLPLAN.1

### 5.1 Temporal Logic as Control Knowledge

The system should implement a **Formula Evaluator** that runs alongside the planner. This evaluator checks constraints written in Linear Temporal Logic (LTL). Unlike standard state constraints that only look at the _now_, LTL allows the planner to reject plans based on the _future_ or _history_.

Why LTL?

LTL formulas allow the definition of "Safety" and "Liveness" constraints.1

- **Safety:** "Something bad never happens." (e.g., $\Box \neg \text{overloaded}(truck)$).
    
- **Liveness:** "Something good eventually happens." (e.g., $\Box (\text{loaded}(x) \rightarrow \Diamond \text{delivered}(x))$).
    

TLPLAN research demonstrates that using LTL for search control can transform intractable problems into polynomial-time problems by pruning vast swathes of the search space that are theoretically valid but practically useless (e.g., moving a package back and forth between trucks).1

### 5.2 The Progression Algorithm

Implementing LTL checking on infinite traces is computationally expensive. However, the architecture utilizes the **Progression Algorithm** described in the TLPLAN research 1 to check logical constraints incrementally.

**Algorithm Logic:**

1. Assign a control formula $\phi$ to the initial state $w_0$.
    
2. When an action transitions the state from $w_i$ to $w_{i+1}$, the system "progresses" the formula $\phi$ through $w_i$ to generate $\phi'$.
    
3. The progression function $Progress(\phi, w_i)$ simplifies the formula based on the facts true in $w_i$.
    
    - If $\phi'$ simplifies to `FALSE`, the action violates a constraint. The branch is **pruned immediately**.
        
    - If $\phi'$ simplifies to `TRUE`, the constraint is satisfied forever.
        
    - Otherwise, $\phi'$ becomes the constraint label for the next state $w_{i+1}$.
        

Boolean Simplification and Bounded Quantification:

The progression algorithm must implement boolean simplification (e.g., TRUE AND P becomes P) to prevent the formula from growing indefinitely. Furthermore, it must handle Bounded Quantification. Formulas like $\forall [x: \text{clear}(x)]...$ are expanded into conjunctions based on the objects currently satisfying clear(x) in the state database.1 This allows the logic to reason about specific objects in the world without needing a full theorem prover.

Integration with LLM:

When the LLM suggests a next step (a ToT branch), the Symbolic Core effectively "simulates" this step. The Formula Evaluator progresses the LTL constraints against this simulation. If a neural suggestion causes the LTL formula to progress to FALSE, the system rejects the LLM's output before committing to it. This acts as the "Neuro-Symbolic Guardrail," ensuring that the creative outputs of the LLM adhere to strict logical safety rules.

### 5.3 The GOAL Modality

To make search control effective, the logic must reference the goal. TLPLAN introduces a `GOAL` modality (e.g., `GOAL(on(A, B))`), which evaluates to true if the predicate holds in the goal state.1

This is critical for "Goal-Directed" control rules. For example:

- "Don't pick up block $x$ unless it needs to be moved."
    
- Logic: $\forall [x:\text{clear}(x)] (\text{ontable}(x) \land \neg \exists [y: \text{GOAL}(\text{on}(x, y))] \rightarrow \bigcirc (\neg \text{holding}(x)))$.
    
- This formula prevents the planner from idly picking up blocks that are already in valid positions, effectively pruning "stupid" branches that an LLM might otherwise explore.1
    

---

## 6. Multi-Agent System (MAS) Architecture

To operationalize this complex interaction, the architecture adopts a Multi-Agent pattern. This aligns with the requirement for Google ADK integration, implying a modular, service-oriented architecture where agents encapsulate distinct reasoning capabilities.

### 6.1 Agent Roles

**1. The Decomposition Agent (The Architect)**

- **Core Logic:** LLM (e.g., Gemini Pro / GPT-4).
    
- **Responsibility:** Holds the prompt templates and context window. It receives a `Compound Task` and the `Contextual State`.
    
- **Action:** It outputs a ranking of applicable Methods or a list of subtasks. It uses ToT to generate multiple potential decompositions for evaluation.
    

**2. The Critic Agent (The Skeptic)**

- **Core Logic:** TLPLAN Formula Evaluator + Standard Precondition Checker.
    
- **Responsibility:** Acts as the filter for the Decomposition Agent.
    
- **Action:** It receives the decomposition proposed by the Architect. It checks:
    
    - _Symbolic Validity:_ Are preconditions met?
        
    - _Logical Safety:_ Does it violate LTL temporal constraints? (Progression Algorithm).
        
    - _Semantic Soundness:_ (Optional) It can query a secondary LLM to critique the plan (e.g., "Is this a roundabout way to solve the problem?").
        
- **Feedback:** If the Critic rejects the plan, it provides specific feedback (e.g., "Method rejected because it violates safety constraint: Overloaded Truck").
    

**3. The Execution Agent (The Simulator)**

- **Core Logic:** STRIPS Database Manager.
    
- **Responsibility:** Maintains the "Ground Truth" of the simulation.
    
- **Action:** When the stack produces a Primitive Operator, this agent applies the specific Add/Delete effects to the database. It manages variables and function values and broadcasts state updates to the other agents.
    

### 6.2 Agent Orchestration Flow

1. **Executor** broadcasts the current state $S$ and the top task $T$ from the stack.
    
2. **Decomposer** (via ToT) proposes $k$ potential methods to address $T$.
    
3. **Critic** analyzes the $k$ methods.
    
    - It prunes Method B because it violates an LTL safety constraint (Progression $\rightarrow$ False).
        
    - It prunes Method C because symbolic preconditions aren't met.
        
4. **Critic** approves Method A as the highest-ranked valid option.
    
5. **Executor** updates the Stack (pushing subtasks of Method A) and updates the State (if any immediate effects apply).
    
6. The loop repeats until the stack is empty.
    

---

## 7. Advanced Temporal and Metric Reasoning

The user's query references "Google ADK" and "Multi-Agent" systems, which often implies operating in environments more complex than static blocks worlds—specifically environments with time and concurrency. The SHOP2 research provides a critical mechanism for handling this: **Multi-Timeline Preprocessing (MTP)**.1

### 7.1 Handling Durative Actions and Concurrency

Standard PDDL allows for durative actions (actions that take time). To handle this in a forward-chaining planner without checking every millisecond, the architecture should implement MTP.

**Mechanism:**

1. **Augmented State:** The state object must track `read-time` and `write-time` for every variable.
    
2. **Operator Translation:** Primitive operators are modified to include `?start` and `?duration` parameters.
    
3. **Conflict Detection:**
    
    - If Agent A writes to variable $X$ at time $t$ (duration $d$), the variable $X$ is locked until $t+d$.
        
    - If Agent B tries to read variable $X$ at time $t+\delta$ (where $\delta < d$), the precondition fails.
        
4. **Outcome:** This allows the planner to schedule concurrent actions (e.g., loading two trucks simultaneously) while respecting physical constraints (e.g., you can't load the same package into two trucks at once).
    

### 7.2 Metric Optimization

SHOP2 supports "Branch-and-Bound" optimization 1, which is essential for finding _good_ plans, not just _valid_ ones.

**Implementation:**

- **Cost Functions:** Assign costs to operators (e.g., `fuel_used`, `time_taken`).
    
- **Heuristic Search:** The LLM should be prompted to estimate the "Cost to Go" (heuristic distance to goal) for different decomposition branches.
    
- **Pruning:** The system maintains a `Best_Cost_Found` variable. If the current path cost + LLM_Estimate > `Best_Cost_Found`, the Critic Agent prunes the branch. This turns the planner into an **Anytime Algorithm**—it finds a solution quickly, then uses remaining time to search for better ones.
    

---

## 8. Implementation Roadmap: From Flat to Hierarchical

This section outlines the concrete engineering steps to restart the build, progressing from the defective flat system to the robust Neuro-Symbolic HTN.

### Phase 1: The Symbolic Foundation (Weeks 1-4)

- **Step 1.1: Data Structures.** Implement classes for `Task`, `Operator`, `Method`, and `State` (using a HashMap or optimized Set for literals).
    
- **Step 1.2: The Stack.** Create the `DecompositionStack` class.
    
- **Step 1.3: The SHOP2 Loop.** Implement the forward-chaining recursion engine. Ensure that the planner can decompose a simple task (e.g., `travel(a, b)`) into primitive actions `walk -> ride -> walk` using manually coded methods. This proves the stack and recursion are working.
    
- **Step 1.4: State Memory.** Implement the `apply_operator` function that modifies the state via Add/Delete lists. Verify that state changes persist correctly across the stack execution.
    

### Phase 2: Search Control and Logic (Weeks 5-8)

- **Step 2.1: LTL Parser.** Implement a parser for temporal logic formulas (Always, Next, Until, Goal).
    
- **Step 2.2: Formula Evaluator.** Build the evaluator that checks if a formula is true in a given state.1 Implement the generator for bounded quantifiers (iterating over objects in the state).
    
- **Step 2.3: Progression Engine.** Implement the algorithm to transform `Progress(Formula, State) -> Formula'`.
    
- **Step 2.4: Validation.** Test with safety constraints (e.g., "Always have cash >= 10"). Verify the planner backtracks immediately when a plan violates this.
    

### Phase 3: Neuro-Symbolic Integration (Weeks 9-12)

- **Step 3.1: State Serialization.** Write functions to convert `State` objects into clean natural language or JSON descriptions for the LLM. Implement the relevance filtering to reduce context size.
    
- **Step 3.2: LLM Interface.** Connect the decomposition logic to an LLM API. Replace the hard-coded method selection with an LLM call.
    
- **Step 3.3: Tree-of-Thoughts.** Modify the stack loop to support branching. When a task allows multiple methods, create nodes in a search tree. Use the LLM to generate and score these nodes.
    

### Phase 4: Multi-Agent Orchestration (Weeks 13+)

- **Step 4.1: Agent Encapsulation.** Refactor the code so the Decomposer, Critic, and Executor are distinct services communicating via a message bus.
    
- **Step 4.2: Feedback Loops.** Implement "Reflexion": If the Critic rejects a method, feed the error message back to the Decomposer to prompt a retry.
    
- **Step 4.3: Metric Optimization.** Implement the cost tracking and Branch-and-Bound logic.
    

---

## 9. Conclusion

The "defects" identified in the user's current system—flatness, lack of memory, and lack of recursion—are not merely implementation bugs but fundamental architectural gaps that prevent the solving of complex, hierarchical problems. By adopting the **Ordered Task Decomposition (SHOP2)** model, the system gains the necessary structure (Stack) and context (State Memory) for complex reasoning. By overlaying this with **Tree-of-Thoughts** driven by LLMs, the system gains heuristic power that exceeds traditional search. Finally, the integration of **TLPLAN's** temporal logic acts as the rigorous binding agent, ensuring that the neural system's creativity remains within the bounds of logical correctness. This layered architecture—Symbolic Core, Logic Safety Net, Neural Brain, and Multi-Agent Body—represents the state-of-the-art blueprint for a Neuro-Symbolic HTN planner.

### 9.1 Summary of Recommendations

|**Component**|**Current Defect**|**Recommended Solution**|**Source Authority**|
|---|---|---|---|
|**Core Engine**|Flat / No Stack|**SHOP2-style Ordered Task Decomposition** with explicit Stack to handle recursion and method expansion.|1|
|**State Memory**|Missing Memory|**Forward-Chaining State Database** (STRIPS-DB) maintaining full world state at every step; supports MTP for concurrency.|1|
|**Heuristics**|Missing / Hard-coded|**LLM-driven Tree-of-Thoughts** to rank methods and generate decompositions based on semantic understanding.||
|**Search Control**|Blind Search|**Linear Temporal Logic (LTL)** formulas handled by a Critic Agent using the Progression Algorithm to prune invalid branches.|1|
|**Architecture**|Monolithic|**Multi-Agent System** (Decomposer, Executor, Critic) enabling modular reasoning and feedback loops.||