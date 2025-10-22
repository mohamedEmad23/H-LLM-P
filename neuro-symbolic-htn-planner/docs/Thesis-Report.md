
# **A Neuro-Symbolic Framework for Dynamic Hierarchical Task Network Planning: Mitigating the Knowledge Engineering Bottleneck using Large Language Models**

## **Abstract**

Hierarchical Task Network (HTN) planning is a powerful paradigm in Artificial Intelligence that mirrors human-like problem-solving by decomposing complex tasks into simpler, more manageable steps. Its practical utility, however, is often constrained by a significant "knowledge engineering bottleneck": the laborious and often infeasible requirement of manually specifying a complete and correct library of task decomposition methods for any given domain. This thesis addresses this fundamental limitation by proposing a novel neuro-symbolic framework that integrates the structured, logical reasoning of symbolic HTN planners with the vast, implicit procedural knowledge of modern Large Language Models (LLMs). The core contribution is a hybrid planning architecture and a corresponding algorithm, **GPT-HTN-Refine**, which dynamically augments an HTN planner's knowledge base. When the symbolic planner encounters a task for which it has no predefined decomposition method, it queries an LLM to generate a plausible sub-plan on-demand. Crucially, the framework ensures the logical soundness of the final plan, even when incorporating components from an inherently non-symbolic and approximate model like an LLM. This is achieved through a novel "verifier task" mechanism, which leverages the symbolic planner's own sound verification capabilities to formally check that the LLM-generated sub-plan achieves its intended effects. This approach effectively treats the LLM as an external, runtime-accessible knowledge source, creating a system that is both flexible and robust. The framework demonstrates a path toward developing more adaptable and powerful automated planning systems that can operate effectively without requiring a complete, pre-specified domain model, thereby significantly mitigating the long-standing knowledge engineering bottleneck.

---

## **1. Introduction**

### 1.1 The Power and Paradox of Hierarchical Planning

Automated planning, a cornerstone of Artificial Intelligence, seeks to enable machines to reason about actions and their consequences to achieve specified goals. Among the various planning paradigms, Hierarchical Task Network (HTN) planning stands out for its intuitive and powerful approach that closely mirrors human cognition.1 Unlike classical planning, which searches for a sequence of actions to transform an initial state into a goal state, HTN planning operates by decomposing high-level, abstract tasks into progressively simpler and more concrete subtasks.2 This process continues recursively until the entire plan consists of primitive tasks—actions that can be directly executed in the world.1

This hierarchical decomposition methodology offers significant advantages. It allows domain experts to encode procedural knowledge and strategic guidance directly into the planning model, constraining the search space and leading to more efficient and realistic plan generation.1 The structure of HTN planning is naturally suited for a wide array of real-world applications where tasks are inherently hierarchical. These include complex logistics and supply chain management, where a high-level goal like "deliver package" is broken down into sub-goals like transportation, loading, and unloading 1; robotics, where a command like "clean the kitchen" is decomposed into navigation, object manipulation, and cleaning actions; and strategic decision-making in domains such as military operations and game AI.1

However, the very source of HTN planning's power gives rise to its central paradox. The effectiveness of an HTN planner is fundamentally dependent on the quality and, most critically, the completeness of its domain knowledge, which is encapsulated in a library of "methods" that define valid task decompositions.1 This dependency creates a significant practical hurdle, leading to what is widely recognized as the knowledge engineering bottleneck.

### 1.2 The Knowledge Engineering Bottleneck: A Persistent Challenge

The knowledge engineering bottleneck is the single most significant impediment to the widespread adoption of HTN planning.1 It refers to the immense difficulty, time, and expertise required to manually author a complete and correct set of HTN methods for any non-trivial domain.1 Domain experts must anticipate every possible situation the planner might encounter and provide a valid decomposition method for every compound task applicable in that situation. In real-world environments, which are often dynamic and complex, this is a Herculean, if not impossible, task.1

When the method library is incomplete, the planner's utility is severely compromised. It may fail to find a solution to a perfectly solvable problem simply because the specific piece of procedural knowledge required for a particular decomposition step is missing from its library.1 This brittleness stands in stark contrast to the flexibility of human problem-solving, where individuals can improvise, draw on commonsense knowledge, or reason from first principles when faced with an unfamiliar sub-problem. The challenge is not merely one of quantity; identifying which method is incomplete is itself a difficult problem, as an action required to make a plan executable could plausibly be a missing subtask in several different high-level methods.1 This fundamental limitation has historically constrained HTN planning to domains that are well-understood and stable enough to permit a near-complete manual formalization.

### 1.3 The Rise of Large Language Models as Reasoning Engines

Recent years have witnessed a paradigm shift in Artificial Intelligence with the advent of Large Language Models (LLMs) such as the GPT (Generative Pre-trained Transformer) family.1 Trained on vast corpora of text and code, these models have demonstrated remarkable emergent capabilities in natural language understanding, commonsense reasoning, and even procedural task generation.1 LLMs can be prompted to produce plausible sequences of steps to achieve a given goal, effectively acting as powerful reasoning engines that can generate plan-like structures from their implicit, learned knowledge.1

This capability presents a compelling opportunity to address the knowledge engineering bottleneck in HTN planning. Instead of relying solely on a static, explicitly programmed knowledge base, a planner could potentially tap into the immense, unstructured knowledge encoded within an LLM. The challenge, however, lies in the nature of LLM-generated output. LLMs are generative and probabilistic, not logical and deterministic. They cannot guarantee the soundness or correctness of the plans they produce and are known to "hallucinate" actions or generate plans for problems that are logically unsolvable.1 Integrating such a powerful but unreliable component into a formal planning system requires a new architectural approach—one that can harness the LLM's flexibility without sacrificing the logical rigor and soundness guarantees of symbolic planning.

### 1.4 Thesis Statement and Contributions

This thesis proposes a novel neuro-symbolic framework that dynamically augments a symbolic Hierarchical Task Network planner with on-demand task decompositions generated by a Large Language Model, thereby mitigating the knowledge engineering bottleneck while guaranteeing the soundness of the resulting plans. The framework treats the domain model not as a static, pre-compiled artifact, but as a dynamic entity that can be expanded at runtime. This represents a fundamental shift in the philosophy of automated planning, moving from "planning _with_ a model" to "planning _while building_ a model." When the symbolic planner encounters a knowledge gap—a compound task for which it has no defined method—it queries the LLM to provide a plausible decomposition. This LLM-generated sub-plan is then critically validated within the symbolic framework before being integrated into the final plan.

The primary contributions of this thesis are:

1. **A Hybrid Neuro-Symbolic Architecture:** The design of a novel framework that seamlessly interleaves the sound, deductive search of a symbolic HTN planner with the approximate, generative capabilities of an LLM. The symbolic planner maintains control, invoking the LLM only as an external knowledge source when its own explicit knowledge is insufficient.
    
2. **A Formal Soundness Guarantee Mechanism:** The introduction of a "verifier task" mechanism, a formal construct that leverages the symbolic planner's own logic to rigorously validate the effects of an LLM-generated sub-plan. This ensures that any final plan produced by the system is guaranteed to be correct, a critical property that purely LLM-based planners lack.
    
