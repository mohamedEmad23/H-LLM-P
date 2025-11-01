# Phase Testing Guide: Multi-LLM Benchmark Suite

## Overview

This guide explains how to run comprehensive tests for all three phases of the Neuro-Symbolic HTN Planner using **real LLM API calls** with strategic provider allocation.

## Architecture Summary

```
Phase 1: Single LLM (Baseline)
├── Test 5 providers independently
├── Each provider tested on all 5 problems
└── Compare single-LLM reasoning capabilities

Phase 3: 3-Agent Multi-LLM System
├── PlanningAgent → Groq (llama-3.3-70b)
├── DecompositionAgent → Gemini (gemini-2.5-flash)
├── ExecutionAgent → Cohere (command-a-03-2025)
└── Test multi-provider collaboration

Phase 4B: 5-Agent Strategic System
├── MonitoringAgent → HuggingFace (Llama-3.3-70B) [fallback: Groq]
├── PlanningAgent → Groq (llama-3.3-70b) [fallback: Gemini]
├── DecompositionAgent → Gemini (gemini-2.5-flash) [fallback: Cohere]
├── ExecutionAgent → Cohere (command-a-03-2025) [fallback: Ollama]
├── ValidationAgent → Ollama (llama3.2) [fallback: HuggingFace]
└── Test strategic coordination with fallbacks
```

## Benchmark Problems (All Phases)

1. **Incomplete Knowledge Graph**: A→D with unknown edge B→C
2. **Constrained Hanoi**: 3 disks, constraint: disk 3 cannot use peg B
3. **Probabilistic Graph**: Expected value decision (Path A: 30min vs Path B: 50% 10min, 50% 40min)
4. **Hybrid Puzzle**: Hierarchical planning (locked peg requires unlock graph traversal)
5. **K-Peg Hanoi**: 5 disks, 4 pegs (Frame-Stewart algorithm: 13 moves vs standard 31)

---

## Phase 1: Single LLM Testing

### File: `tests/test_phase1_single_llm.py`

Tests single LLM reasoning with 5 different providers independently.

### Usage

**Test specific provider:**
```bash
python tests/test_phase1_single_llm.py --provider groq
python tests/test_phase1_single_llm.py --provider cohere
python tests/test_phase1_single_llm.py --provider gemini
python tests/test_phase1_single_llm.py --provider ollama
python tests/test_phase1_single_llm.py --provider huggingface
```

**Test all providers:**
```bash
python tests/test_phase1_single_llm.py --provider all
```

### Expected Output

```
====================================
PHASE 1: SINGLE LLM TESTING
Provider: Groq (llama-3.3-70b-versatile)
====================================

[Problem 1: Incomplete Graph] ✓ Score: 85/100 | Knowledge gap recognized, research suggested
[Problem 2: Constrained Hanoi] ✓ Score: 100/100 | Constraint respected, optimal sequence
[Problem 3: Probabilistic Graph] ✓ Score: 100/100 | Expected value calculated correctly
[Problem 4: Hybrid Puzzle] ✓ Score: 90/100 | Hierarchical decomposition identified
[Problem 5: K-Peg Hanoi] ✓ Score: 70/100 | Frame-Stewart algorithm mentioned

====================================
GROQ SUMMARY
Average Score: 89.0/100
Problems Passed: 5/5
====================================

✓ Saved traces to: results/phase1_traces/phase1_groq_20251101_224530.*
```

### Output Files

- **JSON**: `results/phase1_traces/phase1_{provider}_{timestamp}.json`
  - Full execution logs
  - LLM calls with latency/tokens
  - Evaluation scores per problem
  
- **Markdown**: `results/phase1_traces/phase1_{provider}_{timestamp}.md`
  - Human-readable report
  - LLM response excerpts
  - Performance metrics

### Evaluation Criteria

| Problem | Success Criteria |
|---------|------------------|
| 1 | Recognizes unknown edge, suggests research |
| 2 | Respects constraint, valid sequence |
| 3 | Calculates expected value (25min for B) |
| 4 | Identifies hierarchical structure |
| 5 | Mentions Frame-Stewart or 13 moves |

---

## Phase 3: 3-Agent Multi-LLM Testing

### File: `tests/test_phase3_multi_agent.py`

Tests 3-agent collaboration with **3 different LLMs** (one per agent).

### Architecture

```
PlanningAgent (Groq)
    ↓ message
DecompositionAgent (Gemini)
    ↓ message
ExecutionAgent (Cohere)
```

### Usage

```bash
python tests/test_phase3_multi_agent.py
```

### Expected Output

