# A Memory-Augmented Cognitive Architecture for Multi-Agent Hierarchical Task Planning

## Executive Summary

This report presents a finalized architectural blueprint for a memory-augmented multi-agent system designed to enhance the complex reasoning capabilities of a Hierarchical Task Network (HTN) planner. The proposed architecture addresses the limitations of stateless planning by introducing a robust, persistent, and shared memory layer, enabling sophisticated coordination, dynamic state tracking, and strategic adaptation among a team of specialized agents. The system is specifically tailored to solve a graduated series of complex reasoning problems, ranging from multi-agent graph traversal to generalized N-peg Tower of Hanoi variants, providing a comprehensive solution for advanced thesis research in artificial intelligence.

The core of the proposed system is a hybrid cognitive architecture that integrates the Orchestrator-Worker pattern for centralized coordination with a dedicated Memory Management System (MMS). The Orchestrating Agent serves as the central cognitive executive, responsible for high-level goal decomposition, HTN planning, and task delegation. The MMS, implemented using the SQL-native, agent-centric memory engine Gibson AI's Memori, acts as the system's "second brain." It provides a structured, queryable, and persistent world model that all agents access. This architecture is further enhanced by adopting the "clue generation" paradigm from the MemoRAG framework, enabling the Orchestrator to formulate precise, context-aware queries to the MMS for effective precondition checking and strategic decision-making.

A comparative analysis of leading RAG and memory frameworks—MemoRAG, RAGFlow, Gibson AI's Memori, and AutoRAG—justifies the selection of Memori as the foundational memory component due to its structured data models and explicit support for multi-agent systems. RAGFlow, while powerful, is deemed unsuitable for this symbolic reasoning domain due to its document-centric design and significant infrastructure overhead. AutoRAG is identified as a critical tool for the implementation and optimization phase, ensuring empirical validation of the system's retrieval components.

The report validates this architecture by systematically demonstrating its efficacy in solving five benchmark reasoning problems. Each problem highlights a different facet of the system's capabilities: managing agent specialization through rule-based memory, tracking dynamic state for constraint adherence, handling observability and belief-state updates, enabling precise inter-agent coordination via a shared world state, and facilitating meta-level strategic planning.

Finally, a detailed implementation roadmap is provided, recommending a technology stack that includes the Memori SDK, a PostgreSQL backend, and an agent framework such as AutoGen or CrewAI. This document serves as a complete, implementation-ready guide, offering a theoretically sound and practically validated foundation for constructing an advanced multi-agent HTN system capable of sophisticated, memory-driven reasoning.

---

## Section 1: Architectural Foundations for a Coordinated Multi-Agent System

### 1.1 The Orchestrator-Worker Model in HTN Planning

The proposed enhancement to the existing five-agent system pivots on the introduction of two new central agents, an architecture that aligns with established patterns in multi-agent system design. Specifically, this structure is an implementation of the **Orchestrator Pattern**, also referred to as the supervisor or centralized model.1 In this paradigm, a single, authoritative agent—the Orchestrator—acts as the central coordinator, analogous to a conductor leading an orchestra. This central agent is responsible for receiving high-level goals, decomposing them into manageable sub-tasks, allocating these tasks to a pool of specialized "worker" agents, monitoring their progress, and synthesizing the final results.1

For the domain of Hierarchical Task Network (HTN) planning, this model is particularly apt. The core mechanism of HTN planning is **hierarchical decomposition**, a cognitive design pattern where abstract goals are recursively broken down into more concrete actions until a sequence of primitive, executable tasks is formed.2 The Orchestrator pattern provides a natural locus for this planning process. The Orchestrating Agent becomes the system's central cognitive executive, managing the primary task network and its decomposition. This centralized approach offers significant advantages within a research context, primarily ensuring predictability, debuggability, and clear accountability. Every action taken by a worker agent can be traced back to a specific decision made by the Orchestrator, simplifying analysis and validation.1

While centralized systems can introduce a performance bottleneck or a single point of failure, these trade-offs are acceptable and often desirable for a system of this scale (seven agents in total). The coordination overhead remains manageable, and the benefits of a clear, deterministic control flow outweigh the risks of decentralized complexity, where emergent behaviors can be difficult to predict or debug.1 The Orchestrator-Worker model thus provides a theoretically sound and pragmatically robust foundation for building a coordinated multi-agent HTN system.

### 1.2 Defining the Roles: The Orchestrating Agent and the Memory Management System

To implement the Orchestrator-Worker model effectively, the roles of the new components must be precisely defined. The initial proposal of an "Orchestrating Agent" and a "Memory Agent" is a solid starting point, but a more robust and scalable design emerges from refining the concept of the memory component.

#### Orchestrating Agent

The **Orchestrating Agent** is the central planner and coordinator of the entire system. Its responsibilities are threefold:

1. **Goal Management:** It receives high-level goals from the user or environment (e.g., "solve the Tower of Hanoi with N disks").