3. **The GPT-HTN-Refine Algorithm:** The design, formalization, and analysis of a custom algorithm, GPT-HTN-Refine, that implements the proposed neuro-symbolic framework. The algorithm details the process of knowledge gap detection, contextual prompt construction, LLM response parsing, and verifier task injection.
    
4. **A Practical Implementation Roadmap:** A comprehensive guide for implementing the proposed system using modern, accessible tools, including the PyHop planner and standard LLM APIs. This provides a clear path for future research and practical application of the framework.
    

By combining the strengths of both symbolic and neural approaches, this work aims to create a new class of planning systems that are more robust, flexible, and practical for real-world application than either paradigm in isolation.

---

## **2. Preliminaries in Automated Planning**

To fully appreciate the proposed neuro-symbolic framework, it is essential to first establish a formal understanding of its symbolic foundation: Hierarchical Task Network (HTN) planning. This section provides the necessary definitions and concepts, drawing from established literature in the field of automated planning.1

### 2.1 Formalizing Hierarchical Task Network (HTN) Planning

The HTN planning paradigm is built upon a structured representation of the world, tasks, and the knowledge required to perform them. This formalism provides the logical grounding for the entire planning process.

#### State Representation

The state of the world at any given time is represented as a finite set of ground atoms, or predicates. A predicate is a logical statement that is either true or false. For example, in a logistics domain, the state might be represented by predicates such as `at(truck1, london)`, `in(packageA, truck1)`, and `airport(heathrow)`. This representation assumes a closed-world assumption, where any predicate not explicitly listed in the state is considered false.1

#### Tasks (Primitive and Compound)

The central concept in HTN planning is the "task," which represents an activity to be performed. Tasks are divided into two distinct categories, reflecting the hierarchical nature of the planning process.1

- **Primitive Tasks:** These are the atomic units of action within the domain. A primitive task corresponds to an action that can be directly executed by an agent, causing a direct change in the world state. Examples include `pick-up(blockA)`, `drive(truck1, london, paris)`, or `load(packageA, truck1)`. Each primitive task is formally defined by an "operator".1
    
- **Compound Tasks:** These are abstract, high-level tasks that cannot be directly executed. Instead, they represent complex goals or activities that must be decomposed into a network of simpler subtasks (which can be either primitive or, recursively, other compound tasks). Examples include `build-a-tower`, `deliver-package(packageA, paris)`, or `clean-room`. Compound tasks define _what_ needs to be accomplished, but not _how_.1
    

This explicit separation between the "what" (compound tasks) and the "how" (the methods for decomposition) is a crucial structural feature. It is precisely this separation that makes the HTN paradigm uniquely suited for neuro-symbolic integration. The symbolic system defines the high-level goals and structure, while the LLM can be called upon to provide a specific "how" when one is not explicitly defined in the symbolic knowledge base. This allows for a targeted intervention that fills a knowledge gap without disrupting the overarching logical framework of the planner.

#### Task Networks

A task network is a collection of tasks, either primitive or compound, coupled with a set of ordering constraints that specify temporal relationships between them.1 For instance, a task network for delivering a package might specify that the

`load` task must occur before the `drive` task, and `drive` must occur before the `unload` task. This network represents a partial or complete plan at some level of abstraction. The goal of the HTN planner is to transform an initial, high-level task network into a final, primitive task network whose tasks can be totally ordered into an executable sequence.

### 2.2 Methods and Operators: The Fabric of Domain Knowledge

The domain knowledge in an HTN system is encoded in two primary structures: operators, which define the behavior of primitive tasks, and methods, which define the decomposition of compound tasks.

#### Operators

An operator is the formal definition of a primitive task. It is typically represented as a tuple consisting of:

- **Name:** A unique identifier for the action, including its parameters (e.g., `load(?pkg,?truck,?loc)`).
    
- **Preconditions:** A set of logical predicates that must be true in the current state for the operator to be applicable. For example, to load a package, both the package and the truck must be at the same location.
    
- **Effects:** A description of how the operator changes the world state. This is often split into an "add-list" (predicates that become true) and a "delete-list" (predicates that become false). For instance, after loading a package, the predicate `at(?pkg,?loc)` is deleted, and `in(?pkg,?truck)` is added.1
    

#### Methods

Methods are the core of the procedural knowledge in an HTN planner. A method specifies one valid way to decompose a compound task into a more detailed task network of subtasks.1 A method is formally composed of:

- **Head:** The compound task that the method decomposes (e.g., `deliver-package(?pkg,?dest)`).
    
- **Body (or Subtasks):** A task network of subtasks that, when completed, achieves the compound task. For example, the body for `deliver-package` might be the sequence of subtasks: `get-truck`, `load-package`, `drive-truck`, `unload-package`.
    

A single compound task can have multiple associated methods. This allows the planner to choose different strategies for accomplishing the same high-level goal based on the current state of the world. For example, there might be one method for delivering a package within the same city (using a truck) and another for delivering it between cities (using a plane). The planner selects an applicable method by checking its preconditions, which are conditions that must be met for that specific decomposition to be valid.1

### 2.3 The HTN Planning Process

The HTN planning process is a recursive, top-down search for a valid decomposition of an initial task network.2 The algorithm can be summarized as follows:

1. **Initialization:** The planner starts with an initial state and an initial task network, which typically contains one or more high-level compound tasks.
    
2. **Task Selection:** The planner selects a task from the current task network to process, respecting the ordering constraints.
    
3. **Decomposition/Execution:**
    
    - If the selected task is **compound**, the planner searches its knowledge base for an applicable method whose head matches the task and whose preconditions are satisfied in the current state. If a valid method is found, the compound task is replaced in the network by the method's body (its subtasks), and the ordering constraints are updated accordingly.
        
    - If the selected task is **primitive**, the planner checks if the preconditions of its corresponding operator are satisfied in the current state. If they are, the planner updates its internal state according to the operator's effects and adds the primitive action to the final plan.
        
4. **Recursion and Termination:** The planner recursively applies this process to the new task network. The process terminates successfully when the task network is empty, meaning all initial tasks have been decomposed into a sequence of executable primitive actions. If at any point the planner cannot find an applicable method for a compound task or cannot execute a primitive task, it must backtrack and try a different choice (e.g., a different method for a previous decomposition).3
    

This search for a valid decomposition is what distinguishes HTN planning. The solution is not just any sequence of actions that reaches a goal, but one that is consistent with the hierarchical structure and procedural knowledge encoded in the domain's methods.

---

## **3. Literature Review: LLMs in Planning and Reasoning**

The integration of Large Language Models (LLMs) into the domain of automated planning and agent-based decision-making is a rapidly evolving field. Early approaches treated LLMs as simple translators or naive planners, but recent research has developed more sophisticated architectures that leverage their reasoning capabilities in hierarchical and adaptive ways. This review surveys the key advancements, starting from foundational agent architectures and progressing to the state-of-the-art in neuro-symbolic integration, thereby contextualizing the novel contributions of this thesis.

### 3.1 LLM Agent Architectures

The first wave of LLM-based agents primarily fell into two categories, each with distinct strengths and weaknesses.

