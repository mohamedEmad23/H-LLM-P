## Context

The multi-agent HTN planning system currently lacks persistent memory, limiting its ability to learn from experience and maintain complex world state across distributed agents. This change introduces a Memory Management System (MMS) as a foundational architectural layer, implemented using Gibson AI's Memori (SQL-native, agent-centric memory engine) with MemoRAG-inspired query patterns.

### Background
- Current system: Stateless planning, no plan reuse, agents maintain isolated state
- Thesis requirement: Advanced memory system differentiating this work from existing MAP research
- Problem domains require: Strategic meta-planning (Level 5), close multi-agent coordination (Level 4), error learning

### Constraints
- Must use free-tier/open-source tools (Gibson AI Memori is open source)
- SQL-native preferred over vector DB for structured state queries
- Must support 6-8 agents with centralized coordination
- PostgreSQL or SQLite backend

### Stakeholders
- Thesis student (implementation)
- Professor supervisor (academic validation)
- Multi-agent system (consumers of memory API)

## Goals / Non-Goals

### Goals
- Implement persistent, shared memory layer accessible to all agents
- Enable plan reuse via semantic retrieval from long-term memory
- Support error pattern learning and continuous improvement
- Provide structured memory types: Short-Term, Long-Term, Rules, Entity
- Ensure atomic state updates and consistency across agents
- Adopt MemoRAG "clue generation" for intelligent query formulation

### Non-Goals
- NOT building a general-purpose RAG system (rejected RAGFlow)
- NOT using vector databases for core world state (SQL-based only)
- NOT implementing multi-agent memory via separate databases (single shared MMS)
- NOT supporting distributed/sharded memory (single-node sufficient for thesis scale)

## Decisions

### Decision 1: Gibson AI Memori as Core Memory Backend

**Rationale:**
- SQL-native: Perfect fit for structured, predicate-based HTN world state
- Agent-centric: Explicitly designed for multi-agent systems
- Structured memory types: Maps directly to HTN requirements (short-term state, rules, entities)
- Zero infrastructure overhead: Works with PostgreSQL/SQLite, no vector DB needed
- Open source: Aligns with zero-cost thesis requirement

**Alternatives Considered:**
- **RAGFlow**: Rejected - Document-centric design, heavy infrastructure (Elasticsearch, Redis, MinIO), overkill for symbolic reasoning
- **Custom SQL layer**: Would work but reinvents the wheel; Memori provides mature schema, query optimization, and multi-agent support
- **LangChain Memory**: Too generic, no structured memory types, requires custom schema design

### Decision 2: MemoRAG Clue Generation Paradigm

**Rationale:**
- HTN preconditions are often complex multi-part logical expressions
- Direct translation to SQL can be brittle
- "Clue generation" enables Orchestrator to formulate precise, context-aware queries
- Enables multi-hop reasoning for strategic planning (Level 5 meta-planning)

**Implementation:**
- Orchestrator translates HTN precondition (e.g., `can_move_tower(size=2, to=peg_B)`) into "clues"
- Clues: `["current_disks_on_peg(B)", "disk_sizes([disks_to_move])", "constraint_peg_b(max_size)"]`
- Query builder converts clues to structured SQL queries against MMS
- Results aggregated and evaluated by Orchestrator

**Alternatives Considered:**
- **Direct SQL in preconditions**: Brittle, tightly couples planner to SQL schema
- **LLM-based query generation**: Too slow, non-deterministic, unnecessary for structured state

### Decision 3: Orchestrator-Worker with Shared MMS (No Agent-Local State)

**Rationale:**
- Centralized state ensures consistency (single source of truth)
- Simplifies debugging and validation (all state transitions traceable)
- Prevents race conditions and stale state across agents
- Aligns with Orchestrator-Worker pattern already adopted

**Trade-offs:**
- MMS becomes single point of failure → Mitigated by database transactions and error handling
- Potential bottleneck → Acceptable for thesis scale (6-8 agents, <100 actions/plan)
- Network latency (if PostgreSQL remote) → Mitigated by using SQLite for development/testing

