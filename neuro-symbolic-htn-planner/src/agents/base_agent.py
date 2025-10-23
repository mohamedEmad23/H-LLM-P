"""
Base Agent Class

Abstract base class for all agents in the multi-agent HTN system.
Provides core functionality for communication, state access, and logging.

Author: H-LLM-P Project
Phase: 4A - Multi-Agent Core
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from loguru import logger

from .message_bus import MessageBus, Message, MessageType, MessagePriority
from .agent_state_manager import AgentStateManager


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Provides:
    - Message bus communication
    - State manager access
    - Memory system access (Phase 5+)
    - Interaction logging
    - Error handling
    
    All agents must implement the `process` method.
    """
    
    def __init__(
        self,
        name: str,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base agent.
        
        Args:
            name: Agent name (must be unique)
            llm_client: LLM client for this agent (optional for rule-based agents)
            config: Agent-specific configuration
        """
        self.name = name
        self.llm_client = llm_client
        self.config = config or {}
        
        # Will be injected by coordinator
        self.message_bus: Optional[MessageBus] = None
        self.state_manager: Optional[AgentStateManager] = None
        self.memory = None  # Phase 5+
        
        # Interaction logging
        self.interaction_log: list = []
        
        # Agent statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "tasks_processed": 0,
            "errors": 0,
            "total_processing_time_ms": 0
        }
        
        logger.info(f"Agent '{name}' initialized")
    
    def set_message_bus(self, message_bus: MessageBus):
        """
        Inject message bus dependency.
        
        Args:
            message_bus: MessageBus instance
        """
        self.message_bus = message_bus
        # Subscribe to agent's topic
        self.message_bus.subscribe(self.name, self._handle_message)
        logger.debug(f"Agent '{self.name}' connected to message bus")
    
    def set_state_manager(self, state_manager: AgentStateManager):
        """
        Inject state manager dependency.
        
        Args:
            state_manager: AgentStateManager instance
        """
        self.state_manager = state_manager
        logger.debug(f"Agent '{self.name}' connected to state manager")
    
    async def _handle_message(self, message: Message):
        """
        Internal message handler (called by message bus).
        
        Args:
            message: Incoming message
        """
        self.stats["messages_received"] += 1
        
        logger.debug(
            f"Agent '{self.name}' received message {message.message_id} "
            f"from '{message.sender}' (type: {message.type.value})"
        )
        
        try:
            # Process based on message type
            if message.type == MessageType.REQUEST:
                await self._handle_request(message)
            elif message.type == MessageType.COMMAND:
                await self._handle_command(message)
            elif message.type == MessageType.EVENT:
                await self._handle_event(message)
            else:
                logger.warning(
                    f"Agent '{self.name}' received unexpected message type: {message.type}"
                )
        
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Agent '{self.name}' error handling message: {e}")
            
            # Send error response if it was a request
            if message.type == MessageType.REQUEST and message.response_topic:
                await self.message_bus.respond(message, {
                    "success": False,
                    "error": str(e),
                    "agent": self.name
                })
    
    async def _handle_request(self, message: Message):
        """
        Handle request messages.
        
        Args:
            message: Request message
        """
        start_time = datetime.now()
        
        try:
            # Process the request
            result = await self.process(message.payload)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.stats["total_processing_time_ms"] += processing_time
            self.stats["tasks_processed"] += 1
            
            # Log interaction
            self.log_interaction({
                "message_id": message.message_id,
                "type": "request",
                "sender": message.sender,
                "payload": message.payload,
                "result": result,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send response
            if message.response_topic:
                await self.message_bus.respond(message, {
                    "success": True,
                    "result": result,
                    "agent": self.name,
                    "processing_time_ms": processing_time
                })
        
        except Exception as e:
            logger.error(f"Agent '{self.name}' error processing request: {e}")
            
            if message.response_topic:
                await self.message_bus.respond(message, {
                    "success": False,
                    "error": str(e),
                    "agent": self.name
                })
    
    async def _handle_command(self, message: Message):
        """
        Handle command messages.
        
        Args:
            message: Command message
        """
        # Commands don't require responses
        await self.process(message.payload)
    
    async def _handle_event(self, message: Message):
        """
        Handle event messages.
        
        Args:
            message: Event message
        """
        # Events are notifications, agents can choose to act on them
        await self.on_event(message)
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method - must be implemented by subclasses.
        
        Args:
            input_data: Input data for processing
            
        Returns:
            Processing result
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(f"Agent '{self.name}' must implement process method")
    
    async def on_event(self, message: Message):
        """
        Handle event messages (can be overridden by subclasses).
        
        Args:
            message: Event message
        """
        # Default: log and ignore
        logger.debug(f"Agent '{self.name}' received event: {message.payload.get('event_type')}")
    
    async def send_message(
        self,
        receiver: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.EVENT,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Send a message to another agent.
        
        Args:
            receiver: Name of receiving agent
            payload: Message payload
            message_type: Type of message
            priority: Message priority
            metadata: Optional metadata
        """
        if not self.message_bus:
            logger.error(f"Agent '{self.name}' has no message bus connection")
            return
        
        message = Message(
            sender=self.name,
            receiver=receiver,
            type=message_type,
            priority=priority,
            payload=payload,
            metadata=metadata or {}
        )
        
        await self.message_bus.publish(receiver, message)
        self.stats["messages_sent"] += 1
        
        logger.debug(f"Agent '{self.name}' sent message to '{receiver}'")
    
    async def request(
        self,
        receiver: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Dict[str, Any]:
        """
        Send a request and wait for response.
        
        Args:
            receiver: Name of receiving agent
            payload: Request payload
            timeout: Timeout in seconds
            priority: Message priority
            
        Returns:
            Response payload
            
        Raises:
            TimeoutError: If no response within timeout
            RuntimeError: If response indicates error
        """
        if not self.message_bus:
            raise RuntimeError(f"Agent '{self.name}' has no message bus connection")
        
        message = Message(
            sender=self.name,
            receiver=receiver,
            type=MessageType.REQUEST,
            priority=priority,
            payload=payload
        )
        
        response = await self.message_bus.request_response(receiver, message, timeout)
        self.stats["messages_sent"] += 1
        
        if not response.payload.get("success", False):
            error = response.payload.get("error", "Unknown error")
            raise RuntimeError(f"Request to '{receiver}' failed: {error}")
        
        return response.payload.get("result", {})
    
    async def broadcast_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL
    ):
        """
        Broadcast an event to all subscribers.
        
        Args:
            event_type: Type of event
            event_data: Event data
            priority: Message priority
        """
        if not self.message_bus:
            logger.error(f"Agent '{self.name}' has no message bus connection")
            return
        
        message = Message(
            sender=self.name,
            type=MessageType.EVENT,
            priority=priority,
            payload={
                "event_type": event_type,
                "event_data": event_data
            }
        )
        
        # Broadcast to 'events' topic
        await self.message_bus.publish("events", message)
        self.stats["messages_sent"] += 1
    
    def get_current_state(self, session_id: Optional[str] = None):
        """
        Get current world state.
        
        Args:
            session_id: Session ID (uses active session if None)
            
        Returns:
            Current state or None
        """
        if not self.state_manager:
            logger.error(f"Agent '{self.name}' has no state manager connection")
            return None
        
        return self.state_manager.get_current_state(session_id)
    
    def get_goal_state(self, session_id: Optional[str] = None):
        """
        Get goal state.
        
        Args:
            session_id: Session ID (uses active session if None)
            
        Returns:
            Goal state or None
        """
        if not self.state_manager:
            logger.error(f"Agent '{self.name}' has no state manager connection")
            return None
        
        return self.state_manager.get_goal_state(session_id)
    
    def get_context(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete session context.
        
        Args:
            session_id: Session ID (uses active session if None)
            
        Returns:
            Session context
        """
        if not self.state_manager:
            logger.error(f"Agent '{self.name}' has no state manager connection")
            return {}
        
        return self.state_manager.get_context(session_id)
    
    def log_interaction(self, interaction: Dict[str, Any]):
        """
        Log an interaction for later analysis.
        
        Args:
            interaction: Interaction data
        """
        self.interaction_log.append({
            **interaction,
            "agent": self.name,
            "logged_at": datetime.now().isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        avg_processing_time = (
            self.stats["total_processing_time_ms"] / self.stats["tasks_processed"]
            if self.stats["tasks_processed"] > 0
            else 0
        )
        
        return {
            **self.stats,
            "average_processing_time_ms": avg_processing_time,
            "interaction_log_size": len(self.interaction_log)
        }
    
    def validate_input(self, input_data: Dict[str, Any], required_fields: list) -> bool:
        """
        Validate input data structure.
        
        Args:
            input_data: Input data to validate
            required_fields: List of required field names
            
        Returns:
            True if valid, False otherwise
        """
        for field in required_fields:
            if field not in input_data:
                logger.error(f"Agent '{self.name}': Missing required field '{field}'")
                return False
        return True
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"