#### Iterative Executors (e.g., ReAct)

The ReAct (Reason and Act) framework pioneered an influential approach where the LLM operates in a tight loop of reasoning and action.1 At each step, the agent receives an observation from the environment and is prompted to generate a "thought"—a textual rationale for its next action—followed by the action itself. This interleaving allows the agent to react dynamically to environmental feedback, update its internal strategy, and handle unexpected outcomes. While this iterative process provides significant local adaptability, ReAct-style agents can struggle with long-horizon planning. Without a high-level, persistent plan, they are prone to getting sidetracked by local optima or losing sight of the overall goal, leading to inefficient or failed task execution in complex scenarios.1

#### Plan-and-Execute Frameworks

To address the lack of global guidance in iterative executors, the plan-and-execute paradigm was developed.1 In this two-stage approach, an LLM is first prompted to generate a complete, high-level plan, typically as a sequence of sub-tasks or goals. In the second stage, a separate LLM instance (or the same one) is tasked with executing each sub-task in sequence. This modular approach provides a clear structure and ensures that the agent maintains focus on the overall objective. However, its primary weakness is its rigidity. The initial plan is generated without environmental feedback and is not adapted during execution. If any sub-task is unexpectedly complex or fails due to an unforeseen circumstance, the entire plan can derail, as the agent typically lacks a mechanism to dynamically replan or decompose the failing step further.1

### 3.2 Adaptive and Hierarchical Decomposition

Recognizing the limitations of both purely reactive and rigidly planned approaches, subsequent research has focused on creating frameworks that combine high-level structure with low-level adaptability. These systems often employ hierarchical or on-demand decomposition strategies.

#### ADAPT (As-Needed Decomposition)

The ADAPT framework introduces a crucial innovation: dynamic, "as-needed" decomposition.1 ADAPT begins by attempting to execute a high-level task directly. It only invokes a planner module to decompose the task into sub-tasks if the executor module signals a failure. This process is recursive; if a sub-task also proves too complex for the executor, it is further decomposed. This strategy allows the plan's granularity to adapt dynamically to both the inherent complexity of the task and the specific capabilities of the executor LLM. It avoids the inefficiency of pre-planning every detail while retaining the ability to break down difficult steps, providing a more robust and efficient approach to complex tasks.1

#### HIPLAN (Hierarchical Planning with Guidance)

The HIPLAN framework focuses on leveraging structured past experience to guide the planning process.1 It operates using a "milestone library" constructed offline from expert demonstrations. During execution, HIPLAN provides two levels of guidance. First, it retrieves similar tasks from the library to generate a global "milestone action guide"—a high-level roadmap for the current task. Second, at each step, it retrieves relevant trajectory fragments from completed milestones to generate a local "step-wise hint"—a real-time traffic update that helps correct deviations and align actions with the current milestone. This dual-level guidance system effectively combines the benefits of high-level planning with fine-grained, context-aware adaptability, making it particularly effective for long-horizon tasks.1

#### HyperTree Planning (HTP)

HyperTree Planning introduces a novel reasoning paradigm that structures the planning process as the construction of a hypertree.1 This approach is inspired by human "hierarchical thinking," where complex problems are solved using a flexible, multi-level divide-and-conquer strategy. In the HTP framework, each edge in the reasoning structure can connect a parent node to a set of child nodes, providing a natural way to model the decomposition of a task into multiple parallel or sequential sub-tasks. This structure allows the LLM to effectively manage tasks with long reasoning chains, diverse constraints, and multiple distinct components in a highly organized manner. The framework autonomously generates a task-specific planning outline and then iteratively refines it, demonstrating superior performance on complex planning benchmarks.1

### 3.3 Neuro-Symbolic Integration for Task Planning

The most recent and relevant line of research involves the direct integration of LLMs with classical symbolic planning systems. These hybrid, or neuro-symbolic, approaches aim to combine the formal guarantees and logical consistency of symbolic methods with the commonsense knowledge and flexibility of LLMs.

#### LLMs for PDDL Generation

An early application of neuro-symbolic integration was using LLMs to bridge the gap between human instruction and formal planning languages.1 In these systems, an LLM translates a task specified in natural language into a formal representation, such as the Planning Domain Definition Language (PDDL). This PDDL output, which defines the initial state and goal conditions, is then fed into a traditional symbolic planner to find a solution. While this automates a part of the problem formalization process, the core planning and reasoning remain entirely within the symbolic domain.

#### Interactive Learning and Refinement

Another approach uses LLMs as a conversational front-end for interactive task learning.1 In these systems, a user provides instructions in natural language. The LLM parses the dialogue into predicate-argument structures. If the system encounters an unknown action or concept, it initiates a clarification dialogue, recursively asking the user for a definition. This interactive process allows the system to build a hierarchical task representation from natural conversation, demonstrating the LLM's power as a flexible interface for knowledge acquisition.1

#### ChatHTN (Interleaving Symbolic and Neural Planning)

The ChatHTN framework provides a key inspiration for this thesis.1 It is an HTN planner that directly interleaves symbolic planning with LLM queries. When the planner encounters a compound task for which it has no predefined method in its knowledge base, it pauses its symbolic search and queries ChatGPT to generate a plausible decomposition. This on-demand approach directly addresses the knowledge engineering bottleneck by filling gaps in the domain model at runtime. Most importantly, ChatHTN introduces the concept of "verifier tasks." After injecting an LLM-generated sub-plan, it appends a special primitive task whose preconditions are the intended effects of the original compound task. This forces the symbolic planner to formally verify that the LLM's sub-plan achieved the desired outcome, thereby guaranteeing the soundness of the final, complete plan.1

#### Task Insertion and Method Refinement

It is also valuable to consider purely symbolic approaches for handling incomplete knowledge. The TIHTN (Task Insertion HTN) planning formalism allows a planner to insert primitive tasks that are not part of any predefined method to make a plan executable.1 The plans generated by a TIHTN planner can then be used as a reference to refine the incomplete methods. To resolve the ambiguity of where an inserted task belongs, this approach can be guided by a set of prioritized preferences that capture the likelihood of incompleteness for different methods. This provides a formal, non-LLM baseline for the problem of method refinement and learning from incomplete domain knowledge.1

The following table provides a comparative summary of these modern LLM-based planning frameworks, situating the proposed GPT-HTN-Refine system within the current state of the art.

