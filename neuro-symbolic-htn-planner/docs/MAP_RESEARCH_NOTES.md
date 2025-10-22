# MAP (Modular Agentic Planner) Research Notes

**Paper**: "Improving Planning with Large Language Models: A Modular Agentic Architecture"  
**Authors**: Taylor Webb, Shanka Subhra Mondal, Ida Momennejad  
**Published**: Nature Communications, 2025 (arXiv:2310.00194v4, Oct 2024)  
**Institution**: Microsoft Research + Princeton University  

---

## Executive Summary

MAP is a brain-inspired, modular multi-agent architecture that significantly improves LLM planning performance through specialized agent collaboration. It achieved **74% success** on Tower of Hanoi (3-disk) vs **11% zero-shot GPT-4**, outperforming Chain-of-Thought, Tree-of-Thought, and Multi-Agent Debate.

### Key Innovation

Instead of a single LLM handling all planning aspects, MAP decomposes planning into **6 specialized modules** (TaskDecomposer, Actor, Monitor, Predictor, Evaluator, Orchestrator), each implemented as an LLM with role-specific prompting.

---

## Core Architecture

### 6 Specialized Modules

#### 1. **TaskDecomposer**
- **Function**: Generates subgoals using goal recursion strategy
- **Inspired by**: Anterior PFC (task decomposition, coordination)
- **Input**: Current state $x$, goal $y$
- **Output**: Set of subgoals $Z$
- **Prompt**: Few-shot with goal recursion strategy description
- **Example**: Move smallest number to target, recursively solve smaller problems

#### 2. **Actor**
- **Function**: Proposes $B$ candidate actions given state and subgoal
- **Inspired by**: Actor-Critic framework (RL)
- **Input**: State $x$, subgoal $z$, feedback $\epsilon$ (from Monitor)
- **Output**: $B$ proposed actions $A = \{a_1, \ldots, a_B\}$
- **Temperature**: Scaled iteratively if fails to generate distinct actions
- **Example**: For Tower of Hanoi, proposes 2 distinct valid moves

#### 3. **Monitor**
- **Function**: Gates actions, validates against task rules
- **Inspired by**: Anterior Cingulate Cortex (conflict monitoring)
- **Input**: State $x$, proposed actions $A$
- **Output**: Validity assessment $\sigma$, feedback $\epsilon$
- **Prompt**: Chain-of-thought reasoning, checks each rule
- **Key**: Eliminates hallucinated/invalid actions (0% invalid in MAP vs 30% baseline)

#### 4. **Predictor**
- **Function**: Predicts next state given action
- **Inspired by**: Model-based RL (world model)
- **Input**: State $x$, action $a$
- **Output**: Predicted next state $\tilde{x}$
- **Used in**: Tree search (Algorithm 3)

#### 5. **Evaluator**
- **Function**: Estimates state value (distance to goal)
- **Inspired by**: Orbitofrontal Cortex (state evaluation)
- **Input**: Predicted state $\tilde{x}$, goal $y$
- **Output**: Value estimate $v$ (min steps to goal)
- **Prompt**: Heuristic function + few-shot examples
- **Example**: For Tower of Hanoi, "sum of distances" heuristic

#### 6. **Orchestrator**
- **Function**: Determines goal achievement, terminates planning
- **Inspired by**: Anterior PFC (task coordination)
- **Input**: State $x$, subgoal $z$
- **Output**: Achievement assessment $\Omega$
- **When**: After each subgoal, checks if complete

---

## Planning Algorithms

### Algorithm 1: MAP (Main)

```python
Function MAP(x, y, T, L, B):
    P ← []  # Initialize plan
    Z ← TaskDecomposer(x, y)  # Generate subgoals
    
    for g in 1..length(Z)+1:
        if g ≤ length(Z):
            z ← Z_g  # Current subgoal
        else:
            z ← y  # Final goal
        
        while not Orchestrator(x, z) and length(P) < T:
            a ← Search(1, L, B, x, z)  # Tree search
            x ← Execute(a)  # Apply action
            P ← P + [a]  # Add to plan
    
    return P
```

### Algorithm 2: ProposeAction (Action Proposal Loop)

