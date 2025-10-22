# Multi-Agent Architecture for Neuro-Symbolic HTN Planning

**Authors**: Inspired by Modular Agentic Planner (MAP) research (Webb et al., 2023)  
**Status**: Design Phase  
**Date**: 2025-01-XX  

---

## Executive Summary

This document outlines the architectural design for integrating a **Multi-Agent Specialization system** into the Neuro-Symbolic HTN Planner, evolving from the current LLM-as-Modeler approach to an **LLM-as-Orchestrator** paradigm. The design is inspired by the Modular Agentic Planner (MAP) research, which demonstrated significant improvements in planning tasks through specialized agent collaboration.

### Key Design Principles

1. **Modularity**: Each agent specializes in a specific aspect of HTN planning
2. **Recurrent Interaction**: Agents communicate iteratively to refine plans
3. **Neuro-Symbolic Integration**: Symbolic HTN planner guides neural agent behavior
4. **LLM-Agnostic**: Compatible with all 5 existing LLM providers (DeepSeek V3, Ollama, Groq, Gemini, Cohere)
5. **Backward Compatibility**: Existing Strategic Decomposition Engine remains functional

### Evolution Path

```
Stage 1: LLM-to-Planner (Completed)
         ↓
Stage 2: LLM-as-Modeler (Current - Strategic Decomposition Engine)
         ↓
Stage 3: LLM-as-Orchestrator (This Design - Multi-Agent System)
```

---

## 1. Motivation and Research Foundation

### 1.1 MAP Research Insights

The Modular Agentic Planner (MAP) paper demonstrated:

- **74% success rate** on Tower of Hanoi (3-disk) vs 11% zero-shot GPT-4
- Outperformed Chain-of-Thought (42%), Multi-Agent Debate (25%), Tree-of-Thought (25%)
- **Brain-inspired modularity**: Specialized modules map to prefrontal cortex functions
- **Effective with smaller LLMs**: Llama3-70B + MAP outperformed GPT-4 ICL

**MAP's 6 Core Modules**:
1. **TaskDecomposer**: Generates subgoals using goal recursion strategy
2. **Actor**: Proposes multiple candidate actions
3. **Monitor**: Validates actions against task constraints (conflict monitoring)
4. **Predictor**: Forecasts next states given actions (world model)
5. **Evaluator**: Estimates state value (distance to goal)
6. **Orchestrator**: Determines goal achievement and coordinates modules

### 1.2 Why Multi-Agent for HTN Planning?

Current challenges with single-LLM approaches:
- **Hallucination**: LLMs propose invalid methods not in domain
- **Loops**: Repetitive decomposition patterns
- **Lack of Verification**: No systematic soundness checking
- **Context Overload**: Single LLM handles all aspects simultaneously

Multi-agent advantages:
- **Specialization**: Each agent focuses on one concern
- **Error Detection**: Monitor/Verification agents catch mistakes
- **Parallel Reasoning**: Multiple agents can work concurrently
- **Robustness**: Failure in one agent doesn't break entire system

---

## 2. Agent Architecture Design

### 2.1 Core Agents

#### Agent 1: **Planning Agent** (Strategic Analysis)
**Role**: High-level goal analysis, strategy selection  
**Inspired by**: MAP's TaskDecomposer + Anterior PFC (task decomposition)  
**Responsibilities**:
- Analyze high-level goals in context of HTN domain
- Identify applicable decomposition strategies
- Generate subgoal hierarchies
- Select appropriate planning approaches (forward/backward/hierarchical)

**Input**:
```python
{
  "current_state": StateManager,
  "goal": Task,
  "domain_context": DomainContext,
  "available_methods": List[Method],
  "available_operators": List[Operator]
}
```

**Output**:
```python
{
  "decomposition_strategy": str,  # e.g., "goal_recursion", "means_ends_analysis"
  "subgoals": List[Task],
  "priority_order": List[int],
  "reasoning": str
}
```

**Prompting Strategy**: CoT with HTN-specific reasoning patterns