2. **HTN Planning:** It maintains and processes the main HTN task network. It performs the recursive task decomposition, selecting appropriate methods based on the current world state.4 A critical function is its interaction with the memory system to verify preconditions before applying a decomposition method.

3. **Task Delegation:** Once a task is decomposed into a primitive, executable action (an "operator" in HTN terminology), the Orchestrator delegates this action to the appropriate specialized Worker Agent (e.g., dispatching a task to move a large disk to Agent X). It then awaits a report of success or failure from the worker before proceeding with the plan.


#### Memory Management System (MMS)

The concept of a single "Memory Agent" is an under-specification for the critical role memory plays in this architecture. A more accurate and powerful conceptualization is a dedicated **Memory Management System (MMS)**. This reframing elevates memory from a single agent's responsibility to a foundational architectural layer. The MMS is not a monolithic agent but rather a complete system responsible for the persistence, retrieval, integrity, and management of the shared world state. This approach is informed by the principles of memory engineering for multi-agent systems, which advocate for dedicated persistence architectures, retrieval intelligence, and performance optimization layers.6

This design choice is further supported by the architecture of advanced memory tools like Gibson AI's Memori, which internally uses a multi-agent system (comprising Memory, Conscious, and Retrieval agents) to manage different facets of memory processing.7 By architecting the MMS as a distinct system with a well-defined API, its internal complexity can be encapsulated. The Orchestrator and Worker Agents interact with a simple interface (e.g., `update_state`, `query_state`), oblivious to the sophisticated mechanisms operating within the MMS. This modular design is more scalable, maintainable, and aligns with best practices in software architecture. The MMS becomes the sole gateway to the system's collective memory, ensuring consistency and control.

### 1.3 Principles of Shared Memory in Multi-Agent HTN Systems

For any multi-agent system to achieve coherent, coordinated action, a shared, persistent memory is not an optional feature but an absolute prerequisite. This shared memory acts as the connective tissue that binds the individual agents into a functional whole. In the context of military simulations and squad-based AI, this is often referred to as a "common squad-level knowledge base," which is essential for the planner to make informed, collaborative decisions.9 For the proposed HTN system, the MMS serves this exact purpose, fulfilling several critical functions.

First and foremost, the MMS is responsible for **maintaining a world model**. An HTN planner operates by evaluating the current state of the world to determine which decomposition methods are applicable.4 Without a reliable and up-to-date representation of the world—such as the current positions of disks on pegs or the properties of edges in a graph—the planner cannot function. The MMS serves as this canonical source of truth for the world state.

Second, the MMS enables **state synchronization**. In tasks requiring close coordination, such as the Level 4 Multi-Agent Stack Transfer problem, it is imperative that all agents operate on the same understanding of the world. If Agent Y moves a small disk to clear a large one for Agent X, this change in state must be reflected in a central repository before Agent X attempts its move. The MMS prevents agents from acting on stale or conflicting information by providing a synchronized, shared state that is updated centrally by the Orchestrator after each action.

Third, the MMS is the repository for **storing agent capabilities and static rules**. The system needs to know which agent is authorized to perform which action (e.g., Agent Red can traverse red edges). This type of information, which can be classified as "ahistorical knowledge" or "semantic memory," is static and defines the fundamental constraints and abilities within the system.2 The MMS provides a persistent store for these rules, allowing the Orchestrator to perform capability-based task delegation.

Finally, the MMS must facilitate **consensus and conflict resolution**. Although the Orchestrator pattern centralizes decision-making and minimizes direct agent-to-agent conflict, the shared memory itself can become a point of contention. The system must ensure that updates to the world state are atomic operations, preventing race conditions where the state could become inconsistent if multiple updates were processed concurrently.6 The MMS, as the sole gatekeeper of the world model, is responsible for enforcing this consistency.

---

## Section 2: Comparative Analysis of Advanced Memory and RAG Frameworks

The selection of the appropriate technology to implement the Memory Management System is a critical architectural decision. The tools under consideration—MemoRAG, RAGFlow, Gibson AI's Memori, and AutoRAG—are not merely interchangeable products but represent distinct architectural philosophies and layers of abstraction. A deep analysis reveals their respective strengths and weaknesses in the context of a symbolic, state-based HTN planning system, leading to a clear rationale for a hybrid, "best-of-breed" approach.

### 2.1 MemoRAG: A Paradigm for Advanced Reasoning

MemoRAG introduces a novel approach to Retrieval-Augmented Generation (RAG) that is particularly well-suited for complex reasoning tasks. Its primary innovation is a **dual-system architecture**. This architecture consists of a lightweight, long-context Large Language Model (LLM) that acts as a "memory model" and a more powerful, "heavyweight" generator LLM.11

The process begins with the memory model, which first compresses a large database into a global memory representation. When presented with a query, this model does not attempt to answer it directly but instead generates "clues" or a draft answer. These clues serve to bridge the gap between a potentially ambiguous user query and the precise information needed from the knowledge base.14 For example, a vague query like "What are the financial trends?" might yield clues such as "Identify revenue figures from recent years" or "Locate sections discussing market growth".11 These clues are then used to perform a much more targeted and effective retrieval from the source data. The retrieved information is then passed to the heavyweight generator LLM to synthesize a final, coherent answer.

