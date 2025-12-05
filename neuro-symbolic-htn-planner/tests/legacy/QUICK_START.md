# Quick Start: Run All Benchmark Tests

## 🚀 Fast Track

```bash
# Activate environment
cd /home/mohammed-emad/VS-CODE/B.Sc\ Thesis/gpt-htn-thesis/neuro-symbolic-htn-planner
source .venv/bin/activate

# Phase 1: Test single LLM (choose one)
python tests/test_phase1_single_llm.py --provider groq         # Fast (Groq)
python tests/test_phase1_single_llm.py --provider cohere       # Reliable (Cohere)
python tests/test_phase1_single_llm.py --provider gemini       # Latest (Google)
python tests/test_phase1_single_llm.py --provider ollama       # Local (Ollama)
python tests/test_phase1_single_llm.py --provider huggingface # Hub (HF)
python tests/test_phase1_single_llm.py --provider all          # All providers

# Phase 3: Test 3-agent multi-LLM
python tests/test_phase3_multi_agent.py

# Phase 4B: Test 5-agent strategic system
python tests/test_phase4b_strategic.py
```

## 📊 What Gets Tested

**5 Benchmark Problems** (across all phases):
1. Incomplete Knowledge Graph (unknown edge research)
2. Constrained Hanoi (disk 3 cannot use peg B)
3. Probabilistic Graph (expected value decision)
4. Hybrid Puzzle (hierarchical planning)
5. K-Peg Hanoi (Frame-Stewart algorithm)

## 🎯 Expected Results

### Phase 1 (Single LLM)
- **Best**: Groq ~89/100, Gemini ~87/100
- **Good**: Cohere ~85/100, HuggingFace ~82/100
- **Local**: Ollama ~75/100 (depends on local setup)

### Phase 3 (3-Agent)
- **Expected**: 95-100/100 (collaboration benefit)
- **Agents**: Planning(Groq) + Decomposition(Gemini) + Execution(Cohere)

### Phase 4B (5-Agent)
- **Expected**: 98-100/100 (strategic coordination)
- **Agents**: Monitor(HF) + Plan(Groq) + Decompose(Gemini) + Execute(Cohere) + Validate(Ollama)

## 📁 Output Locations

```
results/
├── phase1_traces/phase1_{provider}_{timestamp}.json
├── phase3_traces/phase3_multi_llm_{timestamp}.json
└── phase4b_traces/phase4b_strategic_{timestamp}.json
```

## ⚡ Time Estimates

- Phase 1 (one provider): ~3-4 minutes
- Phase 1 (all providers): ~15-20 minutes
- Phase 3: ~5-7 minutes
- Phase 4B: ~8-10 minutes

**Total for all**: ~30-40 minutes

## 🔑 Prerequisites

### API Keys Required
```bash
# Add to .env file or export
export GROQ_API_KEY="gsk_..."
export COHERE_API_KEY="..."
export GOOGLE_API_KEY="AIza..."
export HF_TOKEN="hf_..."
```

### Ollama (Optional)
```bash
# Terminal 1: Start server
ollama serve

# Terminal 2: Pull model
ollama pull llama3.2
```

## 🐛 Quick Fixes

### "Provider not available"
→ Check API keys in `.env`

### "Ollama not running"
→ `ollama serve` in separate terminal

### "Rate limit exceeded"
→ Wait 60 seconds, retry

### "Timeout error"
→ Normal for HuggingFace (cold start), fallback will activate

## 📖 Full Documentation

See `tests/PHASE_TESTING_GUIDE.md` for:
- Detailed architecture explanations
- Evaluation criteria per problem
- Cross-phase comparison strategies
- Troubleshooting guide

## 🎓 Thesis Usage

After running tests:
1. Open JSON traces for quantitative data (latency, tokens, scores)
2. Open MD traces for qualitative analysis (reasoning patterns)
3. Compare Phase 1 vs Phase 3 vs Phase 4B results
4. Document multi-LLM collaboration benefits

See `results/USING_LOGS_FOR_THESIS.md` for examples.

---

**Ready?** Start with:
```bash
python tests/test_phase1_single_llm.py --provider groq
```
