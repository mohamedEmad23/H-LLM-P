## ADDED Requirements

### Requirement: Persistent Shared Memory Layer

The system SHALL provide a persistent, shared memory layer (Memory Management System - MMS) that serves as the single source of truth for world state, accessible to all agents in the multi-agent HTN planning system.

#### Scenario: Orchestrator queries current world state
- **WHEN** the Orchestrator needs to check preconditions for an HTN method
- **THEN** it SHALL call `mms.query_state(clues)` with structured clues
- **AND** the MMS SHALL return the requested state information from the database
- **AND** the response SHALL be used to evaluate precondition logic

#### Scenario: Worker agent reports action completion
- **WHEN** a Worker Agent successfully executes a primitive action
- **THEN** it SHALL report the action outcome to the Orchestrator
- **AND** the Orchestrator SHALL call `mms.update_state(changes)` to persist the state transition
- **AND** the update SHALL be atomic to ensure consistency

#### Scenario: Multiple agents coordinate via shared state
- **WHEN** Agent A moves a disk and Agent B needs to access the same peg
- **THEN** Agent B SHALL query the MMS for current peg state before acting
- **AND** the MMS SHALL return the updated state reflecting Agent A's action
- **AND** no stale or conflicting state information SHALL be used

### Requirement: Structured Memory Types

The MMS SHALL implement four distinct memory types, each stored in a separate database table with well-defined semantics.

#### Scenario: Short-term memory stores dynamic world state
- **WHEN** a disk position changes during Tower of Hanoi execution
- **THEN** the change SHALL be stored in the `short_term_memory` table
- **AND** the entry SHALL use a key format like `disk_3_position` with value `peg_C`
- **AND** short-term memory SHALL be cleared at the start of each new problem instance

#### Scenario: Long-term memory stores past plans for reuse
- **WHEN** a problem is successfully solved
- **THEN** the complete plan SHALL be stored in the `long_term_memory` table
- **AND** the plan SHALL be indexed by a problem hash (e.g., `hanoi_n4_k3`)
- **AND** future similar problems SHALL query long-term memory for reusable plans

#### Scenario: Rules memory stores agent capabilities
- **WHEN** the system needs to determine which agent can perform an action
- **THEN** it SHALL query the `rules_memory` table for capability entries
- **AND** rules SHALL use structured JSON format: `{"agent":"red", "action":"traverse", "color":"red"}`
- **AND** rules memory SHALL be static (loaded at initialization, not modified during execution)

#### Scenario: Entity memory tracks object properties
- **WHEN** the planner needs to know the size of a disk
- **THEN** it SHALL query the `memory_entities` table for the disk's properties
- **AND** the entity SHALL have a unique ID (e.g., `disk_4`) and a properties JSON blob
- **AND** entity properties SHALL be immutable within a problem instance

### Requirement: MemoRAG-Inspired Clue Generation

The Orchestrator SHALL translate complex HTN preconditions into structured "clues" that enable precise, context-aware queries to the MMS.

#### Scenario: Precondition translated to multiple clues
- **WHEN** checking if a tower of size N can move to peg B
- **THEN** the Orchestrator SHALL generate clues: `["current_disks_on_peg(B)", "constraint_peg_b(max_size)", "disk_sizes([tower])"]`
- **AND** the Query Builder SHALL convert clues to SQL queries
- **AND** the MMS SHALL execute queries and return aggregated results
- **AND** the Orchestrator SHALL evaluate precondition based on aggregated data

#### Scenario: Multi-hop reasoning for strategic planning
- **WHEN** solving Level 5 N-Peg Time-Limited Hanoi requiring meta-planning
- **THEN** the Orchestrator SHALL query rules memory for Frame-Stewart algorithm formula
- **AND** SHALL query entity memory for disk counts and peg constraints
- **AND** SHALL formulate a strategic plan based on retrieved knowledge
- **AND** clues SHALL enable reasoning across multiple memory tables

### Requirement: Plan Reuse via Semantic Retrieval

The MMS SHALL support querying long-term memory for similar previously solved problems, enabling plan reuse to accelerate planning.

#### Scenario: Retrieve plan for similar problem
- **WHEN** the Orchestrator receives a new Tower of Hanoi problem (N=4, K=3 pegs)
- **THEN** it SHALL compute a problem hash and query long-term memory
- **AND** if a matching or similar plan exists, it SHALL be returned
- **AND** the Orchestrator SHALL attempt to adapt the retrieved plan to the current state
- **AND** if adaptation fails, it SHALL fall back to planning from scratch

#### Scenario: No matching plan found
- **WHEN** querying long-term memory for a novel problem
- **THEN** the MMS SHALL return an empty result
- **AND** the Orchestrator SHALL proceed with normal HTN decomposition
- **AND** the successful plan SHALL be stored for future reuse

#### Scenario: Semantic retrieval with AutoRAG optimization
- **WHEN** using semantic similarity (beyond exact hash matching)
- **THEN** the MMS SHALL use an AutoRAG-optimized embedding model and retrieval strategy
- **AND** the retrieval SHALL be benchmarked for accuracy and latency
- **AND** results SHALL be documented in the thesis performance section

### Requirement: Error Pattern Learning

The MMS SHALL store failed plans with failure reasons, enabling the system to learn from errors and avoid repeating mistakes.