The principal strength of MemoRAG lies in its ability to handle ambiguous information needs, perform multi-hop reasoning, and aggregate information from disparate sources—areas where traditional RAG systems often falter.11 This makes it highly relevant for the more advanced challenges in the problem set, such as the strategic trade-offs in Level 3 (Dynamic Resource Flow Graph) and the meta-level planning required in Level 5 (N-Peg Time-Limited Hanoi).

For the proposed architecture, the key takeaway from MemoRAG is not the adoption of the entire dual-LLM framework but the appropriation of its core _paradigm_: clue generation. The Orchestrating Agent can adopt this pattern to translate the abstract preconditions of an HTN task into a set of precise, structured queries for the MMS. This transforms the Orchestrator from a simple state-checker into a more sophisticated reasoning engine that can intelligently probe the world model to inform its planning decisions.

### 2.2 RAGFlow: An Integrated Engine for Document-Centric Tasks

RAGFlow presents itself as a comprehensive, open-source RAG _engine_. It is a full-stack platform that includes a web user interface, an API server, and an asynchronous task executor, all orchestrated on a backend stack that typically includes services like Elasticsearch, MySQL, Redis, and MinIO.16

The core strength of RAGFlow is its focus on **deep document understanding**. It is engineered to ingest and process complex, unstructured data from heterogeneous sources like PDFs, Word documents, and web pages.19 Its standout features include structure-aware chunking, which preserves the logical context of documents (e.g., tables, headers) during indexing, and a strong emphasis on generating citation-backed answers to reduce hallucinations.16 RAGFlow also includes its own low-code agent orchestration framework, allowing users to build complex workflows for information processing.16

However, the very strengths that make RAGFlow powerful for document-centric applications render it a poor fit for the user's specific domain. The complex reasoning problems at hand are defined by discrete, symbolic states (e.g., disk positions, agent capabilities) rather than information embedded within large text corpora. The HTN planner needs to execute structured queries against a world state ("Is Peg A clear?") not perform semantic searches over documents. Consequently, RAGFlow's sophisticated document parsing and chunking capabilities would be entirely unused. Furthermore, its reliance on a multi-service infrastructure introduces significant operational overhead that is not justified for this project's requirements.18 Therefore, RAGFlow is assessed as an overly complex and mismatched tool for this particular application.

### 2.3 Gibson AI's Memori: A SQL-Native Memory Layer for Agentic Systems

Gibson AI's Memori is fundamentally different from the other tools; it is not a RAG system but an open-source memory _layer_ specifically engineered for AI agents and multi-agent systems.7 Its architecture is built on a **SQL-native** foundation, designed to plug directly into standard relational databases such as SQLite, PostgreSQL, or MySQL.21 Internally, Memori employs its own multi-agent system—comprising a Memory Agent, a Conscious Agent, and a Retrieval Agent—to intelligently process conversations, extract key information, and manage the lifecycle of memories.7

Memori's most compelling feature for this project is its use of **structured memory types**. It automatically defines a database schema that explicitly separates memory into distinct categories, each stored in its own SQL table:

- **Short-Term Memory:** For recent, often transient, context.

- **Long-Term Memory:** For permanent insights and episodic history.

- **Rules Memory:** For user preferences, constraints, and static facts.

- **Entity Memory:** For tracking people, projects, and other objects. 8


This structured, relational approach is a perfect architectural match for the needs of an HTN planner. The planner's world model, with its collection of facts, constraints, and object states, can be mapped directly onto Memori's schema. The SQL-native design allows for complex, structured queries with logical operators (e.g., `WHERE`, `JOIN`, `GROUP BY`), which are far more powerful for checking the precise, logical preconditions of HTN tasks than the vector-based similarity search that underpins most RAG systems.8

Furthermore, Memori is explicitly designed for multi-agent systems, providing a natural foundation for the shared memory required for coordination.7 Its radical simplicity—enabling memory with a single line of code—and its commitment to data ownership and transparency make it an ideal candidate for a research project.8 For these reasons, Memori is identified as the strongest and most suitable technology to form the core of the Memory Management System.

### 2.4 AutoRAG: A Framework for Pipeline Optimization

AutoRAG occupies a unique position in this analysis. It is not a runtime component but an AutoML (Automated Machine Learning) framework designed to systematically **optimize and evaluate RAG pipelines**.24 Given a dataset, AutoRAG automates the process of experimenting with numerous combinations of RAG components—such as different retriever types, chunking strategies, embedding models, and prompt templates—to identify the configuration that performs best on a given set of metrics.24

Its primary strength is in removing the guesswork and manual effort from RAG system development. It provides an empirical, data-driven methodology for justifying architectural choices, which is invaluable in a research context.24

