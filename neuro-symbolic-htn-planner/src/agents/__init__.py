"""
Multi-Agent HTN Planning System

This module implements a progressive multi-agent architecture for HTN planning.

Phase 4A - Core 3 Agents (✅ COMPLETE):
- DecompositionAgent: Breaks down tasks into HTN methods (LLM-heavy)
- ExecutionAgent: Executes plans with symbolic validation (Hybrid)
- VerificationAgent: Verifies plan correctness (LLM-medium)

Phase 4B - Extended 5 Agents (✅ COMPLETE):
- PlanningAgent: High-level strategic planning with Groq Llama 70B
- ContextAgent: State tracking and context management (Hybrid)
- Extended workflow with feedback loops

Phase 4C - Full 6+ Agents (Future):
- CoordinationAgent: Agent orchestration
- MemoryAgent: Advanced RAG with error learning
- OptimizationAgent: Plan optimization and refinement

Author: H-LLM-P Project
Phase: 4B - Extended Multi-Agent System
"""

from .base_agent import BaseAgent
from .message_bus import MessageBus, Message, MessageType, MessagePriority
from .agent_state_manager import AgentStateManager
from .coordinator import AgentCoordinator

# Phase 4A - Core Agents
from .decomposition_agent import DecompositionAgent
from .execution_agent import ExecutionAgent
from .verification_agent import VerificationAgent

# Phase 4B - Extended Agents
from .planning_agent import PlanningAgent
from .context_agent import ContextAgent

# Workflows
from .workflows.core_workflow import CoreWorkflow
from .workflows.extended_workflow import ExtendedWorkflow

__all__ = [
    # Infrastructure
    'BaseAgent',
    'MessageBus',
    'Message',
    'MessageType',
    'MessagePriority',
    'AgentStateManager',
    'AgentCoordinator',
    # Phase 4A - Core Agents
    'DecompositionAgent',
    'ExecutionAgent',
    'VerificationAgent',
    # Phase 4B - Extended Agents
    'PlanningAgent',
    'ContextAgent',
    # Workflows
    'CoreWorkflow',
    'ExtendedWorkflow',
]