**Alternatives Considered:**
- **Agent-local state with periodic sync**: Complex, race conditions, hard to debug
- **Blockchain-style distributed consensus**: Massive overkill, performance nightmare

### Decision 4: AutoRAG for Semantic Retrieval Optimization

**Rationale:**
- Long-term memory (plan reuse) benefits from semantic retrieval
- AutoRAG provides empirical validation of retrieval component choices
- Essential for thesis to justify embedding model, chunking strategy

**Usage:**
- NOT used for core world state (SQL handles that)
- ONLY for long-term memory: "Find similar solved problems to current goal"
- Run during implementation phase to select best embedding model, retrieval strategy
- Results documented in thesis performance section

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────┐
│          Orchestrating Agent                        │
│  (HTN Planner + MemoRAG Query Builder)              │
└─────────────────┬───────────────────────────────────┘
                  │
                  ├─ query_state(clues)
                  ├─ update_state(changes)
                  ├─ query_rules(capability)
                  └─ find_similar_plan(goal_hash)
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│       Memory Management System (MMS)                │
│  ┌─────────────────────────────────────────────┐   │
│  │  Memory API Layer                           │   │
│  │  (query_state, update_state, query_rules)   │   │
│  └─────────────────┬───────────────────────────┘   │
│                    │                                │
│  ┌─────────────────▼───────────────────────────┐   │
│  │     Gibson AI Memori SDK                    │   │
│  │  (Internal: Memory, Conscious, Retrieval    │   │
│  │   agents - abstracted from users)           │   │
│  └─────────────────┬───────────────────────────┘   │
│                    │                                │
│  ┌─────────────────▼───────────────────────────┐   │
│  │     PostgreSQL / SQLite Database            │   │
│  │  ┌──────────────────────────────────────┐   │   │
│  │  │ short_term_memory (current state)    │   │   │
│  │  │ long_term_memory (plan history)      │   │   │
│  │  │ rules_memory (capabilities, rules)   │   │   │
│  │  │ memory_entities (objects, properties)│   │   │
│  │  └──────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────   │
└─────────────────────────────────────────────────────┘
                  ▲
                  │ (read-only state queries)
                  │
┌─────────────────┴───────────────────────────────────┐
│         Worker Agents (Execution Layer)             │
│  (DecompositionAgent, ExecutionAgent,               │
│   VerificationAgent, etc.)                          │
└─────────────────────────────────────────────────────┘
```

### Data Flow: Precondition Check Example

```
1. Orchestrator: Current task = move_tower(size=2, from=A, to=C, via=B)
2. Orchestrator generates clues:
   - "What disks are on peg B?"
   - "What is max size allowed on peg B?"
   - "What are sizes of disks in tower to move?"
3. Query Builder translates to SQL:
   - SELECT value FROM short_term_memory WHERE key LIKE 'disk_%_position' AND value='peg_B'
   - SELECT value FROM rules_memory WHERE key='constraint_peg_b'
   - SELECT size FROM memory_entities WHERE entity_id IN (...)