For the proposed architecture, AutoRAG is not a component of the final deployed system. Instead, it is positioned as a crucial tool to be used during the **development, validation, and optimization phases**. While much of the MMS will rely on structured SQL queries, the long-term memory component—which will store past plans for potential reuse—can benefit from semantic retrieval. AutoRAG can be employed to systematically test and select the most effective embedding model and retrieval strategy for this specific sub-task, ensuring that the system's learning and plan-reuse capabilities are built on an optimized foundation.

### 2.5 Synthesis and Selection Rationale

The analysis of these four frameworks reveals that they are not mutually exclusive competitors but rather represent different layers of a potential solution: a reasoning paradigm (MemoRAG), an integrated engine (RAGFlow), a foundational component layer (Memori), and a meta-optimization tool (AutoRAG). This nuanced understanding allows for the design of a sophisticated, multi-layered architecture that leverages the best aspects of each.

A **hybrid architecture** is therefore proposed:

- **Core Memory Backend:** **Gibson AI's Memori** is selected to implement the Memory Management System. Its SQL-native, structured, and agent-centric design provides the ideal foundation for storing and querying the world state required by the HTN planner. The fundamental distinction between the document-centric nature of traditional RAG and the state-centric requirements of this project's symbolic reasoning tasks is the primary driver of this choice.

- **Query Formulation Strategy:** The **"clue generation" principle from MemoRAG** will be adopted as a cognitive strategy for the Orchestrating Agent. This will enable it to translate complex HTN preconditions into precise, multi-part queries for the MMS, enhancing its reasoning capabilities.

- **Optimization Framework:** **AutoRAG** is recommended as an essential tool for the implementation phase. It will be used to empirically validate and optimize the semantic retrieval components of the MMS, specifically for the long-term memory used in plan reuse.

- **Rejected Component:** **RAGFlow** is respectfully declined. Its powerful document-processing capabilities are a poor fit for the symbolic nature of the problem domain, and its high infrastructure overhead is not justified.


This composite approach creates a robust, defensible, and highly capable architecture that is greater than the sum of its parts.

---

## Section 3: Finalized Architecture of the Memory-Augmented HTN System

### 3.1 Core Component Selection: A Hybrid Approach

The finalized architecture integrates the selected components into a cohesive system designed for coordinated, memory-driven planning. The system is composed of three primary layers: the Coordination Layer (Orchestrating Agent), the Execution Layer (Worker Agents), and the Memory Layer (Memory Management System).

- **Orchestrating Agent:** This is the central controller of the system. It houses the HTN planning engine and is responsible for all high-level reasoning. It interacts directly with the user (to receive goals) and the Memory Management System (to query and update the world state). It implements the MemoRAG-inspired query formulation logic to translate planning needs into structured database queries.

- **Worker Agents (x5):** These are the existing specialized agents from the original system. Their role is simplified to that of pure executors. They receive primitive action commands from the Orchestrator, execute them within the simulated environment, and report back their status (success or failure). They do not interact with each other or with the MMS directly; all coordination is mediated by the Orchestrator.

- **Memory Management System (MMS):** This is the foundational memory layer, implemented using the **Gibson AI's Memori** framework. The MMS encapsulates the entire memory state of the system and exposes a clean, high-level API to the Orchestrator. The internal complexity of Memori, including its own multi-agent processing and database management, is hidden behind this interface, ensuring a clean separation of concerns.


The overall data flow follows a centralized, hub-and-spoke model, with the Orchestrating Agent at the center, ensuring a predictable and traceable execution flow.

### 3.2 The Memory Management System: Structural Design and Data Models

The effectiveness of the entire architecture hinges on the proper configuration and utilization of the MMS. By leveraging Gibson AI's Memori, the system gains a structured, relational database backend that is perfectly suited to the needs of a symbolic planner. The default schema provided by Memori can be directly mapped to the information requirements of the HTN domain.

- **Short-Term Memory (`short_term_memory` table):** This table will be used to store the dynamic state of the current problem-solving instance. It holds volatile information that describes the "here and now" of the environment. For the Tower of Hanoi problem, this would include the current peg location of each disk. For graph traversal, it would track the agent's current node. This memory is cleared at the beginning of each new planning session to ensure a clean slate.21

- **Long-Term Memory (`long_term_memory` table):** This table is designed for episodic and procedural memory. It will store historical data, most importantly, successfully generated plans for previously solved problems. This creates a foundation for plan reuse and learning, a known technique for accelerating HTN planning in dynamic environments.4 The Orchestrator can query this memory at the start of a new problem to see if a similar problem has been solved before.

- **Rules Memory (`rules_memory` table):** This is arguably the most critical component for this architecture. It stores the static, domain-defining knowledge that governs the system's behavior. This includes immutable facts, constraints, and strategic heuristics. Examples include agent capabilities (e.g., `(capability, agent_green, traverse, green_edge)`), problem-specific constraints (e.g., `(constraint, hanoi_aux_peg, max_size, M)`), and even complex strategic knowledge like the mathematical formula for the Frame-Stewart algorithm required for the Level 5 problem.21 This table effectively serves as the HTN planner's externalized knowledge base.