---

#### Agent 2: **Decomposition Agent** (Method Generation)
**Role**: Generate HTN methods (task → subtask sequences)  
**Inspired by**: MAP's Actor + current Strategic Decomposition Engine  
**Responsibilities**:
- Generate multiple candidate methods for a given task
- Propose subtask sequences with preconditions/effects
- Rank methods by feasibility and optimality
- Handle domain-specific constraints

**Input**:
```python
{
  "task": Task,
  "subgoals": List[Task],  # from Planning Agent
  "domain_context": DomainContext,
  "current_state": StateManager,
  "decomposition_strategy": str
}
```

**Output**:
```python
{
  "candidate_methods": List[ParsedMethod],
  "confidence_scores": List[float],
  "reasoning": List[str],
  "alternatives": List[ParsedMethod]
}
```

**Prompting Strategy**: Few-shot with domain examples, CoT reasoning

---

#### Agent 3: **Context Management Agent** (State Tracking)
**Role**: Track state evolution, dependencies, constraints  
**Inspired by**: MAP's Predictor + StateManager  
**Responsibilities**:
- Predict state transitions from proposed actions
- Detect precondition violations
- Track inter-task dependencies
- Maintain planning context across agent interactions

**Input**:
```python
{
  "current_state": StateManager,
  "proposed_action": Operator,
  "pending_tasks": List[Task],
  "completed_tasks": List[Task]
}
```

**Output**:
```python
{
  "predicted_state": StateManager,
  "preconditions_satisfied": bool,
  "violated_constraints": List[str],
  "state_diff": Dict[str, Any],
  "dependencies_met": bool
}
```

**Prompting Strategy**: State prediction with constraint checking

---

#### Agent 4: **Execution Agent** (Action Validation)
**Role**: Validate proposed actions and methods  
**Inspired by**: MAP's Monitor + Anterior Cingulate Cortex (conflict monitoring)  
**Responsibilities**:
- Check action validity against domain rules
- Detect hallucinated methods/operators
- Verify method soundness (subtasks achievable)
- Provide feedback for regeneration

**Input**:
```python
{
  "proposed_method": ParsedMethod,
  "domain_context": DomainContext,
  "current_state": StateManager
}
```

**Output**:
```python
{
  "is_valid": bool,
  "validation_errors": List[str],
  "feedback": str,  # for Decomposition Agent
  "suggested_fixes": List[str],
  "severity": str  # "critical", "warning", "info"
}
```

**Prompting Strategy**: Rule-based validation with CoT reasoning

---

#### Agent 5: **Verification Agent** (Plan Soundness)
**Role**: Ensure overall plan correctness and optimality  
**Inspired by**: MAP's Evaluator + Verifier Task Mechanism  
**Responsibilities**:
- Check plan completeness (all goals achieved)
- Verify causal links between subtasks
- Detect loops and redundant decompositions
- Estimate plan quality (steps, cost, reliability)

**Input**:
```python
{
  "plan": List[Method],
  "goal": Task,
  "initial_state": StateManager,
  "domain_context": DomainContext
}
```

**Output**:
```python
{
  "is_sound": bool,
  "completeness_score": float,
  "quality_score": float,
  "issues": List[str],
  "suggestions": List[str],
  "estimated_steps": int
}
```

**Prompting Strategy**: Heuristic evaluation with HTN semantics

---

#### Agent 6: **Coordination Agent** (Orchestrator)
**Role**: Manage agent interactions and planning workflow  
**Inspired by**: MAP's Orchestrator + Algorithm 1  
**Responsibilities**:
- Route messages between agents
- Determine when subgoals are achieved
- Manage planning loop (iterate until goal met)
- Handle agent failures and retries

**Input**:
```python
{
  "agent_messages": List[AgentMessage],
  "current_plan": List[Method],
  "goal": Task,
  "state": StateManager
}
```

