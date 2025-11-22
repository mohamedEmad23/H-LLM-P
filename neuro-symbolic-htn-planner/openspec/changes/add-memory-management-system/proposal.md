## Why

The current multi-agent HTN planning system operates in a stateless manner where agents lack persistent memory and cannot learn from past executions. This severely limits the system's ability to:
- Reuse successful plans for similar problems
- Learn from errors and improve over time
- Maintain complex world state across distributed agents
- Perform strategic meta-level reasoning (required for Level 5 N-Peg Time-Limited Hanoi)

A robust Memory Management System (MMS) is the critical missing component that will elevate the system from a basic HTN planner to a sophisticated, learning-enabled multi-agent cognitive architecture.

**CRITICAL SIMPLIFICATION (FINALIZED)**: After comprehensive analysis of Gibson AI Memori, MemoRAG, and AutoRAG, this proposal has been **radically simplified** to focus on thesis research objectives. AutoRAG, FAISS, Redis, and PostgreSQL have been **REMOVED** as they introduce unnecessary complexity for a proof-of-concept system at research scale (<10GB data, single user, 6-8 week timeline).

## What Changes - FINALIZED STACK

### Core Components (3 Only)

#### 1. Gibson AI Memori - SQL-Native Memory Backend ⭐⭐⭐⭐⭐
- **Integration**: Wrap Memori SDK (~500 LOC) with thin MMS API layer
- **Backend**: SQLite by default (zero-config, portable, fast for thesis scale)
- **Memory Types**: Short-Term (world state), Long-Term (past plans), Rules (capabilities/constraints), Entity (object properties)
- **Features**: One-line integration, built-in multi-agent support, SQL-native storage

#### 2. MemoRAG Clue Generation PATTERN (NOT Framework) ⭐⭐⭐⭐
- **Pattern**: Decompose complex HTN preconditions into simple "clues" for clearer queries
- **Implementation**: `ClueGenerator` class (~200 LOC) - custom implementation, NOT the full MemoRAG framework
- **Example**: "Can move tower?" → ["peg_B_max_size?", "current_disks_on_B?", "tower_size?"]
- **What We DON'T Use**: MemoRAG's dual-LLM architecture, vector search, caching (unnecessary complexity)

#### 3. SQLite Database - Zero-Config Backend ⭐⭐⭐⭐⭐
- **Why**: Zero setup, portable (single .db file), fast enough (<10GB, <100 queries/sec), thesis-appropriate
- **When to Upgrade**: After thesis defense, if scaling to 100+ agents

### REMOVED TOOLS (Justified Eliminations)

| Tool | Reason for Removal | What We'll Do Instead |
|------|-------------------|----------------------|
| **AutoRAG** | Wrong problem domain (semantic retrieval vs structured HTN) | Simple problem hash matching for plan reuse |
| **FAISS** | HTN queries are exact (SQL WHERE), not semantic (similarity) | SQL queries for all state lookups |
| **Redis** | Premature optimization (caching for 1000s of users, we have 1) | Let Memori handle internal caching |
| **PostgreSQL** | Overkill for thesis scale (<10GB, single user) | Use SQLite; migrate post-defense if needed |

### Simplified Architecture
```
┌─────────────────────────────────────────┐
│    HTN Planner (Orchestrator)           │
│  - Generates clues for preconditions    │
│  - Queries MMS via query_state()        │
│  - Updates MMS via update_state()       │
└─────────────────────────────────────────┘
            ↕ (MMS API - 4 methods)
┌─────────────────────────────────────────┐
│   Memory Management System (MMS)        │
│  ┌──────────────────────────────────┐   │
│  │  Thin API Wrapper (~500 LOC)     │   │
│  │  - query_state(clues) -> dict    │   │
│  │  - update_state(changes) -> bool │   │
│  │  - query_rules(key) -> value     │   │
│  │  - store_plan(id, plan) -> id    │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  Gibson AI Memori SDK            │   │
│  │  - remember() / retrieve()       │   │
│  │  - 4 memory types                │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  SQLite (mms_thesis.db)          │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
            ↕ (State Queries - Read-Only)
┌─────────────────────────────────────────┐
│   Multi-Agent System (5 Agents)         │
│  - Workers query MMS (read-only)        │
│  - Orchestrator updates MMS             │
└─────────────────────────────────────────┘
```