#### Scenario: Failed plan stored with reason
- **WHEN** an HTN plan execution fails (e.g., precondition violated, operator failed)
- **THEN** the Orchestrator SHALL log the failure to long-term memory
- **AND** the entry SHALL include: problem hash, attempted plan, failure point, reason
- **AND** future planning SHALL query for past failures to avoid known bad strategies

#### Scenario: Avoid repeating known failed approach
- **WHEN** planning for a problem with recorded failures
- **THEN** the Orchestrator SHALL query long-term memory for failed plans
- **AND** SHALL exclude methods/operators that previously failed for similar preconditions
- **AND** this SHALL improve success rate over time through continuous learning

### Requirement: Atomic State Updates and Consistency

The MMS SHALL ensure that all state updates are atomic and maintain consistency across concurrent or sequential agent operations.

#### Scenario: State update is atomic
- **WHEN** the Orchestrator calls `mms.update_state(changes)` with multiple field updates
- **THEN** ALL changes SHALL be applied in a single database transaction
- **AND** if any part of the update fails, the entire transaction SHALL be rolled back
- **AND** the world state SHALL remain consistent (no partial updates)

#### Scenario: Prevent race conditions in multi-agent scenario
- **WHEN** two agents could theoretically update related state simultaneously
- **THEN** the MMS SHALL serialize updates (only one transaction at a time)
- **AND** agents SHALL receive the most recent committed state on every query
- **AND** no agent SHALL act on stale or inconsistent state

### Requirement: MMS API for Agent Integration

The MMS SHALL expose a high-level API with methods for querying and updating memory, abstracting database implementation details from agents.

#### Scenario: Query state with structured clues
- **WHEN** an agent calls `mms.query_state(clues=["current_disks_on_peg(A)", "disk_sizes([1,2,3])"])`
- **THEN** the MMS SHALL parse the clues into SQL queries
- **AND** SHALL execute against appropriate memory tables
- **AND** SHALL return results in a structured format (dict or dataclass)

#### Scenario: Update state with change set
- **WHEN** an agent calls `mms.update_state(changes={"disk_3_position": "peg_C"})`
- **THEN** the MMS SHALL validate the change against current state
- **AND** SHALL update the `short_term_memory` table
- **AND** SHALL return confirmation or error

#### Scenario: Query rules for agent capabilities
- **WHEN** the Orchestrator calls `mms.query_rules(key="capability_agent_red")`
- **THEN** the MMS SHALL retrieve the matching entry from `rules_memory`
- **AND** SHALL return the parsed JSON value
- **AND** SHALL cache frequently accessed rules for performance

#### Scenario: Find similar plan
- **WHEN** an agent calls `mms.find_similar_plan(problem_hash="hanoi_n4_k3")`
- **THEN** the MMS SHALL query `long_term_memory` for exact or semantically similar entries
- **AND** SHALL return the plan data if found, or None if not found
- **AND** SHALL log retrieval metrics for AutoRAG optimization analysis

### Requirement: Gibson AI Memori SDK Integration

The MMS SHALL be implemented using the Gibson AI Memori SDK as the core memory backend, leveraging its SQL-native, agent-centric architecture.

#### Scenario: Initialize Memori with database connection
- **WHEN** the MMS is initialized at system startup
- **THEN** it SHALL connect to a PostgreSQL or SQLite database as configured
- **AND** Memori SHALL auto-create schema for four memory tables if they don't exist
- **AND** the connection SHALL be validated before the system accepts planning requests

#### Scenario: Use Memori's internal multi-agent processing
- **WHEN** the MMS receives complex queries or updates
- **THEN** Memori's internal agents (Memory, Conscious, Retrieval) SHALL handle processing
- **AND** this internal complexity SHALL be abstracted from the HTN system
- **AND** the HTN system SHALL interact only via the high-level MMS API

#### Scenario: Database backend selection via configuration
- **WHEN** the system is configured with `MEMORY_DB_TYPE=sqlite` in `config/memory_config.yaml`
- **THEN** the MMS SHALL use SQLite for local, fast development/testing
- **AND** WHEN configured with `MEMORY_DB_TYPE=postgresql`, it SHALL use PostgreSQL
- **AND** the schema and API SHALL remain identical across backends

### Requirement: HTN Planner Integration with MMS

The HTN planner's domain functions (precondition checks, effect applications) SHALL be refactored to call the MMS API instead of maintaining local state.

#### Scenario: Precondition function calls MMS
- **WHEN** the HTN planner evaluates a method precondition (e.g., `is_peg_clear(peg_A)`)
- **THEN** the precondition function SHALL call `mms.query_state(clues=["disks_on_peg(A)"])`
- **AND** SHALL evaluate the returned data (e.g., empty list = peg is clear)
- **AND** SHALL NOT maintain any local copy of the world state

#### Scenario: Operator effect calls MMS
- **WHEN** a primitive operator's `apply()` method is executed
- **THEN** it SHALL call `mms.update_state(changes={...})` to persist state transitions
- **AND** SHALL wait for confirmation before marking the operator as successfully applied
- **AND** if MMS update fails, the operator SHALL report failure and trigger backtracking

#### Scenario: Knowledge gap detection with MMS
- **WHEN** the HTN planner detects a knowledge gap (no applicable method)
- **THEN** it SHALL query `mms.query_rules()` to check if domain knowledge is missing
- **AND** if rules exist but are insufficient, SHALL trigger LLM-based method generation
- **AND** newly generated methods SHALL be stored in rules memory for future use
