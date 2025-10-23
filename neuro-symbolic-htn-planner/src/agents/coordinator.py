"""
Agent Coordinator

Orchestrates multi-agent HTN planning workflow.
Manages agent lifecycle, coordinates communication, and handles errors.

Author: H-LLM-P Project  
Phase: 4A - Multi-Agent Core
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent
from .message_bus import MessageBus, Message, MessageType, MessagePriority
from .agent_state_manager import AgentStateManager, SessionState
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.state_manager import State


class AgentCoordinator:
    """
    Coordinates multi-agent HTN planning workflow.
    
    Responsibilities:
    - Manage agent lifecycle
    - Coordinate agent communication
    - Handle workflow execution
    - Error handling and retries
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize the coordinator"""
        self.agents: Dict[str, BaseAgent] = {}
        self.message_bus = MessageBus()
        self.state_manager = AgentStateManager()
        self._running = False
        
        logger.info("AgentCoordinator initialized")
    
    async def start(self):
        """Start the coordinator and message bus"""
        if self._running:
            logger.warning("Coordinator already running")
            return
        
        await self.message_bus.start()
        self._running = True
        
        logger.success("AgentCoordinator started")
    
    async def stop(self):
        """Stop the coordinator and message bus"""
        if not self._running:
            return
        
        await self.message_bus.stop()
        self._running = False
        
        logger.info("AgentCoordinator stopped")
    
    def register_agent(self, agent: BaseAgent):
        """
        Register an agent with the coordinator.
        
        Args:
            agent: Agent to register
            
        Raises:
            ValueError: If agent name already registered
        """
        if agent.name in self.agents:
            raise ValueError(f"Agent '{agent.name}' already registered")
        
        # Inject dependencies
        agent.set_message_bus(self.message_bus)
        agent.set_state_manager(self.state_manager)
        
        self.agents[agent.name] = agent
        
        logger.success(f"Registered agent: {agent.name}")
    
    def unregister_agent(self, agent_name: str):
        """
        Unregister an agent.
        
        Args:
            agent_name: Name of agent to unregister
        """
        if agent_name in self.agents:
            del self.agents[agent_name]
            logger.info(f"Unregistered agent: {agent_name}")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.
        
        Args:
            agent_name: Agent name
            
        Returns:
            Agent instance or None
        """
        return self.agents.get(agent_name)
    
    def create_session(
        self,
        initial_state: State,
        goal_state: State,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new planning session.
        
        Args:
            initial_state: Starting world state
            goal_state: Desired goal state
            session_id: Optional session ID (generates one if None)
            metadata: Optional session metadata
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.state_manager.create_session(
            session_id=session_id,
            initial_state=initial_state,
            goal_state=goal_state,
            metadata=metadata
        )
        
        logger.success(f"Created planning session: {session_id}")
        return session_id
    
    async def execute_workflow(
        self,
        workflow_type: str,
        session_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a multi-agent workflow.
        
        Args:
            workflow_type: Type of workflow ('sequential', 'parallel', 'loop')
            session_id: Session ID for this workflow
            task_data: Task-specific data
            
        Returns:
            Workflow result
        """
        if workflow_type == "sequential":
            return await self._execute_sequential_workflow(session_id, task_data)
        elif workflow_type == "parallel":
            return await self._execute_parallel_workflow(session_id, task_data)
        elif workflow_type == "loop":
            return await self._execute_loop_workflow(session_id, task_data)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
    
    async def _execute_sequential_workflow(
        self,
        session_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute sequential workflow: Decomposition → Execution → Verification
        
        Args:
            session_id: Session ID
            task_data: Task data
            
        Returns:
            Workflow result
        """
        logger.info(f"Starting sequential workflow for session {session_id}")
        start_time = datetime.now()
        
        result = {
            "session_id": session_id,
            "workflow_type": "sequential",
            "success": False,
            "steps": []
        }
        
        try:
            # Step 1: Decomposition
            decomp_agent = self.get_agent("DecompositionAgent")
            if not decomp_agent:
                raise RuntimeError("DecompositionAgent not found")
            
            logger.info("Step 1: Decomposition")
            decomp_result = await decomp_agent.request(
                receiver="DecompositionAgent",
                payload={
                    "task": task_data.get("task"),
                    "domain": task_data.get("domain"),
                    "session_id": session_id,
                    "context": self.state_manager.get_context(session_id)
                },
                timeout=60.0
            )
            
            result["steps"].append({
                "agent": "DecompositionAgent",
                "result": decomp_result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Step 2: Execution
            exec_agent = self.get_agent("ExecutionAgent")
            if not exec_agent:
                raise RuntimeError("ExecutionAgent not found")
            
            logger.info("Step 2: Execution")
            exec_result = await exec_agent.request(
                receiver="ExecutionAgent",
                payload={
                    "plan": decomp_result.get("plan"),
                    "session_id": session_id,
                    "initial_state": self.state_manager.get_current_state(session_id)
                },
                timeout=120.0
            )
            
            result["steps"].append({
                "agent": "ExecutionAgent",
                "result": exec_result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Step 3: Verification
            verify_agent = self.get_agent("VerificationAgent")
            if not verify_agent:
                raise RuntimeError("VerificationAgent not found")
            
            logger.info("Step 3: Verification")
            verify_result = await verify_agent.request(
                receiver="VerificationAgent",
                payload={
                    "plan": decomp_result.get("plan"),
                    "execution_trace": exec_result.get("trace"),
                    "session_id": session_id,
                    "goal": self.state_manager.get_goal_state(session_id)
                },
                timeout=60.0
            )
            
            result["steps"].append({
                "agent": "VerificationAgent",
                "result": verify_result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Check if successful
            result["success"] = verify_result.get("goal_achieved", False)
            result["verification"] = verify_result
            
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            result["error"] = str(e)
        
        finally:
            execution_time = (datetime.now() - start_time).total_seconds()
            result["execution_time_seconds"] = execution_time
            
            logger.info(
                f"Sequential workflow completed in {execution_time:.2f}s "
                f"(success: {result['success']})"
            )
        
        return result
    
    async def _execute_parallel_workflow(
        self,
        session_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute parallel workflow (Phase 4B+).
        
        Args:
            session_id: Session ID
            task_data: Task data
            
        Returns:
            Workflow result
        """
        # TODO: Implement in Phase 4B
        logger.warning("Parallel workflow not yet implemented (Phase 4B)")
        return {
            "session_id": session_id,
            "workflow_type": "parallel",
            "success": False,
            "error": "Not implemented yet"
        }
    
    async def _execute_loop_workflow(
        self,
        session_id: str,
        task_data: Dict[str, Any],
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Execute loop workflow with retry on failure.
        
        Args:
            session_id: Session ID
            task_data: Task data
            max_iterations: Maximum retry iterations
            
        Returns:
            Workflow result
        """
        logger.info(f"Starting loop workflow for session {session_id} (max {max_iterations} iterations)")
        
        for iteration in range(max_iterations):
            logger.info(f"Loop iteration {iteration + 1}/{max_iterations}")
            
            result = await self._execute_sequential_workflow(session_id, task_data)
            
            if result["success"]:
                result["iterations"] = iteration + 1
                logger.success(f"Loop workflow succeeded on iteration {iteration + 1}")
                return result
            
            logger.warning(f"Iteration {iteration + 1} failed, retrying...")
        
        logger.error(f"Loop workflow failed after {max_iterations} iterations")
        result["iterations"] = max_iterations
        return result
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session statistics
        """
        session = self.state_manager.get_session(session_id)
        if not session:
            return {}
        
        return {
            "session_id": session_id,
            "progress": self.state_manager.get_progress(session_id),
            "state_transitions": len(session.state_history),
            "plan_steps": len(session.plan_trace),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "metadata": session.metadata
        }
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics for all agents"""
        return {
            agent_name: agent.get_stats()
            for agent_name, agent in self.agents.items()
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        return {
            "coordinator": {
                "running": self._running,
                "registered_agents": len(self.agents),
                "agent_names": list(self.agents.keys())
            },
            "message_bus": self.message_bus.get_stats(),
            "state_manager": {
                "total_sessions": len(self.state_manager.sessions),
                "active_session": self.state_manager.active_session
            },
            "agents": self.get_agent_stats()
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
