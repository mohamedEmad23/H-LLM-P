# Standardized KPI Framework for HTN Planner Architectures

**Document Purpose**: Define S.M.A.R.T. Key Performance Indicators for comparing Phase 1-3, Phase 4A, and Phase 4B architectures across 5 complex reasoning problems.

**Evaluation Period**: Baseline benchmarking phase before Memory Management System (MMS) implementation

**Last Updated**: November 1, 2025

---

## KPI Selection Methodology

Following the S.M.A.R.T. criteria:
- **Specific**: Each KPI measures a single, well-defined aspect of performance
- **Measurable**: Quantifiable with clear units and measurement procedures
- **Achievable**: Realistic targets based on system capabilities
- **Relevant**: Directly tied to thesis objectives (neuro-symbolic HTN planning efficacy)
- **Time-bound**: Measured per problem execution (milliseconds/seconds)

---

## Core KPIs (7 Metrics)

### 1. Success Rate (%)

**Definition**: Percentage of problems solved correctly with valid plans that achieve goal state.

**Formula**:
```
Success Rate = (Successful Executions / Total Attempts) × 100
```

**Measurement Procedure**:
- **Success**: Plan executes to completion AND goal state achieved AND no constraint violations
- **Failure**: Planning error, execution error, goal not achieved, or constraint violation

**Target Ranges**:
- Phase 1-3: 65-75% (baseline)
- Phase 4A: 75-82% (multi-agent improvement)
- Phase 4B: 82-90% (strategic planning + context)

**Relevance**: Primary indicator of system reliability and correctness

**Data Collection**:
```json
{
  "problem_id": "multi_color_graph_1",
  "architecture": "phase4b",
  "attempt": 1,
  "success": true,
  "goal_achieved": true,
  "constraint_violations": 0
}
```

---

### 2. Mean Time to Solution (MTTS) - milliseconds

**Definition**: Average time from problem input to valid plan generation (for successful attempts only).

**Formula**:
```
MTTS = Σ(execution_time_ms) / successful_attempts
```

**Measurement Procedure**:
- **Start Time**: When problem is input to architecture
- **End Time**: When final verified plan is returned
- **Includes**: LLM latency, agent coordination, symbolic planning, verification
- **Excludes**: Failed attempts (tracked separately in MTTF)

**Target Ranges**:
- Phase 1-3: 800-1200ms (minimal coordination)
- Phase 4A: 1000-1400ms (+20-30% for 3-agent coordination)
- Phase 4B: 1200-1600ms (+30-40% for 5-agent coordination + strategic planning)

**Relevance**: Measures computational efficiency and responsiveness

**Data Collection**:
```json
{
  "problem_id": "constrained_hanoi_1",
  "architecture": "phase1",
  "start_timestamp": "2025-11-01T10:00:00.123Z",
  "end_timestamp": "2025-11-01T10:00:01.234Z",
  "time_to_solution_ms": 1111,
  "breakdown": {
    "llm_time_ms": 850,
    "symbolic_planning_ms": 200,
    "verification_ms": 61
  }
}
```

---

### 3. Failure Recovery Rate (FRR) - %

**Definition**: Percentage of initial failures recovered through fallback mechanisms or retries.

**Formula**:
```
FRR = (Recovered Failures / Total Failures) × 100

Recovered Failure: Initial component failure → Fallback success → Overall success
Total Failures: All component-level failures (LLM, agent, symbolic)
```

**Measurement Procedure**:
- Track **all** component failures (primary LLM, agent errors, constraint violations)
- Count **recoveries**: Fallback LLM success, retry success, rule-based success
- **Not Recovered**: Complete workflow failure after all fallback attempts

**Target Ranges**:
- Phase 1-3: 0-10% (minimal fallback coverage)
- Phase 4A: 40-55% (agent-level fallbacks implemented)
- Phase 4B: 55-70% (enhanced fallbacks + retry loops)

**Relevance**: Measures system robustness and resilience to failures

**Data Collection**:
```json
{
  "problem_id": "dynamic_resource_flow_1",
  "architecture": "phase4b",
  "failures": [
    {
      "component": "decomposition_agent",
      "failure_type": "primary_llm_timeout",
      "recovery_attempted": true,
      "recovery_method": "fallback_llm_groq",
      "recovery_successful": true
    },
    {
      "component": "verification_agent",
      "failure_type": "primary_llm_parsing_error",
      "recovery_attempted": true,
      "recovery_method": "rule_based_verification",
      "recovery_successful": true
    }
  ],
  "total_failures": 2,
  "recovered_failures": 2,
  "failure_recovery_rate": 100
}
```

---

### 4. Agent Communication Overhead (ACO) - messages/problem

**Definition**: Total inter-agent messages exchanged per problem (Phase 4A/4B only; N/A for Phase 1-3).

