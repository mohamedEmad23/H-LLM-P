"""
Tests for Base Agent Framework

Tests for BaseAgent, MessageBus, AgentStateManager, and AgentCoordinator.

Author: H-LLM-P Project
Phase: 4A - Multi-Agent Core
"""

import pytest
import asyncio
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agents.base_agent import BaseAgent
from agents.message_bus import MessageBus, Message, MessageType, MessagePriority
from agents.agent_state_manager import AgentStateManager
from agents.coordinator import AgentCoordinator
from core.state_manager import State


# Test Agent Implementation
class TestAgent(BaseAgent):
    """Simple test agent for framework testing"""
    
    async def process(self, input_data):
        """Echo back the input"""
        return {
            "echo": input_data,
            "agent": self.name,
            "processed_at": datetime.now().isoformat()
        }


class TestAgentWithDelay(BaseAgent):
    """Test agent with processing delay"""
    
    async def process(self, input_data):
        """Process with delay"""
        delay = input_data.get("delay", 0.1)
        await asyncio.sleep(delay)
        return {
            "delayed": True,
            "delay_seconds": delay,
            "agent": self.name
        }


# MessageBus Tests
@pytest.mark.asyncio
async def test_message_bus_publish_subscribe():
    """Test basic publish-subscribe"""
    bus = MessageBus()
    await bus.start()
    
    received_messages = []
    
    async def callback(message):
        received_messages.append(message)
    
    bus.subscribe("test_topic", callback)
    
    # Publish a message
    msg = Message(
        sender="test_sender",
        receiver="test_receiver",
        payload={"data": "test"}
    )
    
    await bus.publish("test_topic", msg)
    
    # Wait for processing
    await asyncio.sleep(0.5)
    
    assert len(received_messages) == 1
    assert received_messages[0].payload["data"] == "test"
    
    await bus.stop()


@pytest.mark.asyncio
async def test_message_bus_request_response():
    """Test request-response pattern"""
    bus = MessageBus()
    await bus.start()
    
    # Responder callback
    async def responder(message):
        if message.type == MessageType.REQUEST:
            await bus.respond(message, {"response": "got it"})
    
    bus.subscribe("request_topic", responder)
    
    # Send request
    request_msg = Message(
        sender="requester",
        receiver="responder",
        payload={"data": "test"}
    )
    
    response = await bus.request_response("request_topic", request_msg, timeout=5.0)
    
    assert response.payload["response"] == "got it"
    
    await bus.stop()


@pytest.mark.asyncio
async def test_message_bus_priority_ordering():
    """Test that urgent messages are processed first"""
    bus = MessageBus()
    await bus.start()
    
    received_order = []
    
    async def callback(message):
        received_order.append(message.payload["priority"])
    
    bus.subscribe("priority_test", callback)
    
    # Publish low priority first
    low_msg = Message(
        sender="test",
        priority=MessagePriority.LOW,
        payload={"priority": "low"}
    )
    await bus.publish("priority_test", low_msg)
    
    # Then urgent
    urgent_msg = Message(
        sender="test",
        priority=MessagePriority.URGENT,
        payload={"priority": "urgent"}
    )
    await bus.publish("priority_test", urgent_msg)
    
    # Then normal
    normal_msg = Message(
        sender="test",
        priority=MessagePriority.NORMAL,
        payload={"priority": "normal"}
    )
    await bus.publish("priority_test", normal_msg)
    
    # Wait for processing
    await asyncio.sleep(1.0)
    
    # Urgent should be processed first
    assert received_order[0] == "urgent"
    
    await bus.stop()


# AgentStateManager Tests
def test_state_manager_create_session():
    """Test session creation"""
    manager = AgentStateManager()
    
    initial = State(predicates={"at(robot, home)", "battery(100)"})
    goal = State(predicates={"at(robot, office)", "package_delivered"})
    
    session_id = "test_session"
    session = manager.create_session(session_id, initial, goal)
    
    assert session.session_id == session_id
    assert session.initial_state.predicates == initial.predicates
    assert session.goal_state.predicates == goal.predicates
    assert session.current_state.predicates == initial.predicates


def test_state_manager_state_transitions():
    """Test state transition tracking"""
    manager = AgentStateManager()
    
    initial = State(predicates={"at(robot, home)"})
    goal = State(predicates={"at(robot, office)"})
    
    session_id = "test_session"
    manager.create_session(session_id, initial, goal)
    
    # Update state
    new_state = State(predicates={"at(robot, hallway)"})
    manager.update_state(session_id, "move(home, hallway)", new_state)
    
    session = manager.get_session(session_id)
    assert len(session.state_history) == 1
    assert session.current_state.predicates == new_state.predicates


