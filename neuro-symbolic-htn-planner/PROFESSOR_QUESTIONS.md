# Critical Design Decisions - Professor Review Required

**Date**: October 14, 2025  
**Status**: Awaiting Professor Approval Before Implementation  
**Context**: Multi-Agent HTN Planner + Memory System Integration

---

## Executive Summary

We have completed the research and architectural design for:
1. ✅ Multi-Agent Specialization Architecture (6 agents)
2. ✅ MAP (Modular Agentic Planning) Research Analysis
3. ✅ Advanced RAG/Memory System Design

**Before implementation**, we need to finalize several critical decisions regarding:
- **Domain selection** (what tasks will we test on?)
- **Baseline comparison** (what are we comparing against?)
- **Memory system integration** (how does RAG fit in?)
- **Implementation scope** (what to include/exclude?)

---

## SECTION 1: Domain Selection (HIGHEST PRIORITY)

### Question 1.1: Which Task Domain Should We Focus On?

**Context**: Professor advised to focus on **one specific domain** rather than implementing MAP exactly (which tested on multiple domains: Tower of Hanoi, Graph Traversal, BlocksWorld, Logistics).

**Options Analysis**:

#### Option A: **Complex Reasoning Tasks** (Tower of Hanoi, Graph Traversal)
- **Pros**:
  - Well-established benchmarks (Tower of Hanoi, N-Queens, Graph problems)
  - Clear success metrics (solved/not solved, optimal steps)
  - MAP paper provides direct comparison baseline (74% success on ToH 3-disk)
  - Fixed state space (easier to validate)
  - Matches MAP's approach (most relevant to our multi-agent architecture)
  
- **Cons**:
  - Less practical/real-world relevance
  - Limited memory system usage (state space is small)
  - May not fully demonstrate RAG capabilities

#### Option B: **Household/Service Tasks** (Current Implementation)
- **Pros**:
  - Already implemented and tested (4 household tasks)
  - 5 working LLM providers (Ollama, Groq, Gemini, Cohere, DeepSeek V3)
  - 100% success rate with current Strategic Decomposition Engine
  - Real-world applicability (robotics potential)
  - Dynamic state space (user-defined predicates)
  
- **Cons**:
  - May be "too easy" for multi-agent system (already 100% success)
  - Less challenging than MAP benchmarks
  - Harder to show improvement over baseline

#### Option C: **Software Engineering Tasks** (Code generation, debugging, system design)
- **Pros**:
  - Highly practical and real-world relevant
  - Rich domain knowledge (requires extensive memory/RAG)
  - Dynamic, complex state space
  - Natural fit for multi-agent (PlanningAgent → write spec, DecompositionAgent → break into files, ExecutionAgent → write code, VerificationAgent → test)
  
- **Cons**:
  - No established benchmarks for multi-agent planning
  - Difficult to measure "correctness"
  - May be too ambitious for thesis scope

#### Option D: **Healthcare/Medical Planning** (Diagnosis, treatment planning)
- **Pros**:
  - High real-world impact
  - Requires extensive domain knowledge (memory/RAG critical)
  - Complex reasoning with uncertainty
  
- **Cons**:
  - Requires specialized medical datasets (ethical/privacy concerns)
  - No access to medical experts for validation
  - High risk of errors (patient safety)

#### Option E: **Logistics/Supply Chain** (PlanBench BlocksWorld, Delivery planning)
- **Pros**:
  - Established benchmarks (PlanBench: BlocksWorld, Logistics)
  - MAP tested on these (27.4% Mystery BlocksWorld, 24% Logistics)
  - Practical business applications
  - Complex state space with constraints
  
- **Cons**:
  - Requires PDDL domain knowledge
  - May be too domain-specific
  - Less intuitive to evaluate

#### Option F: **Hybrid Approach** (Easy + Hard tasks)
- **Pros**:
  - Test both simple (household) and complex (ToH, Graph) tasks
  - Shows scalability of multi-agent system
  - Comprehensive evaluation
  
- **Cons**:
  - Broader scope (more implementation time)
  - Harder to tell a cohesive story in thesis
  - Professor said "focus on one specific domain"