- **Entity Memory (`memory_entities` table):** This table acts as an object registry for the world model. It defines and tracks all the discrete objects that the planner can reason about, such as the individual pegs and disks in the Hanoi problem, the nodes and edges in the graph problems, and the agents themselves. Each entity can have associated properties (e.g., a disk has a size, an edge has a weight and color) stored here or in related tables.21


The following table provides a concrete mapping of these components to the planner's requirements, serving as a blueprint for the implementation of the MMS.

|**HTN Domain Requirement**|**Memori Component**|**Example SQL-like Data Record / Query**|
|---|---|---|
|**Current World State**|Short-Term Memory|`UPDATE short_term_memory SET value='peg_C' WHERE key='disk_3_position';`|
|**Agent Capabilities**|Rules Memory|`(key='capability', value='{"agent": "red", "action": "traverse", "color": "red"}')`|
|**Hard Constraints**|Rules Memory|`(key='constraint_peg_b', value='{"type": "max_size", "limit": 100}')`|
|**Strategic Formulas**|Rules Memory|`(key='frame_stewart_algo', value='M(N,K) = min{2*M(N-k,K)+M(k,K-1)}')`|
|**Past Solutions (Plan Reuse)**|Long-Term Memory|`SELECT plan FROM long_term_memory WHERE problem_hash='hanoi_n4_k3';`|
|**Object Properties**|Entity Memory|`(entity_id='disk_4', properties='{"type": "disk", "size": 40}')`|

This explicit mapping demonstrates the tight alignment between the features of the selected tool (Memori) and the theoretical requirements of the HTN planning domain, providing a rigorous and defensible foundation for the system's implementation.

### 3.3 Interaction Protocols and Data Flow between Agents

The interactions within the system follow a strict, deterministic protocol orchestrated by the central agent. A typical planning cycle can be broken down into the following steps, which can be visualized using a sequence diagram:

1. **Goal Input:** The user submits a high-level goal to the Orchestrating Agent, for example, `(solve_constrained_hanoi, N=3, M=5)`. The Orchestrator initializes its HTN planner with this as the root task.

2. **State Query & Precondition Check:** The Orchestrator examines the current task at the head of its plan queue (e.g., a compound task `move_tower(size=2, from=A, to=C)`). It determines the preconditions for the available decomposition methods. To evaluate these preconditions, it formulates a structured query to the MMS. For instance, to check if moving a sub-tower of size 2 to the auxiliary peg B is valid, it would query: `QUERY: (current_disks_on_peg(B), disk_sizes([disks_to_move]), constraint_peg_b(max_size))`.

3. **Task Decomposition & Delegation:** The MMS processes the query against its `short_term_memory`, `entity_memory`, and `rules_memory` tables and returns the necessary data. The Orchestrator uses this data to evaluate the precondition. If it holds true, the Orchestrator applies the corresponding method, decomposing the compound task. If this results in a primitive task (e.g., `move_disk(D1, from=A, to=B)`), it identifies the responsible agent by querying the MMS for capabilities (if necessary) and delegates the task: `DELEGATE: (agent_Y, move_disk, D1, A, B)`.

4. **Execution & Reporting:** The designated Worker Agent (Agent Y) receives the command, performs the action in the simulation, and sends a status report back to the Orchestrator (e.g., `REPORT: (status=success)`).

5. **State Update:** Upon receiving a success report, the Orchestrator immediately issues an update command to the MMS to reflect the change in the world state, ensuring the world model remains consistent: `UPDATE: (disk_position, D1, B)`.

6. **Loop:** The Orchestrator moves to the next task in its queue, and the cycle repeats from Step 2 until the entire plan is executed and the goal is achieved. If at any point a precondition fails or an action is reported as failed, the HTN planner's natural backtracking mechanism is triggered, forcing the Orchestrator to explore alternative decomposition methods or plans.


### 3.4 Integrating the Memory System with the HTN Planner

The practical integration of the MMS with the HTN planner is achieved by creating a clean abstraction layer. Many HTN planner implementations define domain conditions and effects using native programming language functions (e.g., C++ or Python functions) rather than purely logical expressions, as this can improve performance by avoiding the need for a separate inference engine.4

In this architecture, these domain-specific functions within the Orchestrating Agent's HTN engine will be implemented as API calls to the MMS. For example, a precondition function like `is_peg_clear(peg_id)` will not check a local data structure but will instead make a network call to the MMS's `query_state` endpoint. Similarly, the `apply` function for a primitive operator, which modifies the world state, will be implemented as a call to the MMS's `update_state` endpoint.

This design choice effectively decouples the planner's domain logic from the memory's underlying implementation. The HTN methods and operators can be written in a clean, declarative style, focusing on the logic of the problem domain, while the complexities of data storage, retrieval, and consistency are handled entirely by the MMS. This modularity is a hallmark of robust system design, allowing the memory backend to be optimized, scaled, or even replaced in the future without requiring a complete rewrite of the core planning logic.

