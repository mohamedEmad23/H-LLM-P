# Phase 3 Quick Start Guide

**Strategic Decomposition Engine (Layer 1) - LLM Ensemble**

---

## 🚀 5-Minute Quick Start

### 1. Setup Environment

```bash
# Option A: GitHub Models (GPT-5, DeepSeek V3, Llama 4)
echo "GITHUB_TOKEN=your_github_pat_here" > .env

# Option B: Local Ollama
ollama serve  # In separate terminal
ollama pull llama3.1:8b

# Option C: Other APIs
echo "GROQ_API_KEY=your_key" >> .env
echo "GOOGLE_API_KEY=your_key" >> .env
```

### 2. Run Tests

```bash
# Activate environment
source .venv/bin/activate  # or ../.venv/bin/activate

# Run tests
./run_phase3_tests.sh

# OR manually
python tests/test_household_tasks.py
```

### 3. View Results

```bash
# View summary
cat results/household_tasks_summary.md

# View JSON
cat results/household_tasks_results.json | jq '.'
```

---

## 📖 Basic Usage

```python
from algorithms.strategic_decomposition_engine import StrategicDecompositionEngine
from llm.github_models_client import GitHubModelsClient
from llm.local_llm_interface import LLMConfig
from llm.prompt_builder import DomainContext

# 1. Initialize engine
engine = StrategicDecompositionEngine()

# 2. Add LLM providers
gpt5 = GitHubModelsClient(
    config=LLMConfig(model_name="openai/gpt-5", temperature=0.7)
)
engine.add_llm_provider("gpt5", gpt5)

# 3. Define domain
domain = DomainContext(
    domain_name="cooking",
    available_operators=["grind", "fill", "brew", "pour"],
    state_variables=["has_ingredient", "clean", "ready"]
)

# 4. Decompose task
result = engine.decompose_task(
    task_name="make_coffee",
    task_description="Make a cup of coffee",
    parameters=["beans", "machine", "cup"],
    domain_context=domain,
    benchmark=True
)

# 5. Get results
print(f"Best LLM: {result['provider_used']}")
print(f"Success rate: {result['benchmark_report'].success_rate:.1%}")
```

---

## 📁 Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/algorithms/strategic_decomposition_engine.py` | Core engine | ~1,100 |
| `tests/test_household_tasks.py` | Test suite | ~700 |
| `docs/PHASE3_STRATEGIC_DECOMPOSITION.md` | Full docs | ~600 |
| `PHASE3_COMPLETE.md` | Summary | ~800 |

---

## 🎯 What It Does

The Strategic Decomposition Engine:
- ✅ Takes a high-level goal (e.g., "make coffee")
- ✅ Uses multiple LLMs to generate HTN methods
- ✅ Validates generated methods automatically
- ✅ Benchmarks all LLMs in real-time
- ✅ Selects the best decomposition
- ✅ Exports performance reports

---

## 🔧 Troubleshooting

**No LLM providers available:**
- Set `GITHUB_TOKEN` in .env
- OR start Ollama: `ollama serve`
- OR add other API keys

**Import errors:**
- Activate venv: `source .venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

**GitHub token not working:**
- Check token has `models` scope
- Visit: https://github.com/settings/tokens

---

## 📊 Expected Output

```
================================================================================
Strategic Decomposition Engine - Household Tasks Testing
================================================================================

✅ 5 LLM provider(s) configured
  ✅ GPT-5 (Azure)
  ✅ DeepSeek V3 (671B MoE)
  ✅ Llama 4 Scout

================================================================================
TEST 1: Make a Cup of Coffee
================================================================================
Benchmarking 5 LLM providers for task: make_coffee
  ✅ gpt5: success (2.134s, confidence: 95%)
  ✅ deepseek_v3: success (2.567s, confidence: 92%)
  ...

✅ Test complete: 80.0% success rate

================================================================================
SUMMARY RESULTS
================================================================================

Overall Success Rate: 82.5%
Average Execution Time: 2.456s

LLM Rankings:
1. gpt5: 100% success, 2.134s avg
2. deepseek_v3: 100% success, 2.567s avg
...
```

---

## 🎓 Learn More

- **Full Documentation**: `docs/PHASE3_STRATEGIC_DECOMPOSITION.md`
- **Completion Summary**: `PHASE3_COMPLETE.md`
- **Quick Reference**: `QUICK_REFERENCE.md`
- **Source Code**: `src/algorithms/strategic_decomposition_engine.py`

---

## ✅ Phase 3 Complete

**Status**: ✅ READY FOR USE
**Total Lines**: ~1,800+ (Phase 3) | ~10,224+ (Cumulative)
**Next**: Phase 4 - Memory & RAG Integration

---

*For detailed information, see full documentation.*
