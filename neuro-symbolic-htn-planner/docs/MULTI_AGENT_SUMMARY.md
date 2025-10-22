# Multi-Agent Architecture Design - Summary

**Date**: January 2025  
**Status**: Design Phase Complete ✅  
**Next Steps**: Implementation Phase  

---

## 🎯 What Was Accomplished

I've completed a comprehensive research and design phase for integrating **Multi-Agent Specialization** into your Neuro-Symbolic HTN Planner, inspired by the Modular Agentic Planner (MAP) research from Microsoft Research and Princeton.

---

## �� Research Foundation

### MAP Paper Analysis
**Source**: "Improving Planning with Large Language Models: A Modular Agentic Architecture" (Webb et al., Nature Communications 2025)

**Key Findings**:
- **74% success rate** on Tower of Hanoi (3-disk) vs 11% zero-shot GPT-4
- Outperformed Chain-of-Thought (42%), Tree-of-Thought (25%), Multi-Agent Debate (25%)
- **0% invalid actions** (vs 30% baseline) through specialized Monitor module
- Smaller LLMs work: Llama3-70B + MAP > GPT-4 baseline
- **Brain-inspired modularity**: 6 specialized modules map to prefrontal cortex functions

**MAP's 6 Core Modules**:
1. **TaskDecomposer**: Generates subgoals using goal recursion
2. **Actor**: Proposes multiple candidate actions
3. **Monitor**: Validates actions against task constraints (prevents hallucinations)
4. **Predictor**: Forecasts next states (world model)
5. **Evaluator**: Estimates state value (distance to goal)
6. **Orchestrator**: Coordinates modules, determines goal achievement

### Multi-Agent HTN Research
- **MA-HTN** (Cardoso & Bordini, 2017): Multi-agent extension of HTN formalism
- **T-HTN** (Parimi, 2021): Timeline-based HTN for multi-agent systems
- **HATP** (Lallement et al., 2018): Hierarchical agent-based task planner

---

## 🏗️ Architecture Design

### Evolution Path

```
Stage 1: LLM-to-Planner (Completed)
         ↓
Stage 2: LLM-as-Modeler (Current - Strategic Decomposition Engine)
         ↓
Stage 3: LLM-as-Orchestrator (NEW - Multi-Agent System) ⭐
```

### 6 Specialized Agents (HTN-Adapted)

#### 1. **Planning Agent** (Strategic Analysis)
**Role**: Analyze high-level goals, generate subgoal hierarchies  
**Inspired by**: MAP's TaskDecomposer + Anterior PFC  
**Input**: Task, state, domain context  
**Output**: Decomposition strategy, subgoals, priority order  

#### 2. **Decomposition Agent** (Method Generation)
**Role**: Generate HTN methods (task → subtask sequences)  
**Inspired by**: MAP's Actor + your Strategic Decomposition Engine  
**Input**: Task, subgoals, domain context  
**Output**: Candidate methods with confidence scores  

#### 3. **Context Management Agent** (State Tracking)
**Role**: Predict state transitions, track dependencies  
**Inspired by**: MAP's Predictor  
**Input**: Current state, proposed action  
**Output**: Predicted state, constraint violations, dependencies  

#### 4. **Execution Agent** (Action Validation)
**Role**: Validate methods against domain rules  
**Inspired by**: MAP's Monitor + Anterior Cingulate Cortex  
**Input**: Proposed method, domain context  
**Output**: Validation result, feedback, suggested fixes  
**KEY**: Prevents hallucinated methods/operators!

#### 5. **Verification Agent** (Plan Soundness)
**Role**: Ensure plan correctness and optimality  
**Inspired by**: MAP's Evaluator + Verifier Task Mechanism  
**Input**: Complete plan, goal, initial state  
**Output**: Soundness check, quality score, issues  

#### 6. **Coordination Agent** (Orchestrator)
**Role**: Manage agent interactions, planning workflow  
**Inspired by**: MAP's Orchestrator  
**Input**: Agent messages, current plan, goal  
**Output**: Next agent to invoke, plan status, final plan  

---

## 📋 Documentation Created

### 1. **MULTI_AGENT_ARCHITECTURE.md** (34KB)
**Sections**:
- Executive summary
- MAP research insights
- 6 agent specifications (roles, inputs, outputs, prompting strategies)
- Agent communication protocol (AgentMessage, MessageBus)
- Multi-agent planning algorithm (60-line pseudocode)
- Integration with Strategic Decomposition Engine
- Example execution trace (make_coffee task)
- Implementation roadmap (5 phases, 10 weeks)
- Success criteria
- Code snippets and usage examples

**Key Design Decisions**:
- **Backward compatible** with existing Strategic Decomposition Engine
- **LLM-agnostic**: Works with all 5 current providers (DeepSeek V3, Ollama, Groq, Gemini, Cohere)
- **Flexible configuration**: Single LLM for all agents OR specialized LLMs per agent
- **Message-based communication**: Async, persistent, order-guaranteed
- **Iterative validation**: Execution Agent provides feedback until method is valid