---

## Section 4: Architectural Validation via Complex Reasoning Scenarios

The robustness and efficacy of the proposed architecture are best demonstrated by applying it to the five complex reasoning problems defined in the project scope. These problems are not merely disparate test cases; they form a logical progression that evaluates increasingly sophisticated cognitive capabilities, from simple rule-based deduction to complex strategic adaptation. The architecture's ability to solve each problem in this hierarchy serves as a powerful validation of its design.

### 4.1 Level 1 (Multi-Color Graph Traversal): Managing Agent Specialization

- **Challenge:** This problem tests the system's ability to perform specialization and decomposition based on static agent capabilities. The planner must delegate pathfinding sub-tasks to the correct agent based on edge color.

- **Architectural Solution:** This is the most straightforward test of the `rules_memory` within the MMS. During initialization, the MMS is populated with the static capabilities of each agent. These are stored as structured records in the `rules_memory` table:

    - `('capability', '{"agent": "Agent Red", "action": "traverse", "property": "red"}')`

    - `('capability', '{"agent": "Agent Blue", "action": "traverse", "property": "blue"}')`

    - `('capability', '{"agent": "Agent Green", "action": "traverse", "property": "green"}')`


    When the Orchestrating Agent's HTN plan requires traversing an edge from node $S$ to node $U$, and that edge is known to be blue (information stored in the `entity_memory`), the precondition for the `traverse_edge(S, U)` task involves a query to the MMS: `QUERY: Find agent with capability (action='traverse', property='blue')`. The MMS queries its `rules_memory` and returns "Agent Blue". The Orchestrator then successfully decomposes the task and delegates the primitive action to Agent Blue. This demonstrates the core loop of querying static rules to enable dynamic, context-aware task delegation.


### 4.2 Level 2 (Constrained Tower of Hanoi): Dynamic State and Constraint Tracking

- **Challenge:** This problem introduces a dynamic resource constraint. The planner must not only follow the standard Hanoi rules but also continuously monitor the cumulative size of disks on the auxiliary peg, altering its strategy if a constraint would be violated.

- **Architectural Solution:** This scenario highlights the interplay between three memory components:

    1. **`rules_memory`:** Stores the hard constraint: `('constraint', '{"peg": "B", "property": "max_size", "value": M}')`.

    2. **`entity_memory`:** Stores the static properties of each disk: `('entity', '{"id": "D_i", "type": "disk", "size": S_i}')`.

    3. **`short_term_memory`:** Tracks the dynamic state, i.e., the current location of every disk: `('state', '{"id": "D_i", "location": "peg_A"}')`.


    Before the Orchestrator can apply a method that involves moving a sub-tower to the auxiliary Peg B, it must perform a complex precondition check. It issues a multi-part query to the MMS, formulated using the MemoRAG-style "clue generation" principle: "Calculate the total size of disks in the sub-tower to be moved AND calculate the total size of disks currently on Peg B. Return both sums and the max_size constraint for Peg B." The MMS executes this by joining information from all three tables. The Orchestrator receives the results and performs the check: `(size_of_sub_tower + size_on_peg_b) <= max_size_b`. If this check fails, the HTN planner's backtracking mechanism is triggered, forcing it to select an alternative decomposition method that uses a different peg as the auxiliary, thereby demonstrating dynamic, state-aware, and constraint-adherent planning.


### 4.3 Level 3 (Dynamic Resource Flow Graph): Handling Observability and Probabilistic States

- **Challenge:** This problem tests the system's ability to handle uncertainty, observability, and strategic trade-offs. The planner must reason about probabilistic edge weights and decide whether to use a costly "research" tool to gain certainty.

- **Architectural Solution:** This showcases the architecture's capacity for belief-state management and dynamic updates. The `entity_memory` initially stores the graph with probabilistic information for each edge: `('entity', '{"id": "edge_uv", "T_est": X, "P_delay": Y, "T_penalty": Z}')`. The `rules_memory` stores the cost of research: `('tool_cost', '{"tool": "researcher", "cost": T_research}')`.

    When the HTN planner encounters a high-risk edge (high $P_{delay}$), the decomposition method involves a strategic decision. The Orchestrator queries the MMS for the edge's properties and the research cost. It then performs a trade-off analysis (potentially using an LLM call for complex heuristics) to weigh the expected cost of traversing without research (`T_{est} + P_{delay} * T_{Penalty}`) against the cost of researching and then traversing (`T_{research} + T_{actual}`). If the decision is to research, the Orchestrator delegates a `research_edge(u, v)` task to Agent B (the Researcher). Agent B executes its tool and reports the `T_{actual}` back. The Orchestrator then immediately issues an `UPDATE` command to the MMS, changing the state of `edge_uv` to be certain: `UPDATE: ('entity', '{"id": "edge_uv", "T_actual": W}')`. The planner then proceeds with this new, certain information. This cycle of querying uncertain state, making a strategic decision, executing an information-gathering action, and updating the world model is a core pattern of planning under uncertainty and demonstrates the system's handling of observability.