```python
Function ProposeAction(x, y, B):
    σ ← false  # Initialize validity
    E ← {}  # Initialize feedback
    
    while σ is false:
        A ← Actor(x, y, E, B)  # Sample B actions
        σ, ε ← Monitor(x, A)  # Check validity
        E ← E ∪ {ε}  # Accumulate feedback
    
    return A
```

- **Key**: Iterative feedback loop between Actor and Monitor
- **Benefit**: Eliminates invalid actions before execution

### Algorithm 3: Search (Tree Search)

```python
Function Search(l, L, B, x, y):
    V_l ← {}  # Value record
    X̃_l ← {}  # Next-state record
    A_l ← ProposeAction(x, y, B)
    
    for b in 1..B:
        x̃_lb ← Predictor(x, A_lb)  # Predict next state
        
        if l < L:
            a_lb ← Search(l+1, L, B, x̃_lb, y)  # Recursive search
            x̃_lb ← Predictor(x̃_lb, a_lb)
        
        v_lb ← Evaluator(x̃_lb, y)  # Evaluate state
        V_l ← V_l ∪ {v_lb}
        X̃_l ← X̃_l ∪ {x̃_lb}
    
    return A_l[argmax(V_l)]  # Best action
```

- **Depth**: $L = 2$ (best tradeoff between performance and cost)
- **Branching**: $B = 2$ actions per state
- **Optimization**: Caching + reusing results from deeper layers

---

## Experimental Results

### Tower of Hanoi (3-disk)

| Method | % Solved | % Invalid Actions |
|--------|----------|-------------------|
| GPT-4 Zero-shot | 11% | 30% |
| GPT-4 ICL | 46% | 12% |
| GPT-4 CoT | 42% | 19% |
| Multi-Agent Debate | 25% | 24% |
| Tree-of-Thought | 25% | 4% |
| **MAP (GPT-4)** | **74%** (100% best) | **0%** |
| MAP (Llama3-70B) | 50% | 2% |

- **Key**: MAP eliminates invalid actions completely (Monitor module)
- **Generalization**: 24% success on 4-disk (OOD) vs 0-2% baselines

### Graph Traversal

| Task | MAP | GPT-4 CoT | ToT |
|------|-----|-----------|-----|
| Valuepath | 100% | 91% | 55% |
| Steppath (4-step) | 95% | 47% | 50% |
| Detour | 85% | 69% | 33% |
| Reward Revaluation | 48% | 54% | 36% |

### PlanBench (Mystery BlocksWorld & Logistics)

| Method | Mystery BW | Logistics |
|--------|------------|-----------|
| GPT-4 Zero-shot | 0.2% | 7% |
| GPT-4 ICL | 7.8% | 12% |
| GPT-4 CoT | 10.6% | 17% |
| **MAP** | **27.4%** | **24%** |

- **Note**: MAP didn't use tree search (too expensive)
- **Still outperformed** baselines significantly

### StrategyQA (Multi-step Reasoning)

| Method | Accuracy |
|--------|----------|
| Human | 81.7% |
| GPT-4 CoT | 84.7% |
| ToT | 87.7% |
| **MAP** | **87.0%** |

---

## Key Findings

### 1. Modularity Matters

**Ablation Study** (Tower of Hanoi 3-disk):
- **Full MAP**: 74% solved
- **w/o Monitor**: 27% solved, 31% invalid actions (!)
- **w/o TaskDecomposer**: 50% solved
- **w/o Tree Search**: 32% solved

→ **Monitor is most critical** module (prevents hallucinations)

### 2. Smaller LLMs Work

**Llama3-70B + MAP** (50% success) > **GPT-4 ICL** (46% success)

→ Modularity compensates for model size

### 3. Transfer Learning

MAP shows superior transfer:
- **n7tree → n15star**: 80% (MAP) vs 5% (ICL), 65% (CoT)
- **BlocksWorld → Mystery BW**: 12.2% (MAP) vs 10% (ICL)
- **ToH → Mystery BW**: 6.6% (MAP) vs 0% (ICL), 1.4% (CoT)

### 4. Computational Cost