### 2. **MAP_RESEARCH_NOTES.md** (15KB)
**Sections**:
- MAP paper summary
- 6 module descriptions with implementation details
- Planning algorithms (with LaTeX pseudocode)
- Experimental results (Tower of Hanoi, Graph Traversal, PlanBench, StrategyQA)
- Ablation studies (Monitor is most critical module)
- Brain-inspired design mappings
- Comparison vs CoT/ToT/MAD
- Prompting strategies with examples
- Failure mode analysis
- Relevance to HTN planning (direct mappings, adaptations needed)
- Open questions for implementation

**Key Insights**:
- **Modularity matters**: Ablating Monitor drops success from 74% to 27%
- **Smaller LLMs work**: Llama3-70B + MAP > GPT-4 baseline
- **Transfer learning**: MAP shows superior generalization across tasks
- **Computational cost**: 2-3x token increase, but **higher success rate**
- **Optimization**: Caching reduces prompts by 65% (148 → 42)

---

## 🔄 Integration Strategy

### Backward Compatibility

**Current System** (Stage 2):
```python
engine = StrategicDecompositionEngine()
engine.add_llm_provider("deepseek_v3", deepseek_client)
engine.add_llm_provider("ollama", ollama_client)

result = engine.decompose_task(task, domain, benchmark=True)
```

**New System** (Stage 3) - **Still Compatible**:
```python
orchestrator = MultiAgentOrchestrator()

# Option 1: Single LLM for all agents
orchestrator.configure_agents(llm_provider=deepseek_client)

# Option 2: Specialized LLMs per agent
orchestrator.configure_agents({
    "planning": deepseek_client,
    "decomposition": groq_client,
    "execution": ollama_client,
    "context": gemini_client,
    "verification": cohere_client
})

result = orchestrator.plan_task(task, domain, benchmark=True)
```

### Integration Points

1. **Strategic Decomposition Engine**: Fallback if multi-agent fails
2. **HTN Planner Core**: Use orchestrator for knowledge gap resolution
3. **Prompt Builder**: Agent-specific system prompts
4. **Response Parser**: Parse agent outputs into HTN structures
5. **LLM Clients**: All 5 providers work with agents

---

## 📊 Multi-Agent Planning Workflow

```
┌─────────────────────────────────────────────────────────┐
│                 Coordination Agent                       │
│                (Central Orchestrator)                    │
└────────┬──────────────────────────────────────────┬─────┘
         │                                           │
    ┌────┴────┐                                 ┌────┴────┐
    │Planning │ ─ Generate subgoals ──────────> │Decompos.│
    │ Agent   │                                  │ Agent   │
    └─────────┘                                  └────┬────┘
         │                                            │
         │                                            │
    ┌────┴────┐                                  ┌────┴────┐
    │Context  │ ◄─ Predict state ─────────────── │Execution│
    │ Agent   │ ─── Track dependencies ────────> │ Agent   │
    └─────────┘                                  └────┬────┘
         │                                            │
         │                                            │
    ┌────┴────┐                                       │
    │Verificat│ ◄─ Validate final plan ──────────────┘
    │ Agent   │
    └─────────┘
```

**Algorithm** (simplified):
1. Planning Agent generates subgoals
2. For each subgoal:
   - Decomposition Agent generates methods
   - Execution Agent validates (feedback loop until valid)
   - Context Agent predicts state
   - Add method to plan
3. Verification Agent checks plan soundness
4. If sound, return plan; else regenerate

---

## 🎯 Success Criteria

The multi-agent system will be considered successful if:

1. **Performance**: ≥80% success rate on household tasks (current: 100% with ensemble)
2. **Quality**: Plans with ≤10% more steps than optimal
3. **Robustness**: Handles invalid LLM outputs gracefully (hallucinations, loops)
4. **Efficiency**: Completes planning in ≤2x time of single-LLM
5. **Generalization**: Works with all 5 LLM providers without modification
6. **Backward Compatibility**: Existing tests pass

---

## 🗓️ Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Implement BaseAgent, MessageBus, AgentMessage
- [ ] Create CoordinationAgent with basic routing
- [ ] Write unit tests for communication

### Phase 2: Core Agents (Week 3-4)
- [ ] Implement PlanningAgent
- [ ] Implement DecompositionAgent (reuse existing logic)
- [ ] Implement ExecutionAgent
- [ ] Write agent-specific unit tests

### Phase 3: Advanced Agents (Week 5-6)
- [ ] Implement ContextAgent
- [ ] Implement VerificationAgent
- [ ] Integrate with existing HTN planner

### Phase 4: Optimization & Benchmarking (Week 7-8)
- [ ] Add caching and parallel execution
- [ ] Run comprehensive benchmarks (household tasks, logistics)
- [ ] Compare against ensemble baseline
- [ ] Optimize prompts based on results

### Phase 5: Documentation & Examples (Week 9-10)
- [ ] Write usage examples for each domain
- [ ] Create tutorial notebooks
- [ ] Document best practices
- [ ] Write research report comparing approaches

---

## 📁 File Structure (To Be Created)