**Formula**:
```
ACO = Total Messages Sent via Message Bus

Includes: Task delegation, status updates, context sharing, coordination signals
Excludes: Internal agent state changes (not communicated)
```

**Measurement Procedure**:
- Count **all** messages sent through Agent Message Bus
- Categorize by type: task, status, context, coordination
- Measure message payload size (bytes) for overhead analysis

**Target Ranges**:
- Phase 1-3: N/A (no multi-agent communication)
- Phase 4A: 8-12 messages/problem (sequential 3-agent workflow)
- Phase 4B: 15-25 messages/problem (5-agent + context sharing + retry loops)

**Relevance**: Measures coordination efficiency and communication complexity

**Data Collection**:
```json
{
  "problem_id": "multi_agent_stack_transfer_1",
  "architecture": "phase4b",
  "messages": [
    {
      "timestamp": "2025-11-01T10:00:00.100Z",
      "sender": "planning_agent",
      "recipient": "decomposition_agent",
      "type": "task_delegation",
      "payload_bytes": 512
    },
    {
      "timestamp": "2025-11-01T10:00:00.850Z",
      "sender": "context_agent",
      "recipient": "all",
      "type": "context_update",
      "payload_bytes": 1024
    }
  ],
  "total_messages": 18,
  "message_types": {
    "task_delegation": 5,
    "status_update": 6,
    "context_sharing": 4,
    "coordination": 3
  },
  "total_payload_kb": 12.5
}
```

---

### 5. Plan Optimality Score (POS) - %

**Definition**: Ratio of generated plan steps to theoretical optimal plan steps.

**Formula**:
```
POS = (Optimal Steps / Generated Steps) × 100

Where:
- Optimal Steps: Minimum steps required (domain-specific)
- Generated Steps: Actual steps in returned plan
```

**Measurement Procedure**:
- **Optimal Steps**: Pre-calculated for each test case (e.g., Tower of Hanoi: 2^n - 1)
- **Generated Steps**: Count primitive actions in final plan
- **Score Interpretation**:
  - 100% = Optimal plan
  - 80-99% = Near-optimal
  - 60-79% = Suboptimal but acceptable
  - <60% = Highly inefficient

**Target Ranges**:
- Phase 1-3: 70-85% (basic LLM decomposition)
- Phase 4A: 80-92% (verification improves quality)
- Phase 4B: 85-96% (strategic planning optimizes decomposition)

**Relevance**: Measures plan quality and strategic thinking capability

**Data Collection**:
```json
{
  "problem_id": "n_peg_hanoi_4_disks_4_pegs",
  "architecture": "phase4b",
  "optimal_steps": 9,
  "generated_steps": 10,
  "plan_optimality_score": 90,
  "plan_quality": "near_optimal"
}
```

---

### 6. LLM Resource Utilization (LRU) - tokens/problem

**Definition**: Total tokens consumed (input + output) across all LLM calls per problem.

**Formula**:
```
LRU = Σ(input_tokens + output_tokens) for all LLM calls

Includes: Primary LLM, Fallback LLM, all agents
```

**Measurement Procedure**:
- Track **every** LLM API call
- Record input/output tokens separately
- Categorize by agent: decomposition, planning, verification, context
- Calculate cost estimate (tokens × model pricing)

**Target Ranges**:
- Phase 1-3: 1,500-3,000 tokens/problem (single LLM integration)
- Phase 4A: 3,500-6,000 tokens/problem (3 agents with LLM)
- Phase 4B: 5,000-8,500 tokens/problem (5 agents + strategic planning)

**Relevance**: Measures computational cost and efficiency of LLM usage

**Data Collection**:
```json
{
  "problem_id": "constrained_hanoi_5_disks",
  "architecture": "phase4b",
  "llm_calls": [
    {
      "agent": "planning_agent",
      "llm": "deepseek_v3",
      "attempt": "primary",
      "input_tokens": 1200,
      "output_tokens": 350,
      "total_tokens": 1550
    },
    {
      "agent": "decomposition_agent",
      "llm": "groq_llama33_70b",
      "attempt": "fallback",
      "input_tokens": 1500,
      "output_tokens": 420,
      "total_tokens": 1920
    }
  ],
  "total_tokens": 7840,
  "cost_estimate_usd": 0.0235
}
```

---

### 7. Context Coherence Score (CCS) - 0-100

**Definition**: Measure of how well the system maintains consistent understanding across problem-solving stages.

**Formula**:
```
CCS = Weighted Average of:
  - State Consistency (40%): No contradictory state assertions
  - Goal Alignment (30%): All actions directed toward goal
  - Constraint Adherence (30%): No constraint violations throughout

CCS = (0.4 × State_Score) + (0.3 × Goal_Score) + (0.3 × Constraint_Score)
```

**Measurement Procedure**:
- **State Consistency**: Check for logical contradictions in state transitions
  - Count: contradictory predicates, impossible states
  - Score: 100 - (10 × contradiction_count)