```
Initializing 3-Agent Multi-LLM System...
✓ PlanningAgent: Groq llama-3.3-70b
✓ DecompositionAgent: Gemini 2.5-flash
✓ ExecutionAgent: Cohere command-a

================================================================================
PHASE 3: 3-AGENT MULTI-LLM SYSTEM
Planning(Groq) | Decomposition(Gemini) | Execution(Cohere)
================================================================================

[Problem 1: Incomplete Graph] ✓ Score: 100/100 | 3-agent collaboration: research then optimal path
[Problem 2: Constrained Hanoi] ✓ Score: 100/100 | Strategic constraint handling: 7 moves, perfect
[Problem 3: Probabilistic Graph] ✓ Score: 100/100 | EV-based decision: Path B (25 min EV)
[Problem 4: Hybrid Puzzle] ✓ Score: 100/100 | Hierarchical coordination: Unlock→Tower (optimal)
[Problem 5: K-Peg Hanoi] ✓ Score: 100/100 | Multi-agent algorithm discovery: Frame-Stewart (13 moves)

================================================================================
PHASE 3 SUMMARY
Average Score: 100.0/100
Problems Passed: 5/5
================================================================================

✓ Saved traces to: results/phase3_traces/phase3_multi_llm_20251101_224800.*
```

### Output Files

- **JSON**: `results/phase3_traces/phase3_multi_llm_{timestamp}.json`
  - Agent-to-agent messages
  - LLM calls per agent with provider tags
  - HTN decompositions
  
- **Markdown**: `results/phase3_traces/phase3_multi_llm_{timestamp}.md`
  - Communication flow
  - Multi-LLM coordination patterns
  - Performance analysis

### Evaluation Focus

- **Collaboration Quality**: How well do different LLMs coordinate?
- **Message Passing**: Is information preserved across agents?
- **Provider Strengths**: Which LLM excels at planning vs execution?
- **Latency Overhead**: Cross-provider communication cost

---

## Phase 4B: 5-Agent Strategic Testing

### File: `tests/test_phase4b_strategic.py`

Tests 5-agent system with **5 different LLMs + fallback providers**.

### Architecture

```
MonitoringAgent (HuggingFace) → [fallback: Groq]
    ↓
PlanningAgent (Groq) → [fallback: Gemini]
    ↓
DecompositionAgent (Gemini) → [fallback: Cohere]
    ↓
ExecutionAgent (Cohere) → [fallback: Ollama]
    ↓
ValidationAgent (Ollama) → [fallback: HuggingFace]
```

### Usage

```bash
python tests/test_phase4b_strategic.py
```

### Expected Output

```
Initializing 5-Agent Strategic System with fallback providers...
✓ MonitoringAgent: HuggingFace Llama-3.3-70B
✓ PlanningAgent: Groq llama-3.3-70b
✓ DecompositionAgent: Gemini 2.5-flash
✓ ExecutionAgent: Cohere command-a
✓ ValidationAgent: Ollama llama3.2 (local)

================================================================================
PHASE 4B: 5-AGENT STRATEGIC SYSTEM (Multi-LLM + Fallback)
Monitor(HF/Groq) | Plan(Groq) | Decompose(Gemini) | Execute(Cohere) | Validate(Ollama/HF)
================================================================================

[Problem 1: Incomplete Graph] ✓ Score: 100/100 | 5-agent strategic system: Monitor→Plan→Decompose→Execute→Validate. Optimal: 17
[Problem 2: Constrained Hanoi] ✓ Score: 100/100 | Strategic constraint handling: 7 moves, perfect
[Problem 3: Probabilistic Graph] ✓ Score: 100/100 | Strategic EV calculation: True
[Problem 4: Hybrid Puzzle] ✓ Score: 100/100 | Strategic hierarchy: Optimal path = True
[Problem 5: K-Peg Hanoi] ✓ Score: 100/100 | Strategic discovery: Frame-Stewart (13 moves)

================================================================================
PHASE 4B SUMMARY
Average Score: 100.0/100
Problems Passed: 5/5
================================================================================

✓ Saved traces to: results/phase4b_traces/phase4b_strategic_20251101_225100.*
```

### Output Files

- **JSON**: `results/phase4b_traces/phase4b_strategic_{timestamp}.json`
  - Full 5-agent workflow
  - Fallback activation logs
  - Strategic decision points
  
- **Markdown**: `results/phase4b_traces/phase4b_strategic_{timestamp}.md`
  - Strategic coordination analysis
  - Fallback mechanism effectiveness
  - Performance comparison

### Evaluation Focus

- **Strategic Planning**: Does monitoring improve outcomes?
- **Validation Quality**: Does validation catch errors?
- **Fallback Effectiveness**: Do fallbacks activate correctly?
- **System Robustness**: Performance under provider failures

---

## Running Complete Test Suite

### Sequential Execution

```bash
# Phase 1 - all providers
python tests/test_phase1_single_llm.py --provider all

# Phase 3 - multi-LLM collaboration
python tests/test_phase3_multi_agent.py

# Phase 4B - strategic system
python tests/test_phase4b_strategic.py
```

