"""
Multi-Agent HTN Planning System

This module implements a progressive multi-agent architecture for HTN planning.

Phase 4A - Core 3 Agents:
- DecompositionAgent: Breaks down tasks into HTN methods (LLM-heavy)
- ExecutionAgent: Executes plans with symbolic validation (Hybrid)
- VerificationAgent: Verifies plan correctness (LLM-medium)

Phase 4B - Extended 6 Agents (if time permits):
- PlanningAgent: High-level strategic planning
- ContextAgent: State tracking and context management
- CoordinationAgent: Agent orchestration

Phase 4C - Full 8 Agents (stretch goal):
- MemoryAgent: Advanced RAG with error learning
- OptimizationAgent: Plan optimization and refinement

Author: H-LLM-P Project
Phase: 4A - Multi-Agent Core
"""

from .base_agent import BaseAgent
from .message_bus import MessageBus, Message, MessageType, MessagePriority
from .agent_state_manager import AgentStateManager
from .coordinator import AgentCoordinator

__all__ = [
    'BaseAgent',
    'MessageBus',
    'Message',
    'MessageType',
    'MessagePriority',
    'AgentStateManager',
    'AgentCoordinator',
]