**Key Simplifications**:
1. No vector database layer
2. No caching layer
3. No separate retrieval engine
4. No AutoRAG optimization loop
5. Single SQLite file (not distributed system)

## Impact

### Breaking Changes
1. **State Management**: HTN planner queries MMS for state instead of local variables
2. **Agent Communication**: Workers read from MMS (orchestrator updates MMS)
3. **Plan Representation**: Plans serialized to JSON for `long_term_memory`

### Affected Specs
- **NEW**: `memory-management` - Entire capability being added
- **MODIFIED**: `multi-agent-coordination` - Agents now interact via shared MMS (orchestrator-worker pattern)
- **MODIFIED**: `htn-planning-core` - Planner preconditions become MMS API calls with clue generation

### Affected Code
- `src/memory/` - **NEW** directory for MMS implementation (~1500 LOC total)
  - `mms_core.py` - Gibson Memori wrapper (~500 LOC)
  - `clue_generator.py` - MemoRAG pattern implementation (~200 LOC)
  - `memory_types.py` - Type definitions (~100 LOC)
- `src/agents/orchestrator.py` - **MODIFIED** to use MMS for state queries (~400 LOC)
- `src/agents/worker_agent.py` - **MODIFIED** to read from MMS (read-only) (~200 LOC)
- `src/core/htn_planner.py` - **MODIFIED** domain functions to call MMS
- `requirements.txt` - Add `memorisdk>=0.1.0`

### Database
- SQLite schema auto-managed by Memori SDK
- Tables: `short_term_memory`, `long_term_memory`, `rules_memory`, `entity_memory`

### Testing
- **NEW**: `tests/test_mms_basic.py` - Unit tests for MMS API
- **NEW**: `tests/test_clue_generator.py` - Clue generation pattern tests
- **NEW**: `tests/test_mms_integration.py` - End-to-end HTN + MMS tests
- **NEW**: `benchmarks/benchmark_mms_performance.py` - Query latency & throughput benchmarks

### Documentation
- **NEW**: `FINALIZED_TOOL_STACK.md` - Complete rationale for tool decisions (70% complexity reduction)
- **NEW**: `INTEGRATION_GUIDE.md` - Step-by-step implementation guide (9 sections, ~2500 LOC examples)
- **MODIFIED**: `design.md` - Updated to reflect simplified architecture
- **MODIFIED**: `tasks.md` - Reduced from 40+ tasks to ~25 tasks (simplified scope)

---

## Migration Strategy (6-8 Weeks)
1. **Week 1-2**: Set up MMS infrastructure (Memori SDK + SQLite), write unit tests, validate query latency
2. **Week 3-4**: Migrate HTN precondition checks to MMS queries with clue generation
3. **Week 5-6**: Integrate multi-agent coordination with MMS (orchestrator-worker pattern)
4. **Week 7-8**: Implement plan reuse (hash matching), benchmark performance, write thesis documentation

---

## Success Metrics (Thesis KPIs)
- [ ] **Precondition Query Latency**: <100ms per query (SQLite easily achieves this)
- [ ] **State Update Success Rate**: 100% (atomic SQL transactions)
- [ ] **Plan Reuse Speedup**: >2x faster on second solve of same problem
- [ ] **Multi-Agent Coordination**: 0 state conflicts in 100 test runs
- [ ] **Code Complexity**: <2000 lines for entire MMS (vs 10K+ for full RAG system)

---

## References
- **Gibson AI Memori**: https://github.com/GibsonAI/memori (2.3k stars, Apache 2.0, SQL-native memory)
- **MemoRAG Paper**: https://arxiv.org/abs/2409.05591 (clue generation pattern inspiration)
- **Finalized Tool Stack**: See `FINALIZED_TOOL_STACK.md` for complete justification (AutoRAG/FAISS/Redis removal)
- **Integration Guide**: See `INTEGRATION_GUIDE.md` for step-by-step implementation (9 sections, code examples)