**Output**:
```python
{
  "next_agent": str,  # which agent to invoke
  "action": str,  # "continue", "regenerate", "complete"
  "plan_status": str,  # "in_progress", "complete", "failed"
  "final_plan": Optional[List[Method]]
}
```

**Prompting Strategy**: Rule-based coordination logic

---

### 2.2 Agent Communication Protocol

#### Message Structure

```python
@dataclass
class AgentMessage:
    """Message passed between agents."""
    sender: str  # Agent ID
    receiver: str  # Agent ID or "broadcast"
    message_type: str  # "request", "response", "feedback", "notification"
    content: Dict[str, Any]
    timestamp: float
    conversation_id: str  # Track multi-turn conversations
    priority: int  # 1-10, higher = more urgent
```

#### Communication Patterns

1. **Request-Response**: Planning Agent → Decomposition Agent
2. **Validation Loop**: Decomposition Agent → Execution Agent → Decomposition Agent (until valid)
3. **Broadcast**: Context Agent → All Agents (state update)
4. **Chain**: Planning → Decomposition → Execution → Verification → Coordination

#### Message Bus Architecture

```
┌─────────────────────────────────────────────────────┐
│               Coordination Agent                     │
│              (Central Orchestrator)                  │
└────────┬────────────────────────────────────────────┘
         │
         │  Route messages
         │
    ┌────┴────────────────────────────────────┐
    │        Message Bus / Event Queue         │
    │    (Async, Persistent, Order-Guaranteed) │
    └────┬────────────────────────────────┬────┘
         │                                │
    ┌────┴─────┐  ┌──────────┐  ┌────────┴─────┐
    │ Planning │  │Decompos. │  │  Context     │
    │  Agent   │  │  Agent   │  │   Agent      │
    └──────────┘  └──────────┘  └──────────────┘
         │                                │
    ┌────┴─────┐                    ┌────┴─────┐
    │Execution │                    │Verificat.│
    │  Agent   │                    │  Agent   │
    └──────────┘                    └──────────┘
```

---

## 3. Integration with Current System

### 3.1 Backward Compatibility

**Current System (Stage 2)**:
```python
# Strategic Decomposition Engine (ensemble benchmarking)
engine = StrategicDecompositionEngine()
engine.add_llm_provider("deepseek_v3", deepseek_client)
engine.add_llm_provider("ollama", ollama_client)

result = engine.decompose_task(
    task_name="make_coffee",
    task_description="Make a cup of coffee",
    parameters=[],
    domain_context=domain,
    benchmark=True  # Tests all LLMs
)
```

**New System (Stage 3) - Compatible**:
```python
# Multi-Agent Orchestrator (can still use ensemble)
orchestrator = MultiAgentOrchestrator()

# Option 1: Use single LLM provider for all agents
orchestrator.configure_agents(llm_provider=deepseek_client)

# Option 2: Different LLMs for different agents (specialization)
orchestrator.configure_agents({
    "planning": deepseek_client,    # Most capable for strategy
    "decomposition": groq_client,   # Fast for generation
    "execution": ollama_client,     # Local for validation
    "context": gemini_client,       # Good at prediction
    "verification": cohere_client   # Long context for plan checking
})

result = orchestrator.plan_task(
    task_name="make_coffee",
    task_description="Make a cup of coffee",
    parameters=[],
    domain_context=domain,
    benchmark=False,  # Or True to compare multi-agent vs ensemble
    max_iterations=10
)
```

### 3.2 Integration Points

#### With Strategic Decomposition Engine
```python
class MultiAgentOrchestrator:
    def __init__(self, fallback_to_ensemble=True):
        self.agents = self._initialize_agents()
        self.coordinator = CoordinationAgent()
        
        # Fallback to ensemble if multi-agent fails
        if fallback_to_ensemble:
            self.ensemble = StrategicDecompositionEngine()
```