### 4.4 Level 4 (Multi-Agent Stack Transfer): Enabling Coordination and Precondition Synchronization

- **Challenge:** This is a pure test of multi-agent coordination through a shared world state. Two agents with different, non-overlapping capabilities must cooperate to solve a single problem, requiring precise synchronization to avoid illegal states.

- **Architectural Solution:** The MMS acts as the central synchronization mechanism, the "source of truth" that enables coordination. The `rules_memory` defines the agent capabilities: `('capability', '{"agent": "Agent X", "can_move":}')` and `('capability', '{"agent": "Agent Y", "can_move":}')`. The `short_term_memory` tracks all disk positions.

    The Orchestrator's top-level plan to move the 4-disk tower from A to C requires moving the top 3 disks from A to B first. This sub-goal is further decomposed. To move disk D3 from A to C, the precondition is that D1 and D2 must not be on A or C. The Orchestrator's plan will first generate a task `move_disk(D2, A, B)`. It queries the MMS, finds Agent Y has the capability, and delegates. Agent Y executes and reports success. The Orchestrator updates the MMS: `D2` is now on `B`. The planner then proceeds to `move_disk(D1, A, B)`. After this is completed and the MMS is updated, the precondition for moving D3—that the smaller disks are clear—is finally met. The Orchestrator can now query the MMS, confirm `is_clear(D3)`, find that Agent X has the capability, and delegate the `move_disk(D3, A, C)` task. This strict sequence of delegation, execution, reporting, state update, and subsequent precondition checking via the shared MMS is the essence of the coordination mechanism. It prevents Agent X from attempting an illegal move before Agent Y has completed its necessary preparatory actions.


### 4.5 Level 5 (N-Peg Time-Limited Hanoi): Supporting Strategic and Adaptive Planning

- **Challenge:** This is the most advanced problem, requiring the system to perform meta-level reasoning to select the optimal planning strategy itself, and to adapt that strategy based on external constraints (a time limit).

- **Architectural Solution:** This scenario leverages the full power of the architecture, particularly the ability to store and execute complex strategic knowledge.

    1. **Strategic Knowledge Storage:** The `rules_memory` stores the Frame-Stewart algorithm, not as a simple value, but as a callable function or a set of logical rules that the MMS can execute: `('strategy', '{"name": "frame_stewart", "logic": <function_pointer_or_code>}')`.

    2. **Meta-Level Planning:** The Orchestrator's highest-level HTN task, `solve_generalized_hanoi(N, K, T_limit)`, has a method whose precondition is a complex, MemoRAG-style query to the MMS: "Execute the 'frame_stewart' strategy for N and K to find the optimal split point `k` and the minimum number of moves `M(N, K)`."

    3. **Constraint-Based Adaptation:** The MMS executes the algorithm and returns the result `M(N, K)`. The Orchestrator then compares this value to the `T_{limit}` parameter. If `M(N, K) > T_{limit}`, the precondition for the optimal method fails. The HTN planner backtracks and selects an alternative method, `use_suboptimal_strategy`, which might involve a simpler, faster-to-calculate but less move-efficient plan.


    This demonstrates the architecture's ability to go beyond simple state checking. It can store abstract strategic knowledge, use that knowledge to perform meta-level analysis on the problem itself, and adapt its entire planning approach based on the results of that analysis and external constraints. This represents the highest level of cognitive capability tested and validates the architecture's design for complex, strategic reasoning.


---

## Section 5: Implementation Roadmap and Strategic Recommendations

### 5.1 Recommended Technology Stack and Toolchain

To translate the finalized architecture into a functional system, a carefully selected set of tools and technologies is recommended. This stack prioritizes open-source availability, Python-based implementation for ease of integration, and explicit support for the core architectural components.

- **Memory Backend:** The foundational component is **Gibson AI's Memori**. The implementation should begin by installing its Python SDK (`pip install memorisdk`).7 For initial development and prototyping, the default **SQLite** backend is sufficient and requires zero configuration.8 For more robust testing and to leverage advanced features, transitioning to a **PostgreSQL** database is recommended. PostgreSQL provides better concurrency control and scalability, which will be important as the complexity of agent interactions increases.7

- **Agent Framework:** The implementation of the Orchestrating Agent and the five Worker Agents can be significantly accelerated by using an established multi-agent framework. Both **AutoGen** and **CrewAI** are excellent choices, as Gibson AI's Memori provides pre-built integration examples for both.7 These frameworks provide robust abstractions for defining agent roles, managing communication, and orchestrating task execution, allowing the developer to focus on the unique logic of the HTN planner and the worker agents' capabilities.

- **HTN Planner:** A Python-based HTN planner library should be integrated into the core logic of the Orchestrating Agent. There are several open-source options available. The key implementation task will be to "re-wire" the planner's internal state-checking functions. Instead of accessing local variables, these functions (e.g., for checking preconditions or applying operator effects) must be modified to make API calls to the MMS interface, as detailed in Section 3.4.