**Per-problem (Tower of Hanoi 3-disk)**:
- **GPT-4 ICL**: 1 prompt, 810 tokens, 190s, 46% solved
- **MAP**: 148.6 prompts, 109K tokens, 14.5s, 74% solved
- **MAP (efficient)**: 42 prompts, 47K tokens, 2.8s, 77% solved (with caching)

→ **2-3x token increase**, but **higher success rate**

---

## Brain-Inspired Design

MAP modules map to prefrontal cortex (PFC) subregions:

| MAP Module | Brain Region | Function |
|------------|--------------|----------|
| TaskDecomposer | Anterior PFC | Task decomposition, goal hierarchy |
| Actor | Motor cortex | Action generation |
| Monitor | Anterior Cingulate Cortex | Conflict monitoring, error detection |
| Predictor | Orbitofrontal Cortex | State prediction |
| Evaluator | Orbitofrontal Cortex | State/action evaluation |
| Orchestrator | Anterior PFC | Task coordination, goal tracking |

→ Human planning = **recurrent interaction** of specialized regions

---

## Comparison: MAP vs Other Methods

### vs Chain-of-Thought (CoT)
- **CoT**: Single LLM, autoregressive reasoning
- **MAP**: Multiple modules, iterative refinement
- **Advantage**: MAP catches errors (Monitor), explores alternatives (tree search)

### vs Tree-of-Thought (ToT)
- **ToT**: Generator + Evaluator (2 modules)
- **MAP**: 6 specialized modules
- **Advantage**: MAP has dedicated Monitor (error detection), TaskDecomposer (goal hierarchy), Orchestrator (termination)
- **Result**: MAP > ToT on all tasks

### vs Multi-Agent Debate (MAD)
- **MAD**: Multiple LLMs with same prompts (debate)
- **MAP**: Multiple LLMs with specialized prompts
- **Advantage**: Specialization > general debate

---

## Prompting Strategies

### TaskDecomposer Prompt

```
Use the goal recursion strategy. First if the smallest number 
isn't at the correct position in list C, then set the subgoal 
of moving the smallest number to its correct position in list C. 
But before that, the numbers larger than the smallest number and 
present in the same list as the smallest number must be moved to 
a list other than list C...
```

- **Strategy**: Goal recursion (recursive subgoal decomposition)
- **Few-shot**: 2 examples with step-by-step reasoning

### Monitor Prompt

```
Check if the proposed move satisfies or violates Rule #1 and Rule #2.
Rule #1: You can only move a number if it is at the rightmost end.
Rule #2: You can only move to a list if larger than all numbers.
```

- **Strategy**: Chain-of-thought validation
- **Few-shot**: 2 examples (1 valid, 1 invalid)

### Evaluator Prompt

```
Predict the minimum number of valid moves required to reach the 
goal configuration from the current configuration using the 
"sum of distances" heuristic.
```

- **Strategy**: Heuristic function generation + few-shot evaluation
- **Two-step**: 1) Generate heuristic, 2) Apply heuristic

---

## Failure Modes (Analyzed on Tower of Hanoi)

**6 failures out of 24 problems (75% success)**:

| Failure Mode | Frequency | Responsible Module |
|--------------|-----------|---------------------|
| Incorrect decomposition | 2/6 | TaskDecomposer |
| No progress | 6/6 | Actor + Evaluator |
| Falling into loops | 5/6 | Actor + Evaluator |

- **Perfect modules**: Monitor, Predictor, Orchestrator (0 failures)
- **Needs improvement**: TaskDecomposer (2/6), Actor/Evaluator (6/6)

---

## Implementation Details

### Hyperparameters

- **LLM**: GPT-4 (32K context for ToH/CogEval, 128K for PlanBench/StrategyQA)
- **Temperature**: 0 (most modules), scaled for Actor (0.1 increments if not diverse)
- **Top-p**: 0
- **Tree Search**: $B=2$ branches, $L=2$ depth
- **Max Actions**: $T=10$ (ToH 3-disk), $T=20$ (ToH 4-disk), $T=6$ (graph)
- **Few-shot**: 2-3 examples per module

### Optimization: Caching

MAP (efficient) caches:
- Actor proposals (if state unchanged)
- Predictor outputs (if action unchanged)
- Evaluator scores (if state unchanged)

→ **65% reduction in prompts** (148 → 42), same performance

---

