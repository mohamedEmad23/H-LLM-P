# Problem Ingestion Capability

## Capability Overview
Provides phase-agnostic YAML-based problem ingestion for HTN planner architectures.

## ADDED Requirements

### Requirement: YAML Problem Loading
The system MUST load problem definitions from YAML files with schema validation.

#### Scenario: Load valid YAML problem
**Given** a valid YAML file in `problems/hanoi_constrained.yaml`
**When** the user calls `ProblemLoader.load_problem("hanoi_constrained")`
**Then** the system returns a validated `Problem` object
**And** all required fields are populated

#### Scenario: Reject invalid YAML schema
**Given** a YAML file with missing `domain_hints` field
**When** the user attempts to load the problem
**Then** the system raises `ValueError` with descriptive error message
**And** no Problem object is created

### Requirement: Phase Detection
The system MUST detect available architectural phases at runtime.

#### Scenario: Detect Phase 1 components
**Given** `src.core.htn_planner` module is importable
**When** `SystemPhaseDetector.detect_available_phases()` is called
**Then** the result includes `"phase_1": true`

#### Scenario: Graceful degradation when phase unavailable
**Given** Phase 5 components are not installed
**When** `SystemPhaseDetector.get_best_available_phase()` is called
**Then** the system returns highest available phase (e.g., "phase_4")
**And** no import errors are raised

### Requirement: Phase 1 Execution
The system MUST execute problems using single LLM architecture.

#### Scenario: Execute problem with Phase 1
**Given** a loaded `Problem` object for Tower of Hanoi
**When** `ProblemCLI._solve_phase_1(problem)` is executed
**Then** the system queries LLM with YAML-derived prompt
**And** KPIs are logged via BenchmarkLogger
**And** results are saved to `results/phase-1-traces/`

### Requirement: Phase 3 Execution
The system MUST execute problems using multi-agent coordinator.

#### Scenario: Execute problem with Phase 3
**Given** a loaded `Problem` object for sorting
**When** `Phase3Executor.execute(problem)` is executed
**Then** the system initializes 3 specialized agents
**And** agent workflow processes domain_hints from YAML
**And** agent communication is tracked in KPI 4
**And** results are saved to `results/phase-3-traces/`

### Requirement: Phase 4 Execution
The system MUST execute problems using strategic multi-agent workflow.

#### Scenario: Execute problem with Phase 4
**Given** a loaded `Problem` object for pathfinding
**When** `Phase4Executor.execute(problem)` is executed
**Then** the system initializes extended workflow with 5+ agents
**And** context coherence score (KPI 7) is tracked
**And** results are saved to `results/phase-4-traces/`

### Requirement: Unified KPI Tracking
The system MUST track standardized KPIs across all phases.

#### Scenario: Track KPIs during Phase 1 execution
**Given** a problem execution in Phase 1
**When** BenchmarkLogger is used with context manager
**Then** the system logs success rate, time to solution, token usage
**And** trace JSON includes all 7 KPIs
**And** SQLite database is updated with execution record

#### Scenario: Cross-phase KPI comparison
**Given** same problem executed on Phase 1, 3, and 4
**When** benchmark reports are generated
**Then** KPI values are directly comparable
**And** phase-specific metrics are clearly distinguished

### Requirement: CLI Interface
The system MUST provide interactive and batch problem execution modes.

#### Scenario: Interactive REPL mode
**Given** user runs `python -m interface.problem_cli --interactive`
**When** user types `solve hanoi_constrained`
**Then** the system loads YAML, detects best phase, executes problem
**And** results are displayed to terminal
**And** trace files are saved

#### Scenario: Batch processing
**Given** user runs `python -m interface.problem_cli --solve hanoi_constrained`
**When** command completes
**Then** the system executes problem without interaction
**And** returns exit code 0 on success, 1 on failure