def test_state_manager_goal_achievement():
    """Test goal achievement checking"""
    manager = AgentStateManager()
    
    initial = State(predicates={"at(robot, home)"})
    goal = State(predicates={"at(robot, office)"})
    
    session_id = "test_session"
    manager.create_session(session_id, initial, goal)
    
    # Goal not achieved yet
    assert not manager.check_goal_achieved(session_id)
    
    # Update to goal state
    goal_state = State(predicates={"at(robot, office)", "done"})
    manager.update_state(session_id, "move_to_office", goal_state)
    
    # Goal achieved
    assert manager.check_goal_achieved(session_id)


def test_state_manager_progress():
    """Test progress tracking"""
    manager = AgentStateManager()
    
    initial = State(predicates={"at(robot, home)"})
    goal = State(predicates={"at(robot, office)", "package_delivered", "battery_charged"})
    
    session_id = "test_session"
    manager.create_session(session_id, initial, goal)
    
    # Partial progress
    partial_state = State(predicates={"at(robot, office)", "battery_charged"})
    manager.update_state(session_id, "progress", partial_state)
    
    progress = manager.get_progress(session_id)
    
    assert progress["goal_predicates_total"] == 3
    assert progress["goal_predicates_achieved"] == 2
    assert progress["goal_predicates_remaining"] == 1
    assert progress["progress_percentage"] == pytest.approx(66.67, rel=1)


# BaseAgent Tests
@pytest.mark.asyncio
async def test_base_agent_creation():
    """Test agent creation"""
    agent = TestAgent(name="test_agent", config={"test": "config"})
    
    assert agent.name == "test_agent"
    assert agent.config["test"] == "config"
    assert agent.stats["messages_sent"] == 0


@pytest.mark.asyncio
async def test_base_agent_message_handling():
    """Test agent message handling"""
    bus = MessageBus()
    await bus.start()
    
    agent = TestAgent(name="test_agent")
    agent.set_message_bus(bus)
    
    # Send request to agent
    request_msg = Message(
        sender="client",
        receiver="test_agent",
        type=MessageType.REQUEST,
        payload={"data": "test"}
    )
    
    response = await bus.request_response("test_agent", request_msg, timeout=5.0)
    
    assert response.payload["success"]
    assert response.payload["result"]["echo"]["data"] == "test"
    
    await bus.stop()


@pytest.mark.asyncio
async def test_base_agent_send_message():
    """Test agent sending messages"""
    bus = MessageBus()
    await bus.start()
    
    agent1 = TestAgent(name="agent1")
    agent2 = TestAgent(name="agent2")
    
    agent1.set_message_bus(bus)
    agent2.set_message_bus(bus)
    
    # Agent1 sends message to Agent2
    await agent1.send_message("agent2", {"greeting": "hello"})
    
    # Wait for processing
    await asyncio.sleep(0.5)
    
    assert agent1.stats["messages_sent"] == 1
    
    await bus.stop()


# AgentCoordinator Tests
@pytest.mark.asyncio
async def test_coordinator_register_agent():
    """Test agent registration"""
    coordinator = AgentCoordinator()
    await coordinator.start()
    
    agent = TestAgent(name="test_agent")
    coordinator.register_agent(agent)
    
    assert "test_agent" in coordinator.agents
    assert agent.message_bus is not None
    assert agent.state_manager is not None
    
    await coordinator.stop()


@pytest.mark.asyncio
async def test_coordinator_create_session():
    """Test session creation via coordinator"""
    coordinator = AgentCoordinator()
    await coordinator.start()
    
    initial = State(predicates={"at(robot, home)"})
    goal = State(predicates={"at(robot, office)"})
    
    session_id = coordinator.create_session(initial, goal)
    
    assert session_id is not None
    session = coordinator.state_manager.get_session(session_id)
    assert session is not None
    
    await coordinator.stop()


@pytest.mark.asyncio
async def test_coordinator_context_manager():
    """Test coordinator as async context manager"""
    async with AgentCoordinator() as coordinator:
        assert coordinator._running
        
        agent = TestAgent(name="test_agent")
        coordinator.register_agent(agent)
        
        assert "test_agent" in coordinator.agents
    
    # Should be stopped after context exit
    assert not coordinator._running


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