4. MMS executes queries, returns aggregated results
5. Orchestrator evaluates precondition: Can move? (max_disk_size <= constraint)
6. If true, applies method; if false, backtracks
```

### Memory Type Mapping

| HTN Requirement | Memori Component | SQL Table | Example Data |
|-----------------|------------------|-----------|--------------|
| Current disk positions | Short-Term Memory | `short_term_memory` | `(key='disk_3_position', value='peg_C')` |
| Agent can traverse red edges | Rules Memory | `rules_memory` | `(key='capability_agent_red', value='{"action":"traverse","color":"red"}')` |
| Peg B max size = 100 | Rules Memory | `rules_memory` | `(key='constraint_peg_b', value='{"max_size":100}')` |
| Frame-Stewart algorithm | Rules Memory | `rules_memory` | `(key='strategy_n_peg_hanoi', value='M(N,K)=...')` |
| Past Tower of Hanoi plan | Long-Term Memory | `long_term_memory` | `(problem_hash='hanoi_n4_k3', plan=[...])` |
| Disk properties | Entity Memory | `memory_entities` | `(entity_id='disk_4', properties='{"size":40}')` |

## Risks / Trade-offs

### Risk 1: MMS Becomes Bottleneck
- **Likelihood**: Low (6-8 agents, <100 queries/plan)
- **Impact**: Medium (slows planning)
- **Mitigation**:
  - Use SQLite for dev/test (local, fast)
  - Batch queries where possible
  - Profile and optimize with `EXPLAIN ANALYZE`

### Risk 2: SQL Schema Mismatch with HTN Semantics
- **Likelihood**: Medium (Memori schema is generic)
- **Impact**: High (could break precondition checks)
- **Mitigation**:
  - Carefully design key naming conventions (e.g., `disk_3_position`, `constraint_peg_b`)
  - Create abstraction layer in `memory_api.py` to hide schema details
  - Comprehensive integration tests for each domain

### Risk 3: Plan Reuse Retrieval Accuracy
- **Likelihood**: Medium (semantic retrieval is hard)
- **Impact**: Medium (failed plan reuse just falls back to planning)
- **Mitigation**:
  - Use AutoRAG to empirically select best embedding model
  - Start with simple problem hash matching, add semantic retrieval later
  - Validate retrieval accuracy with benchmark suite

### Trade-off: Centralized vs Distributed Memory
- **Chosen**: Centralized (single MMS, shared by all agents)
- **Benefit**: Consistency, simplicity, debuggability
- **Cost**: Single point of failure, potential bottleneck
- **Justification**: For thesis scale (6-8 agents), centralized is overwhelmingly simpler and sufficient

## Migration Plan

### Phase 1: Infrastructure Setup (Week 1)
1. Install Memori SDK, AutoRAG
2. Create PostgreSQL database, run Memori schema init
3. Create `src/memory/` directory, stub API

### Phase 2: Core MMS Implementation (Week 2)
1. Implement `memory_client.py`, `memory_api.py`
2. Implement clue-based `query_builder.py`
3. Write unit tests for MMS API

### Phase 3: HTN Planner Integration (Week 3)
1. Modify `htn_planner.py` domain functions to call MMS
2. Refactor `state_manager.py` to delegate to MMS
3. Test Tower of Hanoi with MMS-backed state

### Phase 4: Multi-Agent Integration (Week 4)
1. Modify Orchestrator and Worker Agents to use MMS
2. Remove local state management from agents
3. Test Phase 3 multi-agent scenarios with MMS

### Phase 5: Advanced Features (Week 5)
1. Implement plan reuse with AutoRAG-optimized retrieval
2. Implement error pattern learning
3. Add strategic knowledge (Frame-Stewart) to rules memory

### Rollback Plan
- Keep `state_manager.py` as local fallback (feature flag: `USE_MMS=false`)
- If MMS fails critically, disable and revert to stateless planning
- Comprehensive backups of database before schema changes

## Open Questions

1. **Should short-term memory be cleared after each problem, or persist across session?**
   - Recommendation: Clear per-problem, but log to long-term memory for learning

2. **How to handle concurrent state updates from multiple agents (if we move to parallel execution)?**
   - Current: Sequential execution, no concurrency
   - Future: Implement optimistic locking or transaction-based updates

3. **Should we use PostgreSQL or SQLite for production?**
   - Development/Testing: SQLite (fast, local, zero setup)
   - Thesis demo: PostgreSQL (more realistic, better for thesis write-up)
   - Recommendation: Support both via config flag

4. **How much historical data to keep in long-term memory?**
   - Start: Keep all (thesis scale is small, <1000 plans)
   - Later: Implement LRU eviction or archiving if needed