#### With HTN Planner Core
```python
class HTNPlanner:
    def plan(self, task, state, domain):
        # Check knowledge gap
        if self.knowledge_gap_detector.has_gap(task, domain):
            # Use multi-agent orchestrator
            result = self.orchestrator.plan_task(
                task_name=task.name,
                domain_context=domain,
                current_state=state
            )
            
            # Add generated method to domain
            domain.add_method(result["best_method"])
        
        # Continue with traditional HTN planning
        return self.pyhop_plan(task, state, domain)
```

#### With Prompt Builder
```python
class BaseAgent:
    def __init__(self, role, llm_client, prompt_builder):
        self.role = role
        self.llm = llm_client
        self.prompt_builder = prompt_builder
    
    def generate(self, task, context):
        # Use existing prompt builder with agent-specific strategy
        system_prompt = self.prompt_builder.get_agent_system_prompt(self.role)
        user_prompt = self.prompt_builder.build_agent_task_prompt(
            agent_role=self.role,
            task=task,
            context=context
        )
        
        return self.llm.generate(user_prompt, system_prompt=system_prompt)
```

---

## 4. Planning Workflow

### 4.1 Multi-Agent Planning Algorithm

```python
Algorithm: MultiAgentHTNPlanning(task, state, domain)

Input:
  - task: High-level task to accomplish
  - state: Current world state
  - domain: HTN domain (methods, operators)

Output:
  - plan: List of Methods to achieve task
  - metadata: Agent conversation logs, performance metrics

1. Initialize agents with LLM providers
2. coordinator.start_planning(task, state, domain)
3. 
4. LOOP until goal achieved or max_iterations:
5.   
6.   # Planning Phase
7.   planning_result = planning_agent.analyze(task, state, domain)
8.   subgoals = planning_result["subgoals"]
9.   strategy = planning_result["decomposition_strategy"]
10.  
11.  FOR each subgoal in subgoals:
12.    
13.    # Decomposition Phase (with validation loop)
14.    LOOP until valid_method or max_attempts:
15.      
16.      # Generate candidate methods
17.      decomp_result = decomposition_agent.generate_methods(
18.        subgoal, strategy, state, domain
19.      )
20.      
21.      # Validate with Execution Agent
22.      validation = execution_agent.validate(
23.        decomp_result["candidate_methods"], domain, state
24.      )
25.      
26.      IF validation["is_valid"]:
27.        break
28.      ELSE:
29.        # Provide feedback for regeneration
30.        feedback = validation["feedback"]
31.      
32.    END LOOP
33.    
34.    # Context Update
35.    predicted_state = context_agent.predict_state(
36.      state, decomp_result["best_method"]
37.    )
38.    
39.    # Add method to plan
40.    plan.append(decomp_result["best_method"])
41.    state = predicted_state
42.    
43.    # Check if subgoal achieved
44.    IF coordinator.is_goal_achieved(subgoal, state):
45.      subgoals.remove(subgoal)
46.    
47.  END FOR
48.  
49.  # Verification Phase
50.  verification = verification_agent.verify_plan(
51.    plan, task, initial_state, domain
52.  )
53.  
54.  IF verification["is_sound"]:
55.    return plan, metadata
56.  ELSE:
57.    # Regenerate problematic methods
58.    plan = coordinator.fix_plan(plan, verification["issues"])
59.  
60. END LOOP
61. 
62. return plan, metadata
```

### 4.2 Example Execution Trace (Make Coffee)

