"""Quick framework validation"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

print("Testing imports...")

try:
    from agents.message_bus import MessageBus, Message
    print("✓ MessageBus imported")
except Exception as e:
    print(f"✗ MessageBus import failed: {e}")

try:
    from agents.agent_state_manager import AgentStateManager
    print("✓ AgentStateManager imported")
except Exception as e:
    print(f"✗ AgentStateManager import failed: {e}")

try:
    from agents.base_agent import BaseAgent
    print("✓ BaseAgent imported")
except Exception as e:
    print(f"✗ BaseAgent import failed: {e}")

try:
    from agents.coordinator import AgentCoordinator
    print("✓ AgentCoordinator imported")
except Exception as e:
    print(f"✗ AgentCoordinator import failed: {e}")

print("\nAll imports successful!")
