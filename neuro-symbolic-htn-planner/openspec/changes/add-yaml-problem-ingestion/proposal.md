# Proposal: YAML-Based Problem Ingestion System for Cross-Architecture Evaluation

## Overview

Implement a phase-agnostic problem ingestion system that allows all architectural phases (Phase 1: Single LLM, Phase 3: Multi-Agent, Phase 4: Strategic Multi-Agent) to consume standardized YAML problem definitions and produce comparable benchmarking results.

## Problem Statement

Currently, the HTN planning system has:
- **Hardcoded problem definitions** in test files
- **No standardized input format** across phases
- **Inconsistent evaluation** making cross-phase comparison difficult
- **Manual test harness** for each architecture variant

This makes it impossible to fairly evaluate and compare:
- Phase 1: Single LLM (Groq/Gemini/Ollama/HF) with HTN reasoning
- Phase 3: Multi-Agent (3 specialized agents with different LLMs)
- Phase 4: Strategic Multi-Agent (5+ agents with advanced workflow)

## Proposed Solution

### 1. Standardized YAML Problem Format
- ✅ Already implemented in `problems/*.yaml`
- 5 benchmark problems: hanoi_constrained, sorting, pathfinding, 3sum, resource_allocation
- Consistent schema with domain_hints, constraints, expected_output

### 2. Phase-Agnostic CLI Interface
- ✅ `problem_cli.py` with runtime phase detection
- ✅ `SystemPhaseDetector` for dynamic component discovery
- ⚠️  Needs completion: Phase-specific problem ingestion adapters

### 3. Architecture-Specific Executors
Create dedicated executors for each phase:
- **Phase 1 Executor**: Single LLM + HTN planning
- **Phase 3 Executor**: Multi-agent coordinator with 3 agents
- **Phase 4 Executor**: Strategic workflow with 5+ agents

### 4. Unified KPI Collection
- ✅ `BenchmarkLogger` already tracks 7 KPIs
- ⚠️  Needs integration into each executor
- Target output: `results/phase-{1,3,4}-traces/{problem}_{timestamp}.json`

## Success Criteria

1. **Same 5 problems run on all 3 phases** using identical YAML input
2. **Consistent KPI tracking** across all architectures
3. **Comparable results** in standardized JSON format
4. **Independent testing** - each phase can be benchmarked separately
5. **Easy debugging** - trace files show architecture-specific execution paths

## Implementation Plan

### Stage 1: Phase 1 Integration (Single LLM)
- ✅ YAML loader in problem_cli.py
- ⚠️  Complete `_solve_phase_1()` to properly use benchmark logger
- ⚠️  Create Phase 1 runner script: `run_phase1_benchmark.py`
- Test with all 5 problems across different LLM providers

### Stage 2: Phase 3 Integration (Multi-Agent)
- Create `phase3_executor.py` that ingests YAML → AgentCoordinator
- Adapt multi-agent workflow to accept YAML problem structure
- Map YAML hints to agent task decomposition
- Integrate with BenchmarkLogger

### Stage 3: Phase 4 Integration (Strategic Multi-Agent)
- Create `phase4_executor.py` for extended workflow
- Handle strategic planning with context/verification agents
- Full KPI tracking with agent communication overhead
- Advanced error recovery patterns

### Stage 4: Unified Test Harness
- Single script to run all phases: `run_full_benchmark.py`
- Cross-phase comparison report generator
- Visualization of KPI differences

## Technical Decisions

### Why Not Merge Executors?
Each phase has fundamentally different:
- **Control flow**: Single LLM vs coordinator-based orchestration
- **State management**: Local vs distributed agent state
- **Error handling**: Direct retry vs multi-agent consensus
- **KPI collection**: Different granularity and checkpoints

### Why YAML?
- Human-readable and editable
- Version controllable
- Easy to extend with new constraints
- Industry standard for config

### Why Separate Trace Directories?
- Easy to compare phase-specific execution patterns
- Independent debugging per architecture
- Clear separation for thesis presentation

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| YAML schema changes break tests | High | Use schema validation, version YAML format |
| KPIs not comparable across phases | High | Standardize measurement points, document differences |
| Phase detection fails | Medium | Explicit phase selection override flag |
| Different LLM costs skew comparison | Medium | Normalize by token usage, not wall-clock time |

## Timeline

- **Week 1**: Complete Phase 1 integration ✓ (50% done)
- **Week 2**: Implement Phase 3 executor and integration
- **Week 3**: Implement Phase 4 executor and integration
- **Week 4**: Unified harness, cross-phase analysis, documentation

## Dependencies

- Existing: YAML problems, BenchmarkLogger, problem_cli.py
- New: Phase-specific executors, unified test harness
- Blocked by: None

## Approval Required

This proposal requires approval before implementation begins. The foundation is already 40% complete with problem_cli.py infrastructure.

**Requested by**: Thesis development team
**Date**: November 14, 2025
