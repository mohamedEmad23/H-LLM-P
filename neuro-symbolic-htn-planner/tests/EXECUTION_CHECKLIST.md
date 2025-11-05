# Multi-Phase Testing Execution Checklist

Use this checklist to track progress as you run all benchmark tests.

---

## Pre-Execution Setup

- [ ] **Environment activated**: `source .venv/bin/activate`
- [ ] **API keys configured**:
  - [ ] `GROQ_API_KEY` set (check: `echo $GROQ_API_KEY`)
  - [ ] `COHERE_API_KEY` set (check: `echo $COHERE_API_KEY`)
  - [ ] `GOOGLE_API_KEY` set (check: `echo $GOOGLE_API_KEY`)
  - [ ] `HF_TOKEN` set (check: `echo $HF_TOKEN`)
- [ ] **Ollama running** (optional): `ollama serve` in separate terminal
- [ ] **Ollama model pulled** (optional): `ollama pull llama3.2`
- [ ] **Results directories exist**: `mkdir -p results/{phase1,phase3,phase4b}_traces`

---

## Phase 1: Single LLM Testing

**Objective**: Test each provider independently on all 5 problems

### Groq Testing
- [ ] **Run**: `python tests/test_phase1_single_llm.py --provider groq`
- [ ] **Time**: _____ minutes
- [ ] **Average Score**: _____ /100
- [ ] **Problems Passed**: _____ /5
- [ ] **Output Files**:
  - [ ] `results/phase1_traces/phase1_groq_*.json`
  - [ ] `results/phase1_traces/phase1_groq_*.md`
- [ ] **Notes/Issues**: ________________________________

### Cohere Testing
- [ ] **Run**: `python tests/test_phase1_single_llm.py --provider cohere`
- [ ] **Time**: _____ minutes
- [ ] **Average Score**: _____ /100
- [ ] **Problems Passed**: _____ /5
- [ ] **Output Files**:
  - [ ] `results/phase1_traces/phase1_cohere_*.json`
  - [ ] `results/phase1_traces/phase1_cohere_*.md`
- [ ] **Notes/Issues**: ________________________________

### Gemini Testing
- [ ] **Run**: `python tests/test_phase1_single_llm.py --provider gemini`
- [ ] **Time**: _____ minutes
- [ ] **Average Score**: _____ /100
- [ ] **Problems Passed**: _____ /5
- [ ] **Output Files**:
  - [ ] `results/phase1_traces/phase1_gemini_*.json`
  - [ ] `results/phase1_traces/phase1_gemini_*.md`
- [ ] **Notes/Issues**: ________________________________

### Ollama Testing (Optional)
- [ ] **Run**: `python tests/test_phase1_single_llm.py --provider ollama`
- [ ] **Time**: _____ minutes
- [ ] **Average Score**: _____ /100
- [ ] **Problems Passed**: _____ /5
- [ ] **Output Files**:
  - [ ] `results/phase1_traces/phase1_ollama_*.json`
  - [ ] `results/phase1_traces/phase1_ollama_*.md`
- [ ] **Notes/Issues**: ________________________________

### HuggingFace Testing
- [ ] **Run**: `python tests/test_phase1_single_llm.py --provider huggingface`
- [ ] **Time**: _____ minutes
- [ ] **Average Score**: _____ /100
- [ ] **Problems Passed**: _____ /5
- [ ] **Output Files**:
  - [ ] `results/phase1_traces/phase1_huggingface_*.json`
  - [ ] `results/phase1_traces/phase1_huggingface_*.md`
- [ ] **Notes/Issues**: ________________________________

### Phase 1 Summary
- [ ] **Total Time**: _____ minutes
- [ ] **Best Provider**: _____________ (Score: _____ /100)
- [ ] **Fastest Provider**: _____________ (Avg latency: _____ ms)
- [ ] **Most Token Efficient**: _____________ (Avg tokens: _____)

---

## Phase 3: 3-Agent Multi-LLM Testing

**Objective**: Test 3-agent collaboration (Groq + Gemini + Cohere)

- [ ] **Run**: `python tests/test_phase3_multi_agent.py`
- [ ] **Time**: _____ minutes
- [ ] **Average Score**: _____ /100
- [ ] **Problems Passed**: _____ /5
- [ ] **Output Files**:
  - [ ] `results/phase3_traces/phase3_multi_llm_*.json`
  - [ ] `results/phase3_traces/phase3_multi_llm_*.md`

### Performance Analysis
- [ ] **vs Best Phase 1**: Score difference = _____ points
- [ ] **Agent Communication**: _____ messages logged
- [ ] **Cross-Provider Latency**: Avg _____ ms per agent transition
- [ ] **Collaboration Quality**: (Excellent / Good / Fair / Poor)