```
src/agents/
├── __init__.py
├── base_agent.py              # BaseAgent class
├── communication.py           # AgentMessage, MessageBus
├── agent_coordinator.py       # CoordinationAgent
├── planning_agent.py          # Planning Agent
├── decomposition_agent.py     # Decomposition Agent
├── context_agent.py           # Context Management Agent
├── execution_agent.py         # Execution Agent
├── verification_agent.py      # Verification Agent
└── multi_agent_orchestrator.py  # Main orchestrator

tests/
├── test_agents.py             # Unit tests per agent
├── test_agent_communication.py
├── test_multi_agent_integration.py
└── test_agent_household_tasks.py  # Benchmark
```

---

## 💡 Key Insights & Recommendations

### 1. **Start with Monitor/Execution Agent**
MAP's ablation study showed Monitor is **most critical** (27% → 74% success). Implement ExecutionAgent first to prevent hallucinations.

### 2. **Use Smaller LLMs for Validation**
Ollama (local, free) can handle validation tasks. Save DeepSeek V3 for complex reasoning (Planning, Decomposition).

### 3. **Iterative Feedback Loop**
Decomposition Agent ↔ Execution Agent feedback loop is essential. Keep iterating until method is valid.

### 4. **Cache Aggressively**
MAP reduced prompts by 65% with caching. Implement early for cost savings.

### 5. **Few-Shot Examples**
All agents should have 2-3 in-context examples. Use your existing household tasks for examples.

### 6. **Benchmark Against Ensemble**
Your Strategic Decomposition Engine (100% success) is strong baseline. Multi-agent should match or exceed.

---

## ⚠️ Open Questions (Need Your Input)

### 1. **Tree Search Adaptation**
MAP uses tree search (depth 2, branching 2) in action space. How to adapt to HTN Method space (variable depth)?

**Proposed Solution**: Search Method decompositions, limit depth to 2 levels of hierarchy.

### 2. **Method Quality Metric**
MAP counts steps to goal. HTN has hierarchical decomposition. What metric for Method quality?

**Options**:
- Count total primitive operators in full plan
- Measure plan depth (hierarchy levels)
- Estimate execution time/cost

### 3. **Ensemble vs Multi-Agent**
Should we keep ensemble benchmarking (test all LLMs) or focus on multi-agent?

**Proposed**: Support both modes - user can choose:
- `orchestrator.plan_task(benchmark="ensemble")` → Test all LLMs
- `orchestrator.plan_task(benchmark="multi-agent")` → Agent collaboration

### 4. **Domain-Specific Agents**
Should we create specialized agents for specific domains (robotics, healthcare)?

**Recommendation**: Start with general agents, add specialization later if needed.

---

## 🚀 Next Steps (Your Choice)

You have **3 options** to proceed:

### Option A: **Start Implementation** (Hands-On)
I can begin implementing the base agent framework (Phase 1):
1. Create `src/agents/` directory
2. Implement `BaseAgent`, `MessageBus`, `AgentMessage`
3. Write unit tests
4. Create example usage

**Time**: ~2-3 hours for foundation

### Option B: **Design Refinement** (More Planning)
We can refine the design before coding:
1. Discuss open questions above
2. Finalize agent responsibilities
3. Design prompting strategies in detail
4. Create domain-specific task examples

**Time**: ~1 hour discussion

### Option C: **Prototype First** (Quick Test)
Create a minimal prototype with 2-3 agents:
1. Decomposition Agent (generate methods)
2. Execution Agent (validate methods)
3. Simple coordination logic

**Goal**: Prove concept works before full implementation

**Time**: ~2-3 hours for prototype

---

## 📖 References

1. **Webb, T., Mondal, S. S., & Momennejad, I. (2023)**. "Improving Planning with Large Language Models: A Modular Agentic Architecture". *Nature Communications*, 2025. arXiv:2310.00194

2. **Cardoso, R. C., & Bordini, R. H. (2017)**. "A Multi-Agent Extension of a Hierarchical Task Network Planning Formalism". *WESAAC 2016*.

3. **Parimi, V. (2021)**. "T-HTN: Timeline Based HTN Planning for Multi-Agent Systems". *CMU Robotics Institute*.

4. **Your Current System**: Strategic Decomposition Engine (Phase 3 complete, 100% success, 5 LLM providers)

---

## ✅ Summary Checklist

What's been completed:

- [x] Research MAP paper thoroughly
- [x] Research multi-agent HTN planning literature
- [x] Design 6 specialized agents adapted for HTN
- [x] Design agent communication protocol
- [x] Design multi-agent planning algorithm
- [x] Plan integration with Strategic Decomposition Engine
- [x] Create comprehensive architecture document (34KB)
- [x] Create MAP research notes (15KB)
- [x] Define success criteria
- [x] Create 5-phase implementation roadmap

What's next:

- [ ] Choose implementation approach (A, B, or C above)
- [ ] Create base agent framework
- [ ] Implement specialized agents
- [ ] Write tests and benchmarks
- [ ] Compare multi-agent vs ensemble

---

**The design phase is complete. You now have a comprehensive blueprint for implementing a multi-agent HTN planning system inspired by state-of-the-art research. The architecture is modular, extensible, backward compatible, and ready for implementation.**

**What would you like to do next?**
