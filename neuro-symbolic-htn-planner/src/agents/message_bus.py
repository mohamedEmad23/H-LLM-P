"""
Message Bus for Inter-Agent Communication

Implements async publish-subscribe pattern for agent communication.
Supports request-response, event broadcasting, and message queuing.

Author: H-LLM-P Project
Phase: 4A - Multi-Agent Core
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from loguru import logger


class MessageType(Enum):
    """Types of messages that can be sent between agents"""

    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"
    COMMAND = "command"


class MessagePriority(Enum):
    """Message priority levels for queue processing"""

    URGENT = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Message:
    """
    Standard message format for inter-agent communication.

    Attributes:
        message_id: Unique identifier for this message
        timestamp: When the message was created
        sender: Name of the sending agent
        receiver: Name of the receiving agent (None for broadcast)
        type: Type of message (request, response, event, error)
        priority: Message priority (urgent, normal, low)
        payload: The actual message content
        response_topic: Optional topic for response messages
        correlation_id: Optional ID linking request/response
        metadata: Additional metadata (session_id, task_id, retry_count)
    """

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    sender: str = ""
    receiver: Optional[str] = None
    type: MessageType = MessageType.EVENT
    priority: MessagePriority = MessagePriority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    response_topic: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "sender": self.sender,
            "receiver": self.receiver,
            "type": self.type.value,
            "priority": self.priority.value,
            "payload": self.payload,
            "response_topic": self.response_topic,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary"""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(),
            sender=data.get("sender", ""),
            receiver=data.get("receiver"),
            type=MessageType(data.get("type", "event")),
            priority=MessagePriority(data.get("priority", 2)),
            payload=data.get("payload", {}),
            response_topic=data.get("response_topic"),
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata", {}),
        )


class MessageBus:
    """
    Async message bus for agent communication.

    Supports:
    - Publish-subscribe pattern
    - Request-response with timeout
    - Event broadcasting
    - Message queuing with priorities
    - Message logging for analysis
    """

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize message bus.

        Args:
            max_queue_size: Maximum number of messages in queue
        """
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )
        self.message_log: List[Message] = []
        self.response_futures: Dict[str, asyncio.Future] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

        logger.info("MessageBus initialized")

    async def start(self):
        """Start the message bus worker"""
        if self._running:
            logger.warning("MessageBus already running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.success("MessageBus started")

    async def stop(self):
        """Stop the message bus worker"""
        if not self._running:
            return

        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("MessageBus stopped")

    def subscribe(self, topic: str, callback: Callable):
        """
        Subscribe to a topic.

        Args:
            topic: Topic name to subscribe to
            callback: Async function to call when message is published
        """
        self.subscribers[topic].append(callback)
        logger.debug(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str, callback: Callable):
        """
        Unsubscribe from a topic.

        Args:
            topic: Topic name to unsubscribe from
            callback: Callback function to remove
        """
        if topic in self.subscribers and callback in self.subscribers[topic]:
            self.subscribers[topic].remove(callback)
            logger.debug(f"Unsubscribed from topic: {topic}")

    async def publish(self, topic: str, message: Message):
        """
        Publish a message to a topic.

        Args:
            topic: Topic to publish to
            message: Message to publish
        """
        # Log message
        self.message_log.append(message)

        # Add to priority queue
        priority = message.priority.value
        await self.message_queue.put((priority, message.timestamp, topic, message))

        logger.debug(
            f"Published message {message.message_id} to topic '{topic}' "
            f"(type: {message.type.value}, priority: {message.priority.value})"
        )

    async def _process_queue(self):
        """Process messages from the queue"""
        while self._running:
            try:
                # Get message from queue (blocks until message available)
                priority, timestamp, topic, message = await asyncio.wait_for(
                    self.message_queue.get(), timeout=1.0
                )

                # Deliver to subscribers
                await self._deliver_message(topic, message)

                self.message_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")

    async def _deliver_message(self, topic: str, message: Message):
        """
        Deliver message to all subscribers of a topic.

        Args:
            topic: Topic to deliver to
            message: Message to deliver
        """
        if topic not in self.subscribers:
            logger.debug(f"No subscribers for topic: {topic}")
            return

        # Call all subscriber callbacks
        tasks = []
        for callback in self.subscribers[topic]:
            tasks.append(asyncio.create_task(callback(message)))

        # Wait for all callbacks to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Error in subscriber callback for topic '{topic}': {result}"
                    )

    async def request_response(
        self, topic: str, message: Message, timeout: float = 30.0
    ) -> Message:
        """
        Send a request and wait for a response.

        Args:
            topic: Topic to send request to
            message: Request message
            timeout: Timeout in seconds

        Returns:
            Response message

        Raises:
            asyncio.TimeoutError: If no response received within timeout
        """
        # Create response topic
        response_topic = f"{topic}_response_{message.message_id}"
        message.response_topic = response_topic
        message.type = MessageType.REQUEST

        # Create future for response
        response_future = asyncio.Future()
        self.response_futures[response_topic] = response_future

        # Subscribe to response topic
        async def response_handler(response_msg: Message):
            if not response_future.done():
                response_future.set_result(response_msg)

        self.subscribe(response_topic, response_handler)

        # Publish request
        await self.publish(topic, message)

        try:
            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        finally:
            # Cleanup
            self.unsubscribe(response_topic, response_handler)
            if response_topic in self.response_futures:
                del self.response_futures[response_topic]

    async def respond(
        self, original_message: Message, response_payload: Dict[str, Any]
    ):
        """
        Send a response to a request message.

        Args:
            original_message: The original request message
            response_payload: Payload for the response
        """
        if not original_message.response_topic:
            logger.warning(
                f"Cannot respond: no response_topic in message {original_message.message_id}"
            )
            return

        response = Message(
            sender=original_message.receiver or "unknown",
            receiver=original_message.sender,
            type=MessageType.RESPONSE,
            priority=original_message.priority,
            payload=response_payload,
            correlation_id=original_message.message_id,
            metadata=original_message.metadata,
        )

        await self.publish(original_message.response_topic, response)

    def get_message_log(
        self,
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        Get filtered message log.

        Args:
            sender: Filter by sender
            receiver: Filter by receiver
            message_type: Filter by message type
            limit: Maximum number of messages to return

        Returns:
            List of filtered messages
        """
        filtered = self.message_log

        if sender:
            filtered = [m for m in filtered if m.sender == sender]
        if receiver:
            filtered = [m for m in filtered if m.receiver == receiver]
        if message_type:
            filtered = [m for m in filtered if m.type == message_type]

        if limit:
            filtered = filtered[-limit:]

        return filtered

    def clear_message_log(self):
        """Clear the message log"""
        self.message_log.clear()
        logger.info("Message log cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        return {
            "total_messages": len(self.message_log),
            "queue_size": self.message_queue.qsize(),
            "subscribers": {
                topic: len(callbacks) for topic, callbacks in self.subscribers.items()
            },
            "running": self._running,
            "pending_responses": len(self.response_futures),
        }