---

### Question 1.2: Fixed vs Dynamic State Space?

**Context**: MAP uses **fixed state space** (Tower of Hanoi: 3 pegs, known configuration). Our current HTN planner uses **dynamic state space** (user-defined predicates).

**Options**:

#### Option A: **Fixed State Space** (Like MAP)
- **Pros**:
  - Easier to validate (known correct answers)
  - Simpler predictor agent (deterministic state transitions)
  - Direct comparison to MAP benchmarks
  
- **Cons**:
  - Less flexible (hard to generalize)
  - Doesn't showcase HTN planner's strength (user-defined domains)

#### Option B: **Dynamic State Space** (Current Approach)
- **Pros**:
  - More general and flexible
  - Showcases HTN planner capabilities
  - Real-world applicability
  
- **Cons**:
  - Harder to validate (no "ground truth")
  - Context agent must track arbitrary predicates
  - Execution agent must validate arbitrary preconditions

#### Option C: **Semi-Fixed** (Fixed predicates, dynamic values)
- **Example**: Household tasks with fixed predicates (`has_ingredient(X)`, `location(agent, Y)`) but dynamic values
- **Pros**: Balance of structure and flexibility
- **Cons**: May not satisfy "fixed" requirement

**Recommendation Needed**: Which state space model aligns with thesis goals?

---

### Question 1.3: Robotics Component?

**Context**: You mentioned "I do not have a current robot to test on" but household tasks suggest robotics applicability.

**Questions**:
1. Should we design the system with **future robot integration** in mind (even if not tested)?
2. Should we use **simulation** (e.g., PyBullet, Gazebo) to demonstrate physical feasibility?
3. Or should we focus purely on **abstract planning** (no physical component)?

---

## SECTION 2: Baseline Comparison (What Are We Comparing Against?)

### Question 2.1: Primary Comparison Baseline?

**Context**: To show multi-agent system is better, we need baselines.

**Options**:

#### Baseline A: **Our Current System** (Strategic Decomposition Engine)
- **What it is**: Single LLM with ensemble benchmarking (5 providers)
- **Current Performance**: 100% success on household tasks
- **Comparison**: Multi-agent vs single-LLM (with same providers)

#### Baseline B: **MAP Baselines** (From paper)
- **What they are**: Zero-shot, Few-shot (ICL), Chain-of-Thought (CoT), Tree-of-Thought (ToT), Multi-Agent Debate (MAD)
- **Comparison**: Multi-agent HTN vs MAP baselines on MAP tasks (ToH, Graph)
- **Note**: Requires implementing MAP tasks (Tower of Hanoi, Graph Traversal)

#### Baseline C: **Classical HTN Planners** (SHOP2, PANDA)
- **What they are**: Traditional symbolic planners (no LLM)
- **Comparison**: Neuro-symbolic (LLM + HTN) vs pure symbolic
- **Note**: May be unfair (classical planners need complete domain specs)

#### Baseline D: **All of the Above**
- **Comprehensive**: Compare against current system + MAP baselines + classical planners
- **Cons**: More work, more complexity

**Recommendation Needed**: Which baselines should we include?

---

### Question 2.2: Prompting Strategy Baselines?

**Context**: MAP tested Zero-shot, Few-shot, Chain-of-Thought. Our current system uses CoT-style prompts.

**Should we implement and compare**:
1. ✅ **Zero-shot** (no examples)
2. ✅ **Few-shot** (2-3 in-context examples, like MAP)
3. ✅ **Chain-of-Thought** (step-by-step reasoning, current approach)
4. ⚠️ **Tree-of-Thought** (explore multiple reasoning paths)
   - Question: Is this redundant with multi-agent tree search?
5. ⚠️ **Multi-Agent Debate** (multiple LLMs debate, no specialization)
   - Question: Is this worth implementing for comparison?

**Recommendation Needed**: Which prompting strategies should we compare?

---

## SECTION 3: Memory System Integration

### Question 3.1: When to Introduce RAG/Memory?

**Context**: We have a comprehensive RAG/Memory system design (Memory_System.md), but it's not yet implemented.

