1. System Overview

1.1 Vision Statement


A progressive multi-agent HTN planning system that combines symbolic reasoning with LLM-based intelligence, featuring:

Specialist agents with tailored LLM models
Two-phase memory system (minimal RAG → full memory)
Progressive scaling (3 → 6 → 8 agents)
Continuous learning from errors
Zero-cost implementation using free-tier APIs

1.2 Core Principles

Specialization Over Generalization: Each agent uses the best-suited LLM for its task
Hybrid Intelligence: Mix LLM-based (complex) and rule-based (fast) reasoning
Progressive Validation: Implement core first, scale based on results
Continuous Learning: Learn from both successes and failures
Cost Consciousness: Use small models for simple tasks, large for complex

1.3 Unique Contributions

Multi-agent HTN system with full memory (beyond existing papers)
Advanced memory system with error pattern learning
Progressive LLM integration (8 providers, specialist routing)
Continuous improvement from agent interactions
Comprehensive benchmarking at each implementation phase
1.4 Target Domains
Primary: Complex Reasoning Tasks

Tower of Hanoi: 3, 4, 5 disks (baseline → medium → complex)
Graph Traversal: Shortest path, cycle detection, maybe TSP
Backup: Software Engineering (after RAG implementation)

Focus: Pure algorithmic/planning - no robotics

## 2. Architecture Design
### 2.1 Progressive Scaling Plan

```
Phase 4A: Core 3 Agents (MUST HAVE)
├── DecompositionAgent (LLM-heavy)
├── ExecutionAgent (Hybrid)
└── VerificationAgent (LLM-medium)

Phase 4B: Extended 6 Agents (IF TIME PERMITS)
├── Core 3 Agents (above)
├── PlanningAgent (LLM-heavy)
├── ContextAgent (Hybrid)
└── CoordinationAgent (LLM-light)

Phase 4C: Full 8 Agents (STRETCH GOAL)
├── Extended 6 Agents (above)
├── MemoryAgent (Hybrid + Vector DB)
└── OptimizationAgent (LLM-medium)
```

### 2.2 System Architecture Diagram

```mermaid
┌─────────────────────────────────────────────────────────────┐
│                    Agent Coordinator                         │
│  (Orchestration, Routing, Session Management)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Message Bus                             │
│  (Async communication, Event broadcasting)                   │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Decomposition│  │  Execution   │  │ Verification │
│    Agent     │  │    Agent     │  │    Agent     │
│              │  │              │  │              │
│ Llama 70B    │  │ Qwen 7B +    │  │ Llama 8B     │
│ (HF)         │  │ Rules        │  │ (HF)         │
└──────────────┘  └──────────────┘  └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                  ┌──────────────────┐
                  │   State Manager   │
                  │ (World state,     │
                  │  Plan tracking)   │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Memory System   │
                  │ (RAG, Error DB,  │
                  │  Plan Cache)     │
                  └──────────────────┘
```

### 2.3 Agent Interaction Patterns

Pattern 1: Sequential (Core Flow)

User Request → Decomposition → Execution → Verification → Result


**Pattern 2: Loop (Refinement)**

```Markdown
Decomposition → Execution → Verification
                     ↑              │
                     └──── Retry ───┘
                    (if validation fails)
```

**Pattern 3: Parallel (Extended)**

```Markdown
User Request → Planning Agent ──┐
               Context Agent  ──┼→ Coordination → Core Agents
               Memory Agent   ──┘
```

**Key Components**

1. LLM Client Integration: Each agent gets its specialist model
2. Message Bus Connection: For inter-agent communication
3. State Manager Access: Read/write world state
4. Memory System Access: Query past plans, errors
5. Logging: Comprehensive interaction logs

```JSON
TIER_1_PROVIDERS = {
    "llama-70b-hf": {
        "provider": "huggingface",
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "latency": "1.5s",
        "quality": "⭐⭐⭐⭐⭐",
        "use_for": ["complex_reasoning", "strategic_planning"]
    },
    "qwen-7b-hf": {
        "provider": "huggingface",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "latency": "1.9s",
        "quality": "⭐⭐⭐⭐",
        "use_for": ["simple_tasks", "validation", "coordination"]
    }
}
```

```JSON
TIER_2_PROVIDERS = {
    "llama-8b-hf": {
        "provider": "huggingface",
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "latency": "3.7s",
        "quality": "⭐⭐⭐⭐",
        "use_for": ["detailed_analysis", "verification"]
    },
    "groq-llama-70b": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "latency": "2-5s",
        "quality": "⭐⭐⭐⭐⭐",
        "use_for": ["emergency_fallback", "parallel_processing"]
    },
    "gemini-2.0": {
        "provider": "google",
        "model": "gemini-2.0-flash-exp",
        "latency": "4-6s",
        "quality": "⭐⭐⭐⭐",
        "use_for": ["balanced_tasks", "context_analysis"]
    },
    "deepseek-v3": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "latency": "7-10s",
        "quality": "⭐⭐⭐⭐",
        "use_for": ["backup", "cost_sensitive"]
    }
}
```

```JSON

TIER_3_PROVIDERS = {
    "cohere": {
        "provider": "cohere",
        "model": "command-r-plus",
        "latency": "17-38s",
        "quality": "⭐⭐⭐",
        "use_for": ["reliability_critical", "final_verification"]
    },
    "ollama-local": {
        "provider": "ollama",
        "model": "llama3.2:latest",
        "latency": "100-250s",
        "quality": "⭐⭐⭐",
        "use_for": ["offline_mode", "zero_cost_testing"]
    }
}
```

## Model Routing Logic

```PYTHON
class ModelRouter:
    """Intelligent routing of tasks to appropriate LLM models"""

    ROUTING_RULES = {
        "complexity": {
            "simple": ["qwen-7b-hf", "groq-llama-70b"],
            "medium": ["llama-8b-hf", "gemini-2.0"],
            "complex": ["llama-70b-hf", "groq-llama-70b"]
        },
        "speed_priority": {
            "urgent": ["qwen-7b-hf", "llama-70b-hf", "groq-llama-70b"],
            "normal": ["llama-8b-hf", "gemini-2.0"],
            "batch": ["deepseek-v3", "cohere"]
        },
        "quality_priority": {
            "critical": ["llama-70b-hf", "groq-llama-70b"],
            "important": ["llama-8b-hf", "gemini-2.0"],
            "standard": ["qwen-7b-hf", "deepseek-v3"]
        }
    }

    def route(self, task_type: str, complexity: str,
              priority: str) -> str:
        """Select best model for task"""
        # Implementation in Phase 4A
        pass
```
