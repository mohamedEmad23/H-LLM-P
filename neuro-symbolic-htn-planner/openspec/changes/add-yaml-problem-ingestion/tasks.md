# Implementation Tasks: YAML Problem Ingestion System

## Stage 1: Phase 1 Integration (Single LLM)
- [ ] 1.1 Verify YAML problem loader functionality
- [ ] 1.2 Update `_solve_phase_1()` to properly construct problem from YAML
- [ ] 1.3 Integrate BenchmarkLogger KPI tracking
- [ ] 1.4 Test with all 5 problems (hanoi, sorting, pathfinding, 3sum, resource_allocation)
- [ ] 1.5 Create `scripts/run_phase1_benchmark.py` runner script
- [ ] 1.6 Validate results output to `results/phase-1-traces/`

## Stage 2: Phase 3 Integration (Multi-Agent)
- [ ] 2.1 Create `src/interface/phase3_executor.py` module
- [ ] 2.2 Implement YAML → AgentCoordinator adapter
- [ ] 2.3 Map domain_hints to agent task decomposition prompts
- [ ] 2.4 Integrate BenchmarkLogger with coordinator workflow
- [ ] 2.5 Track agent communication overhead (KPI 4)
- [ ] 2.6 Test with all 5 problems
- [ ] 2.7 Create `scripts/run_phase3_benchmark.py` runner script
- [ ] 2.8 Validate results output to `results/phase-3-traces/`

## Stage 3: Phase 4 Integration (Strategic Multi-Agent)
- [ ] 3.1 Create `src/interface/phase4_executor.py` module
- [ ] 3.2 Implement YAML → Extended Workflow adapter
- [ ] 3.3 Map domain_hints to strategic planning workflow
- [ ] 3.4 Integrate context and verification agents
- [ ] 3.5 Track full KPI suite including context coherence
- [ ] 3.6 Test with all 5 problems
- [ ] 3.7 Create `scripts/run_phase4_benchmark.py` runner script
- [ ] 3.8 Validate results output to `results/phase-4-traces/`

## Stage 4: Unified Test Harness
- [ ] 4.1 Create `scripts/run_full_benchmark.py` master script
- [ ] 4.2 Implement parallel execution of all phases
- [ ] 4.3 Create cross-phase comparison report generator
- [ ] 4.4 Generate KPI visualization dashboard
- [ ] 4.5 Create `docs/BENCHMARK_GUIDE.md` documentation

## Stage 5: Validation & Testing
- [ ] 5.1 Run full benchmark suite on all 5 problems × 3 phases
- [ ] 5.2 Verify KPI consistency across architectures
- [ ] 5.3 Validate trace file formats
- [ ] 5.4 Test with different LLM providers (Phase 1)
- [ ] 5.5 Performance regression check
- [ ] 5.6 Update README.md with usage examples

## Stage 6: Documentation
- [ ] 6.1 Document YAML problem schema with examples
- [ ] 6.2 Create executor architecture diagrams
- [ ] 6.3 Document KPI collection methodology per phase
- [ ] 6.4 Write troubleshooting guide
- [ ] 6.5 Update thesis documentation with benchmark methodology
