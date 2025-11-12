# Project Context

## Purpose

**Thesis Title**: Neuro-Symbolic Hierarchical Task Network Planning with Large Language Models

This is a B.Sc thesis project developing a progressive multi-agent HTN (Hierarchical Task Network) planning system that combines symbolic reasoning with LLM-based intelligence. The system evolves from basic CoT (Chain of Thought) + HTN integration to a sophisticated multi-agent architecture with specialized agents for different planning phases.

### Core Goals
- Achieve >70% success rate on complex reasoning tasks (Tower of Hanoi, Graph Traversal)
- Implement a 6-8 agent multi-agent architecture inspired by MAP (Modular Agentic Planner) research
- Develop a two-phase memory system (minimal RAG → full memory with MMS)
- Progressive scaling across multiple implementation phases
- Zero-cost implementation using free-tier APIs

### Unique Contributions
- Multi-agent HTN system with full memory (beyond existing papers)
- Advanced memory system with error pattern learning
- Progressive LLM integration (8 providers, specialist routing)
- Continuous improvement from agent interactions
- Comprehensive benchmarking at each implementation phase

## Tech Stack

### Core Technologies
- **Python 3.9+**: Primary language
- **Pytest**: Testing framework
- **YAML**: Configuration files
- **Git**: Version control

### LLM Providers (Tiered Architecture)
**Tier 1 (Primary)**
- HuggingFace: Llama-3.3-70B-Instruct, Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct
- GitHub Models: DeepSeek V3, GPT-5

**Tier 2 (Fallback)**
- Groq: Llama-3.3-70B-Versatile
- Google: Gemini-2.0-Flash-Exp
- DeepSeek: DeepSeek-Chat

**Tier 3 (Backup/Local)**
- Cohere: Command-R-Plus
- Ollama: Llama3.2 (local, zero-cost testing)

### Memory & RAG (Phase 5 - Planned)
- **Gibson AI's Memori**: SQL-native memory layer for multi-agent systems
- **PostgreSQL/SQLite**: Backend database
- **AutoRAG**: Pipeline optimization and validation
- **MemoRAG**: Clue generation paradigm for query formulation

### Agent Framework (Phase 4+)
- Custom multi-agent coordinator
- Message bus for async communication
- State manager for world state tracking

## Project Conventions

### Code Style
- **PEP 8 compliance** for Python code
- **Type hints** required for all function signatures
- **Docstrings** using Google style for all classes and public methods
- **Snake_case** for variables and functions
- **PascalCase** for class names
- **UPPER_CASE** for constants
- **Line length**: 100 characters max
- **Import order**: Standard library → Third-party → Local imports

### File Organization
```
src/
├── agents/          # Multi-agent system (Phase 3+)
├── algorithms/      # HTN algorithms and strategies
├── core/            # Core HTN components (state, task, operator, methods)
├── domains/         # Domain definitions (blocks world, Hanoi, etc.)
├── llm/             # LLM client integrations
└── utils/           # Shared utilities

tests/
├── phase-0-foundation/
├── phase-1-single-llm/
├── phase-3-multi-agent/
└── phase-4-strategic/
```

### Architecture Patterns

#### HTN Planning Core
- **STRIPS-style operators**: Preconditions and effects for state transitions
- **Recursive decomposition**: Compound tasks → primitive tasks
- **Backtracking search**: Method selection with failure recovery
- **Knowledge gap detection**: Triggers LLM integration when symbolic planning insufficient

#### Multi-Agent Architecture (Phase 3+)
- **Orchestrator-Worker Pattern**: Central coordinating agent + specialized worker agents
- **Message Bus**: Async communication between agents
- **Shared Memory**: MMS (Memory Management System) as single source of truth
- **Hub-and-Spoke**: Orchestrator mediates all agent interactions

#### Agent Specialization
- **DecompositionAgent**: Complex task breakdown (Llama 70B)
- **ExecutionAgent**: Action execution with rule-based optimization (Qwen 7B + Rules)
- **VerificationAgent**: Plan validation (Llama 8B)
- **PlanningAgent**: Strategic planning (Phase 4B)
- **ContextAgent**: Context management (Phase 4B)
- **MemoryAgent**: Memory retrieval and learning (Phase 5)

### Testing Strategy

#### Phase-Based Testing
- Each phase has dedicated test suite in `tests/phase-X-*/`
- Benchmark tests track performance metrics across phases
- Regression testing ensures previous phases remain functional

#### Test Types
1. **Unit Tests**: Core components (state, task, operator, methods)
2. **Integration Tests**: HTN planner with LLM integration
3. **Domain Tests**: Specific domains (household tasks, Tower of Hanoi)
4. **Benchmark Tests**: Performance comparison across LLM providers
5. **Multi-Agent Tests**: Agent coordination and communication (Phase 3+)

#### Running Tests
```bash
# All tests for current phase
pytest tests/phase-X-* -v

# Specific domain
pytest tests/test_household_tasks.py -v

# With detailed output
pytest tests/test_simple_htn.py -v -s

# Benchmarks
python benchmarks/run_tests.py
```

#### Success Criteria
- **Tower of Hanoi (3-disk)**: >70% success rate (baseline: 11% GPT-4 zero-shot)
- **Graph Traversal**: Successful shortest path and cycle detection
- **Execution time**: <10s for simple problems, <60s for complex
- **Test coverage**: >80% for core components

### Git Workflow

#### Branch Strategy
- **main**: Stable, production-ready code
- **memorySystem/Phase1**: Current development (Memory Management System Phase 1)
- **phase-X-feature**: Feature branches for specific phase work