```
=== Multi-Agent Planning Trace ===

Task: make_coffee(cup1)
Domain: Cooking (15 operators, 8 methods)

[Iteration 1]
├─ PLANNING AGENT
│  Input: task=make_coffee, state={has_ingredient(beans), has_ingredient(water), clean(machine)}
│  Strategy: goal_recursion (decompose into sequential subgoals)
│  Subgoals: [grind_beans, fill_water, brew_coffee, pour_coffee]
│  
├─ DECOMPOSITION AGENT (subgoal: grind_beans)
│  Generated 3 candidate methods:
│    1. method_grind_beans_standard: [get_beans → grind → store] (confidence: 0.92)
│    2. method_grind_beans_fine: [get_beans → grind(fine) → store] (confidence: 0.87)
│    3. method_grind_beans_coarse: [get_beans → grind(coarse) → store] (confidence: 0.84)
│  
├─ EXECUTION AGENT
│  Validating method_grind_beans_standard...
│  ✓ All operators exist in domain
│  ✓ Preconditions achievable: has_ingredient(beans), clean(grinder)
│  ✓ Effects consistent: ground_beans(container1)
│  Status: VALID
│  
├─ CONTEXT AGENT
│  Current state: {has_ingredient(beans), clean(grinder)}
│  Applying: get_beans → grind → store
│  Predicted state: {ground_beans(container1), clean(grinder)}
│  Dependencies: None violated
│  
├─ COORDINATION AGENT
│  Subgoal "grind_beans" achieved
│  Moving to next subgoal: fill_water
│  Plan length: 1 method, 3 operators
│  Continue planning...

[Iteration 2]
├─ DECOMPOSITION AGENT (subgoal: fill_water)
│  Generated 2 candidate methods:
│    1. method_fill_water_tank: [open_tank → pour_water → close_tank] (confidence: 0.95)
│    2. method_fill_water_manual: [pour_water_directly] (confidence: 0.78)
│  
├─ EXECUTION AGENT
│  Validating method_fill_water_tank...
│  ✗ ERROR: Operator "open_tank" not in domain!
│  Feedback: "Use only available operators: fill_water_reservoir"
│  
├─ DECOMPOSITION AGENT (retry with feedback)
│  Regenerating with constraint: must use fill_water_reservoir
│  Generated method: method_fill_water_corrected: [fill_water_reservoir(amount=250ml)]
│  
├─ EXECUTION AGENT
│  Validating method_fill_water_corrected...
│  ✓ Valid
│  
├─ CONTEXT AGENT
│  Predicted state: {ground_beans(container1), water_filled(reservoir, 250ml)}
│  
[... Iterations 3-4 for brew_coffee and pour_coffee ...]

[Iteration 5 - Verification]
├─ VERIFICATION AGENT
│  Checking plan completeness...
│  ✓ All subgoals achieved
│  ✓ No causal loops detected
│  ✓ Final state matches goal: coffee_ready(cup1)
│  Quality score: 0.91 (4 methods, 12 operators, optimal path)
│  
├─ COORDINATION AGENT
│  Planning COMPLETE
│  Final plan: 4 methods, 12 operators
│  Execution time: 32.4s
│  Total agent calls: 18
│  LLM tokens: 8,743

=== Plan Generated ===
Method 1: method_grind_beans_standard
  - get_beans(container1)
  - grind(container1, medium)
  - store_grounds(container1, filter)

Method 2: method_fill_water_corrected
  - fill_water_reservoir(250ml)

Method 3: method_brew_coffee_standard
  - place_filter(filter)
  - brew(180F, 4min)

Method 4: method_pour_coffee_standard
  - pour_into_cup(cup1)
  - serve(cup1)
```

---

## 5. Technical Implementation

### 5.1 Directory Structure

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

### 5.2 Core Classes

#### BaseAgent

```python
class BaseAgent:
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, 
                 agent_id: str,
                 role: str,
                 llm_client: BaseLLMClient,
                 prompt_builder: PromptBuilder):
        self.agent_id = agent_id
        self.role = role
        self.llm = llm_client
        self.prompt_builder = prompt_builder
        self.memory = []  # Conversation history
        
    def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process incoming message and generate response."""
        raise NotImplementedError
    
    def generate_response(self, prompt: str, context: Dict) -> str:
        """Generate LLM response with retry logic."""
        system_prompt = self.prompt_builder.get_agent_system_prompt(self.role)
        
        try:
            response = self.llm.generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=self.llm.config.max_tokens,
                temperature=self.llm.config.temperature
            )
            return response.content
        except LLMException as e:
            logger.error(f"Agent {self.agent_id} LLM error: {e}")
            raise
```

#### AgentMessage