|Framework Name|Core Strategy|Handling of Hierarchy|Soundness Guarantee|Key Limitation|
|---|---|---|---|---|
|**ReAct**|Interleaves reasoning and acting in a reactive loop.|Implicit; no explicit hierarchical structure.|No|Lacks global guidance; struggles with long-horizon tasks.|
|**Plan-and-Execute**|Generates a static high-level plan, then executes sub-tasks.|Single-level, static decomposition.|No|Brittle; cannot adapt to execution failures or replan.|
|**ADAPT**|Decomposes tasks recursively and on-demand upon failure.|Dynamic, multi-level decomposition.|No|Relies on LLM self-evaluation for failure detection, which can be unreliable.|
|**HIPLAN**|Uses a library of expert demonstrations for global and local guidance.|Guided by a retrieved "milestone" hierarchy.|No|Performance depends heavily on the quality and relevance of the expert library.|
|**HyperTree Planning**|Models planning as the construction of a hypertree outline.|Multi-level, flexible "divide-and-conquer" structure.|No|Does not guarantee plan correctness; focuses on generating plausible outlines.|
|**ChatHTN**|Interleaves symbolic HTN planning with on-demand LLM queries.|Uses existing HTN methods; LLM provides single-level decomposition for knowledge gaps.|Yes (via verifier tasks)|LLM is only used for primitive task sequences; cannot generate new compound sub-tasks.|
|**GPT-HTN-Refine (Proposed)**|Augments a symbolic HTN planner with on-demand LLM method generation.|Leverages existing HTN hierarchy; LLM provides new method bodies on-demand.|Yes (via verifier tasks)|Performance is dependent on LLM quality and prompt engineering.|

This review demonstrates a clear trajectory in the field: from simple, monolithic LLM agents toward more structured, adaptive, and hierarchical systems. The neuro-symbolic approach, particularly as pioneered by ChatHTN, represents the frontier of this research by seeking to combine the best of both worlds. The proposed GPT-HTN-Refine framework builds directly upon this frontier, aiming to create a system that is not only sound and flexible but also capable of learning and expanding its symbolic knowledge over time.

---

## **4. A Neuro-Symbolic Architecture for On-Demand HTN Planning**

To address the knowledge engineering bottleneck while preserving the formal guarantees of symbolic planning, this thesis proposes a hybrid neuro-symbolic architecture. This architecture is designed not to replace the symbolic HTN planner, but to augment its capabilities by integrating a Large Language Model as an on-demand source of procedural knowledge. This section details the core principles, components, and operational cycle of this proposed system.

### 4.1 Core Principle: Interleaving Soundness and Flexibility

The guiding philosophy of the architecture is the strategic interleaving of soundness and flexibility. The system operates under the principle that the symbolic planner is the ultimate arbiter of correctness, while the LLM is a powerful tool for generating plausible hypotheses when the symbolic system's knowledge is incomplete.

In this model, the symbolic HTN planner can be conceptualized as the "conductor" of an orchestra. It is responsible for maintaining the overall structure of the plan, ensuring that all actions are logically consistent with the world state, and verifying that all preconditions are met and effects are correctly applied. Its operation is governed by the strict, formal rules of the domain model—the "sheet music."

The LLM, in contrast, acts as a world-class "improviser." When the conductor reaches a point in the score where the music is missing—that is, when the planner encounters a compound task for which it has no predefined method—it can turn to the improviser. The LLM, drawing upon its vast training and implicit understanding of countless procedures, can generate a novel sequence of actions—a plausible "solo"—to bridge the gap. However, before this improvisation is accepted into the final performance, the conductor reasserts control, using its formal knowledge to ensure the solo fits harmonically and rhythmically with the rest of the piece. This is the role of the verifier task: to check that the LLM's flexible, creative output is sound and correct within the planner's logical world.

### 4.2 System Components

The architecture consists of three primary, interconnected modules that work in concert to achieve this dynamic planning capability.

- **The Symbolic HTN Planner Core:** This is the foundational component of the system. It is a standard HTN planner, such as one based on the PyHop algorithm.3 Its responsibilities include maintaining the current world state as a set of ground predicates, managing the list of tasks to be accomplished, and executing the main planning loop. It processes tasks by applying known methods from its knowledge base to decompose compound tasks and applying operators to execute primitive tasks.
    
- **The Knowledge Gap Detector:** This module is integrated directly into the planner's main control loop. Its function is to identify the specific failure condition that signals a need for external knowledge. A "knowledge gap" is formally declared when the task at the head of the planner's task list is a compound task, and after iterating through the entire library of known methods, no method is found to be applicable in the current state. This trigger is precise and unambiguous, ensuring that the LLM is only invoked when absolutely necessary.
    
- **The LLM Query Engine:** This is the bridge between the symbolic and neural components. When a knowledge gap is detected, this module is activated. Its responsibilities are threefold:
    
    1. **Prompt Construction:** It dynamically assembles a detailed, context-rich prompt to send to the LLM.
        
    2. **API Communication:** It handles the technical details of sending the query to the LLM's API and receiving the response.
        
    3. **Response Parsing:** It processes the unstructured, natural language text returned by the LLM and parses it into a structured, machine-readable format—specifically, a list of primitive task instances that can be injected back into the symbolic planner's task list.
        

### 4.3 The Dynamic Planning Cycle

The interplay between these components can be best understood by walking through a concrete example, such as the logistics transportation problem described in the `ChatHTN` work.1

1. **Initial Task:** The symbolic planner is initialized with the state and the initial task `transportPackage(pck, src, dest)`.
    
2. **Symbolic Decomposition:** The planner finds a known method for `transportPackage`, which decomposes it into a sequence of subtasks: `truckTransport(pck, src, ap1)`, `planeTransport(pck, ap1, ap2)`, and `truckTransport(pck, ap2, dest)`.
    
3. **Successful Sub-Task:** The planner processes the first task, `truckTransport`. It finds a valid method in its knowledge base, decomposes it into primitive tasks (`loadTruck`, `drive`, `unloadTruck`), and successfully simulates their execution, updating its internal state.
    
4. **Knowledge Gap Detected:** The planner now moves to the next task, `planeTransport(pck, ap1, ap2)`. It searches its method library but finds no applicable method for this task in the current state. The Knowledge Gap Detector is triggered.
    
5. **LLM Query:** The LLM Query Engine is invoked. It constructs a prompt that includes:
    
    - **The Goal:** "Generate a sequence of primitive tasks to achieve the compound task `planeTransport(pck, ap1, ap2)`."
        
    - **Task Semantics:** "The preconditions are `at(pck, ap1)` and `airport(ap1)`, and the effects are `at(pck, ap2)`."
        
    - **Current State:** A summary of relevant predicates, such as `at(plane1, ap1)`.
        
    - **Available Actions:** A list of all known primitive task names and their parameters (e.g., `loadPlane(?plane,?pkg,?loc)`, `fly(?plane,?from,?to)`, etc.).
        
6. **LLM Response and Parsing:** The LLM returns a natural language response, such as: "To transport the package by plane, you should: 1. Load the package onto the plane. 2. Fly the plane to the destination airport. 3. Unload the package from the plane." The parser converts this into a formal list: `[loadPlane(plane1, pck, ap1), fly(plane1, ap1, ap2), unloadPlane(plane1, pck, ap2)]`.
    
7. **Injection and Verification:** The planner injects this new sub-plan into its main task list. Crucially, it also appends a dynamically generated verifier task, `planeTransport_verifier`, immediately after the sequence.
    
8. **Resumption of Symbolic Planning:** The symbolic planner resumes its normal operation. It executes `loadPlane`, `fly`, and `unloadPlane`, updating its state at each step. It then encounters `planeTransport_verifier` and checks its preconditions. If the LLM's plan was correct, the state will now satisfy `at(pck, ap2)`, the verifier task will succeed, and planning will continue with the final `truckTransport` task. If the LLM's plan was flawed, the verifier's preconditions will not be met, and this entire planning branch will fail, correctly preventing an unsound plan from being generated.
    