## Relevance to Our HTN Planner

### Direct Mappings

| MAP Module | Our Component | Notes |
|------------|---------------|-------|
| TaskDecomposer | Strategic Decomposition Engine | Already have subgoal generation |
| Actor | Decomposition Engine | Generate Methods (not actions) |
| Monitor | Execution Agent (new) | Validate Methods against domain |
| Predictor | Context Agent (new) | Predict state after Method |
| Evaluator | Verification Agent (new) | Estimate Method quality |
| Orchestrator | Coordination Agent (new) | Manage HTN planning loop |

### Differences

| Aspect | MAP | Our System |
|--------|-----|------------|
| **Planning Type** | Classical planning (action sequences) | HTN planning (task decomposition) |
| **Output** | Action plan | Method hierarchy |
| **Validation** | Action validity | Method soundness (subtasks achievable) |
| **State Space** | Fixed (e.g., Tower of Hanoi lists) | Dynamic (user-defined predicates) |
| **Domain** | Encoded in prompts | Explicit (Methods, Operators, State) |

### Adaptations Needed

1. **Actor → DecompositionAgent**: Generate Methods (not actions)
2. **Monitor → ExecutionAgent**: Validate Methods (not actions)
3. **Predictor → ContextAgent**: Predict state after Method execution
4. **Evaluator → VerificationAgent**: Estimate Method quality (not action value)
5. **Tree Search**: Adapt to Method space (not action space)

---

## Takeaways for Implementation

### 1. **Modularity is Key**
- Don't combine Monitor + Evaluator (like ToT does)
- Separate concerns: planning, generation, validation, prediction, evaluation

### 2. **Monitor is Critical**
- Prevents hallucinations (most common LLM failure)
- Iterative feedback loop with Actor/DecompositionAgent

### 3. **Few-Shot > Zero-Shot**
- All modules use 2-3 in-context examples
- Chain-of-thought reasoning in prompts

### 4. **Optimize Later**
- Start with full MAP (no caching)
- Add caching after measuring bottlenecks

### 5. **Benchmark Everything**
- Compare: Multi-Agent vs Ensemble vs Single-LLM
- Metrics: Success rate, tokens, time, quality

### 6. **Smaller LLMs Can Work**
- Llama3-70B + MAP > GPT-4 baseline
- Consider: DeepSeek V3 (671B) for complex agents, Ollama (local) for validation

---

## Open Questions for Our Implementation

1. **How to adapt tree search to HTN?**
   - MAP searches action space (depth 2)
   - HTN has Method space (variable depth)
   - Solution: Search Method decompositions, limit depth

2. **What is HTN equivalent of "state value"?**
   - MAP: Estimated steps to goal
   - HTN: Estimated Methods to complete task?
   - Or: Estimated primitive operators in full plan?

3. **How to handle Method preconditions?**
   - MAP validates action preconditions (simple rules)
   - HTN validates Method preconditions (complex predicates)
   - Solution: ExecutionAgent checks precondition achievability

4. **Should we keep ensemble benchmarking?**
   - MAP uses single LLM for all modules
   - Our Strategic Decomposition Engine benchmarks multiple LLMs
   - Solution: Support both modes (multi-agent + ensemble)

5. **How to measure Method quality?**
   - MAP counts steps to goal
   - HTN has hierarchical decomposition
   - Solution: Count total primitive operators, measure plan depth

---

## Code Repository

**GitHub**: https://github.com/MAPLLM/MAPICLR2025sub

**Files of Interest**:
- `/prompts/`: Agent prompts for ToH, CogEval, PlanBench, StrategyQA
- `/algorithms/`: MAP algorithm implementations
- `/results/`: Benchmark results, ablation studies

---

## Citation

```bibtex
@article{webb2024improving,
  title={Improving Planning with Large Language Models: A Modular Agentic Architecture},
  author={Webb, Taylor and Mondal, Shanka Subhra and Momennejad, Ida},
  journal={Nature Communications},
  year={2025},
  note={arXiv:2310.00194}
}
```

---

**End of MAP Research Notes**

This document summarizes the key insights from the MAP paper relevant to implementing a multi-agent HTN planning system. The architecture is well-suited for adaptation to our neuro-symbolic HTN planner.