```python
@dataclass
class AgentMessage:
    """Message structure for inter-agent communication."""
    sender: str
    receiver: str
    message_type: str  # "request", "response", "feedback", "notification"
    content: Dict[str, Any]
    timestamp: float
    conversation_id: str
    priority: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

#### MessageBus

```python
class MessageBus:
    """Central message routing system for agents."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_queue: List[AgentMessage] = []
        self.message_history: List[AgentMessage] = []
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the message bus."""
        self.agents[agent.agent_id] = agent
    
    def send_message(self, message: AgentMessage):
        """Send message to specified agent or broadcast."""
        self.message_history.append(message)
        
        if message.receiver == "broadcast":
            for agent in self.agents.values():
                if agent.agent_id != message.sender:
                    response = agent.process_message(message)
                    if response:
                        self.send_message(response)
        else:
            agent = self.agents.get(message.receiver)
            if agent:
                response = agent.process_message(message)
                if response:
                    self.send_message(response)
    
    def get_conversation(self, conversation_id: str) -> List[AgentMessage]:
        """Retrieve all messages in a conversation."""
        return [m for m in self.message_history if m.conversation_id == conversation_id]
```

---

## 6. Prompting Strategies

### 6.1 Agent-Specific Prompts

#### Planning Agent System Prompt

```
You are a Strategic Planning Agent for HTN (Hierarchical Task Network) planning.

Your role:
- Analyze high-level goals and decompose them into subgoals
- Select appropriate decomposition strategies (goal recursion, means-ends analysis)
- Consider domain constraints and available methods/operators
- Prioritize subgoals based on dependencies and optimality

Guidelines:
1. Use goal recursion: Move smallest element to target, recursively solve smaller problems
2. Consider preconditions: Subgoals must be achievable in sequence
3. Minimize steps: Prefer efficient decomposition paths
4. Stay within domain: Only propose subgoals with available methods

Output format:
{
  "decomposition_strategy": "<strategy_name>",
  "subgoals": [<subgoal_1>, <subgoal_2>, ...],
  "priority_order": [1, 2, 3, ...],
  "reasoning": "<explanation>"
}
```

#### Execution Agent System Prompt

```
You are an Execution Validation Agent for HTN planning.

Your role:
- Validate proposed methods against domain rules
- Detect hallucinated operators or methods
- Check precondition satisfaction
- Provide constructive feedback for invalid methods

Validation checklist:
1. All operators exist in domain
2. Preconditions are achievable
3. Effects are consistent with operator definitions
4. No circular dependencies
5. Subtasks are properly ordered

Output format (if invalid):
{
  "is_valid": false,
  "validation_errors": ["<error_1>", "<error_2>"],
  "feedback": "<constructive suggestion>",
  "suggested_fixes": ["<fix_1>", "<fix_2>"]
}
```

### 6.2 Few-Shot Examples

Each agent will have 2-3 in-context examples specific to their role:

```python
PLANNING_AGENT_EXAMPLES = [
    {
        "input": {
            "task": "make_coffee",
            "domain": "cooking",
            "available_methods": ["grind", "brew", "pour"]
        },
        "output": {
            "decomposition_strategy": "sequential_decomposition",
            "subgoals": ["grind_beans", "fill_water", "brew_coffee", "pour_coffee"],
            "priority_order": [1, 2, 3, 4],
            "reasoning": "Coffee making requires sequential steps: beans must be ground before brewing, water must be added before brewing, coffee must be brewed before pouring."
        }
    },
    # ... more examples
]
```

---

## 7. Performance Considerations

### 7.1 Computational Cost

**Expected Costs**:
- **Single-LLM (Current)**: ~5-10 LLM calls per task
- **Multi-Agent**: ~15-30 LLM calls per task (2-3x increase)
- **Token Usage**: ~50-100% increase due to agent communication overhead

**Optimizations**:
1. **Caching**: Cache agent responses for identical inputs
2. **Parallel Agents**: Run Context and Verification agents concurrently
3. **Early Termination**: Stop validation loop once method is valid
4. **Smaller LLMs**: Use local Ollama for validation agents, DeepSeek V3 for complex reasoning

### 7.2 Benchmarking Metrics

```python
@dataclass
class MultiAgentBenchmark:
    """Benchmark results for multi-agent planning."""
    task_name: str
    success: bool
    total_time: float
    agent_calls: Dict[str, int]  # calls per agent
    total_tokens: int
    llm_costs: Dict[str, float]  # cost per LLM
    plan_quality: float  # 0-1 score
    comparison_to_ensemble: Dict[str, Any]