**Options**:

#### Option A: **Implement Multi-Agent First, Add Memory Later**
- **Phase 1**: Multi-agent HTN planner (no memory)
- **Phase 2**: Add RAG/Memory system
- **Evaluation**: Compare multi-agent (no memory) vs multi-agent (with memory)
- **Pros**: Clearer attribution of improvements (is it agents or memory?)
- **Cons**: May not show full potential in Phase 1

#### Option B: **Implement Multi-Agent + Memory Together**
- **Phase 1**: Integrated multi-agent + RAG system
- **Evaluation**: Compare full system vs baselines
- **Pros**: Shows complete system from start
- **Cons**: Harder to debug (two major changes at once)

#### Option C: **Memory First, Then Multi-Agent**
- **Phase 1**: Add RAG to current Strategic Decomposition Engine
- **Phase 2**: Add multi-agent coordination
- **Pros**: Incremental changes, easier to validate
- **Cons**: Delays multi-agent implementation

**Recommendation Needed**: Which implementation order?

---

### Question 3.2: Memory System Scope?

**Context**: Memory_System.md describes comprehensive RAG with:
- Pre-retrieval (chunking, query expansion)
- Retrieval (hybrid search, GraphRAG)
- Post-retrieval (re-ranking, compression)
- Adaptive RAG (routing, iterative retrieval)

**Questions**:
1. Should we implement **full RAG pipeline** (all features) or **minimal RAG** (basic vector store)?
2. Should we use **GraphRAG** (knowledge graph) or **simple vector search**?
   - GraphRAG matches HTN structure (task hierarchy = graph)
   - But adds significant complexity
3. Should we implement **Adaptive RAG** (routing based on query complexity)?
   - Aligns with multi-agent coordination
   - But requires additional classifier model

**Recommendation Needed**: What level of RAG sophistication for thesis scope?

---

### Question 3.3: Memory for What?

**Context**: Memory system can store different types of knowledge.

**What should agents retrieve from memory**:
1. ✅ **Domain Knowledge** (facts about the world, like "water boils at 100°C")
2. ✅ **Past Plans** (successful task decompositions to reuse)
3. ✅ **Method Library** (HTN methods for common tasks)
4. ⚠️ **Error Patterns** (common failures to avoid)
5. ⚠️ **Agent Interaction History** (how agents collaborated in past)

**Recommendation Needed**: Which memory types are most valuable for the chosen domain?

---

## SECTION 4: Implementation Scope

### Question 4.1: Tree Search - Do We Need It?

**Context**: MAP uses tree search (depth=2, branching=2) to explore action space. ToT also uses tree search.

**Questions**:
1. Is tree search **essential** for multi-agent system?
   - MAP: 74% success (with tree search) vs 32% (without tree search)
   - But: Tree search adds significant complexity
2. Is tree search the same as **Tree-of-Thought** (ToT)?
   - MAP tree search: Explore action sequences
   - ToT: Explore reasoning paths
   - Different purposes, but both use tree structure
3. Should we implement **both** MAP-style tree search AND ToT?
   - Or just one?
   - Or neither (focus on agent specialization)?

**Recommendation Needed**: Include tree search in scope?

---

### Question 4.2: How Many Agents?