#### Commit Conventions
Use conventional commits format:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build/tooling changes

**Scopes**: `core`, `llm`, `agents`, `memory`, `tests`, `benchmarks`, `docs`

**Examples**:
```
feat(memory): implement Gibson AI Memori integration
fix(htn): resolve backtracking issue in method selection
test(phase-4): add multi-agent coordination tests
docs(readme): update Phase 5 memory system architecture
```

#### Phase Completion Protocol
1. Complete all tests for the phase
2. Update documentation in `docs/phase-X-*/`
3. Generate benchmark report in `results/phase-X-*/`
4. Create completion checklist (e.g., `PHASE3_FINAL_CHECKLIST.md`)
5. Merge to main after validation

## Domain Context

### HTN Planning Fundamentals
- **World State**: Predicate-based representation (e.g., `on(block_a, block_b)`)
- **Tasks**: Primitive (executable) vs Compound (require decomposition)
- **Operators**: STRIPS-style actions with preconditions/effects
- **Methods**: Decomposition rules mapping compound tasks to subtasks
- **Planning**: Recursive decomposition until all tasks are primitive

### Target Problem Domains

#### Primary Domains
1. **Tower of Hanoi**: 3-5 disks, constrained pegs, N-peg variants
2. **Graph Traversal**: Shortest path, cycle detection, multi-agent coordination
3. **Multi-Agent Stack Transfer**: Coordinated disk movement across agents

#### Complexity Levels
- **Level 1**: Multi-Agent Graph Traversal (capability-based routing)
- **Level 2**: Agent-Constrained Hanoi (peg size limits)
- **Level 3**: Dynamic Resource Flow Graph (strategic trade-offs)
- **Level 4**: Multi-Agent Stack Transfer (close coordination)
- **Level 5**: N-Peg Time-Limited Hanoi (meta-level planning, Frame-Stewart algorithm)

### LLM Integration Patterns

#### Knowledge Gap Detection
When symbolic planner cannot proceed (unknown methods, ambiguous state), trigger LLM:
- Generate task decompositions via CoT prompting
- Parse LLM responses into HTN methods
- Validate generated methods against current state

#### Specialist Model Routing
- **Complex reasoning**: Llama 70B, DeepSeek V3
- **Simple tasks**: Qwen 7B, Llama 8B
- **Verification**: Llama 8B, Cohere
- **Emergency fallback**: Groq, Gemini 2.0
- **Offline mode**: Ollama (local)

## Important Constraints

### Academic Requirements
- **Thesis deadline**: Submit by end of academic year
- **Supervisor approval**: Professor review required for major architectural changes
- **Originality**: Must demonstrate novel contributions beyond existing MAP/HTN research
- **Documentation**: Comprehensive thesis report with architecture diagrams and benchmarks

### Technical Constraints
- **Zero-cost budget**: All LLM providers must have free tier
- **No robotics**: Focus on pure algorithmic/planning tasks
- **Rate limits**: Free-tier API rate limits require provider rotation
- **Local testing**: Must support offline mode via Ollama

### Implementation Priorities
1. **Core HTN engine** (Phase 0-1): Foundation must be solid
2. **Multi-agent coordination** (Phase 3-4): Critical for thesis contribution
3. **Memory system** (Phase 5): Differentiator from existing research
4. **Extended agents** (Phase 4B-C): If time permits

### Performance Requirements
- **Success rate**: >70% on Tower of Hanoi (3-disk)
- **Response time**: <10s for simple problems
- **Memory efficiency**: SQL-based, no vector DB overhead for core state
- **Scalability**: Support 3 → 6 → 8 agent progression

## External Dependencies

### LLM Provider APIs
- **HuggingFace Inference API**: Primary LLM provider (free tier)
- **GitHub Models API**: DeepSeek V3, GPT-5 access
- **Groq API**: High-speed inference fallback
- **Google AI Studio**: Gemini 2.0 access
- **Cohere API**: Reliable backup provider
- **Ollama**: Local LLM server for offline testing

### Memory & Database (Phase 5)
- **Gibson AI Memori SDK**: SQL-native memory layer
- **PostgreSQL**: Production database backend
- **SQLite**: Development/testing database

### Development Tools
- **pytest**: Unit and integration testing
- **ruff**: Python linting (replaces flake8, black, isort)
- **mypy**: Static type checking
- **bandit**: Security vulnerability scanning

### Documentation Tools
- **Mermaid**: Architecture and flow diagrams
- **Markdown**: All documentation
- **OpenSpec**: Spec-driven development workflow

### Configuration Management
- **YAML files**: `config/default_config.yaml`, `config/huggingface_config.yaml`
- **Environment variables**: API keys via `.env` (never committed)
- **Provider configs**: Per-provider LLM settings (model, latency, quality tiers)

## Research References

### Key Papers
- **MAP (Modular Agentic Planner)**: Multi-agent architecture inspiration
- **HTN Planning**: Classic STRIPS and hierarchical planning theory
- **MemoRAG**: Clue generation paradigm for RAG systems
- **RAGFlow**: Document-centric RAG (rejected for this project)

### Project Documentation
- `docs/THESIS_DOCUMENTATION_PROFESSOR_SUPERVISOR.md`: Complete architecture evolution
- `Idea-Vault/Design-Specifications.md`: System design and agent specs
- `Idea-Vault/Memory_System_Updated.md`: Memory architecture blueprint
- Phase-specific docs in `docs/phase-X-*/`