### 4.4 Maintaining Soundness: The Verifier Task Mechanism

The verifier task is the cornerstone of the framework's ability to guarantee plan soundness. It provides a formal mechanism for "symbolic grounding" of the LLM's output, bridging the gap between the model's plausible linguistic narrative and the planner's rigorous, logical world model.1

An LLM's response is not a sequence of formal operations but a textual suggestion. The planner cannot inherently trust that this suggestion will produce the desired outcome. The verifier task resolves this by translating the LLM's implicit claim into an explicit, testable hypothesis within the symbolic system.

Formally, for any compound task `c` with a defined set of effects `eff(c)`, a verifier task `c_ver` is a primitive task whose corresponding operator is defined as follows:

- **Name:** `c_ver`
    
- **Preconditions:** `eff(c)`
    
- **Effects:** `∅` (empty)
    

When the symbolic planner attempts to execute the `c_ver` operator, it performs its standard, sound precondition check. It rigorously evaluates whether the predicates in `eff(c)` are true in its internal world state, which has been updated by the execution of the LLM-generated primitive actions. If and only if the check succeeds does the planner proceed. This mechanism effectively co-opts the trusted, logical machinery of the symbolic planner to act as a validator for the untrusted, generative output of the neural model. This "propose-then-verify" pattern is a powerful and generalizable strategy for safely integrating any powerful but unreliable generative system into a framework that requires formal guarantees. It cleanly separates the creative, hypothesis-generating process from the critical, hypothesis-testing process, leveraging the best of both the neural and symbolic worlds.

---

## **5. Theoretical Framework and Formalism**

To establish the proposed architecture on a rigorous foundation, this section extends the standard formalism of HTN planning to explicitly account for the integration of a Large Language Model. We define the new neuro-symbolic planning problem, formalize the key concepts of on-demand methods and verifier tasks, and analyze the theoretical properties of the resulting framework, particularly its soundness and completeness.

### 5.1 Formal Definition of the Neuro-Symbolic Planning Problem

A standard HTN planning problem is formally defined by the tuple P=(s0​,w0​,D), where s0​ is the initial state, w0​ is the initial task network, and D is the planning domain. The domain D=(O,M) consists of a set of operators O for primitive tasks and a set of methods M for compound tasks.1

We extend this definition to create the Neuro-Symbolic HTN planning problem, PNS​, by incorporating the LLM as a formal component of the problem definition:

PNS​=(s0​,w0​,D,LLM)

Here, the new component, LLM, is a function that represents the generative capability of the Large Language Model. This function takes the current state s∈S and a compound task c∈C as input and returns a potential task network, tn′, which is a candidate decomposition for c:

LLM:S×C→TN![](data:image/svg+xml;utf8,<svg%20xmlns="http://www.w3.org/2000/svg"%20width="100%"%20height="0.286em"%20viewBox="0%200%201033%20286"%20preserveAspectRatio="none"><path%20d="M344%2055.266c-142%200-300.638%2081.316-311.5%2086.418
-8.01%203.762-22.5%2010.91-23.5%205.562L1%20120c-1-2-1-3-1-4%200-5%203-9%208-10l18.4-9C160.9
%2031.9%20283%200%20358%200c148%200%20188%20122%20331%20122s314-97%20326-97c4%200%208%202%2010%207l7%2021.114
c1%202.14%201%203.21%201%204.28%200%205.347-3%209.626-7%2010.696l-22.3%2012.622C852.6%20158.372%20751
%20181.476%20676%20181.476c-149%200-189-126.21-332-126.21z"></path></svg>)

where S is the set of all states, C is the set of compound tasks, and TN![](data:image/svg+xml;utf8,<svg%20xmlns="http://www.w3.org/2000/svg"%20width="100%"%20height="0.286em"%20viewBox="0%200%201033%20286"%20preserveAspectRatio="none"><path%20d="M344%2055.266c-142%200-300.638%2081.316-311.5%2086.418
-8.01%203.762-22.5%2010.91-23.5%205.562L1%20120c-1-2-1-3-1-4%200-5%203-9%208-10l18.4-9C160.9
%2031.9%20283%200%20358%200c148%200%20188%20122%20331%20122s314-97%20326-97c4%200%208%202%2010%207l7%2021.114
c1%202.14%201%203.21%201%204.28%200%205.347-3%209.626-7%2010.696l-22.3%2012.622C852.6%20158.372%20751
%20181.476%20676%20181.476c-149%200-189-126.21-332-126.21z"></path></svg>) is the set of all possible task networks. The output of the LLM function is probabilistic and not guaranteed to be a valid or sound decomposition. It serves as a source of candidate methods that are not present in the explicitly defined method set M.

### 5.2 Extending the HTN Formalism

To accommodate the output of the LLM function within the symbolic planning process, we introduce two new formal concepts.

#### On-Demand Methods

An "on-demand method," denoted as mLLM​, is a method that is not part of the initial method set M but is generated dynamically by the LLM function during the planning process. When the planner encounters a compound task c in state s for which no applicable method exists in M, it invokes the LLM function to generate a candidate task network, tn′=LLM(s,c). This generated task network tn′ is then treated as the body of a new, temporary method mLLM​=(c,tn′). This allows the planner to use its standard decomposition mechanism on a method that was created just-in-time, effectively expanding the domain knowledge D at runtime.

#### Verifier Tasks Formalized

To ensure the logical soundness of plans that incorporate on-demand methods, we formalize the verifier task mechanism. For every compound task c that has a defined set of effects, eff(c), we can define a corresponding verifier task, cver​. This verifier task is a primitive task, and its associated operator, over​, is formally defined as:

over​=(name(cver​),preconditions:eff(c),add-effects:∅,delete-effects:∅)

The critical feature of this operator is that its preconditions are precisely the intended effects of the compound task it is verifying. Since it has no effects of its own, its sole purpose is to act as a logical checkpoint. When the planner attempts to apply over​, it must verify that all predicates in eff(c) are true in the current state. If they are not, the operator is not applicable, and the planning branch fails.

### 5.3 Properties of the Framework

With these formalisms in place, we can analyze the theoretical properties of the GPT-HTN-Refine framework.

#### Soundness

A planning system is sound if any plan it returns is guaranteed to be a valid solution to the problem. The proposed neuro-symbolic framework is provably sound.

**Proof Outline:** The proof of soundness rests on two pillars: (1) the inherent soundness of the underlying symbolic HTN planner's state progression and precondition checking, and (2) the mandatory inclusion of a verifier task for every decomposition generated by the LLM.

Let π be a plan returned by the GPT-HTN-Refine algorithm for a problem PNS​. The plan π is a sequence of primitive actions. For any sub-sequence of actions in π that was generated by an on-demand method mLLM​ for a compound task c, the algorithm ensures that this sub-sequence is immediately followed by the execution of the operator over​ for the verifier task cver​.1

The symbolic planner will only successfully execute over​ if its preconditions, which are defined to be eff(c), are satisfied in the state resulting from the execution of the LLM-generated sub-sequence. Therefore, the successful execution of the complete plan π implies that for every LLM-generated decomposition, the intended effects of the corresponding compound task were verifiably achieved. All other actions in the plan originate from the sound methods in M and are processed by the sound symbolic planner. Thus, the entire plan is a valid, executable sequence that correctly achieves the initial task network, and the framework is sound.

#### Completeness

A planning system is complete if it is guaranteed to find a solution whenever one exists. The proposed framework is **not** complete.

This lack of completeness stems from two sources. First, the framework inherits the potential incompleteness of its underlying symbolic planner. Many practical HTN planners, such as those based on the SHOP or PyHop algorithms, employ a depth-first search strategy and do not perform exhaustive exploration of the search space. They may enter infinite recursive loops or commit to a failing decomposition path when an alternative successful path exists, and thus are not complete.1

Second, the LLM component introduces an additional source of incompleteness. The LLM's output is probabilistic and non-deterministic. Even if a perfectly valid decomposition for a compound task exists, there is no guarantee that the LLM will generate it on any given query. It may fail to produce a response, generate an incorrect or nonsensical sequence of actions, or produce a valid decomposition on one attempt but not on another.

While full completeness is not achievable, the practical implementation of the framework can include mechanisms to mitigate some sources of incompleteness. For instance, as suggested by the `ChatHTN` implementation, the planner can track previously visited (state, task) pairs. If such a pair is encountered again, it indicates a potential loop, and the algorithm can prune that search branch, preventing some infinite recursions that might be introduced by a faulty LLM decomposition.1

---

## **6. Algorithm Design and Analysis: The GPT-HTN-Refine Algorithm**

This section presents the technical core of the thesis: the design and analysis of the **GPT-HTN-Refine** algorithm. This algorithm operationalizes the neuro-symbolic architecture described in Section 4, providing a concrete procedure for interleaving symbolic HTN planning with on-demand LLM-driven method generation. We present the pseudocode for the main algorithm and its key sub-procedure, followed by an analysis of its computational complexity and plan quality.

### 6.1 Algorithm Pseudocode

The GPT-HTN-Refine algorithm is realized through a recursive procedure, `Seek_Plan_Refined`, which extends a standard HTN planning search. The algorithm manages a state, a list of tasks to accomplish, and the plan generated so far. Its structure is heavily inspired by the `chatSeekPlan` procedure 1, adapted to formalize the concepts of on-demand method generation and verification.

**Algorithm 1: The GPT-HTN-Refine Algorithm**

```
1: function GPT_HTN_REFINE(initial_state, initial_tasks)
2:   return Seek_Plan_Refined(initial_state, initial_tasks, empty_plan)
3: end function
4:
5: function Seek_Plan_Refined(state, tasks, plan)
6:   if tasks is empty then
7:     return plan
8:   end if
9:
10:  t_0 ← first task in tasks
11:  remaining_tasks ← rest of tasks
12:
13:  if t_0 is a primitive task then
14:    operator ← get_operator(t_0)
15:    if operator is applicable in state then
16:      new_state ← apply_operator(state, operator)
17:      return Seek_Plan_Refined(new_state, remaining_tasks, plan + [t_0])
18:    else
19:      return failure
20:    end if
21:  end if
22:
23:  if t_0 is a compound task then
24:    applicable_methods ← find_applicable_methods(t_0, state)
25:    for each method m in applicable_methods do
26:      subtasks ← get_subtasks(m)
27:      verifier_task ← create_verifier_task(t_0)
28:      new_tasks ← subtasks + [verifier_task] + remaining_tasks
29:      solution ← Seek_Plan_Refined(state, new_tasks, plan)
30:      if solution is not failure then
31:        return solution
32:      end if
33:    end for
34:
35:    // Knowledge Gap: No symbolic methods found, query LLM
36:    llm_subtasks ← LLM_Generate_Method(state, t_0)
37:    if llm_subtasks is not failure then
38:      verifier_task ← create_verifier_task(t_0)
39:      new_tasks ← llm_subtasks + [verifier_task] + remaining_tasks
40:      solution ← Seek_Plan_Refined(state, new_tasks, plan)
41:      if solution is not failure then
42:        return solution
43:      end if
44:    end if
45:  end if
46:
47:  return failure
48: end function
```

The algorithm proceeds as follows:

- **Lines 6-8:** The base case for the recursion. If the task list is empty, the plan is complete and is returned.
    
- **Lines 13-21:** If the current task `t_0` is primitive, the algorithm checks if its operator is applicable. If so, it updates the state, adds the action to the plan, and recurses on the remaining tasks. If not, this branch of the search fails.
    
- **Lines 23-33:** If `t_0` is compound, the algorithm first attempts a symbolic solution. It iterates through all known methods in the domain knowledge. For each applicable method, it constructs a new task list containing the method's subtasks, the crucial `verifier_task`, and the remaining tasks. It then recurses. If any of these recursive calls return a valid solution, it is immediately returned.
    
- **Lines 35-44:** This is the neuro-symbolic extension. If the loop over symbolic methods completes without finding a solution, a "knowledge gap" is identified. The algorithm then calls the `LLM_Generate_Method` procedure. If the LLM successfully returns a list of subtasks, they are injected into the task list, along with a verifier task, and the search continues.
    
- **Line 47:** If both symbolic and LLM-based attempts fail, the function returns failure, causing the planner to backtrack.
    

### 6.2 The `LLM_Generate_Method` Procedure

This sub-procedure encapsulates the interaction with the Large Language Model. Its design is critical for eliciting useful and correct decompositions from the LLM.

**Algorithm 2: The LLM_Generate_Method Procedure**

```
1: function LLM_Generate_Method(state, compound_task)
2:   prompt ← Construct_LLM_Prompt(state, compound_task)
3:   response_text ← Query_LLM_API(prompt)
4:   parsed_tasks ← Parse_LLM_Response(response_text)
5:
6:   if parsed_tasks is valid then
7:     return parsed_tasks
8:   else
9:     return failure
10:  end if
11: end function
12:
13: function Construct_LLM_Prompt(state, compound_task)
14:   // 1. Define the role and goal
15:   prompt ← "You are an expert AI planning assistant. Your task is to decompose a high-level task into a sequence of primitive, executable actions."
16:
17:   // 2. Describe the task to be decomposed
18:   prompt += "Decompose the following compound task: " + name(compound_task)
19:   prompt += "Preconditions for this task are: " + preconditions(compound_task)
20:   prompt += "Expected effects upon completion are: " + effects(compound_task)
21:
22:   // 3. Provide the context (current state)
23:   prompt += "The current state of the world includes: " + relevant_predicates(state)
24:
25:   // 4. List the available tools (primitive actions)
26:   prompt += "You can only use the following primitive actions: " + list_all_operators()
27:
28:   // 5. Specify the output format
29:   prompt += "Provide the decomposition as a numbered list of actions with their parameters. Do not add any other explanation."
30:
31:  return prompt
32: end function
```

The key steps in this procedure are:

- **Prompt Construction:** As detailed in `Construct_LLM_Prompt`, a highly structured prompt is assembled. Providing comprehensive context is crucial for guiding the LLM's generation process.1 This includes not just the task to be decomposed, but also its formal semantics (preconditions and effects), the relevant parts of the current world state, and a complete list of the available primitive actions. Specifying the exact output format minimizes the complexity of the parsing step.
    
- **Response Parsing and Validation:** After receiving the raw text response from the LLM, a parser (e.g., using regular expressions) attempts to extract a sequence of primitive task instances. This step is critical for robustness. The parser must validate that each extracted task name corresponds to a known primitive operator in the domain and that the number of arguments is correct. If the response is malformed or contains non-existent actions, the procedure fails, preventing invalid plans from entering the search space.
    

### 6.3 Analysis of Computational Complexity

The computational complexity of the GPT-HTN-Refine algorithm is a hybrid of its symbolic and neural components.

- **Symbolic Complexity:** In the worst case, the symbolic search space of HTN planning can be undecidable if recursion is allowed, and EXPTIME-complete for decidable fragments like propositional TIHTN planning.1 The search involves exploring a tree of possible decompositions, where the branching factor is determined by the number of applicable methods for each compound task.
    
- **Neural Complexity:** The cost of an LLM inference is not directly tied to the combinatorial complexity of the planning problem's state space. Instead, it is primarily a function of the length of the input prompt and the generated output (completion). While a single API call can be computationally expensive and introduce latency, it is a constant-time operation with respect to the size of the search tree.
    

The overall complexity is therefore a trade-off. By invoking the LLM, the algorithm can potentially prune vast sections of the symbolic search tree. If the LLM provides a correct decomposition for a task that would have otherwise required the symbolic planner to explore thousands of failing branches, the total time to find a solution can be drastically reduced. Conversely, if the LLM repeatedly provides incorrect decompositions, the cost of these failed API calls adds significant overhead to the planning process.

### 6.4 Analysis of Plan Quality and Robustness

The plans generated by GPT-HTN-Refine have unique properties when compared to both purely symbolic and purely neural planners.

- **Robustness to Incomplete Knowledge:** The framework's primary advantage is its robustness. A standard HTN planner with an incomplete method library is brittle; it will fail on any problem that requires a missing method. GPT-HTN-Refine, by contrast, can potentially solve such problems by dynamically generating the missing knowledge, making it far more resilient to incomplete domain models.1
    
- **Guaranteed Soundness:** Compared to LLM-only planners (like ReAct or Plan-and-Execute), the framework provides a formal guarantee of soundness.1 Purely LLM-based approaches often generate plans that are semantically plausible but logically flawed, containing hallucinated actions or failing to satisfy preconditions. The verifier task mechanism of GPT-HTN-Refine eliminates this risk, ensuring that any returned plan is executable and correct with respect to the symbolic domain model.
    
- **Plan Optimality:** The framework does not guarantee plan optimality. Like most standard HTN planners, it performs a depth-first search and typically returns the first solution it finds.3 The decompositions provided by the LLM are generated based on plausibility and commonsense, not on an optimality criterion such as plan length or cost. Therefore, while the generated plans are correct, they may not be the most efficient solutions possible.
    

---

## **7. Practical Implementation: Tools, Steps, and Alternatives**

Translating the theoretical GPT-HTN-Refine framework into a working system requires selecting appropriate tools and following a clear implementation roadmap. This section provides a practical guide for building a prototype, justifying the choice of core technologies, detailing the implementation steps, and discussing viable alternatives and extensions.

### 7.1 Core Toolkit Selection and Justification

The selection of the right tools is crucial for a successful implementation, especially for a bachelor's thesis project where simplicity and ease of integration are paramount.

#### HTN Planner: PyHop

For the symbolic planner core, **PyHop** is the recommended choice.3

- **Justification:**
    
    - **Language Synergy:** PyHop is written entirely in Python, the de facto standard language for machine learning and interacting with LLM APIs. This eliminates the need for cross-language wrappers or complex inter-process communication, allowing for seamless integration of the LLM query engine directly into the planner's code.4
        
    - **Simplicity and Intelligibility:** The core PyHop planner is famously concise, comprising less than 150 lines of code.4 This simplicity makes it an ideal pedagogical tool and a perfect foundation for a research prototype. The focus can remain on the novel neuro-symbolic contributions rather than on deciphering a complex, monolithic planning system.6
        
    - **Ease of Modification:** In PyHop, states, operators, and methods are all represented as standard Python objects and functions.4 This makes it trivial to modify the core planning loop to detect knowledge gaps and inject new tasks generated by the LLM.
        

#### LLM Integration: Python API Libraries

For interacting with Large Language Models, standard Python libraries provide a robust and straightforward interface.

- **OpenAI API (GPT series):** The official `openai` Python library is the standard for accessing models like GPT-4o.
    
    - **Implementation:** The process involves obtaining an API key, setting it as an environment variable for security, and using the `OpenAI` client to make API calls. The primary function is `client.chat.completions.create`, which takes a `model` name and a list of `messages` as input. The `messages` list follows a conversational structure with specified roles ("system", "user", "assistant") to provide context and instructions to the model.7
        
- **Meta API (Llama series):** For open-source models like Llama 3, Meta provides the `llama-api-client` library.
    
    - **Implementation:** The usage pattern is very similar to the OpenAI library. After setting an API key, the `LlamaAPIClient` is initialized. The `client.chat.completions.create` method is used to send requests, also taking a `model` name and a list of `messages` with "role" and "content" keys.11 This similarity makes it relatively easy to design the system to be model-agnostic.
        

### 7.2 Step-by-Step Implementation Guide

The following steps outline the process of modifying PyHop to implement the GPT-HTN-Refine algorithm, using the logistics domain as a running example.

Step 1: Define the Base HTN Domain in PyHop

First, define the known operators and methods using Python functions as required by PyHop. The domain will be intentionally incomplete. For instance, define operators for load-truck, drive-truck, unload-truck, and a method for truck-transport, but omit any method for plane-transport.2

Step 2: Modify the Planner Loop to Detect Knowledge Gaps

The core of the integration lies in modifying PyHop's main recursive search function (often called seek_plan or pyhop). The modification involves checking the result of the search for applicable methods.

Python

```
# Inside the modified seek_plan function
task_name, *task_args = tasks
if task_name in state.methods:
    # Original PyHop logic: find and apply a symbolic method
    #...
else:
    # Knowledge Gap Detected: No methods found for this compound task
    # This is where the call to the LLM will be triggered
    llm_subtasks = llm_generate_method(state, tasks)
    if llm_subtasks:
        #... proceed with the new subtasks...
```

Step 3: Implement the Prompt Engineering Function

Create a dedicated Python function to construct the detailed prompt for the LLM. This function will dynamically assemble the string based on the current state and the task that needs decomposition.

Python

```
def construct_llm_prompt(state, task):
    # Extract task name, preconditions, effects, etc., from domain definitions
    # Format them into a clear, structured prompt as detailed in Algorithm 2
    #...
    return formatted_prompt
```

Step 4: Implement the LLM Query and Response Parser

Write a function that handles the API call and parses the result. This function will call the function from Step 3, send the prompt to the chosen LLM API, and then process the text response.

Python

```
import openai

def llm_generate_method(state, task):
    prompt = construct_llm_prompt(state, task)
    client = openai.OpenAI() # Assumes API key is in environment variables
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    response_text = response.choices.message.content
    # Use regex or string splitting to parse response_text
    # into a list of tuples, e.g., [('load_plane', 'p1', 't1'),...]
    parsed_tasks = parse_llm_response(response_text)
    return parsed_tasks
```

Step 5: Dynamic Task and Verifier Injection

Finally, modify the planner loop from Step 2 to handle the output from the LLM. This involves creating the verifier task and inserting the new sequence of tasks into the planner's agenda.

Python

```
# Inside the modified seek_plan function, in the 'else' block
llm_subtasks = llm_generate_method(state, tasks)
if llm_subtasks:
    # Create the verifier task
    verifier_task_name = f"{task_name}_verifier"
    # (Assume verifier operators are pre-defined or dynamically created)
    verifier_task = (verifier_task_name, *task_args)

    # Prepend the new tasks to the remaining tasks
    new_tasks = llm_subtasks + [verifier_task] + tasks[1:]
    return seek_plan(state, new_tasks, plan)
```

### 7.3 Alternatives and Extensions

While the proposed toolkit is ideal for a prototype, several alternatives and extensions can be considered for more advanced implementations or future work.

- **Alternative Planners:** For domains requiring more complex features like partial ordering of tasks or advanced numeric and temporal reasoning, a more powerful planner like **SHOP2** would be a better choice.14 SHOP2 is a highly influential, feature-rich HTN planner. While its original implementation is in LISP, a Java port,
    
    **JSHOP2**, is available and might be more accessible.16 However, integrating with JSHOP2 from Python would require more complex engineering, possibly involving inter-process communication, which could add significant overhead to the project.
    
- **Local LLM Inference:** Relying on commercial APIs for LLMs can be costly and introduce latency. For many applications, especially those requiring privacy or low-latency responses, running an LLM locally is a superior alternative. Frameworks like **Ollama** and libraries from **Hugging Face Transformers** make it increasingly feasible to run powerful open-source models like Llama 3 on local hardware.18 Interacting with a local Ollama server from Python is straightforward and involves making requests to a local API endpoint, closely mirroring the code structure used for commercial APIs.19
    
- **Complementary Strategies for Knowledge Gaps:** The neuro-symbolic approach can be combined with other techniques for handling incomplete domain knowledge. For example, the framework could be extended to incorporate the ideas of task insertion with preferences from.1 In such a hybrid system, the planner could first attempt to solve a knowledge gap using symbolic task insertion. Only if that fails would it resort to the more computationally expensive LLM query. This would create a tiered system for addressing incompleteness, prioritizing cheaper, formal methods before invoking the powerful but costly neural component.
    

---

## **8. Conclusion and Future Directions**

This thesis has presented a comprehensive framework for a neuro-symbolic Hierarchical Task Network planning system designed to address one of the most enduring challenges in automated planning: the knowledge engineering bottleneck. By strategically interleaving the sound, formal reasoning of a symbolic planner with the flexible, on-demand procedural knowledge generation of a Large Language Model, the proposed GPT-HTN-Refine algorithm offers a path toward more robust, adaptable, and practical planning systems.

### 8.1 Summary of Contributions

The primary contribution of this work is the design, formalization, and practical implementation roadmap for a sound neuro-symbolic HTN planning framework. The system dynamically mitigates the knowledge engineering bottleneck by treating the LLM as a runtime-extensible knowledge base. When faced with an unknown compound task, the planner queries the LLM for a plausible decomposition. Crucially, the introduction of a formal "verifier task" mechanism ensures that any LLM-generated sub-plan is rigorously validated by the symbolic planner's own logic, guaranteeing the soundness of the final plan. This "propose-then-verify" architecture successfully harnesses the generative power of LLMs to overcome knowledge gaps without sacrificing the logical correctness essential for reliable automated planning. The result is a system that can solve a broader class of problems than a symbolic planner with an incomplete domain model, while providing the correctness guarantees that purely LLM-based planners lack.

### 8.2 Limitations

Despite its strengths, the proposed framework has several inherent limitations that must be acknowledged.

- **Dependence on LLM Quality and Reliability:** The framework's ability to overcome knowledge gaps is fundamentally contingent on the quality of the LLM's output. The generation of a correct and relevant task decomposition is not guaranteed. A weak, poorly prompted, or uncooperative LLM may produce nonsensical, incorrect, or irrelevant action sequences, which would cause the verifier task to fail and ultimately lead to planning failure. The system is robust to _incorrect_ LLM outputs (it will not produce an unsound plan), but it cannot recover from an LLM's _inability_ to produce a correct output.
    
- **Lack of Plan Optimality:** The framework prioritizes soundness and solvability over optimality. Standard HTN planners like PyHop typically perform a depth-first search and return the first valid plan they find, without any guarantee that it is optimal in terms of length, cost, or any other metric.3 The decompositions generated by the LLM are based on semantic plausibility, not on a formal cost model. Therefore, the resulting plans, while correct, may be less efficient than those produced by planners designed specifically for optimal planning.
    
- **Sensitivity to Prompt Engineering:** The performance of the LLM Query Engine is highly sensitive to the quality and structure of the prompt provided to the LLM.7 Crafting a prompt that effectively communicates the task, its context, and the required output format is a non-trivial engineering challenge that may require significant tuning and experimentation for each new domain.
    

### 8.3 Future Work

The framework presented in this thesis opens up several promising avenues for future research, aiming to build more intelligent, efficient, and interactive planning systems.

- **Learning and Caching of Generated Methods:** A significant extension would be to enable the system to learn from its successful interactions with the LLM. When an LLM-generated decomposition is successfully executed and verified, the system could automatically formalize this decomposition into a new, permanent symbolic method and add it to its knowledge base.1 This would create a learning loop where the planner becomes more competent over time. Subsequent encounters with the same compound task could then be solved efficiently using the newly learned symbolic method, reducing reliance on expensive and time-consuming LLM API calls and effectively amortizing the cost of knowledge acquisition.
    
- **Interactive Refinement and Human-in-the-Loop Planning:** The current framework is fully autonomous, but it could be extended to incorporate a human user into the planning loop. Inspired by systems for interactive task learning 1, if the LLM generates a decomposition that is flawed or sub-optimal, the system could present it to a human expert for review and correction. The user could then edit, reorder, or replace subtasks in the proposed decomposition. This interactive refinement process would combine the rapid generation capabilities of the LLM, the formal verification of the symbolic planner, and the deep domain expertise of a human user, leading to a highly collaborative and effective planning process.
    
- **Extension to Probabilistic and Multi-Agent Domains:** The core neuro-symbolic principle of "propose-then-verify" could be adapted to more complex planning paradigms. In probabilistic planning, an LLM could be used to propose plausible outcomes or recovery strategies for actions with uncertain effects, which a symbolic model checker could then verify. In multi-agent planning, an LLM could generate communication or coordination protocols for a team of agents to achieve a joint task, with each agent's individual planner then verifying the feasibility and soundness of its part of the collaborative plan. Exploring these extensions would push the boundaries of neuro-symbolic reasoning into domains characterized by uncertainty and complex agent interactions.