**Context**: Our architecture proposes 6 agents (inspired by MAP's 6 modules). But MAP's modules are not all "agents" - some are simple functions.

**Proposed Agents**:
1. ✅ **PlanningAgent** - High-level task analysis
2. ✅ **DecompositionAgent** - Generate HTN methods
3. ✅ **ContextAgent** - State tracking
4. ✅ **ExecutionAgent** - Validate actions/methods
5. ✅ **VerificationAgent** - Plan quality evaluation
6. ✅ **CoordinationAgent** - Orchestrate workflow

**Questions**:
1. Are 6 agents too many for thesis scope?
   - Could we start with 3 core agents (Decomposition, Execution, Verification)?
   - Add others later if time permits?
2. Should all agents be **LLM-based** or can some be **rule-based**?
   - Example: ExecutionAgent could use symbolic rule checking (faster, cheaper)
   - vs LLM-based validation (more flexible)

**Recommendation Needed**: How many agents for initial implementation?

---

### Question 4.3: Multi-LLM or Single-LLM?

**Context**: We currently have 5 working LLM providers (Ollama, Groq, Gemini, Cohere, DeepSeek V3).

**Options**:

#### Option A: **Each Agent = Different LLM Provider**
- Example: PlanningAgent=GPT-4, DecompositionAgent=DeepSeek V3, ExecutionAgent=Groq
- **Pros**: 
  - Leverages strengths of each model (Groq for speed, DeepSeek for reasoning)
  - Novel approach (heterogeneous multi-agent system)
- **Cons**: 
  - Complex to manage
  - Harder to attribute performance

#### Option B: **All Agents = Same LLM Provider**
- Example: All agents use GPT-4 (or DeepSeek V3)
- **Pros**: 
  - Simpler to implement and debug
  - Clear comparison (multi-agent vs single-LLM with same model)
  - Matches MAP approach
- **Cons**: 
  - Doesn't leverage our 5-provider ecosystem

#### Option C: **Hybrid** (Critical agents = powerful LLM, simple agents = fast LLM)
- Example: DecompositionAgent=DeepSeek V3 (671B), ExecutionAgent=Groq (fast validation)
- **Pros**: Optimized for performance and cost
- **Cons**: More complex

**Recommendation Needed**: Which multi-LLM strategy?

---

## SECTION 5: Evaluation Metrics

### Question 5.1: What Defines "Success"?

**Context**: Different domains have different success criteria.

**Metrics to Track**:

#### For All Domains:
1. ✅ **Success Rate** (% of tasks solved correctly)
2. ✅ **Token Usage** (cost efficiency)
3. ✅ **Execution Time** (speed)
4. ✅ **Plan Quality** (number of steps, optimality)

#### Domain-Specific:
- **Tower of Hanoi**: Solved in optimal moves? (7 for 3-disk)
- **Household Tasks**: Task completed? (current: 100% success)
- **Graph Traversal**: Correct path found?
- **Software Engineering**: Code compiles? Tests pass? Functionality correct?

**Questions**:
1. What is the **primary metric** for thesis evaluation?
   - Success rate? (most important for MAP)
   - Plan quality? (important for planning research)
   - Efficiency? (important for practical systems)
2. Should we measure **agent contribution**?
   - Which agent was most critical for success?
   - Ablation study (remove each agent, measure impact)

**Recommendation Needed**: Priority ranking of metrics?

---

### Question 5.2: Comparison to Human Performance?

**Context**: MAP compares to human performance on some tasks (StrategyQA: 81.7% human vs 87% MAP).

**Questions**:
1. Should we collect **human baseline** data?
   - Have humans solve the same tasks
   - Compare multi-agent system to human planning
2. Is this necessary for thesis?
   - Or is comparison to other AI systems sufficient?

**Recommendation Needed**: Include human baseline?

---

## SECTION 6: Thesis Narrative

### Question 6.1: What Story Are We Telling?

**Context**: Thesis needs a clear narrative arc.

**Possible Narratives**:

#### Narrative A: **Modularity Improves Planning**
- **Story**: Single LLM struggles with complex planning → Multi-agent specialization improves performance
- **Focus**: Agent specialization (PlanningAgent for strategy, DecompositionAgent for tactics, etc.)
- **Evaluation**: Multi-agent vs single-LLM on progressively harder tasks

#### Narrative B: **Neuro-Symbolic Integration**
- **Story**: Pure neural (LLM) or pure symbolic (HTN) have limitations → Neuro-symbolic multi-agent combines both strengths
- **Focus**: How agents bridge neural reasoning and symbolic planning
- **Evaluation**: Neuro-symbolic multi-agent vs pure LLM vs pure HTN

#### Narrative C: **Memory-Augmented Planning**
- **Story**: LLMs have limited knowledge → RAG-augmented multi-agent system learns from experience
- **Focus**: How memory system enables knowledge-intensive planning
- **Evaluation**: Multi-agent (with memory) vs multi-agent (no memory) vs baselines

#### Narrative D: **Brain-Inspired Architecture**
- **Story**: Human planning uses specialized brain regions → Multi-agent system mimics this with specialized LLM agents
- **Focus**: MAP-inspired architecture (like prefrontal cortex modules)
- **Evaluation**: Multi-agent vs other planning methods (CoT, ToT, MAD)

**Recommendation Needed**: Which narrative aligns with professor's expectations?

---

### Question 6.2: Contribution Claims?

**Context**: Thesis must make clear contribution claims.

**Possible Contributions**:
1. ✅ **Novel Architecture**: Multi-agent neuro-symbolic HTN planner (first of its kind?)
2. ✅ **Empirical Evaluation**: Comprehensive comparison of multi-agent vs baselines
3. ⚠️ **Theoretical Framework**: Formal analysis of multi-agent planning (may be too ambitious)
4. ⚠️ **Open-Source Implementation**: Reusable system for research community
5. ⚠️ **New Benchmarks**: Create new planning tasks for evaluation (if using new domain)

**Recommendation Needed**: Which contributions should we emphasize?

---

## SECTION 7: Practical Constraints

### Question 7.1: Timeline?

**Context**: Need to estimate implementation time.

**Estimated Effort**:
- **Multi-Agent Framework** (base + 6 agents): 2-3 weeks
- **Memory/RAG System** (full pipeline): 3-4 weeks
- **Domain Implementation** (tasks, tests): 1-2 weeks
- **Benchmarking & Evaluation**: 1-2 weeks
- **Thesis Writing**: 4-6 weeks

**Total**: ~12-17 weeks (3-4 months)

**Questions**:
1. What is the **thesis deadline**?
2. Do we have time for **full implementation** (multi-agent + memory)?
3. Should we prioritize **breadth** (all features) or **depth** (fewer features, better evaluation)?

**Recommendation Needed**: Timeline and prioritization?

---

### Question 7.2: Computational Resources?

**Context**: Multi-agent system requires multiple LLM calls.

**Current Resources**:
- ✅ Local: Ollama (free, unlimited)
- ✅ Cloud APIs: Groq, Gemini, Cohere, DeepSeek V3 (free tier or paid)

**Costs** (estimated per task):
- **Single-LLM**: ~1 prompt, ~1,000 tokens, ~$0.001-0.01
- **Multi-Agent (6 agents)**: ~50-150 prompts, ~50,000-150,000 tokens, ~$0.05-1.50
- **With Tree Search**: ~2-3x increase

**Questions**:
1. What is the **budget** for API costs?
2. Should we primarily use **Ollama** (free, local) for development?
3. Use cloud APIs only for **final evaluation**?

**Recommendation Needed**: Budget and resource allocation?

---

## SECTION 8: Summary of Critical Decisions

### Highest Priority (Must Decide Before Implementation)

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| **1** | **Domain Selection** | Complex Reasoning (ToH, Graph) vs Household Tasks vs Software Engineering vs Hybrid | Determines entire implementation |
| **2** | **State Space** | Fixed vs Dynamic vs Semi-Fixed | Affects agent design (Context, Predictor) |
| **3** | **Baseline Comparison** | Current system vs MAP baselines vs Classical HTN vs All | Defines evaluation strategy |
| **4** | **Memory Integration** | Multi-agent first vs Memory first vs Together | Affects implementation order |

### High Priority (Should Decide Soon)

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| **5** | **Tree Search** | Include vs Exclude | Affects complexity and performance |
| **6** | **Number of Agents** | 3 core vs 6 full | Affects scope and timeline |
| **7** | **Multi-LLM Strategy** | Heterogeneous vs Homogeneous vs Hybrid | Affects performance and complexity |
| **8** | **Primary Metric** | Success rate vs Plan quality vs Efficiency | Defines "success" |

### Medium Priority (Can Decide During Implementation)

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| **9** | **Prompting Strategies** | Zero-shot, Few-shot, CoT, ToT, MAD | Affects baseline completeness |
| **10** | **RAG Scope** | Minimal vs Full pipeline vs GraphRAG | Affects memory system complexity |
| **11** | **Agent Implementation** | All LLM-based vs Hybrid (LLM + rules) | Affects performance and cost |
| **12** | **Human Baseline** | Include vs Exclude | Affects evaluation completeness |

---

## Recommended Discussion Flow with Professor

### Meeting Structure:

1. **Start with Domain** (10 min)
   - Present options A-F
   - Get professor's preference
   - This decision drives everything else

2. **Clarify Thesis Narrative** (10 min)
   - Discuss narratives A-D
   - Understand professor's expectations
   - Align on contribution claims

3. **Define Scope** (10 min)
   - Timeline and deadlines
   - Resource constraints (budget, compute)
   - Breadth vs depth tradeoff

4. **Decide Baselines** (10 min)
   - What are we comparing against?
   - Which prompting strategies?
   - Human baseline necessary?

5. **Memory Integration Strategy** (5 min)
   - When to implement RAG?
   - How sophisticated should it be?

6. **Implementation Details** (5 min)
   - Number of agents
   - Tree search necessity
   - Multi-LLM strategy

**Total**: ~50 minutes (leave 10 min for follow-up questions)

---

## Pre-Meeting Homework

### For You (Student):
1. ✅ Read MAP paper thoroughly
2. ✅ Read Memory_System.md
3. ✅ Read MULTI_AGENT_ARCHITECTURE.md
4. ⏳ **Prepare 3 slides**:
   - Slide 1: Current system status (5 LLM providers working, Strategic Decomposition Engine)
   - Slide 2: Proposed multi-agent architecture (6 agents, inspired by MAP)
   - Slide 3: Domain options comparison table

### For Professor:
- Review this document (PROFESSOR_QUESTIONS.md)
- Consider thesis expectations and timeline
- Think about preferred domain and narrative

---

## After Meeting - Action Items Template

```markdown
# Post-Professor Meeting - Finalized Decisions

**Date**: [DATE]
**Attendees**: [NAMES]

## Decisions Made

### Domain
- **Selected**: [Tower of Hanoi / Household / Software / Other]
- **Rationale**: [WHY]
- **State Space**: [Fixed / Dynamic / Semi-Fixed]

### Baseline Comparison
- **Primary Baseline**: [Current system / MAP baselines / Classical HTN]
- **Prompting Strategies**: [Zero-shot, Few-shot, CoT, ToT, MAD]
- **Human Baseline**: [Yes / No]

### Implementation Scope
- **Number of Agents**: [3 / 6 / Other]
- **Tree Search**: [Include / Exclude]
- **Memory/RAG**: [Phase 1 / Phase 2 / Together]
- **RAG Sophistication**: [Minimal / Full / GraphRAG]

### Timeline
- **Thesis Deadline**: [DATE]
- **Implementation Target**: [DATE]
- **Evaluation Target**: [DATE]

### Narrative
- **Thesis Story**: [Modularity / Neuro-Symbolic / Memory-Augmented / Brain-Inspired]
- **Contribution Claims**: [List 2-3 main claims]

### Resources
- **Budget**: [$AMOUNT or Free tier only]
- **Compute**: [Ollama primary / Cloud APIs]

## Next Steps
1. [ ] Implement [COMPONENT] by [DATE]
2. [ ] Test [BASELINE] by [DATE]
3. [ ] Evaluate [METRIC] by [DATE]
```

---

## Conclusion

This document contains **12 critical decisions** across **8 sections** that need to be finalized before implementing the multi-agent HTN planner.

**Most Critical**: Domain selection (Question 1.1) - this decision cascades to all others.

**Recommended Approach**: 
1. Meet with professor using this document as guide
2. Record decisions using template above
3. Create implementation roadmap based on decisions
4. Begin development with clear scope and timeline

---

**Next Steps After Professor Meeting**:
1. Update todo list with finalized decisions
2. Create detailed implementation plan (week-by-week)
3. Begin Phase 1 development
4. Schedule regular check-ins with professor (bi-weekly?)

---

**Document Status**: ✅ Ready for Professor Review

**Created**: October 14, 2025  
**Author**: Thesis Student + AI Assistant  
**Purpose**: Pre-implementation decision-making guide