```

Compare:
- **Multi-Agent** vs **Ensemble** (Strategic Decomposition Engine)
- **Multi-Agent** vs **Single-LLM** (Zero-shot)
- **Multi-Agent (Llama3-70B)** vs **Single-LLM (DeepSeek V3)**

---

## 8. Domain-Specific Considerations

### 8.1 Task Complexity Criteria

When to use Multi-Agent:
- ✅ Complex tasks with 4+ subgoals
- ✅ Tasks requiring validation (safety-critical domains)
- ✅ Tasks with many constraints
- ✅ Domains with large operator sets (>20)

When Single-LLM is sufficient:
- ❌ Simple tasks (1-2 subgoals)
- ❌ Well-defined domains with few operators
- ❌ Tasks with high latency requirements
- ❌ Prototyping/exploration phases

### 8.2 Domain Examples

#### Good Fit: Household Tasks (Current Benchmark)
- **make_coffee**: 4 subgoals, validation important (safety)
- **clean_room**: 5+ subgoals, ordering matters
- **prepare_breakfast**: 3-4 parallel subgoals, context tracking needed

#### Good Fit: Logistics (PlanBench)
- **transport_goods**: Complex preconditions, multi-step
- **load_truck**: Capacity constraints, validation crucial

#### Poor Fit: Blocks World (Simple)
- **stack_blocks**: Only 2-3 subgoals, simple rules
- Better suited for single-LLM or traditional HTN

---

## 9. Future Extensions

### 9.1 Learning Agents

Agents could learn from experience:
```python
class LearnableAgent(BaseAgent):
    def __init__(self, ...):
        super().__init__(...)
        self.success_history = []
        self.failure_patterns = []
    
    def update_from_feedback(self, task, success, feedback):
        """Update agent behavior based on planning outcomes."""
        if success:
            self.success_history.append((task, feedback))
        else:
            self.failure_patterns.append((task, feedback))
        
        # Adjust prompting strategy based on learned patterns
        self.prompt_builder.adapt_to_feedback(self.failure_patterns)
```

### 9.2 Specialized Domain Agents

For specific domains (robotics, healthcare):
```python
class RoboticsExecutionAgent(ExecutionAgent):
    """Execution agent specialized for robotics domain."""
    
    def validate(self, method, domain, state):
        # Additional robotics-specific checks
        self._check_physical_constraints(method)
        self._check_safety_constraints(method)
        return super().validate(method, domain, state)
```

### 9.3 Human-in-the-Loop

```python
class HumanFeedbackAgent(BaseAgent):
    """Agent that solicits human feedback for ambiguous decisions."""
    
    def process_message(self, message):
        if message.content["confidence"] < 0.7:
            # Ask human for clarification
            human_input = self.request_human_feedback(message.content)
            return self.incorporate_feedback(human_input)
