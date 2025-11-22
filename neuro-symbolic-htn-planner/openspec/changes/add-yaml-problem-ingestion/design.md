# Design Document: Phase-Agnostic Problem Ingestion Architecture

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    YAML Problem Files                            │
│  (problems/*.yaml - 5 benchmark problems)                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Problem CLI (Interface Layer)                    │
│  - ProblemLoader: YAML → Problem dataclass                       │
│  - SystemPhaseDetector: Runtime component discovery              │
│  - ProblemCLI: Interactive & batch modes                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Phase 1     │ │  Phase 3     │ │  Phase 4     │
│  Executor    │ │  Executor    │ │  Executor    │
│              │ │              │ │              │
│ Single LLM   │ │ Multi-Agent  │ │ Strategic    │
│ + HTN        │ │ Coordinator  │ │ Workflow     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
        ┌────────────────────────────────┐
        │     BenchmarkLogger (KPI)      │
        │  - Tracks 7 standardized KPIs  │
        │  - JSON + SQLite storage       │
        │  - Per-phase trace files       │
        └────────────────────────────────┘
                        │
                        ▼
        ┌────────────────────────────────┐
        │      Results Storage           │
        │  - phase-1-traces/             │
        │  - phase-3-traces/             │
        │  - phase-4-traces/             │
        │  - kpis/ (aggregated)          │
        └────────────────────────────────┘
```

## Component Specifications

### 1. YAML Problem Schema

**Location**: `problems/*.yaml`

**Required Fields**:
```yaml
problem_type: string          # Unique identifier
description: string           # Human-readable description
initial_state: object         # Problem-specific starting condition
constraints: object           # Rules and limitations
expected_output: object       # Success criteria
metadata:
  difficulty: string          # easy|medium|hard|very hard
  category: string            # Problem classification
  tags: array<string>         # Searchable tags
domain_hints:
  primary_task: string        # Top-level HTN task
  subtasks: array<string>     # Decomposition hints
  key_operators: array<string># Primitive operations
```

**Validation Rules**:
- All fields required (schema enforced by `Problem.from_dict()`)
- Difficulty must be from predefined enum
- Domain hints guide LLM/agent decomposition strategy

### 2. Problem CLI Architecture

**Location**: `src/interface/problem_cli.py`

**Key Classes**:

#### `Problem` (Dataclass)
- Immutable representation of YAML problem
- Used across all phases (phase-agnostic)

#### `ProblemLoader`
- YAML validation and parsing
- Error handling for malformed files
- Schema version compatibility

#### `SystemPhaseDetector`
- Runtime import checks for phase components
- Graceful degradation if components missing
- Explicit phase override capability

#### `ProblemCLI`
- Interactive REPL mode
- Batch processing mode
- Routes to phase-specific executors

### 3. Phase-Specific Executors

Each executor implements same interface but different internal logic:

#### **Phase 1 Executor** (`_solve_phase_1()`)
**Input**: `Problem` object
**Process**:
1. Build LLM prompt from YAML (description + hints)
2. Query single LLM for HTN decomposition
3. Parse LLM response
4. Validate against expected_output
5. Log KPIs via BenchmarkLogger

**Output**: Trace JSON in `results/phase-1-traces/`

**KPIs Tracked**:
- Success Rate (KPI 1)
- Time to Solution (KPI 2)
- LLM Resource Utilization (KPI 6)
- Plan Optimality (KPI 5)

#### **Phase 3 Executor** (`src/interface/phase3_executor.py` - NEW)
**Input**: `Problem` object
**Process**:
1. Initialize AgentCoordinator with 3 specialized agents
2. Convert YAML → multi-agent task structure
3. Execute coordinated workflow:
   - PlanningAgent: Analyzes domain_hints
   - DecompositionAgent: Breaks down subtasks
   - ExecutionAgent: Executes key_operators
4. Validate consensus against expected_output
5. Log KPIs including agent communication

**Output**: Trace JSON in `results/phase-3-traces/`

**KPIs Tracked**:
- All Phase 1 KPIs +
- Agent Communication Overhead (KPI 4)
- Failure Recovery Rate (KPI 3) via agent consensus

#### **Phase 4 Executor** (`src/interface/phase4_executor.py` - NEW)
**Input**: `Problem` object
**Process**:
1. Initialize Extended Workflow with 5+ agents
2. Strategic planning phase:
   - ContextAgent: Analyze problem context
   - PlanningAgent: High-level strategy
3. Tactical execution:
   - DecompositionAgent: Task breakdown
   - ExecutionAgent: Operation execution
4. Verification loop:
   - VerificationAgent: Validate state consistency
5. Full KPI tracking with context coherence

**Output**: Trace JSON in `results/phase-4-traces/`

**KPIs Tracked**:
- All Phase 1 + Phase 3 KPIs +
- Context Coherence Score (KPI 7)
- Advanced error recovery patterns

### 4. BenchmarkLogger Integration

**Location**: `src/utils/benchmark_logger.py`

**Usage Pattern** (all executors):
```python
from utils.benchmark_logger import BenchmarkLogger

logger = BenchmarkLogger(output_dir=f"results/phase-{N}-traces")

with logger.track_execution(
    problem_id=problem.problem_type,
    architecture=f"phase{N}",
    optimal_steps=problem.expected_output.get("move_count")
):
    # Execute problem solving
    logger.log_llm_call(agent="...", llm="...", ...)
    logger.log_timing("phase_name", duration_ms)
    logger.log_success(goal_achieved=True, ...)
```

**Output Files**:
- `{problem}_{timestamp}.json` - Detailed execution trace
- `benchmarks.db` - SQLite for cross-run queries
- Aggregated KPI reports

### 5. Unified Test Harness

**Location**: `scripts/run_full_benchmark.py` (NEW)

**Functionality**:
```bash
# Run all phases on all problems
python scripts/run_full_benchmark.py --all

# Run specific phase on specific problem
python scripts/run_full_benchmark.py --phase 1 --problem hanoi_constrained

# Compare results across phases
python scripts/run_full_benchmark.py --compare --problem sorting
```

**Output**: Cross-phase comparison report with:
- Success rates per phase
- Performance metrics (time, tokens, steps)
- KPI heatmap visualization

## Data Flow

### Phase 1 Flow
```
YAML → ProblemLoader → Problem
  ↓
ProblemCLI._solve_phase_1()
  ↓
LLMClient.generate(prompt_from_yaml)
  ↓
Parse + Validate
  ↓
BenchmarkLogger.log_*()
  ↓
results/phase-1-traces/{problem}_{timestamp}.json
```

### Phase 3 Flow
```
YAML → ProblemLoader → Problem
  ↓
Phase3Executor.execute()
  ↓
AgentCoordinator.execute_workflow(
  tasks_from_domain_hints
)
  ↓
Multi-agent consensus
  ↓
BenchmarkLogger.log_*() (includes agent msgs)
  ↓
results/phase-3-traces/{problem}_{timestamp}.json
```

### Phase 4 Flow
```
YAML → ProblemLoader → Problem
  ↓
Phase4Executor.execute()
  ↓
ExtendedWorkflow.run(
  strategy_from_hints
)
  ↓
Context + Verification loop
  ↓
BenchmarkLogger.log_*() (full KPI suite)
  ↓
results/phase-4-traces/{problem}_{timestamp}.json
```

## Key Design Decisions

### 1. Why Separate Executors?
**Decision**: Create independent executors for each phase instead of unified executor with branching logic.

**Rationale**:
- **Clarity**: Each phase has distinct control flow
- **Testing**: Easy to test phases in isolation
- **Debugging**: Clear trace of phase-specific execution
- **Evolution**: Can modify one phase without affecting others

**Trade-off**: Code duplication vs maintainability → chose maintainability

### 2. YAML as Single Source of Truth
**Decision**: All problem definitions in YAML, no hardcoded domain logic in executors.

**Rationale**:
- **Reproducibility**: Version control for problem definitions
- **Extensibility**: Add new problems without code changes
- **Thesis**: Easy to document benchmark methodology
- **Comparison**: Guarantees same input across phases

### 3. BenchmarkLogger as Universal KPI Tracker
**Decision**: Use existing BenchmarkLogger for all phases instead of phase-specific loggers.

**Rationale**:
- **Consistency**: Standardized KPI measurement
- **Comparison**: Direct cross-phase comparison
- **Aggregation**: Single database for all results
- **Reuse**: Leverage existing robust implementation

### 4. Trace Files in Phase-Specific Directories
**Decision**: Separate output directories per phase.

**Rationale**:
- **Organization**: Easy to find results for specific phase
- **Debugging**: Isolate issues to specific architecture
- **Presentation**: Thesis chapter per phase with clear results path
- **Parallelization**: No file conflicts when running multiple phases

## Implementation Strategy

### Incremental Rollout
1. **Week 1**: Complete Phase 1 executor (50% done)
   - Update `_solve_phase_1()` in problem_cli.py
   - Test with all 5 YAML problems
   - Validate KPI tracking

2. **Week 2**: Implement Phase 3 executor
   - Create new `phase3_executor.py`
   - Integrate with existing AgentCoordinator
   - Test with all 5 problems

3. **Week 3**: Implement Phase 4 executor
   - Create new `phase4_executor.py`
   - Integrate with ExtendedWorkflow
   - Full KPI suite validation

4. **Week 4**: Unified harness + analysis
   - Master benchmark script
   - Cross-phase report generator
   - Documentation

### Testing Strategy
- **Unit Tests**: Each executor independently
- **Integration Tests**: YAML → Executor → Results
- **Regression Tests**: Ensure existing tests still pass
- **Benchmark Tests**: Full suite on all 5 problems

## Error Handling

### YAML Validation Errors
- **Problem**: Invalid YAML syntax or missing fields
- **Handling**: Early validation in ProblemLoader with clear error messages
- **Recovery**: User fixes YAML and re-runs

### Phase Detection Failures
- **Problem**: Required components not installed
- **Handling**: SystemPhaseDetector returns None, CLI shows helpful error
- **Recovery**: Install dependencies or use `--phase` override

### Execution Failures
- **Problem**: LLM timeout, constraint violation, etc.
- **Handling**: Log as failure with BenchmarkLogger
- **Recovery**: Record in KPI 3 (Failure Recovery Rate)

## Performance Considerations

### Parallel Execution
- Different phases can run concurrently
- Different problems can run concurrently
- Coordinate via filesystem (separate output directories)

### Resource Usage
- Phase 1: Single LLM call per problem
- Phase 3: 3x LLM calls (multi-agent)
- Phase 4: 5+ LLM calls (strategic workflow)
- Track costs via KPI 6 (token usage)

### Storage
- JSON trace files: ~10-50 KB per execution
- SQLite database: Indexed for fast queries
- Retention policy: Keep all for thesis analysis

## Future Extensions

### Phase 5 Integration (MMS)
When Memory Management System is implemented:
- Add `phase5_executor.py`
- Track memory query overhead (new KPI)
- Compare with/without memory system

### Additional Problems
- YAML schema supports arbitrary problems
- Add via `problems/*.yaml` (no code changes)
- Automatic integration with all phases

### LLM Provider Comparison
- Phase 1 already supports multiple providers
- Extend to Phase 3/4 for multi-LLM experiments
- Track per-provider performance metrics

## Approval & Next Steps

This design enables:
✅ Fair cross-architecture comparison
✅ Independent phase testing
✅ Thesis-ready benchmarking methodology
✅ Future extensibility

**Ready for implementation** pending proposal approval.
