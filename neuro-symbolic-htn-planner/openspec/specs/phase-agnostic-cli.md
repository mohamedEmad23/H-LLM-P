# Spec Issue: Phase-Agnostic Problem CLI

## Issue ID
`SPEC-001`

## Priority
**HIGH** - Required for thesis evaluation and benchmarking

## Problem Statement
The Problem Ingestion Layer CLI (`problem_cli.py`) currently imports `DomainMapper`, a Phase 5 (Memory System) component that doesn't exist in Phase 1-4 architectures. This creates a hard dependency that breaks the CLI in earlier phases, preventing:
- Thesis professors from testing arbitrary problems across all architectures
- Fair benchmark comparisons between Phase 1 (Single LLM), Phase 3 (Multi-Agent), and Phase 5 (Multi-Agent + MMS)
- Demonstration of architectural evolution and performance improvements

## Requirements

### FR-001: Universal CLI Compatibility
**Description**: CLI must detect available system components at runtime and route accordingly.

**Acceptance Criteria**:
- CLI works in Phase 1 (Single LLM) environment without Phase 3/5 imports
- CLI works in Phase 3 (Multi-Agent) environment without Phase 5 imports
- CLI works in Phase 5 (Multi-Agent + MMS) with full feature set
- Zero hard-coded phase dependencies

### FR-002: Graceful Degradation
**Description**: System must fallback intelligently when advanced components unavailable.

**Routing Logic**:
```
Phase 5 available? → Use DomainMapper with MMS cache
    ↓ No
Phase 3 available? → Use multi-agent planning directly
    ↓ No
Phase 1 available? → Use single LLM planner
    ↓ No
Error: No planner available
```

### FR-003: Benchmark Consistency
**Description**: Same YAML problem definitions must work across all phases for fair comparison.

**Requirements**:
- YAML schema remains identical across phases
- Problem validation independent of phase
- Results format consistent for benchmark aggregation

## Technical Approach

### Component Detection
```python
class SystemPhaseDetector:
    @staticmethod
    def detect_available_phases() -> dict:
        """Runtime detection of available components."""
        return {
            'phase_5': can_import('src.planning.domain_mapper'),
            'phase_3': can_import('src.agents.coordinator'),
            'phase_1': can_import('src.core.htn_planner')
        }
```

### Phase-Aware Routing
```python
def solve_problem(problem: Problem) -> Plan:
    phases = SystemPhaseDetector.detect_available_phases()

    if phases['phase_5']:
        return _solve_with_mms(problem)
    elif phases['phase_3']:
        return _solve_with_multi_agent(problem)
    elif phases['phase_1']:
        return _solve_with_single_llm(problem)
    else:
        raise RuntimeError("No planner available")
```

## Success Metrics

### Compatibility
- ✅ CLI runs without errors in Phase 1 environment
- ✅ CLI runs without errors in Phase 3 environment
- ✅ CLI runs without errors in Phase 5 environment

### Benchmark Validity
- ✅ Same YAML problem produces results in all 3 phases
- ✅ Results include phase identifier for comparison
- ✅ Performance metrics (time, LLM calls, plan quality) recorded consistently

### Professor Testing
- ✅ Professor can submit custom YAML problem
- ✅ System runs problem across all architectures
- ✅ Results clearly show Phase 5 (Multi-Agent + MMS) outperforms Phase 1/3

## Implementation Tasks

1. **Audit Dependencies**: Identify all Phase 5 imports in `problem_cli.py`
2. **Create Detector**: Implement `SystemPhaseDetector` class
3. **Add Routing**: Create phase-specific solver methods
4. **Update Tests**: Verify CLI in Phase 1, 3, 5 environments
5. **Clean LLM Clients**: Remove Mistral and Eden (hallucinated outputs)
6. **Document**: Create architectural decision record

## Related Files
- `neuro-symbolic-htn-planner/src/interface/problem_cli.py`
- `neuro-symbolic-htn-planner/src/planning/domain_mapper.py` (Phase 5 only)
- `neuro-symbolic-htn-planner/src/agents/coordinator.py` (Phase 3+)
- `neuro-symbolic-htn-planner/src/core/htn_planner.py` (Phase 1+)

## Expected Outcome
A universal problem submission interface that enables:
1. Thesis professors to test arbitrary problems across all architectures
2. Benchmark comparisons proving Phase 5 superiority
3. Graceful degradation maintaining compatibility with legacy phases