```

---

## 10. Implementation Roadmap

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

## 11. Success Criteria

The multi-agent system will be considered successful if:

1. **Performance**: Achieves ≥80% success rate on household tasks (current: 100% with ensemble)
2. **Quality**: Generates plans with ≤10% more steps than optimal
3. **Robustness**: Handles invalid LLM outputs gracefully (hallucinations, loops)
4. **Efficiency**: Completes planning in ≤2x time of single-LLM approach
5. **Generalization**: Works with all 5 LLM providers without modification
6. **Backward Compatibility**: Existing tests pass with new system

---

## 12. References

1. **Webb, T., Mondal, S. S., & Momennejad, I. (2023)**. "Improving Planning with Large Language Models: A Modular Agentic Architecture". *Nature Communications*, 2025. arXiv:2310.00194

2. **Cardoso, R. C., & Bordini, R. H. (2017)**. "A Multi-Agent Extension of a Hierarchical Task Network Planning Formalism". *WESAAC 2016*.

3. **Georgievski, I., & Aiello, M. (2014)**. "An Overview of Hierarchical Task Network Planning". arXiv:1403.7426

4. **Parimi, V. (2021)**. "T-HTN: Timeline Based HTN Planning for Multi-Agent Systems". *CMU Robotics Institute*.

5. **Your Current System**: Strategic Decomposition Engine (Phase 3 complete, 100% success, 5 LLM providers)

---

## Appendix A: Code Snippets

### A.1 Basic Agent Implementation

```python
class PlanningAgent(BaseAgent):
    """Strategic planning agent for HTN decomposition."""
    
    def __init__(self, agent_id: str, llm_client: BaseLLMClient, prompt_builder: PromptBuilder):
        super().__init__(agent_id, "planning", llm_client, prompt_builder)
    
    def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process planning request and generate subgoals."""
        if message.message_type != "request":
            return None
        
        # Extract task and context
        task = message.content["task"]
        state = message.content["state"]
        domain = message.content["domain_context"]
        
        # Generate planning prompt
        prompt = self._build_planning_prompt(task, state, domain)
        
        # Get LLM response
        response = self.generate_response(prompt, context={})
        
        # Parse response into subgoals
        subgoals = self._parse_subgoals(response)
        
        # Create response message
        return AgentMessage(
            sender=self.agent_id,
            receiver=message.sender,
            message_type="response",
            content={
                "subgoals": subgoals,
                "decomposition_strategy": "goal_recursion",
                "reasoning": response
            },
            timestamp=time.time(),
            conversation_id=message.conversation_id,
            priority=message.priority
        )
    
    def _build_planning_prompt(self, task, state, domain):
        """Build prompt for planning agent."""
        return f"""Analyze this HTN planning task:

Task: {task.name}
Parameters: {task.parameters}
Current State: {state}

Domain: {domain.domain_name}
Available Methods: {[m.name for m in domain.available_methods]}
Available Operators: {[o.name for o in domain.available_operators]}

Your role: Generate a sequence of subgoals to achieve the task using goal recursion.

Output format:
{{
  "subgoals": ["subgoal_1", "subgoal_2", ...],
  "decomposition_strategy": "goal_recursion",
  "reasoning": "Explanation of decomposition"
}}
"""
```

### A.2 Multi-Agent Orchestrator Usage

```python
# Initialize orchestrator
orchestrator = MultiAgentOrchestrator()

# Configure agents with LLM providers
orchestrator.configure_agents({
    "planning": deepseek_client,
    "decomposition": groq_client,
    "execution": ollama_client,
    "context": gemini_client,
    "verification": cohere_client
})

# Plan a task
result = orchestrator.plan_task(
    task_name="make_coffee",
    task_description="Make a cup of coffee",
    parameters=["cup1"],
    domain_context=cooking_domain,
    initial_state=StateManager(state),
    max_iterations=10,
    timeout=60.0
)

# Access results
print(f"Success: {result['success']}")
print(f"Plan: {result['plan']}")
print(f"Agent calls: {result['agent_calls']}")
print(f"Total time: {result['total_time']}s")
print(f"Tokens used: {result['total_tokens']}")

# Benchmark against ensemble
benchmark = orchestrator.compare_with_ensemble(
    task_name="make_coffee",
    domain_context=cooking_domain
)
print(benchmark.to_markdown())
```

---

**End of Architecture Document**

This design provides a comprehensive blueprint for implementing a multi-agent HTN planning system inspired by MAP research, while maintaining compatibility with the existing Strategic Decomposition Engine. The system is designed to be modular, extensible, and benchmarkable against current approaches.