### Batch Script (Linux/Mac)

```bash
#!/bin/bash

echo "=== PHASE 1: Testing all providers ==="
for provider in groq cohere gemini ollama huggingface; do
    echo "Testing $provider..."
    python tests/test_phase1_single_llm.py --provider $provider
done

echo "=== PHASE 3: Multi-LLM collaboration ==="
python tests/test_phase3_multi_agent.py

echo "=== PHASE 4B: Strategic system ==="
python tests/test_phase4b_strategic.py

echo "=== ALL TESTS COMPLETE ==="
```

---

## Analysis & Comparison

### Cross-Phase Comparison

After running all tests, compare:

1. **Provider Performance (Phase 1)**:
   - Which provider scores highest on each problem?
   - Latency comparison: Groq vs Cohere vs Gemini vs Ollama vs HuggingFace
   - Token efficiency
   
2. **Multi-LLM Benefit (Phase 3)**:
   - Does 3-agent system outperform single LLM?
   - Which agent combinations work best?
   - Communication overhead cost
   
3. **Strategic Value (Phase 4B)**:
   - Does 5-agent system justify complexity?
   - Monitoring/Validation ROI
   - Fallback mechanism effectiveness

### Generate Comparison Report

```python
import json
from pathlib import Path

# Load all traces
phase1_traces = list(Path("results/phase1_traces").glob("*.json"))
phase3_traces = list(Path("results/phase3_traces").glob("*.json"))
phase4b_traces = list(Path("results/phase4b_traces").glob("*.json"))

# Compare average scores
for trace_file in phase1_traces:
    with open(trace_file) as f:
        data = json.load(f)
        # Extract scores, latencies, etc.
```

---

## Troubleshooting

### Issue: "Provider not available"

**Symptom**: `⚠ HuggingFace failed, using Groq fallback`

**Solution**: Check API keys in environment or `.env`:
```bash
export GROQ_API_KEY="..."
export COHERE_API_KEY="..."
export GOOGLE_API_KEY="..."
export HF_TOKEN="..."
```

### Issue: Ollama not running

**Symptom**: `⚠ Ollama not available, using HuggingFace fallback`

**Solution**: Start Ollama service:
```bash
ollama serve  # In separate terminal
ollama pull llama3.2  # If not already pulled
```

### Issue: Rate limiting

**Symptom**: `429 Too Many Requests`

**Solution**: 
- Add delays between tests (modify code: `time.sleep(2)`)
- Use provider-specific rate limit configs
- Upgrade API tier (Groq, Cohere, etc.)

### Issue: Timeout errors

**Symptom**: Request takes too long, no response

**Solution**: Increase timeout in LLM client config:
```python
config = LLMConfig(model_name="...", timeout=60)  # 60 seconds
```

---

## Environment Requirements

### Required API Keys

```bash
# .env file
GROQ_API_KEY=gsk_...
COHERE_API_KEY=...
GOOGLE_API_KEY=AIza...
HF_TOKEN=hf_...
```

### Required Packages

```bash
pip install -r requirements.txt
```

Includes:
- `groq`
- `cohere`
- `google-generativeai`
- `huggingface_hub`
- `ollama` (optional, for local testing)

---

## Expected Timeline

- **Phase 1 (all providers)**: ~15-20 minutes (5 providers × 5 problems × ~30s each)
- **Phase 3**: ~5-7 minutes (5 problems × ~1min each)
- **Phase 4B**: ~8-10 minutes (5 problems × ~1.5min each)

**Total**: ~30-40 minutes for complete suite

---

## Output Structure

```
results/
├── phase1_traces/
│   ├── phase1_groq_20251101_224530.json
│   ├── phase1_groq_20251101_224530.md
│   ├── phase1_cohere_20251101_224820.json
│   ├── phase1_cohere_20251101_224820.md
│   ├── phase1_gemini_...
│   ├── phase1_ollama_...
│   └── phase1_huggingface_...
│
├── phase3_traces/
│   ├── phase3_multi_llm_20251101_225400.json
│   └── phase3_multi_llm_20251101_225400.md
│
└── phase4b_traces/
    ├── phase4b_strategic_20251101_230100.json
    └── phase4b_strategic_20251101_230100.md
```

---

## Next Steps

1. **Run all tests** to collect real LLM responses
2. **Analyze results** to identify optimal provider combinations
3. **Compare phases** to validate multi-agent benefit
4. **Document findings** in thesis with execution traces as evidence
5. **Optimize** based on latency/cost/accuracy tradeoffs

---

## Questions?

See also:
- `results/EXECUTION_TRACING_COMPLETE.md` - Logging system documentation
- `results/USING_LOGS_FOR_THESIS.md` - How to use logs for thesis writing
- `docs/PHASE3_QUICKSTART.md` - Multi-agent architecture overview