- **Optimization Toolchain:** For the optimization phase, the **AutoRAG** library should be used.24 This will involve writing Python scripts that configure AutoRAG to benchmark various embedding models (e.g., from Hugging Face) and retrieval strategies for the long-term memory component. The goal is to empirically determine the most performant configuration for retrieving relevant past plans, which will be stored as text or structured data in the MMS's `long_term_memory` table.


### 5.2 A Phased Implementation and Testing Strategy

A phased, iterative approach to implementation is recommended to manage complexity and ensure each component is robust before integrating the next.

- **Phase 1: Core System Setup and Static Reasoning.**

    - **Objective:** Establish the basic communication loop and validate static rule-based reasoning.

    - **Tasks:**

        1. Initialize the MMS using Memori with a SQLite backend.

        2. Define the initial database schema in the MMS, populating the `entity_memory` and `rules_memory` tables.

        3. Implement a basic Orchestrating Agent and one Worker Agent (e.g., Agent Red).

        4. Integrate a simple HTN planner into the Orchestrator.

        5. Implement and test the full workflow for the **Level 1 (Multi-Color Graph Traversal)** problem. This will validate the core functionality of rule lookup and task delegation.

- **Phase 2: Dynamic State Management and Coordination.**

    - **Objective:** Implement the tracking of dynamic world state and validate multi-agent synchronization.

    - **Tasks:**

        1. Expand the MMS and Orchestrator logic to fully utilize the `short_term_memory` for tracking dynamic state changes.

        2. Implement the full set of Worker Agents (X and Y).

        3. Develop the HTN domains for the **Level 2 (Constrained Tower of Hanoi)** and **Level 4 (Multi-Agent Stack Transfer)** problems.

        4. Rigorously test the coordination protocols, ensuring that state updates are atomic and preconditions based on the actions of other agents are correctly evaluated.

- **Phase 3: Advanced Reasoning and Tool Integration.**

    - **Objective:** Incorporate uncertainty, tool use, and meta-level strategic planning.

    - **Tasks:**

        1. Implement the logic for handling probabilistic data within the MMS.

        2. Integrate the "Researcher" agent (Agent B) and its associated external tool call.

        3. Develop the MemoRAG-inspired complex query formulation within the Orchestrator.

        4. Implement and test the HTN domains for the **Level 3 (Dynamic Resource Flow Graph)** and **Level 5 (N-Peg Time-Limited Hanoi)** problems.

- **Phase 4: Performance Optimization and Refinement.**

    - **Objective:** Empirically optimize the system's retrieval components.

    - **Tasks:**

        1. Use the AutoRAG framework to benchmark various embedding models and retrieval configurations for the `long_term_memory` component.

        2. Integrate the winning configuration into the MMS.

        3. Conduct end-to-end performance testing and refine the system based on the results.

        4. Transition the MMS backend from SQLite to PostgreSQL for final evaluation.


### 5.3 Contributions to Thesis and Avenues for Future Research

This project, when implemented according to the proposed architecture, offers significant contributions to the field of AI and provides a strong foundation for a graduate thesis.

#### Thesis Contributions

The primary contribution is the design, implementation, and validation of a **novel, hybrid cognitive architecture** that successfully bridges the gap between symbolic AI planning and modern agentic memory systems. Specifically, it demonstrates how a classical, deterministic planner (HTN) can be augmented with a structured, database-centric memory system (Memori) to enable a team of agents to solve complex reasoning tasks that require coordination, state tracking, and strategic adaptation. The work provides an empirical validation of this architecture against a graduated set of benchmark problems, showcasing its versatility and power. It also contributes a practical methodology for integrating these disparate technologies into a cohesive and functional whole.

#### Avenues for Future Research

This architecture opens up several promising avenues for future investigation:

- **Decentralization and Hierarchical Architectures:** The current model is centralized. A valuable line of future research would be to explore how this system could be adapted to a decentralized peer-to-peer or a multi-level hierarchical pattern.1 This would involve investigating how to distribute the memory and planning functions to improve scalability and resilience, especially for systems with a much larger number of agents.

- **Automated Knowledge Acquisition:** The current architecture relies on a hand-coded `rules_memory`. A significant advancement would be to develop agents capable of **automated knowledge acquisition**. These agents could learn the rules of the domain, agent capabilities, and even strategic heuristics by observing the environment, reading documentation, or analyzing past performance, transitioning the system from a pre-programmed knowledge base to a truly learned one.28

- **Enhanced Plan Reuse and Learning:** The `long_term_memory` component provides a basis for plan reuse. Future work could significantly enhance this capability by developing more sophisticated algorithms within the Orchestrator to learn from planning failures and successes. By analyzing why certain plans failed and others succeeded, the agent could refine its method selection heuristics over time, improving its planning efficiency and success rate in novel situations.4 This would move the system closer to a continuously learning and self-improving autonomous agent.
