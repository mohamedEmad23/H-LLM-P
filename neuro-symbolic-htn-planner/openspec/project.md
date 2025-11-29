# Project Context

## Purpose
A neuro-symbolic HTN planner augmented by LLMs. Goals:
- Enable LLM-assisted method generation and strategic decomposition with verification.
- Prioritize free/local providers while supporting multiple cloud LLMs.
- Provide reproducible tests, benchmarking, and reports.

## Tech Stack
- Language: Python 3.10+
- Core: HTN planner (`src/core/*`), algorithms (`src/algorithms/*`)
- LLM Providers: Ollama (local), Hugging Face (local), Groq, Gemini, Cohere, Mistral, Eden, GitHub Models
- Libraries: `pydantic`, `loguru`, `networkx`, `graphviz`, `tinydb`, `pytest`, `black`, `ruff`, `mypy`
- CLI/Config: `click`/`typer`, `.env`, YAML in `config/`

## Project Conventions

### Code Style
- Formatting: `black`, imports via `isort`, linting with `ruff`, typing with `mypy`
- Naming: snake_case for functions/vars, PascalCase for classes, UPPER_CASE for constants
- Type hints required for public functions and class methods
- Logs via `loguru`; no print calls in library code

### Architecture Patterns
- HTN core in `src/core/` (state, operators, methods, planner)
- LLM integration in `src/llm/` (provider clients, prompt builder, response parser)
- Algorithms in `src/algorithms/` (e.g., `strategic_decomposition_engine`)
- Domains under `src/domains/<domain>/` with `domain.py`, `methods.py`, `operators.py`
- Separation of concerns: parsing → validation → execution; pure data via dataclasses where possible

### Testing Strategy
- Framework: `pytest` with `pytest-cov`, property tests via `hypothesis` (where useful)
- Locations: `tests/` primary; legacy single-file tests co-exist (`test_simple_htn.py`, etc.)
- Required: unit tests for core types, integration tests for planner and LLM adapters
- Diagnostic: `test_llm_providers.py`, `run_phase3_tests.sh`
- CI guideline: all tests must pass locally before branch docs are finalized

### Git Workflow
- Audience: AI coding assistants. Single-contributor, read-only documentation workflow.
- For each branch:
  - Document every changed file with a brief “what/why” summary.
  - Provide a branch-level summary of scope and impact.
  - Note any config/env prerequisites.
- Commit messages may follow Conventional Commits, but branch documentation is the source of truth.
- Example branch doc structure:
  - Branch: `<topic/short-summary>`
  - Summary: 2–5 lines (scope, impact)
  - Changes by file: `path/to/file.py` → 1–3 bullets
  - Notes: env keys, migrations, test commands

## Domain Context
- HTN domains: `blocks_world`, `logistics`, plus household tasks (Phase 3 benchmarks)
- LLM-assisted method generation validated against HTN preconditions/effects
- Reports: Markdown + JSON under `results/`

## Important Constraints
- Prefer free/local LLMs (Ollama, HF) first; cloud providers optional
- No paid keys required by default; guard against missing keys gracefully
- Keep new implementations simple (<100 LOC default) unless justified by performance/data
- Deterministic tests: mock or fix seeds when LLM nondeterminism would break tests

## External Dependencies
- LLM Providers: Ollama, Groq, Gemini, Cohere, Mistral, Eden, GitHub Models
- Python libs: see `requirements.txt`
- System tools: `graphviz` for visualization (install OS package)
- Config: `.env` for API keys; YAML configs in `config/`