### Notes/Issues
```
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
```

---

## Phase 4B: 5-Agent Strategic System Testing

**Objective**: Test 5-agent strategic coordination with fallbacks

- [ ] **Run**: `python tests/test_phase4b_strategic.py`
- [ ] **Time**: _____ minutes
- [ ] **Average Score**: _____ /100
- [ ] **Problems Passed**: _____ /5
- [ ] **Output Files**:
  - [ ] `results/phase4b_traces/phase4b_strategic_*.json`
  - [ ] `results/phase4b_traces/phase4b_strategic_*.md`

### Performance Analysis
- [ ] **vs Phase 3**: Score difference = _____ points
- [ ] **vs Best Phase 1**: Score difference = _____ points
- [ ] **Monitoring Value**: (High / Medium / Low)
- [ ] **Validation Value**: (High / Medium / Low)
- [ ] **Fallback Activations**: _____ times (which agents: _____________)

### Agent Performance
- [ ] **MonitoringAgent (HuggingFace)**: (Success / Fallback to Groq)
- [ ] **PlanningAgent (Groq)**: (Success / Fallback to Gemini)
- [ ] **DecompositionAgent (Gemini)**: (Success / Fallback to Cohere)
- [ ] **ExecutionAgent (Cohere)**: (Success / Fallback to Ollama)
- [ ] **ValidationAgent (Ollama)**: (Success / Fallback to HuggingFace)

### Notes/Issues
```
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
```

---

## Cross-Phase Comparison

### Performance Summary

| Phase | Avg Score | Time | Tokens | Cost Est. |
|-------|-----------|------|--------|-----------|
| Phase 1 (Best) | _____ /100 | _____ min | _____ | $_____ |
| Phase 3 | _____ /100 | _____ min | _____ | $_____ |
| Phase 4B | _____ /100 | _____ min | _____ | $_____ |

### Problem-Specific Insights

**Problem 1 (Incomplete Graph)**:
- [ ] Best Phase: _____________
- [ ] Key Insight: _______________________________________________

**Problem 2 (Constrained Hanoi)**:
- [ ] Best Phase: _____________
- [ ] Key Insight: _______________________________________________

**Problem 3 (Probabilistic Graph)**:
- [ ] Best Phase: _____________
- [ ] Key Insight: _______________________________________________

**Problem 4 (Hybrid Puzzle)**:
- [ ] Best Phase: _____________
- [ ] Key Insight: _______________________________________________

**Problem 5 (K-Peg Hanoi)**:
- [ ] Best Phase: _____________
- [ ] Key Insight: _______________________________________________

---

## Analysis & Documentation

- [ ] **Extract quantitative data**: Scores, latencies, tokens from JSON traces
- [ ] **Extract qualitative data**: Reasoning patterns from Markdown traces
- [ ] **Provider comparison matrix**: Create spreadsheet with all metrics
- [ ] **Collaboration analysis**: Document agent communication patterns
- [ ] **Failure mode analysis**: Identify common error patterns
- [ ] **Cost-benefit analysis**: Compare performance vs complexity/cost

---

## Thesis Integration

- [ ] **Methodology section**: Cite test design and evaluation criteria
- [ ] **Results section**: Include tables/graphs from traces
- [ ] **Discussion section**: Analyze multi-agent benefit
- [ ] **Conclusion section**: Summarize optimal configurations
- [ ] **Appendix**: Include sample execution traces

---

## Follow-Up Actions

- [ ] **Optimize provider allocation**: Based on results, adjust LLM assignments
- [ ] **Extend benchmark suite**: Add more challenging problems if needed
- [ ] **Cost optimization**: Identify opportunities to reduce token usage
- [ ] **Fallback tuning**: Adjust fallback chain based on failure patterns
- [ ] **Documentation**: Update README with final results

---

## Final Status

**Execution Date**: ___________________
**Total Time**: _____ minutes
**Overall Success**: (Complete / Partial / Issues)

**Key Findings**:
```
1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________
```

**Recommendations**:
```
1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________
```

---

## Quick Reference Commands

```bash
# Phase 1 - Test all providers
python tests/test_phase1_single_llm.py --provider all

# Phase 1 - Test specific provider
python tests/test_phase1_single_llm.py --provider groq

# Phase 3 - Multi-agent
python tests/test_phase3_multi_agent.py

# Phase 4B - Strategic system
python tests/test_phase4b_strategic.py

# View results
ls -lh results/phase1_traces/
ls -lh results/phase3_traces/
ls -lh results/phase4b_traces/
```

---

**Status**: Ready to execute ✅
**Next Action**: Start with Phase 1 (Groq provider)