- **Goal Alignment**: Measure relevance of each action to goal
  - Calculate: actions moving toward goal / total actions
  - Score: relevance_ratio × 100

- **Constraint Adherence**: Track constraint violations
  - Count: soft constraint violations, hard constraint violations
  - Score: 100 - (5 × soft_violations) - (20 × hard_violations)

**Target Ranges**:
- Phase 1-3: 70-80 (basic coherence, some drift)
- Phase 4A: 80-90 (verification catches inconsistencies)
- Phase 4B: 90-98 (context agent maintains coherence throughout)

**Relevance**: Measures system understanding and cognitive consistency (neuro-symbolic integration quality)

**Data Collection**:
```json
{
  "problem_id": "dynamic_resource_flow_complex",
  "architecture": "phase4b",
  "state_consistency": {
    "contradictions": 0,
    "score": 100
  },
  "goal_alignment": {
    "relevant_actions": 14,
    "total_actions": 15,
    "score": 93
  },
  "constraint_adherence": {
    "soft_violations": 1,
    "hard_violations": 0,
    "score": 95
  },
  "context_coherence_score": 96
}
```

---

## KPI Aggregation & Reporting

### Per-Problem Report
Each test execution generates individual KPI measurements stored in:
```
results/kpis/{architecture}/{problem_id}/run_{timestamp}.json
```

### Cross-Architecture Comparison
Aggregate KPIs across all 5 problems per architecture:
```
results/kpis/comparative_analysis.json
```

### Visualization Requirements
- **Success Rate**: Bar chart (3 architectures × 5 problems)
- **MTTS**: Box plot showing distribution + outliers
- **FRR**: Stacked bar chart (recovered vs unrecovered failures)
- **ACO**: Line graph (Phase 4A vs 4B across problems)
- **POS**: Radar chart (5 problems as axes, 3 architectures overlaid)
- **LRU**: Stacked area chart (token usage by agent)
- **CCS**: Heatmap (architectures × problems, color gradient)

---

## Statistical Significance Testing

For each KPI comparison (e.g., Phase 1-3 vs Phase 4A):
- Run **minimum 3 trials** per problem per architecture
- Calculate mean, standard deviation, confidence intervals
- Apply **paired t-test** (p < 0.05 for significance)
- Report effect size (Cohen's d)

---

## KPI Thresholds & Quality Gates

**Success Criteria for Each Architecture:**

| KPI | Phase 1-3 Target | Phase 4A Target | Phase 4B Target |
|-----|-----------------|----------------|----------------|
| Success Rate | ≥70% | ≥78% | ≥85% |
| MTTS | ≤1200ms | ≤1400ms | ≤1600ms |
| FRR | ≥5% | ≥50% | ≥60% |
| ACO | N/A | ≤12 msgs | ≤25 msgs |
| POS | ≥75% | ≥85% | ≥90% |
| LRU | ≤3000 tokens | ≤6000 tokens | ≤8500 tokens |
| CCS | ≥75 | ≥85 | ≥92 |

**Overall Quality Gate**: Architecture passes if **5 out of 7 KPIs** meet target thresholds.

---

## Measurement Tools & Implementation

### Required Instrumentation

**1. Timing Decorator**:
```python
@measure_time
async def process_task(self, task_data):
    # Automatic timing capture
```

**2. LLM Call Tracker**:
```python
class TrackedLLMClient:
    def generate(self, prompt, **kwargs):
        tokens = self._count_tokens(prompt, response)
        self.logger.log_llm_call(tokens)
```

**3. Message Bus Monitor**:
```python
class MonitoredMessageBus:
    def send_message(self, sender, recipient, payload):
        self.logger.log_message(sender, recipient, len(payload))
```

**4. Fallback Detector**:
```python
if not primary_result['success'] and self.fallback_client:
    self.logger.log_fallback('primary_failed')
    result = await self._try_fallback()
    if result['success']:
        self.logger.log_fallback('fallback_success')
```

### Data Storage Schema

**SQLite Database**: `results/kpis/benchmarks.db`

Tables:
- `executions`: Primary execution log
- `kpi_measurements`: KPI values per run
- `llm_calls`: Detailed LLM usage
- `messages`: Agent communication log
- `failures`: Failure tracking

**JSON Export**: For visualization and analysis

---

## Usage in Thesis

**Methodology Section**:
- Reference this framework as the evaluation protocol
- Explain S.M.A.R.T. criteria and KPI selection rationale

**Results Section**:
- Present aggregate KPI tables
- Include all 7 visualizations
- Discuss statistical significance

**Discussion Section**:
- Analyze KPI trends across architectures
- Identify trade-offs (e.g., MTTS vs POS)
- Recommend improvements for MMS phase

---

**Prepared by**: H-LLM-P Project Team
**Approval**: Thesis Professor Supervisor
**Version**: 1.0 - Baseline Benchmarking Phase
